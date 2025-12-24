from __future__ import annotations

import hashlib
import json
import os
import shutil
from subprocess import CalledProcessError, DEVNULL, PIPE, TimeoutExpired
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from tools import provenance_io
from tools.safe_subprocess import run_checked
from tools.safe_subprocess import run_checked

from .config import BackupSpec, ProvenanceSpec, RestoreSpec, SbomSpec
from .errors import DrDrillError


DEFAULT_RESTORE_TIMEOUT_SECONDS = 3600


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def verify_backup_digest(spec: BackupSpec) -> Dict[str, Any]:
    if not spec.path.exists():
        raise DrDrillError(f"backup artifact missing: {spec.path}")
    actual = _sha256(spec.path)
    if actual != spec.sha256:
        raise DrDrillError(f"backup digest mismatch: expected {spec.sha256}, found {actual}")
    return {"path": str(spec.path), "sha256": actual}


def load_backup_payload(spec: BackupSpec) -> Dict[str, Any]:
    try:
        with spec.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI
        raise DrDrillError(f"backup payload not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DrDrillError("backup payload must be a JSON object")
    return payload


def validate_backup_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    services = payload.get("services")
    if not isinstance(services, list) or not services:
        raise DrDrillError("backup payload missing services")
    if not all(isinstance(svc, dict) for svc in services):
        raise DrDrillError("backup payload contains invalid service entries")
    failing = [svc for svc in services if svc.get("status") != "ready"]
    if failing:
        names = ", ".join(str(svc.get("name", '<unknown>')) for svc in failing)
        raise DrDrillError(f"backup payload integrity check failed: non-ready services: {names}")
    return {"services": len(services)}


def validate_sbom(spec: SbomSpec) -> Dict[str, Any]:
    if not spec.path.exists():
        raise DrDrillError(f"SBOM missing: {spec.path}")
    try:
        with spec.path.open("r", encoding="utf-8") as handle:
            sbom = json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI
        raise DrDrillError(f"SBOM not valid JSON: {exc}") from exc
    components = sbom.get("components")
    if not isinstance(components, list) or not components:
        raise DrDrillError("SBOM has no components")
    return {"components": len(components)}


def validate_provenance(spec: ProvenanceSpec, expected_digest: str) -> Dict[str, Any]:
    if not spec.path.exists():
        raise DrDrillError(f"provenance missing: {spec.path}")
    try:
        records = provenance_io.load_records(spec.path)
    except provenance_io.ProvenanceParseError as exc:
        raise DrDrillError(str(exc)) from exc
    provenance_io.select_envelope(records, expected_digest, 0)
    return {"records": len(records)}


@dataclass(frozen=True)
class RestoreOutcome:
    output_dir: Path
    restored_backup: Path | None
    duration_seconds: float


def perform_restore(
    backup: BackupSpec,
    restore: RestoreSpec,
    sbom: SbomSpec,
    provenance: ProvenanceSpec,
) -> RestoreOutcome:
    restore.output_dir.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    restored_backup: Path | None = None

    if restore.copy_backup:
        restored_backup = restore.output_dir / backup.path.name
        shutil.copy2(backup.path, restored_backup)

    if restore.script:
        env = {
            **os.environ,
            "BACKUP_PATH": str(backup.path),
            "PROVENANCE_PATH": str(provenance.path),
            "SBOM_PATH": str(sbom.path),
            "RESTORE_DIR": str(restore.output_dir),
        }
        timeout_seconds = (
            restore.timeout_seconds if restore.timeout_seconds is not None else DEFAULT_RESTORE_TIMEOUT_SECONDS
        )
        script_path = Path(restore.script).expanduser().resolve()
        if not script_path.exists():
            raise DrDrillError(f"restore script not found: {restore.script}")
        if not os.access(script_path, os.X_OK):
            raise DrDrillError(f"restore script is not executable: {script_path}")

        try:
            run_checked(
                [
                    str(script_path),
                    str(backup.path),
                    str(provenance.path),
                    str(sbom.path),
                    str(restore.output_dir),
                ],
                allowed_programs={script_path},
                check=True,
                env=env,
                timeout=timeout_seconds,
                stdout=DEVNULL,
                stderr=PIPE,
                text=True,
            )
        except TimeoutExpired as exc:
            raise DrDrillError(
                f"restore script timed out after {timeout_seconds} seconds"
            ) from exc
        except CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            message = f"restore script failed with exit code {exc.returncode}"
            if stderr:
                message = f"{message}: {stderr}"
            raise DrDrillError(message) from exc

    duration = time.monotonic() - start
    return RestoreOutcome(output_dir=restore.output_dir, restored_backup=restored_backup, duration_seconds=duration)


def validate_restored_backup(outcome: RestoreOutcome, expected: BackupSpec) -> Dict[str, Any]:
    restored_path: Path | None = outcome.restored_backup
    if restored_path is None:
        candidate = outcome.output_dir / expected.path.name
        if not candidate.exists():
            raise DrDrillError("restored backup artifact not found")
        restored_path = candidate

    actual = _sha256(restored_path)
    if actual != expected.sha256:
        raise DrDrillError(
            f"restored backup digest mismatch: expected {expected.sha256}, found {actual}"
        )
    return {"path": str(restored_path), "sha256": actual}
