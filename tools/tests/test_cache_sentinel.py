from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def run_cache_sentinel(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "tools/cache_sentinel.py", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def test_record_and_verify_cache(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "a.txt").write_text("alpha")
    (cache_dir / "sub").mkdir()
    (cache_dir / "sub" / "b.txt").write_text("bravo")

    manifest = tmp_path / "manifest.json"
    result = run_cache_sentinel(
        [
            "record",
            "--cache-dir",
            str(cache_dir),
            "--output",
            str(manifest),
        ],
        repo_root,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(manifest.read_text())
    assert data["entry_count"] == 2

    verify = run_cache_sentinel(
        [
            "verify",
            "--cache-dir",
            str(cache_dir),
            "--manifest",
            str(manifest),
            "--quarantine-dir",
            str(tmp_path / "quarantine"),
            "--report",
            str(tmp_path / "report.json"),
        ],
        repo_root,
    )
    assert verify.returncode == 0, verify.stderr
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["missing"] == []

    # tamper file to trigger quarantine
    (cache_dir / "a.txt").write_text("tampered")
    verify2 = run_cache_sentinel(
        [
            "verify",
            "--cache-dir",
            str(cache_dir),
            "--manifest",
            str(manifest),
            "--quarantine-dir",
            str(tmp_path / "quarantine"),
        ],
        repo_root,
    )
    assert verify2.returncode == 1
    quarantined = list((tmp_path / "quarantine").rglob("*.txt"))
    assert any("a.txt" in str(path) for path in quarantined)
