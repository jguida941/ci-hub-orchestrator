from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import provenance_io

from .errors import DrDrillError


def _parse_iso8601(value: str) -> datetime:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - surfaced in CI
        raise DrDrillError(f"invalid ISO-8601 timestamp: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


@dataclass(frozen=True)
class BackupSpec:
    path: Path
    sha256: str
    captured_at: datetime


@dataclass(frozen=True)
class SbomSpec:
    path: Path


@dataclass(frozen=True)
class ProvenanceSpec:
    path: Path


@dataclass(frozen=True)
class RestoreSpec:
    output_dir: Path
    script: Path | None
    copy_backup: bool
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class PolicySpec:
    max_rpo_minutes: float | None
    max_rto_seconds: float | None


@dataclass(frozen=True)
class Manifest:
    source: Path
    backup: BackupSpec
    sbom: SbomSpec
    provenance: ProvenanceSpec
    restore: RestoreSpec
    policies: PolicySpec


def _normalize_sha256(value: str) -> str:
    normalized = provenance_io.normalize_digest(value)
    if not normalized:
        raise DrDrillError("backup sha256 digest missing")
    return normalized


def _load_backup(data: dict[str, Any], base: Path) -> BackupSpec:
    path = data.get("path")
    sha256 = data.get("sha256")
    captured = data.get("captured_at")
    if not path or not sha256 or not captured:
        raise DrDrillError("backup manifest must include path, sha256, and captured_at")
    backup_path = _resolve_path(base, path)
    digest = _normalize_sha256(sha256)
    captured_at = _parse_iso8601(str(captured))
    return BackupSpec(path=backup_path, sha256=digest, captured_at=captured_at)


def _load_sbom(data: dict[str, Any], base: Path) -> SbomSpec:
    path = data.get("path")
    if not path:
        raise DrDrillError("sbom manifest must include path")
    return SbomSpec(path=_resolve_path(base, path))


def _load_provenance(data: dict[str, Any], base: Path) -> ProvenanceSpec:
    path = data.get("path")
    if not path:
        raise DrDrillError("provenance manifest must include path")
    return ProvenanceSpec(path=_resolve_path(base, path))


def _load_restore(data: dict[str, Any], base: Path) -> RestoreSpec:
    output_dir = data.get("output_dir")
    if not output_dir:
        raise DrDrillError("restore manifest must include output_dir")
    script = data.get("script")
    copy_backup = bool(data.get("copy_backup", False))
    script_path = _resolve_path(base, script) if script else None
    timeout_raw = data.get("timeout_seconds")
    timeout_seconds: int | None = None
    if timeout_raw is not None:
        try:
            timeout_seconds = int(timeout_raw)
        except (TypeError, ValueError) as exc:
            raise DrDrillError(f"restore timeout_seconds must be an integer, got {timeout_raw!r}") from exc
        if timeout_seconds <= 0:
            raise DrDrillError(f"restore timeout_seconds must be positive, got {timeout_seconds}")
    return RestoreSpec(
        output_dir=_resolve_path(base, output_dir),
        script=script_path,
        copy_backup=copy_backup,
        timeout_seconds=timeout_seconds,
    )


def _load_policies(data: dict[str, Any] | None) -> PolicySpec:
    if not data:
        return PolicySpec(max_rpo_minutes=None, max_rto_seconds=None)
    max_rpo = data.get("max_rpo_minutes")
    max_rto = data.get("max_rto_seconds")
    def _coerce(name: str, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise DrDrillError(f"policy {name} must be numeric, got {value!r}") from exc
    return PolicySpec(
        max_rpo_minutes=_coerce("max_rpo_minutes", max_rpo),
        max_rto_seconds=_coerce("max_rto_seconds", max_rto),
    )


def load_manifest(path: Path) -> Manifest:
    manifest_path = path.resolve()
    if not manifest_path.exists():
        raise DrDrillError(f"manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise DrDrillError(f"manifest not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DrDrillError(f"manifest must be a JSON object, got {type(data).__name__}")
    base = manifest_path.parent
    backup = _load_backup(data.get("backup", {}), base)
    sbom = _load_sbom(data.get("sbom", {}), base)
    provenance = _load_provenance(data.get("provenance", {}), base)
    restore = _load_restore(data.get("restore", {}), base)
    policies = _load_policies(data.get("policies"))
    return Manifest(
        source=manifest_path,
        backup=backup,
        sbom=sbom,
        provenance=provenance,
        restore=restore,
        policies=policies,
    )
