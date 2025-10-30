from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "determinism_check.sh"

DOCKER_STUB = """#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "buildx" ]]; then
  exit 0
fi
shift
if [[ "${1:-}" != "imagetools" ]]; then
  exit 0
fi
shift
if [[ "${1:-}" != "inspect" ]]; then
  exit 0
fi
shift

RAW=false
PLATFORM="all"

if [[ "${1:-}" == "--raw" ]]; then
  RAW=true
  shift
fi

if [[ "${1:-}" == "--platform" ]]; then
  PLATFORM="$2"
  shift 2
fi

IMAGE="${1:-}"
STATE_DIR="${DOCKER_STUB_STATE_DIR:-}"
if [[ -n "$STATE_DIR" ]]; then
  mkdir -p "$STATE_DIR"
fi
platform_key="${PLATFORM//[^A-Za-z0-9._-]/_}"
if [[ -z "$platform_key" ]]; then
  platform_key="all"
fi
state_file=""
if [[ -n "$STATE_DIR" ]]; then
  state_file="$STATE_DIR/${platform_key}.count"
fi
count=0
if [[ -n "$state_file" && -f "$state_file" ]]; then
  count=$(cat "$state_file")
fi
count=$((count + 1))
if [[ -n "$state_file" ]]; then
  printf '%s' "$count" > "$state_file"
fi

if [[ "$RAW" == "true" ]]; then
  content="baseline-${PLATFORM}"
  if [[ -n "${DETERMINISM_STUB_DIFF:-}" ]]; then
    IFS=',' read -r -a entries <<< "${DETERMINISM_STUB_DIFF}"
    for entry in "${entries[@]}"; do
      IFS=':' read -r target_platform target_run <<< "$entry"
      if [[ "$target_platform" == "$PLATFORM" && "$target_run" == "$count" ]]; then
        content="drift-${PLATFORM}-${count}"
      fi
    done
  fi
  printf '{"platform":"%s","content":"%s"}\\n' "$PLATFORM" "$content"
else
  printf 'pretty manifest for %s\\n' "$IMAGE"
fi
"""


def _write_docker_stub(tmp_path: Path) -> Path:
  bin_dir = tmp_path / "bin"
  bin_dir.mkdir()
  docker_path = bin_dir / "docker"
  docker_path.write_text(DOCKER_STUB, encoding="utf-8")
  docker_path.chmod(stat.S_IRWXU)
  return docker_path


def _run_check(tmp_path: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
  docker_stub = _write_docker_stub(tmp_path)
  output_dir = tmp_path / "determinism"
  env = os.environ.copy()
  env.update(
    {
      "PATH": f"{docker_stub.parent}:{env.get('PATH', '')}",
      "DOCKER_STUB_STATE_DIR": str(tmp_path / "state"),
      "DETERMINISM_PLATFORMS": "linux/amd64,linux/arm64",
      "DETERMINISM_RUNS": "2",
      "DETERMINISM_SLEEP_SECONDS": "0",
    }
  )
  if extra_env:
    env.update(extra_env)
  cmd = [
    str(SCRIPT),
    "ghcr.io/example/app@sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
    str(output_dir),
  ]
  # Safe: command is internal script with controlled args.
  return subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True)  # noqa: S603


def test_determinism_check_consistent(tmp_path: Path):
  result = _run_check(tmp_path)
  assert result.returncode == 0, result.stderr.decode()

  output_dir = tmp_path / "determinism"
  report_path = output_dir / "determinism-report.json"
  summary_path = output_dir / "summary.txt"
  assert report_path.is_file()
  assert summary_path.is_file()

  report = json.loads(report_path.read_text(encoding="utf-8"))
  platforms = {entry["platform"]: entry for entry in report["platforms"]}
  assert "all" in platforms
  assert "linux/amd64" in platforms
  assert platforms["linux/amd64"]["consistent"] is True
  assert platforms["linux/arm64"]["consistent"] is True
  summary_text = summary_path.read_text(encoding="utf-8")
  assert "deterministic" in summary_text


def test_determinism_check_detects_drift(tmp_path: Path):
  result = _run_check(tmp_path, extra_env={"DETERMINISM_STUB_DIFF": "linux/arm64:2"})
  assert result.returncode == 2

  output_dir = tmp_path / "determinism"
  report_path = output_dir / "determinism-report.json"
  report = json.loads(report_path.read_text(encoding="utf-8"))
  platform_map = {entry["platform"]: entry for entry in report["platforms"]}
  arm_entry = platform_map["linux/arm64"]
  assert arm_entry["consistent"] is False
  assert arm_entry["mismatch_runs"] == [2]


def test_determinism_check_rejects_invalid_run_count(tmp_path: Path):
  result = _run_check(tmp_path, extra_env={"DETERMINISM_RUNS": "two"})
  assert result.returncode != 0
  stderr = result.stderr.decode()
  assert "must be an integer value" in stderr
