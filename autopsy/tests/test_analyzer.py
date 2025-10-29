from __future__ import annotations

from pathlib import Path

from autopsy import analyzer


def _write_log(tmp_path: Path, name: str, content: str) -> Path:
    log_path = tmp_path / name
    log_path.write_text(content, encoding="utf-8")
    return log_path


def test_analyze_logs_detects_pytest_attribute_error(tmp_path):
    log = _write_log(
        tmp_path,
        "project-tests.log",
        """
=========================== short test summary info ============================
FAILED tests/test_example.py::test_handles_none - AttributeError: 'NoneType' object has no attribute 'run'
        """.strip(),
    )
    rules = analyzer.load_rules(analyzer.DEFAULT_RULES_PATH)
    findings = analyzer.analyze_logs([log], rules)
    assert findings, "Expected at least one finding for AttributeError"
    detected = [
        f for f in findings if f.tool == "pytest" and "NoneType" in f.message
    ]
    assert detected, f"AttributeError finding missing in {findings}"
    assert detected[0].severity == "warn"


def test_analyze_logs_handles_multiple_tools(tmp_path):
    log = _write_log(
        tmp_path,
        "ci.log",
        """
npm ERR! code ELIFECYCLE
npm ERR! errno 1
Error: duplicate resource found
        """.strip(),
    )
    terraform_log = _write_log(
        tmp_path, "terraform-plan.log", "Error: Unsupported argument\n"
    )
    rules = analyzer.load_rules(analyzer.DEFAULT_RULES_PATH)
    findings = analyzer.analyze_logs([log, terraform_log], rules)
    severities = {f.severity for f in findings}
    tools = {f.tool for f in findings}
    assert "npm" in tools
    assert "terraform" in tools
    assert "error" in severities or "warn" in severities


def test_build_report_summarizes_findings(tmp_path):
    log = _write_log(tmp_path, "pytest.log", "ModuleNotFoundError: tests.missing\n")
    rules = analyzer.load_rules(analyzer.DEFAULT_RULES_PATH)
    findings = analyzer.analyze_logs([log], rules)
    report = analyzer.build_report(
        findings=findings,
        repo="example/repo",
        branch="main",
        commit_sha="abc123",
        run_id="run-1",
        sources=[log],
    )
    assert report["summary"]["total_findings"] == len(findings)
    assert report["findings"]
    assert report["summary"]["severity"]["error"] >= 1
