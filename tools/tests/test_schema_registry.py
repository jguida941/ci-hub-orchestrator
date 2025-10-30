from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_registry_check(registry: Path) -> subprocess.CompletedProcess[bytes]:
    cmd = [sys.executable, "scripts/check_schema_registry.py", "--registry", str(registry)]
    # Safe: invokes repository validation script with controlled arguments.
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True)  # noqa: S603


def test_registry_validation_succeeds():
    registry_path = REPO_ROOT / "schema" / "registry.json"
    result = _run_registry_check(registry_path)
    assert result.returncode == 0, result.stderr.decode()


def test_registry_validation_detects_missing_fixture(tmp_path: Path):
    registry_path = REPO_ROOT / "schema" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    topic = registry["topics"]["pipeline_run"]
    schema_version = topic["schema_versions"][0]
    schema_version["path"] = str((REPO_ROOT / schema_version["path"]).resolve())
    schema_version["fixtures"] = [
        str((REPO_ROOT / "fixtures" / "pipeline_run_v1_2" / "missing.ndjson").resolve())
    ]
    ingestion = topic.get("ingestion", {})
    if "warehouse_model" in ingestion:
        ingestion["warehouse_model"] = str((REPO_ROOT / ingestion["warehouse_model"]).resolve())
    if "dbt_models" in ingestion:
        ingestion["dbt_models"] = [str((REPO_ROOT / model).resolve()) for model in ingestion["dbt_models"]]
    broken_registry = tmp_path / "registry.json"
    broken_registry.write_text(json.dumps(registry), encoding="utf-8")

    result = _run_registry_check(broken_registry)
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "missing fixture" in stderr.lower()
