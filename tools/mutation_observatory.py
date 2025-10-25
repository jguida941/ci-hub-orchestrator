#!/usr/bin/env python3
"""Run mutation test analyzers and emit structured resilience telemetry."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


class MutationObservatoryError(Exception):
    """Raised when the mutation observatory cannot complete."""


@dataclass
class TargetConfig:
    name: str
    tool: str
    parser: str
    report_path: Path
    threshold: float
    command: Optional[List[str]] = None
    workdir: Optional[Path] = None
    env: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    baseline_score: Optional[float] = None
    timeout_seconds: Optional[float] = None
    allow_stale_reports: bool = False


def load_config(config_path: Path) -> tuple[dict[str, Any], list[TargetConfig]]:
    """Load and validate the observatory configuration."""

    if not config_path.exists():
        raise MutationObservatoryError(f"config file not found: {config_path}")

    raw = _load_mapping_from_file(config_path)

    version = raw.get("version", "v1")
    if version != "v1":
        raise MutationObservatoryError(f"unsupported config version: {version}")

    targets_cfg = raw.get("targets")
    if not isinstance(targets_cfg, list) or not targets_cfg:
        raise MutationObservatoryError("config targets must be a non-empty list")

    base_dir = config_path.parent
    default_threshold_value = raw.get("min_resilience", 0.7)
    default_threshold = _coerce_float(
        default_threshold_value,
        default=0.7,
        key="config.min_resilience",
        min_value=0.0,
        max_value=1.0,
    )
    targets: list[TargetConfig] = []

    for idx, entry in enumerate(targets_cfg):
        if not isinstance(entry, dict):
            raise MutationObservatoryError(f"target #{idx} must be a mapping")
        try:
            name = str(entry["name"])
            tool = str(entry["tool"])
            parser = str(entry.get("parser", tool))
            report_path = Path(entry["report_path"])
        except KeyError as exc:  # pragma: no cover - config validation
            raise MutationObservatoryError(f"missing required key for target #{idx}: {exc}") from exc

        threshold_raw = entry.get("threshold", default_threshold)
        threshold = _coerce_float(
            threshold_raw,
            default=default_threshold,
            key=f"target '{name}' threshold",
            min_value=0.0,
            max_value=1.0,
        )
        command = _normalize_command(entry.get("command"))
        workdir = entry.get("workdir")
        resolved_workdir = (base_dir / Path(workdir)).resolve() if workdir else None
        env = _ensure_string_dict(entry.get("env"), f"env for target '{name}'")
        labels = entry.get("labels") or {}
        baseline_score = _coerce_optional_float(
            entry.get("baseline_score"),
            key=f"target '{name}' baseline_score",
            min_value=0.0,
            max_value=1.0,
        )
        timeout_seconds = entry.get("timeout_seconds", entry.get("timeout"))
        timeout_seconds = _coerce_optional_float(
            timeout_seconds,
            key=f"target '{name}' timeout_seconds",
            min_value=0.0,
        )
        allow_stale_reports = _coerce_bool(
            entry.get("allow_stale_report", entry.get("allow_stale_reports")),
            key=f"target '{name}' allow_stale_report",
            default=False,
        )

        if report_path.is_absolute():
            resolved_report = report_path
        else:
            search_root = resolved_workdir or base_dir
            resolved_report = (search_root / report_path).resolve()

        if command is None and not resolved_report.exists():
            raise MutationObservatoryError(
                f"report path for target '{name}' not found before run: {resolved_report}"
            )

        targets.append(
            TargetConfig(
                name=name,
                tool=tool,
                parser=parser,
                report_path=resolved_report,
                threshold=threshold,
                command=command,
                workdir=resolved_workdir,
                env=env,
                labels=_ensure_string_dict(labels, f"labels for target '{name}'"),
                baseline_score=baseline_score,
                timeout_seconds=timeout_seconds,
                allow_stale_reports=allow_stale_reports,
            )
        )

    meta = {
        "repo": raw.get("repo"),
        "branch": raw.get("branch"),
        "commit_sha": raw.get("commit_sha"),
        "min_resilience": default_threshold,
    }
    return meta, targets


def _load_mapping_from_file(config_path: Path) -> dict[str, Any]:
    text = config_path.read_text()
    suffix = config_path.suffix.lower()
    data: Any
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise MutationObservatoryError(
                "PyYAML is required to parse YAML configs; install the 'pyyaml' extra"
            )
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        if yaml is not None:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)

    if not isinstance(data, dict):
        raise MutationObservatoryError("config root must be a mapping")
    return data


def _load_json_report(report_path: Path, context: str) -> Any:
    try:
        with report_path.open() as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise MutationObservatoryError(f"{context} not found: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise MutationObservatoryError(f"{context} is not valid JSON: {report_path}") from exc
    except OSError as exc:
        raise MutationObservatoryError(f"failed to read {context}: {report_path}") from exc


def _normalize_command(command: Any) -> Optional[List[str]]:
    if command is None:
        return None
    if isinstance(command, str):
        return shlex.split(command)
    if isinstance(command, (list, tuple)):
        normalized: list[str] = []
        for part in command:
            normalized.append(str(part))
        return normalized
    raise MutationObservatoryError(f"unsupported command type: {command!r}")


def _ensure_string_dict(raw_map: Any, context: str) -> dict[str, str]:
    if not raw_map:
        return {}
    if not isinstance(raw_map, dict):
        raise MutationObservatoryError(f"{context} must be a mapping")
    return {str(k): str(v) for k, v in raw_map.items()}


def _coerce_float(
    value: Any,
    *,
    default: float,
    key: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> float:
    if value is None:
        numeric = default
    else:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise MutationObservatoryError(f"{key} must be numeric") from exc
    if min_value is not None and numeric < min_value:
        raise MutationObservatoryError(
            f"{key} must be at least {min_value} (got {numeric!r})"
        )
    if max_value is not None and numeric > max_value:
        raise MutationObservatoryError(
            f"{key} must be at most {max_value} (got {numeric!r})"
        )
    return numeric


def _coerce_optional_float(
    value: Any,
    *,
    key: str,
    default: Optional[float] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Optional[float]:
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise MutationObservatoryError(f"{key} must be numeric") from exc
    if min_value is not None and numeric < min_value:
        raise MutationObservatoryError(
            f"{key} must be at least {min_value} (got {numeric!r})"
        )
    if max_value is not None and numeric > max_value:
        raise MutationObservatoryError(
            f"{key} must be at most {max_value} (got {numeric!r})"
        )
    return numeric


def _coerce_bool(value: Any, *, key: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise MutationObservatoryError(f"{key} must be a boolean")


def _escape_markdown(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "\\": "\\\\",
        "`": "\\`",
        "|": "\\|",
        "<": "\\<",
        ">": "\\>",
    }
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)
    return text


def run_command(
    command: list[str],
    workdir: Optional[Path],
    env: dict[str, str],
    *,
    timeout: Optional[float] = None,
    target_name: str,
) -> tuple[float, Optional[int]]:
    """Execute the configured mutation command and return (duration, exit code)."""

    if not command:
        return 0.0, None

    run_env = os.environ.copy()
    run_env.update(env)
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            check=False,
            cwd=workdir,
            env=run_env,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise MutationObservatoryError(
            f"command for target '{target_name}' "
            f"timed out after {timeout} seconds: {command}"
        ) from exc

    duration = time.monotonic() - start
    if result.returncode != 0:
        print(
            f"[mutation_observatory] command for target '{target_name}' exited with code {result.returncode}",
            file=sys.stderr,
        )
    return duration, result.returncode


def parse_report(parser: str, report_path: Path) -> dict[str, Any]:
    if parser == "stryker":
        return _parse_stryker_report(report_path)
    if parser == "mutmut_json":
        return _parse_mutmut_report(report_path)
    if parser == "generic":
        data = _load_json_report(report_path, "generic report")
        if not isinstance(data, dict):
            raise MutationObservatoryError(f"generic report must be an object: {report_path}")
        return data
    raise MutationObservatoryError(f"unsupported parser '{parser}' for report {report_path}")


def _parse_stryker_report(report_path: Path) -> dict[str, Any]:
    payload = _load_json_report(report_path, "stryker report")
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, dict):
        raise MutationObservatoryError(f"invalid Stryker report structure: {report_path}")

    killed = int(metrics.get("killed", 0))
    survived = int(metrics.get("survived", 0))
    no_coverage = int(metrics.get("noCoverage", 0))
    timed_out = int(metrics.get("timedOut", metrics.get("timeout", 0)))
    ignored = int(metrics.get("ignored", 0))
    compile_errors = int(metrics.get("compileErrors", 0))
    runtime_errors = int(metrics.get("runtimeErrors", 0))
    total_mutants = int(
        metrics.get(
            "totalMutants",
            killed + survived + no_coverage + timed_out + ignored + compile_errors + runtime_errors,
        )
    )

    return {
        "tool": "stryker",
        "total_mutants": total_mutants,
        "killed": killed,
        "survived": survived,
        "timeout": timed_out,
        "no_coverage": no_coverage,
        "mutation_score": float(metrics.get("mutationScore", 0.0)),
    }


def _parse_mutmut_report(report_path: Path) -> dict[str, Any]:
    payload = _load_json_report(report_path, "mutmut report")
    stats = payload.get("stats", payload)
    if not isinstance(stats, dict):
        raise MutationObservatoryError(f"invalid mutmut report structure: {report_path}")

    killed = int(stats.get("killed", 0))
    survived = int(stats.get("survived", 0))
    timeout = int(stats.get("timeout", stats.get("timeouts", 0)))
    skipped = int(stats.get("skipped", stats.get("no_coverage", 0)))
    total_mutants = int(stats.get("total_mutants", killed + survived + timeout + skipped))

    return {
        "tool": payload.get("tool", "mutmut"),
        "total_mutants": total_mutants,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "no_coverage": skipped,
        "mutation_score": _safe_percent(killed, total_mutants),
    }


def _safe_percent(killed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (killed / total) * 100.0


def build_target_result(
    target: TargetConfig,
    metrics: dict[str, Any],
    duration: float,
    exit_code: Optional[int],
) -> dict[str, Any]:
    total_mutants = int(metrics.get("total_mutants", 0))
    killed = int(metrics.get("killed", 0))
    survived = int(metrics.get("survived", 0))
    timeout = int(metrics.get("timeout", 0))
    no_coverage = int(metrics.get("no_coverage", 0))

    resilience_score = (killed / total_mutants) if total_mutants > 0 else 0.0
    mutation_score = float(metrics.get("mutation_score", resilience_score * 100))
    baseline = target.baseline_score
    delta = None
    if baseline is not None:
        delta = resilience_score - baseline

    status = "pass" if resilience_score >= target.threshold else "fail"

    return {
        "name": target.name,
        "tool": target.tool,
        "parser": target.parser,
        "report_path": str(target.report_path),
        "threshold": target.threshold,
        "status": status,
        "resilience_score": resilience_score,
        "mutation_score": mutation_score,
        "duration_seconds": duration,
        "command_exit_code": exit_code,
        "baseline_score": baseline,
        "delta_vs_baseline": delta,
        "stats": {
            "total_mutants": total_mutants,
            "killed": killed,
            "survived": survived,
            "timeout": timeout,
            "no_coverage": no_coverage,
        },
        "labels": target.labels,
    }


def aggregate_results(target_results: list[dict[str, Any]], *, min_resilience: float) -> dict[str, Any]:
    total_mutants = sum(t["stats"]["total_mutants"] for t in target_results)
    total_killed = sum(t["stats"]["killed"] for t in target_results)
    weighted_resilience = (total_killed / total_mutants) if total_mutants > 0 else 0.0
    status = "pass" if all(t["status"] == "pass" for t in target_results) else "fail"
    meets_min_resilience = weighted_resilience >= min_resilience
    if status == "pass" and not meets_min_resilience:
        status = "fail"
    return {
        "resilience_score": weighted_resilience,
        "status": status,
        "total_mutants": total_mutants,
        "total_killed": total_killed,
        "min_resilience": min_resilience,
        "meets_min_resilience": meets_min_resilience,
    }


def format_markdown(run: dict[str, Any]) -> str:
    repo = _escape_markdown(run.get("repo", "unknown"))
    branch = _escape_markdown(run.get("branch", "unknown"))
    commit = _escape_markdown(run.get("commit_sha", "unknown"))
    run_id = _escape_markdown(run.get("run_id", "unknown"))
    lines = [
        "## Mutation Observatory",
        f"- Run ID: `{run_id}`",
        f"- Repo: `{repo}` @ `{branch}` ({commit})",
        f"- Overall resilience: {run['resilience_score']:.1%} ({run['status'].upper()})",
        "",
        "| Target | Tool | Resilience | Threshold | Status | Killed / Total |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for target in run["targets"]:
        stats = target["stats"]
        name = _escape_markdown(target["name"])
        tool = _escape_markdown(target["tool"])
        status = _escape_markdown(target["status"].upper())
        lines.append(
            f"| {name} | {tool} | {target['resilience_score']:.1%} | "
            f"{target['threshold']:.0%} | {status} | "
            f"{stats['killed']} / {stats['total_mutants']} |"
        )
    return "\n".join(lines)


def run_observatory(
    config_path: Path,
    *,
    repo: Optional[str],
    branch: Optional[str],
    commit_sha: Optional[str],
    run_id: Optional[str],
) -> dict[str, Any]:
    meta, targets = load_config(config_path)

    repo_val = repo or meta.get("repo") or os.environ.get("CI_REPOSITORY", "unknown")
    branch_val = branch or meta.get("branch") or os.environ.get("CI_BRANCH", "unknown")
    commit_val = commit_sha or meta.get("commit_sha") or os.environ.get("GIT_SHA", "unknown")
    run_identifier = run_id or str(uuid.uuid4())

    target_results: list[dict[str, Any]] = []

    for target in targets:
        duration, exit_code = run_command(
            target.command or [],
            target.workdir,
            target.env,
            timeout=target.timeout_seconds,
            target_name=target.name,
        )
        if exit_code not in (None, 0):
            if target.allow_stale_reports:
                print(
                    f"[mutation_observatory] reusing existing report for target '{target.name}' despite exit code {exit_code}",
                    file=sys.stderr,
                )
            else:
                raise MutationObservatoryError(
                    f"command for target '{target.name}' exited with code {exit_code}; "
                    "set allow_stale_report=true to reuse a previous report"
                )
        metrics = parse_report(target.parser, target.report_path)
        target_results.append(build_target_result(target, metrics, duration, exit_code))

    min_resilience = _coerce_float(
        meta.get("min_resilience", 0.7),
        default=0.7,
        key="config.min_resilience",
        min_value=0.0,
        max_value=1.0,
    )
    aggregate = aggregate_results(target_results, min_resilience=min_resilience)

    run = {
        "schema": "mutation_run.v1",
        "run_id": run_identifier,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repo": repo_val,
        "branch": branch_val,
        "commit_sha": commit_val,
        "resilience_score": aggregate["resilience_score"],
        "status": aggregate["status"],
        "min_resilience": aggregate["min_resilience"],
        "meets_min_resilience": aggregate["meets_min_resilience"],
        "targets": target_results,
    }
    return run


def write_outputs(
    run: dict[str, Any],
    *,
    output_path: Path,
    ndjson_path: Optional[Path],
    markdown_path: Optional[Path],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(run, indent=2) + "\n")

    if ndjson_path:
        ndjson_path.parent.mkdir(parents=True, exist_ok=True)
        with ndjson_path.open("a") as handle:
            handle.write(json.dumps(run) + "\n")

    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(format_markdown(run) + "\n")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run mutation analyzers and emit mutation_run telemetry"
    )
    parser.add_argument("--config", required=True, type=Path, help="Path to observatory YAML config")
    parser.add_argument("--output", required=True, type=Path, help="Destination JSON file")
    parser.add_argument("--ndjson", type=Path, help="Optional NDJSON append-only log")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown summary output")
    parser.add_argument("--repo", help="Override repo slug (owner/name)")
    parser.add_argument("--branch", help="Override git branch")
    parser.add_argument("--commit-sha", help="Override commit SHA")
    parser.add_argument("--run-id", help="Override UUID for this run")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        run = run_observatory(
            args.config,
            repo=args.repo,
            branch=args.branch,
            commit_sha=args.commit_sha,
            run_id=args.run_id,
        )
        write_outputs(
            run,
            output_path=args.output,
            ndjson_path=args.ndjson,
            markdown_path=args.markdown,
        )
        if run.get("status") != "pass":
            print(
                "[mutation_observatory] failing gate: one or more targets fell below the configured threshold",
                file=sys.stderr,
            )
            return 3
        return 0
    except MutationObservatoryError as exc:
        print(f"[mutation_observatory] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
