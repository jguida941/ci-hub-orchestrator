from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import Manifest, load_manifest
from .errors import DrDrillError, PolicyViolation
from .operations import (
    load_backup_payload,
    perform_restore,
    validate_backup_payload,
    validate_provenance,
    validate_restored_backup,
    validate_sbom,
    verify_backup_digest,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_id(ts: datetime) -> str:
    return f"dr-{int(ts.timestamp())}"


def _compute_rpo_minutes(captured_at: datetime, now: datetime) -> float:
    delta = now - captured_at
    return max(delta.total_seconds() / 60.0, 0.0)


@dataclass(frozen=True)
class DrillEvent:
    step: str
    started_at: str
    ended_at: str
    status: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DrillReport:
    schema: str
    run_id: str
    started_at: str
    ended_at: str
    backup_captured_at: str
    manifest: str
    metrics: Dict[str, Any]
    notes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DrillResult:
    report: DrillReport
    events: List[DrillEvent]


def _serialize_notes(details: Any) -> str:
    if not details:
        return ""
    if isinstance(details, str):
        return details
    try:
        return json.dumps(details, sort_keys=True)
    except TypeError:
        return str(details)


def _enforce_policies(manifest: Manifest, rpo_minutes: float, rto_seconds: float) -> Dict[str, Any]:
    breaches: Dict[str, Any] = {}
    if manifest.policies.max_rpo_minutes is not None and rpo_minutes > manifest.policies.max_rpo_minutes:
        breaches["max_rpo_minutes"] = {
            "limit": manifest.policies.max_rpo_minutes,
            "observed": rpo_minutes,
        }
    if manifest.policies.max_rto_seconds is not None and rto_seconds > manifest.policies.max_rto_seconds:
        breaches["max_rto_seconds"] = {
            "limit": manifest.policies.max_rto_seconds,
            "observed": rto_seconds,
        }
    if breaches:
        raise PolicyViolation(f"policy thresholds breached: {json.dumps(breaches, indent=2)}")
    return {
        "max_rpo_minutes": manifest.policies.max_rpo_minutes,
        "max_rto_seconds": manifest.policies.max_rto_seconds,
    }


def run_drill(manifest_path: Path, evidence_dir: Path, *, now: Optional[datetime] = None) -> DrillResult:
    manifest = load_manifest(manifest_path)
    run_started = _utc_now()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if now is not None:
        if now.tzinfo is None:
            raise DrDrillError("now parameter must be timezone-aware")
        now = now.astimezone(timezone.utc)

    events: List[DrillEvent] = []

    def run_step(name: str, func: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        step_started = _utc_now()
        try:
            details = func() or {}
        except DrDrillError as exc:
            step_ended = _utc_now()
            events.append(
                DrillEvent(
                    step=name,
                    started_at=_isoformat(step_started),
                    ended_at=_isoformat(step_ended),
                    status="failure",
                    notes=_serialize_notes({"type": exc.__class__.__name__, "message": str(exc)}),
                )
            )
            raise
        except Exception as exc:  # pragma: no cover - surfaced in CI
            step_ended = _utc_now()
            events.append(
                DrillEvent(
                    step=name,
                    started_at=_isoformat(step_started),
                    ended_at=_isoformat(step_ended),
                    status="failure",
                    notes=_serialize_notes({"type": exc.__class__.__name__, "message": str(exc)}),
                )
            )
            raise DrDrillError(f"{exc.__class__.__name__}: {exc}") from exc
        else:
            step_ended = _utc_now()
            events.append(
                DrillEvent(
                    step=name,
                    started_at=_isoformat(step_started),
                    ended_at=_isoformat(step_ended),
                    status="success",
                    notes=_serialize_notes(details),
                )
            )
            return details

    # Step 1: verify backup checksum and structure.
    run_step("verify_backup_digest", lambda: verify_backup_digest(manifest.backup))

    payload_stats: Dict[str, Any] = {}

    def _inspect_backup() -> Dict[str, Any]:
        payload = load_backup_payload(manifest.backup)
        stats = validate_backup_payload(payload)
        payload_stats.update(stats)
        return stats

    run_step("verify_backup_payload", _inspect_backup)
    run_step("validate_sbom", lambda: validate_sbom(manifest.sbom))
    run_step("validate_provenance", lambda: validate_provenance(manifest.provenance, manifest.backup.sha256))

    restore_outcome_box: Dict[str, Any] = {}

    def _restore() -> Dict[str, Any]:
        outcome = perform_restore(manifest.backup, manifest.restore, manifest.sbom, manifest.provenance)
        restore_outcome_box["outcome"] = outcome
        return {
            "output_dir": str(outcome.output_dir),
            "duration_seconds": outcome.duration_seconds,
        }

    run_step("restore_artifact", _restore)

    outcome = restore_outcome_box.get("outcome")
    if outcome is None:  # pragma: no cover - defensive
        raise DrDrillError("restore did not produce an outcome")

    run_step("validate_restored_backup", lambda: validate_restored_backup(outcome, manifest.backup))

    completed_at = _utc_now()
    current_time = now or completed_at
    rto_seconds = outcome.duration_seconds
    rpo_minutes = _compute_rpo_minutes(manifest.backup.captured_at, current_time)

    policy_details = run_step(
        "enforce_policies",
        lambda: _enforce_policies(manifest, rpo_minutes, rto_seconds),
    )

    report = DrillReport(
        schema="dr_drill.v2",
        run_id=_run_id(run_started),
        started_at=_isoformat(run_started),
        ended_at=_isoformat(completed_at),
        backup_captured_at=_isoformat(manifest.backup.captured_at),
        manifest=str(manifest.source),
        metrics={
            "rto_seconds": round(rto_seconds, 3),
            "rpo_minutes": round(rpo_minutes, 3),
        },
        notes={
            "policy": policy_details,
            "services_checked": payload_stats.get("services"),
        },
    )
    return DrillResult(report=report, events=events)
