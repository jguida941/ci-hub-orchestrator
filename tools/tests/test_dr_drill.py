from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.dr_drill.config import BackupSpec, RestoreSpec, load_manifest
from tools.dr_drill.errors import DrDrillError, PolicyViolation
from tools.dr_drill.operations import (
    load_backup_payload,
    perform_restore,
    validate_backup_payload,
    validate_provenance,
    validate_restored_backup,
    validate_sbom,
    verify_backup_digest,
)
from tools.dr_drill.runner import run_drill


MANIFEST_PATH = Path("data/dr/manifest.json")


def test_manifest_loads_and_resolves_paths():
    manifest = load_manifest(MANIFEST_PATH)
    assert manifest.backup.path.exists()
    assert manifest.sbom.path.exists()
    assert manifest.provenance.path.exists()
    assert manifest.restore.output_dir.name == "restore"
    assert manifest.backup.sha256.startswith("sha256:")


def test_backup_digest_verification(tmp_path):
    manifest = load_manifest(MANIFEST_PATH)
    info = verify_backup_digest(manifest.backup)
    assert info["sha256"] == manifest.backup.sha256

    corrupted = tmp_path / "backup.json"
    corrupted.write_text('{"corrupt": true}\n', encoding="utf-8")
    spec = BackupSpec(
        path=corrupted,
        sha256=manifest.backup.sha256,
        captured_at=manifest.backup.captured_at,
    )
    with pytest.raises(DrDrillError):
        verify_backup_digest(spec)


def test_backup_payload_validation():
    manifest = load_manifest(MANIFEST_PATH)
    payload = load_backup_payload(manifest.backup)
    stats = validate_backup_payload(payload)
    assert stats["services"] == 2


def test_sbom_and_provenance_validation():
    manifest = load_manifest(MANIFEST_PATH)
    sbom_stats = validate_sbom(manifest.sbom)
    assert sbom_stats["components"] >= 1
    prov_stats = validate_provenance(manifest.provenance, manifest.backup.sha256)
    assert prov_stats["records"] == 1


def test_restore_and_validation(tmp_path):
    manifest = load_manifest(MANIFEST_PATH)
    restore_spec = RestoreSpec(
        output_dir=tmp_path / "restore",
        script=manifest.restore.script,
        copy_backup=manifest.restore.copy_backup,
    )
    outcome = perform_restore(manifest.backup, restore_spec, manifest.sbom, manifest.provenance)
    details = validate_restored_backup(outcome, manifest.backup)
    assert Path(details["path"]).exists()


def test_run_drill_success(tmp_path):
    manifest = load_manifest(MANIFEST_PATH)
    evidence_dir = tmp_path / "evidence"
    now = manifest.backup.captured_at + timedelta(minutes=30)
    result = run_drill(MANIFEST_PATH, evidence_dir, now=now)

    assert result.report.schema == "dr_drill.v2"
    assert result.report.metrics["rpo_minutes"] == pytest.approx(30.0, rel=1e-2)
    assert any(event.step == "enforce_policies" for event in result.events)
    assert all(isinstance(event.notes, str) for event in result.events)
    assert evidence_dir.exists()


def test_run_drill_policy_violation(tmp_path):
    manifest = load_manifest(MANIFEST_PATH)
    evidence_dir = tmp_path / "evidence"
    # Set current time far enough out to breach the 7-day RPO limit.
    now = manifest.backup.captured_at + timedelta(days=8)
    with pytest.raises(PolicyViolation):
        run_drill(MANIFEST_PATH, evidence_dir, now=now)
