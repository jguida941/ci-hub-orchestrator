"""Shared helper functions for report commands."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from cihub.ci_report import RunContext
from cihub.cli import (
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.utils.env import _parse_env_bool


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def _get_repo_name(config: dict[str, Any], repo_path: Path) -> str:
    repo_env = os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        return repo_env
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    owner = repo_info.get("owner")
    name = repo_info.get("name")
    if owner and name:
        return f"{owner}/{name}"
    remote = get_git_remote(repo_path)
    if remote:
        parsed = parse_repo_from_remote(remote)
        if parsed[0] and parsed[1]:
            return f"{parsed[0]}/{parsed[1]}"
    return ""


def _build_context(
    repo_path: Path,
    config: dict[str, Any],
    workdir: str,
    correlation_id: str | None,
    build_tool: str | None = None,
    project_type: str | None = None,
    docker_compose_file: str | None = None,
    docker_health_endpoint: str | None = None,
) -> RunContext:
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    branch = os.environ.get("GITHUB_REF_NAME") or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=_get_repo_name(config, repo_path),
        branch=branch,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_number=os.environ.get("GITHUB_RUN_NUMBER"),
        commit=os.environ.get("GITHUB_SHA") or "",
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _detect_java_project_type(workdir: Path) -> str:
    pom = workdir / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<modules>" in content:
            modules = len(re.findall(r"<module>.*?</module>", content))
            return f"Multi-module ({modules} modules)" if modules else "Multi-module"
        return "Single module"

    settings_gradle = workdir / "settings.gradle"
    settings_kts = workdir / "settings.gradle.kts"
    if settings_gradle.exists() or settings_kts.exists():
        return "Multi-module"
    if (workdir / "build.gradle").exists() or (workdir / "build.gradle.kts").exists():
        return "Single module"
    return "Unknown"


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for path in tool_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tool = str(data.get("tool") or path.stem)
            outputs[tool] = data
        except json.JSONDecodeError:
            continue
    return outputs


def _resolve_write_summary(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    env_value = _parse_env_bool(os.environ.get("CIHUB_WRITE_GITHUB_SUMMARY"))
    if env_value is not None:
        return env_value
    return True


def _resolve_include_details(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    env_value = _parse_env_bool(os.environ.get("CIHUB_REPORT_INCLUDE_DETAILS"))
    if env_value is not None:
        return env_value
    return False


def _resolve_summary_path(path_value: str | None, write_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if write_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_summary(text: str, summary_path: Path | None, print_stdout: bool) -> None:
    if summary_path is None:
        if print_stdout:
            print(text)
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    parsed = _parse_env_bool(str(value))
    if parsed is not None:
        return parsed
    return False
