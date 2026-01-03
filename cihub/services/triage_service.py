"""Triage bundle generation service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRIAGE_SCHEMA_VERSION = "cihub-triage-v1"
PRIORITY_SCHEMA_VERSION = "cihub-priority-v1"

SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
CATEGORY_ORDER = ["workflow", "security", "test", "lint", "docs", "build", "cihub"]

CATEGORY_BY_TOOL = {
    "pytest": "test",
    "mutmut": "test",
    "hypothesis": "test",
    "build": "build",
    "jacoco": "test",
    "pitest": "test",
    "checkstyle": "lint",
    "spotbugs": "lint",
    "pmd": "lint",
    "ruff": "lint",
    "black": "lint",
    "isort": "lint",
    "mypy": "lint",
    "bandit": "security",
    "pip_audit": "security",
    "semgrep": "security",
    "trivy": "security",
    "owasp": "security",
    "codeql": "security",
    "sbom": "security",
    "docker": "build",
}

SEVERITY_BY_CATEGORY = {
    "workflow": "blocker",
    "security": "high",
    "test": "medium",
    "lint": "low",
    "docs": "low",
    "build": "medium",
    "cihub": "blocker",
}


@dataclass(frozen=True)
class TriageBundle:
    triage: dict[str, Any]
    priority: dict[str, Any]
    markdown: str
    history_entry: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    if not tool_dir.exists():
        return outputs
    for path in tool_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        tool = str(data.get("tool") or path.stem)
        outputs[tool] = data
    return outputs


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _normalize_category(tool: str) -> str:
    return CATEGORY_BY_TOOL.get(tool, "cihub")


def _severity_for(category: str) -> str:
    return SEVERITY_BY_CATEGORY.get(category, "medium")


def _tool_env_name(tool: str) -> str:
    return f"CIHUB_RUN_{tool.replace('-', '_').upper()}"


def _tool_artifacts(output_dir: Path, tool: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    tool_outputs = output_dir / "tool-outputs"
    seen = set()

    def _add(path: Path | str, kind: str) -> None:
        path_str = str(path)
        if not path_str or path_str in seen:
            return
        seen.add(path_str)
        artifacts.append({"path": path_str, "kind": kind})

    json_path = tool_outputs / f"{tool}.json"
    if json_path.exists():
        _add(json_path, "tool_result")

    stdout_path = tool_outputs / f"{tool}.stdout.log"
    stderr_path = tool_outputs / f"{tool}.stderr.log"
    if stdout_path.exists():
        _add(stdout_path, "stdout")
    if stderr_path.exists():
        _add(stderr_path, "stderr")

    for key, value in (payload.get("artifacts") or {}).items():
        if not value:
            continue
        _add(value, key)

    return artifacts


def _repro_command(tool: str, repo_path: Path, workdir: str | None, output_dir: Path) -> dict[str, Any]:
    env_name = _tool_env_name(tool)
    command = f"cihub ci --repo {repo_path} --workdir {workdir or '.'} --output-dir {output_dir}"
    return {"command": command, "cwd": str(repo_path), "env": {env_name: "true"}}


def _failure_entry(
    *,
    tool: str,
    status: str,
    reason: str,
    message: str,
    output_dir: Path,
    tool_payload: dict[str, Any],
    repo_path: Path,
    workdir: str | None,
) -> dict[str, Any]:
    category = _normalize_category(tool)
    severity = _severity_for(category)
    return {
        "id": f"{tool}:{status}",
        "category": category,
        "severity": severity,
        "tool": tool,
        "status": status,
        "reason": reason,
        "message": message,
        "artifacts": _tool_artifacts(output_dir, tool, tool_payload),
        "reproduce": _repro_command(tool, repo_path, workdir, output_dir),
        "hints": [
            f"Review tool outputs under {output_dir / 'tool-outputs'}",
            "Re-run with CIHUB_VERBOSE=True to stream tool output",
        ],
    }


def _build_markdown(bundle: dict[str, Any], max_failures: int = 10) -> str:
    run = bundle.get("run", {}) if isinstance(bundle.get("run"), dict) else {}
    paths = bundle.get("paths", {}) if isinstance(bundle.get("paths"), dict) else {}
    failures = bundle.get("failures", []) if isinstance(bundle.get("failures"), list) else []

    lines = [
        "# CIHub Triage",
        "",
        f"Repository: {run.get('repo') or '-'}",
        f"Branch: {run.get('branch') or '-'}",
        f"Commit: {run.get('commit_sha') or '-'}",
        f"Correlation ID: {run.get('correlation_id') or '-'}",
        f"Output Dir: {paths.get('output_dir') or '-'}",
        "",
        "## Priority Failures",
    ]

    if not failures:
        lines.append("No failures detected.")
        return "\n".join(lines).strip() + "\n"

    for failure in failures[:max_failures]:
        artifacts = failure.get("artifacts", []) if isinstance(failure.get("artifacts"), list) else []
        artifact_lines = [f"- {item.get('path')} ({item.get('kind')})" for item in artifacts if item.get("path")]
        reproduce = failure.get("reproduce", {}) if isinstance(failure.get("reproduce"), dict) else {}
        env = reproduce.get("env", {}) if isinstance(reproduce.get("env"), dict) else {}
        env_str = ", ".join([f"{k}={v}" for k, v in env.items()]) if env else "-"

        lines.extend(
            [
                "",
                f"### {failure.get('tool')} ({failure.get('severity')})",
                f"- Status: {failure.get('status')}",
                f"- Category: {failure.get('category')}",
                f"- Reason: {failure.get('reason')}",
                f"- Message: {failure.get('message')}",
                f"- Reproduce: {reproduce.get('command') or '-'}",
                f"- Env: {env_str}",
                "- Artifacts:",
                *(artifact_lines if artifact_lines else ["  - -"]),
                "- Fix checklist:",
                f"  - Inspect artifacts and logs for {failure.get('tool')}",
                "  - Re-run locally with the reproduce command",
                "  - Apply deterministic fixes from tool output",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _sort_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    category_index = {name: idx for idx, name in enumerate(CATEGORY_ORDER)}

    def _sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        severity = str(item.get("severity") or "medium")
        category = str(item.get("category") or "cihub")
        severity_rank = SEVERITY_ORDER.get(severity, 99)
        category_rank = category_index.get(category, len(CATEGORY_ORDER))
        return (severity_rank, category_rank, str(item.get("tool") or ""))

    return sorted(failures, key=_sort_key)


def generate_triage_bundle(
    output_dir: Path,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    meta: dict[str, Any] | None = None,
) -> TriageBundle:
    output_dir = output_dir.resolve()
    report_path = report_path or output_dir / "report.json"
    summary_path = summary_path or output_dir / "summary.md"
    meta = meta or {}

    report = _load_json(report_path)
    tool_outputs = _load_tool_outputs(output_dir / "tool-outputs")
    failures: list[dict[str, Any]] = []
    notes: list[str] = []

    repo_path = output_dir.parent
    workdir = None
    if report:
        environment = report.get("environment", {}) if isinstance(report.get("environment"), dict) else {}
        workdir = environment.get("workdir")

        tools_configured = report.get("tools_configured", {}) if isinstance(report.get("tools_configured"), dict) else {}
        tools_ran = report.get("tools_ran", {}) if isinstance(report.get("tools_ran"), dict) else {}
        tools_success = report.get("tools_success", {}) if isinstance(report.get("tools_success"), dict) else {}

        for tool, enabled in tools_configured.items():
            if not enabled:
                continue
            ran = bool(tools_ran.get(tool, False))
            success = bool(tools_success.get(tool, False))
            if success:
                continue
            status = "failed" if ran else "skipped"
            reason = "tool_failed" if ran else "tool_skipped"
            message = f"Tool '{tool}' {status}"
            payload = tool_outputs.get(tool, {})
            failures.append(
                _failure_entry(
                    tool=tool,
                    status=status,
                    reason=reason,
                    message=message,
                    output_dir=output_dir,
                    tool_payload=payload,
                    repo_path=repo_path,
                    workdir=workdir,
                )
            )
    else:
        reason = "missing_report" if not report_path.exists() else "invalid_report"
        message = "report.json not found" if reason == "missing_report" else "report.json invalid"
        failures.append(
            {
                "id": f"cihub:{reason}",
                "category": "cihub",
                "severity": "blocker",
                "tool": "cihub",
                "status": "missing_report",
                "reason": reason,
                "message": message,
                "artifacts": [],
                "reproduce": {
                    "command": f"cihub ci --repo {repo_path} --output-dir {output_dir}",
                    "cwd": str(repo_path),
                },
                "hints": [
                    "Confirm the workflow completed and produced report.json",
                    "Re-run cihub ci to regenerate report outputs",
                ],
            }
        )
        if tool_outputs:
            notes.append(f"Found tool outputs in {output_dir / 'tool-outputs'} without report.json")

    if meta.get("error"):
        notes.append(f"error: {meta['error']}")

    priority = _sort_failures(failures)
    failure_count = len([f for f in failures if f.get("status") in {"failed", "missing_report"}])
    skipped_count = len([f for f in failures if f.get("status") == "skipped"])

    run = {
        "correlation_id": report.get("hub_correlation_id") if report else meta.get("correlation_id"),
        "repo": report.get("repository") if report else meta.get("repo"),
        "commit_sha": report.get("commit") if report else meta.get("commit_sha"),
        "branch": report.get("branch") if report else meta.get("branch"),
        "run_id": report.get("run_id") if report else meta.get("run_id"),
        "run_number": report.get("run_number") if report else meta.get("run_number"),
        "workflow_ref": (report.get("metadata", {}) or {}).get("workflow_ref") if report else meta.get("workflow_ref"),
        "command": meta.get("command", "cihub triage"),
        "args": meta.get("args", []),
    }

    summary = {
        "overall_status": "failed" if failures else "passed",
        "failure_count": failure_count,
        "warning_count": 0,
        "skipped_count": skipped_count,
        "tool_counts": {
            "configured": len(report.get("tools_configured", {})) if report else 0,
            "ran": len([t for t in (report.get("tools_ran", {}) if report else {}).values() if t]),
        },
    }

    triage = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "generated_at": _timestamp(),
        "run": run,
        "paths": {
            "output_dir": str(output_dir),
            "report_path": str(report_path) if report_path.exists() else "",
            "summary_path": str(summary_path) if summary_path.exists() else "",
        },
        "summary": summary,
        "failures": priority,
        "warnings": [],
        "notes": notes,
    }

    priority_payload = {
        "schema_version": PRIORITY_SCHEMA_VERSION,
        "failures": priority,
    }

    history_entry = {
        "timestamp": triage["generated_at"],
        "correlation_id": run.get("correlation_id") or "",
        "output_dir": str(output_dir),
        "overall_status": summary["overall_status"],
        "failure_count": summary["failure_count"],
    }

    markdown = _build_markdown(triage, max_failures=10)

    return TriageBundle(
        triage=triage,
        priority=priority_payload,
        markdown=markdown,
        history_entry=history_entry,
    )


def write_triage_bundle(bundle: TriageBundle, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    triage_path = output_dir / "triage.json"
    priority_path = output_dir / "priority.json"
    md_path = output_dir / "triage.md"
    history_path = output_dir / "history.jsonl"

    triage_path.write_text(json.dumps(bundle.triage, indent=2), encoding="utf-8")
    priority_path.write_text(json.dumps(bundle.priority, indent=2), encoding="utf-8")
    md_path.write_text(bundle.markdown, encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bundle.history_entry) + "\n")

    return {
        "triage": triage_path,
        "priority": priority_path,
        "markdown": md_path,
        "history": history_path,
    }
