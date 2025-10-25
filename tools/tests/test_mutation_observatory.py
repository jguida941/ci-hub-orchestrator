from __future__ import annotations

import json
from pathlib import Path
import sys
import textwrap

import pytest

from tools import mutation_observatory as mo


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "mutation"


def test_run_observatory_sample_config(tmp_path):
    config_path = FIXTURE_DIR / "observatory-sample.json"
    run = mo.run_observatory(
        config_path,
        repo="acme/repo",
        branch="feature/mutation",
        commit_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        run_id="run-test-1",
    )

    assert run["schema"] == "mutation_run.v1"
    assert run["status"] == "fail"  # backend target is below threshold
    assert pytest.approx(run["resilience_score"], rel=1e-5) == 9 / 14
    assert len(run["targets"]) == 2

    frontend = next((t for t in run["targets"] if t["name"] == "frontend"), None)
    backend = next((t for t in run["targets"] if t["name"] == "backend"), None)
    assert frontend is not None, "frontend target not found in run"
    assert backend is not None, "backend target not found in run"

    assert pytest.approx(frontend["resilience_score"], rel=1e-5) == 5 / 8
    assert frontend["status"] == "pass"
    assert backend["status"] == "fail"
    assert backend["stats"]["total_mutants"] == 6

    output_path = tmp_path / "run.json"
    summary_path = tmp_path / "summary.md"
    ndjson_path = tmp_path / "runs.ndjson"
    mo.write_outputs(run, output_path=output_path, ndjson_path=ndjson_path, markdown_path=summary_path)

    with output_path.open() as handle:
        saved = json.load(handle)
    assert saved["run_id"] == "run-test-1"

    with summary_path.open() as handle:
        summary_text = handle.read()
    assert "Mutation Observatory" in summary_text
    assert "| backend |" in summary_text

    with ndjson_path.open() as handle:
        line = handle.readline().strip()
    assert json.loads(line)["run_id"] == "run-test-1"


@pytest.mark.skipif(mo.yaml is None, reason="PyYAML not installed")
def test_run_observatory_yaml_config():
    config_path = FIXTURE_DIR / "observatory-sample.yaml"
    run = mo.run_observatory(
        config_path,
        repo=None,
        branch=None,
        commit_sha=None,
        run_id="run-yaml",
    )
    assert len(run["targets"]) == 2
    assert run["targets"][0]["report_path"].endswith(".json")


def test_write_outputs_markdown_escapes_special_chars(tmp_path):
    config_path = FIXTURE_DIR / "observatory-sample.json"
    run = mo.run_observatory(
        config_path,
        repo=None,
        branch=None,
        commit_sha=None,
        run_id="markdown-run",
    )
    run["targets"][0]["name"] = "front|end"
    run["targets"][0]["tool"] = "stryker|js"
    output_path = tmp_path / "run.json"
    summary_path = tmp_path / "summary.md"
    mo.write_outputs(run, output_path=output_path, ndjson_path=None, markdown_path=summary_path)
    summary = summary_path.read_text()
    assert "front\\|end" in summary
    assert "stryker\\|js" in summary


def test_write_outputs_ndjson_appends(tmp_path):
    config_path = FIXTURE_DIR / "observatory-sample.json"
    run_one = mo.run_observatory(
        config_path,
        repo=None,
        branch=None,
        commit_sha=None,
        run_id="append-1",
    )
    run_two = mo.run_observatory(
        config_path,
        repo=None,
        branch=None,
        commit_sha=None,
        run_id="append-2",
    )
    ndjson_path = tmp_path / "runs.ndjson"
    mo.write_outputs(run_one, output_path=tmp_path / "out1.json", ndjson_path=ndjson_path, markdown_path=None)
    mo.write_outputs(run_two, output_path=tmp_path / "out2.json", ndjson_path=ndjson_path, markdown_path=None)
    with ndjson_path.open() as handle:
        lines = [json.loads(line) for line in handle.read().strip().splitlines()]
    assert [line["run_id"] for line in lines] == ["append-1", "append-2"]


def test_main_returns_nonzero_when_status_fail(tmp_path):
    output_path = tmp_path / "run.json"
    markdown_path = tmp_path / "run.md"
    rc = mo.main(
        [
            "--config",
            str(FIXTURE_DIR / "observatory-sample.json"),
            "--output",
            str(output_path),
            "--markdown",
            str(markdown_path),
        ]
    )
    assert rc == 3
    assert output_path.exists()


def test_main_returns_zero_on_success(tmp_path):
    config = {
        "version": "v1",
        "min_resilience": 0.5,
        "targets": [
            {
                "name": "frontend",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": str(FIXTURE_DIR / "stryker-report.json"),
                "threshold": 0.1,
            },
            {
                "name": "backend",
                "tool": "mutmut",
                "parser": "mutmut_json",
                "report_path": str(FIXTURE_DIR / "mutmut-report.json"),
                "threshold": 0.1,
            },
        ],
    }
    config_path = tmp_path / "pass-config.json"
    config_path.write_text(json.dumps(config))

    output_path = tmp_path / "pass.json"
    rc = mo.main(
        [
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )
    assert rc == 0
    data = json.loads(output_path.read_text())
    assert data["status"] == "pass"


def test_load_config_missing_targets(tmp_path):
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("version: v1\n")
    with pytest.raises(mo.MutationObservatoryError):
        mo.load_config(config_path)


def test_threshold_validation_rejects_out_of_range(tmp_path):
    config = {
        "version": "v1",
        "min_resilience": 0.7,
        "targets": [
            {
                "name": "invalid-threshold",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": str(FIXTURE_DIR / "stryker-report.json"),
                "threshold": 1.5,
            }
        ],
    }
    config_path = tmp_path / "invalid.json"
    config_path.write_text(json.dumps(config))
    with pytest.raises(mo.MutationObservatoryError):
        mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="invalid")


def test_run_observatory_executes_command_and_generates_report(tmp_path):
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    config_path = workdir / "config.json"
    report_relative = "generated-report.json"
    report_path = workdir / report_relative
    assert not report_path.exists()

    script = textwrap.dedent(
        f"""
        import json, pathlib
        path = pathlib.Path("{report_relative}")
        data = {{
            "metrics": {{
                "mutationScore": 75.0,
                "killed": 3,
                "survived": 1,
                "noCoverage": 0,
                "timedOut": 0,
                "totalMutants": 4
            }}
        }}
        path.write_text(json.dumps(data))
        """
    ).strip()

    config = {
        "version": "v1",
        "targets": [
            {
                "name": "generated",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": report_relative,
                "threshold": 0.5,
                "command": [sys.executable, "-c", script],
                "workdir": ".",
                "timeout_seconds": 5,
            }
        ],
    }
    config_path.write_text(json.dumps(config))

    run = mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="cmd-run")

    assert report_path.exists(), "command did not generate report"
    assert run["targets"][0]["duration_seconds"] >= 0.0
    assert run["targets"][0]["status"] == "pass"


def test_run_observatory_missing_report_raises_error(tmp_path):
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    config_path = workdir / "config.json"
    report_relative = "missing-report.json"
    script = "import sys; sys.exit(0)"
    config = {
        "version": "v1",
        "targets": [
            {
                "name": "missing-report",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": report_relative,
                "threshold": 0.5,
                "command": [sys.executable, "-c", script],
                "workdir": ".",
            }
        ],
    }
    config_path.write_text(json.dumps(config))

    with pytest.raises(mo.MutationObservatoryError) as excinfo:
        mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="missing")
    assert "report" in str(excinfo.value)


def test_report_path_resolves_relative_to_workdir(tmp_path):
    repo_root = tmp_path / "repo"
    config_dir = repo_root / "configs"
    config_dir.mkdir(parents=True)
    report_relative = "reports/stryker-output.json"
    script = textwrap.dedent(
        f"""
        import json, pathlib
        path = pathlib.Path("{report_relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {{
            "metrics": {{
                "mutationScore": 80.0,
                "killed": 8,
                "survived": 2,
                "noCoverage": 0,
                "timedOut": 0,
                "totalMutants": 10
            }}
        }}
        path.write_text(json.dumps(data))
        """
    ).strip()
    config = {
        "version": "v1",
        "targets": [
            {
                "name": "workspace-relative",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": report_relative,
                "threshold": 0.5,
                "command": [sys.executable, "-c", script],
                "workdir": "..",
            }
        ],
    }
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(config))

    run = mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="workdir-run")

    expected_report = (repo_root / report_relative).resolve()
    assert expected_report.exists(), "report was not written relative to workdir"
    assert run["targets"][0]["report_path"] == str(expected_report)


def test_run_observatory_errors_on_nonzero_exit_without_allowance(tmp_path):
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    config_path = workdir / "config.json"
    report_name = "failing-report.json"
    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        path = pathlib.Path("{report_name}")
        data = {{
            "metrics": {{
                "mutationScore": 0.0,
                "killed": 0,
                "survived": 1,
                "noCoverage": 0,
                "timedOut": 0,
                "totalMutants": 1
            }}
        }}
        path.write_text(json.dumps(data))
        sys.exit(3)
        """
    ).strip()
    config = {
        "version": "v1",
        "targets": [
            {
                "name": "non-zero-exit",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": report_name,
                "threshold": 0.9,
                "command": [sys.executable, "-c", script],
                "workdir": ".",
            }
        ],
    }
    config_path.write_text(json.dumps(config))

    with pytest.raises(mo.MutationObservatoryError):
        mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="fail-exit")


def test_run_observatory_allows_stale_report_when_configured(tmp_path):
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    report_name = "stale-report.json"
    report_path = workdir / report_name
    report_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "mutationScore": 50.0,
                    "killed": 1,
                    "survived": 1,
                    "noCoverage": 0,
                    "timedOut": 0,
                    "totalMutants": 2,
                }
            }
        )
    )
    script = "import sys; sys.exit(4)"
    config = {
        "version": "v1",
        "targets": [
            {
                "name": "stale-ok",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": report_name,
                "threshold": 0.4,
                "command": [sys.executable, "-c", script],
                "workdir": ".",
                "allow_stale_report": True,
            }
        ],
    }
    config_path = workdir / "config.json"
    config_path.write_text(json.dumps(config))

    run = mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="stale")
    target = run["targets"][0]
    assert target["command_exit_code"] == 4
    assert target["status"] == "pass"


def test_min_resilience_enforced(tmp_path):
    config_path = tmp_path / "config.json"
    config = {
        "version": "v1",
        "min_resilience": 0.9,
        "targets": [
            {
                "name": "frontend",
                "tool": "stryker",
                "parser": "stryker",
                "report_path": str(FIXTURE_DIR / "stryker-report.json"),
                "threshold": 0.5,
            },
            {
                "name": "backend",
                "tool": "mutmut",
                "parser": "mutmut_json",
                "report_path": str(FIXTURE_DIR / "mutmut-report.json"),
                "threshold": 0.5,
            },
        ],
    }
    config_path.write_text(json.dumps(config))

    run = mo.run_observatory(config_path, repo=None, branch=None, commit_sha=None, run_id="min-thresh")

    assert all(t["status"] == "pass" for t in run["targets"]), "targets should pass individual thresholds"
    assert run["status"] == "fail"
    assert run["min_resilience"] == pytest.approx(0.9)
    assert run["meets_min_resilience"] is False


def test_parse_stryker_report_counts_all_mutant_outcomes(tmp_path):
    report_path = tmp_path / "stryker.json"
    payload = {
        "metrics": {
            "killed": 1,
            "survived": 1,
            "noCoverage": 1,
            "timedOut": 1,
            "ignored": 1,
            "compileErrors": 1,
            "runtimeErrors": 1,
        }
    }
    report_path.write_text(json.dumps(payload))

    metrics = mo._parse_stryker_report(report_path)

    assert metrics["total_mutants"] == 7
