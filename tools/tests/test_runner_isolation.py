from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(config: Path, workflows_dir: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    cmd = [sys.executable, "scripts/check_runner_isolation.py", "--config", str(config)]
    if workflows_dir is not None:
        cmd.extend(["--workflows-dir", str(workflows_dir)])
    # Safe: executes repository script with fixed arguments for test coverage.
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True)  # noqa: S603


def test_runner_isolation_passes_default_config():
    config = REPO_ROOT / "config" / "runner-isolation.yaml"
    result = _run(config)
    assert result.returncode == 0, result.stderr.decode()


def test_runner_isolation_detects_missing_job(tmp_path: Path):
    config = REPO_ROOT / "config" / "runner-isolation.yaml"
    broken_config = tmp_path / "runner-isolation.yaml"
    broken_config.write_text(
        config.read_text().replace("project-tests", "nonexistent-job"),
        encoding="utf-8",
    )
    result = _run(broken_config)
    assert result.returncode != 0
    assert "missing" in result.stderr.decode().lower()


def test_self_hosted_profile_requires_labels(tmp_path: Path):
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    workflow_path = workflows_dir / "sample.yml"
    workflow_path.write_text(
        """
name: sample
jobs:
  build:
    runs-on: [self-hosted, build-fips, linux]
    steps:
      - run: echo ok
""",
        encoding="utf-8",
    )

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    cache_script = scripts_dir / "cache.sh"
    cache_script.write_text("#!/bin/sh\n", encoding="utf-8")
    cache_script.chmod(0o755)

    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()
    egress_file = policies_dir / "egress.md"
    egress_file.write_text("allowlist", encoding="utf-8")

    config_path = tmp_path / "runner-isolation.yaml"
    config_path.write_text(
        """
version: 1
defaults:
  require_cancel_in_progress: false
  allowed_runners:
    - self-hosted
    - linux
    - build-fips
workflows:
  sample.yml:
    jobs:
      build:
        self_hosted_profile: isolated-build-fips
self_hosted_profiles:
  isolated-build-fips:
    required_labels:
      - self-hosted
      - linux
      - build-fips
    cache_provenance_script: scripts/cache.sh
    egress_policy: policies/egress.md
""",
        encoding="utf-8",
    )

    result = _run(config_path, workflows_dir)
    assert result.returncode == 0, result.stderr.decode()

    # Remove a required label and expect failure
    workflow_path.write_text(
        """
name: sample
jobs:
  build:
    runs-on: [self-hosted, linux]
    steps:
      - run: echo ok
""",
        encoding="utf-8",
    )
    result = _run(config_path, workflows_dir)
    assert result.returncode != 0
    assert "missing required runner labels" in result.stderr.decode()


def test_self_hosted_profile_requires_scripts(tmp_path: Path):
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "wf.yml").write_text(
        """
name: wf
jobs:
  build:
    runs-on: [self-hosted, build-fips, linux]
    steps:
      - run: echo ok
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "runner-isolation.yaml"
    config_path.write_text(
        """
version: 1
defaults:
  require_cancel_in_progress: false
  allowed_runners:
    - self-hosted
    - build-fips
    - linux
workflows:
  wf.yml:
    jobs:
      build:
        self_hosted_profile: missing-assets
self_hosted_profiles:
  missing-assets:
    required_labels:
      - self-hosted
      - build-fips
      - linux
    cache_provenance_script: scripts/missing.sh
    egress_policy: policies/missing.md
""",
        encoding="utf-8",
    )

    result = _run(config_path, workflows_dir)
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "cache_provenance_script" in stderr or "egress_policy" in stderr


def test_runner_isolation_rejects_non_string_runner(tmp_path: Path):
    config = REPO_ROOT / "config" / "runner-isolation.yaml"
    broken_config = tmp_path / "runner-isolation.yaml"
    text = config.read_text(encoding="utf-8")
    broken_config.write_text(text.replace("- ubuntu-latest", "- 123"), encoding="utf-8")
    result = _run(broken_config)
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "allowed_runners" in stderr.lower()
