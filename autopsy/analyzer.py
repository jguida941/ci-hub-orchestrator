from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import yaml

DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules" / "default_rules.yml"
ALLOWED_SEVERITIES = {"info", "warn", "error"}
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}
LOG_EXTENSIONS = {".log", ".txt", ".out"}


@dataclass
class Rule:
    """Represents a single autopsy rule compiled for fast matching."""

    rule_id: str
    tool: str
    pattern: re.Pattern[str]
    severity: str
    suggestion: str | None
    docs_uri: str | None
    message_group: str | None
    file_globs: Sequence[str]

    def applies_to(self, path: Path) -> bool:
        if not self.file_globs:
            return True
        try:
            rel = path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            rel = Path(os.path.relpath(path, Path.cwd())).as_posix()
        for glob_pattern in self.file_globs:
            if fnmatch.fnmatch(path.name, glob_pattern) or fnmatch.fnmatch(rel, glob_pattern):
                return True
        return False


@dataclass
class Finding:
    tool: str
    pattern: str
    file: str
    line: int
    message: str
    suggestion: str | None
    severity: str
    docs_uri: str | None

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "tool": self.tool,
            "pattern": self.pattern,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity,
        }
        if self.suggestion:
            record["suggestion"] = self.suggestion
        if self.docs_uri:
            record["docs_uri"] = self.docs_uri
        return record


class RuleLoaderError(RuntimeError):
    """Raised when a rule definition cannot be parsed."""


def load_rules(path: Path) -> list[Rule]:
    """Load autopsy rules from a YAML file."""

    if not path.exists():
        raise RuleLoaderError(f"rules file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise RuleLoaderError("rules file must contain a list of rule entries")

    rules: list[Rule] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise RuleLoaderError(f"rule #{idx} must be a mapping")
        try:
            rule_id = str(entry["id"])
            tool = str(entry.get("tool", "unknown"))
            pattern_text = str(entry["pattern"])
        except KeyError as exc:
            raise RuleLoaderError(f"rule #{idx} missing required key: {exc}") from exc

        severity = str(entry.get("severity", "warn")).lower()
        if severity not in ALLOWED_SEVERITIES:
            raise RuleLoaderError(f"rule '{rule_id}' has invalid severity '{severity}'")

        flags_value = entry.get("flags", [])
        flags = _compile_flags(flags_value, rule_id)
        try:
            pattern = re.compile(pattern_text, flags)
        except re.error as exc:
            raise RuleLoaderError(f"rule '{rule_id}' has invalid regex: {exc}") from exc

        file_globs = entry.get("files") or []
        if file_globs and not isinstance(file_globs, (list, tuple)):
            raise RuleLoaderError(f"rule '{rule_id}' files must be a list")

        message_group = entry.get("message_group")
        if message_group is not None and not isinstance(message_group, str):
            raise RuleLoaderError(f"rule '{rule_id}' message_group must be a string")

        suggestion = entry.get("suggestion")
        if suggestion is not None and not isinstance(suggestion, str):
            raise RuleLoaderError(f"rule '{rule_id}' suggestion must be a string")

        docs_uri = entry.get("docs_uri")
        if docs_uri is not None and not isinstance(docs_uri, str):
            raise RuleLoaderError(f"rule '{rule_id}' docs_uri must be a string")

        rules.append(
            Rule(
                rule_id=rule_id,
                tool=tool,
                pattern=pattern,
                severity=severity,
                suggestion=suggestion,
                docs_uri=docs_uri,
                message_group=message_group,
                file_globs=tuple(str(item) for item in file_globs),
            )
        )
    return rules


def _compile_flags(flags_value: object, rule_id: str) -> int:
    if not flags_value:
        return 0
    if isinstance(flags_value, str):
        flags_value = [flags_value]
    if not isinstance(flags_value, (list, tuple)):
        raise RuleLoaderError(f"rule '{rule_id}' flags must be a string or list")

    flag_map = {
        "I": re.IGNORECASE,
        "IGNORECASE": re.IGNORECASE,
        "M": re.MULTILINE,
        "MULTILINE": re.MULTILINE,
        "S": re.DOTALL,
        "DOTALL": re.DOTALL,
    }
    flags = 0
    for raw_flag in flags_value:
        name = str(raw_flag).upper()
        value = flag_map.get(name)
        if value is None:
            raise RuleLoaderError(f"rule '{rule_id}' has unsupported regex flag '{raw_flag}'")
        flags |= value
    return flags


def discover_log_files(inputs: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            for candidate in item.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in LOG_EXTENSIONS:
                    files.append(candidate)
        else:
            print(f"[autopsy] warning: log path not found: {item}", file=sys.stderr)
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for file in files:
        if file not in seen:
            seen.add(file)
            unique_files.append(file)
    return unique_files


def analyze_logs(log_files: Sequence[Path], rules: Sequence[Rule]) -> list[Finding]:
    findings: list[Finding] = []
    seen_keys: set[tuple[str, str, int, str]] = set()
    cwd = Path.cwd()
    for log_file in log_files:
        if not log_file.exists():
            print(f"[autopsy] warning: skipping missing log file {log_file}", file=sys.stderr)
            continue
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            print(f"[autopsy] warning: failed to read {log_file}: {exc}", file=sys.stderr)
            continue
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.rstrip()
            if not line:
                continue
            for rule in rules:
                if not rule.applies_to(log_file):
                    continue
                match = rule.pattern.search(line)
                if not match:
                    continue
                if rule.message_group and rule.message_group in match.groupdict():
                    captured = match.group(rule.message_group)
                    message = captured.strip() if captured else line.strip()
                else:
                    message = line.strip()
                key = (rule.rule_id, str(log_file), line_number, message)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                try:
                    rel_file = log_file.relative_to(cwd).as_posix()
                except ValueError:
                    rel_file = Path(os.path.relpath(log_file, cwd)).as_posix()
                findings.append(
                    Finding(
                        tool=rule.tool,
                        pattern=rule.pattern.pattern,
                        file=rel_file,
                        line=line_number,
                        message=message,
                        suggestion=rule.suggestion,
                        severity=rule.severity,
                        docs_uri=rule.docs_uri,
                    )
                )
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.line, f.pattern))
    return findings


def build_report(
    *,
    findings: Sequence[Finding],
    repo: str,
    branch: str,
    commit_sha: str,
    run_id: str,
    sources: Sequence[Path],
) -> dict[str, object]:
    severity_counts = {"error": 0, "warn": 0, "info": 0}
    for finding in findings:
        if finding.severity in severity_counts:
            severity_counts[finding.severity] += 1

    cwd = Path.cwd()
    source_paths: list[str] = []
    for source in sources:
        try:
            source_paths.append(source.relative_to(cwd).as_posix())
        except ValueError:
            source_paths.append(Path(os.path.relpath(source, cwd)).as_posix())
    summary = {
        "total_findings": len(findings),
        "severity": severity_counts,
        "sources": source_paths,
    }
    report: dict[str, object] = {
        "schema": "autopsy.v1",
        "run_id": run_id,
        "repo": repo,
        "branch": branch,
        "commit_sha": commit_sha,
        "findings": [finding.to_record() for finding in findings],
        "summary": summary,
    }
    return report


def write_report(report: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_ndjson(findings: Sequence[Finding], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(finding.to_record()))
            handle.write("\n")


def write_summary(report: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    findings = report.get("findings", [])
    summary = report.get("summary", {})
    total = summary.get("total_findings", 0)
    lines: list[str] = [
        "# Pipeline Autopsy",
        "",
        f"- Run: `{report.get('run_id', '')}`",
        f"- Repo: `{report.get('repo', '')}` @ `{report.get('commit_sha', '')}`",
        f"- Findings: **{total}**",
        "",
    ]
    severity = summary.get("severity", {})
    if severity:
        lines.append("| Severity | Count |")
        lines.append("| --- | --- |")
        for label in ("error", "warn", "info"):
            lines.append(f"| {label.title()} | {severity.get(label, 0)} |")
        lines.append("")
    if not findings:
        lines.append("No root causes detected.")
    else:
        lines.append("## Top Findings")
        lines.append("")
        for finding in findings[:5]:
            location = f"{finding['file']}#L{finding['line']}"
            snippet = finding["message"]
            lines.append(f"- **{finding['severity'].upper()}** `{location}` — {snippet}")
        lines.append("")
    destination.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze pipeline logs and emit Autopsy findings.")
    parser.add_argument(
        "-l",
        "--log",
        dest="logs",
        action="append",
        type=Path,
        required=True,
        help="Log file or directory to scan (repeatable)",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help=f"Path to rules file (default: {DEFAULT_RULES_PATH})",
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report output path")
    parser.add_argument("--ndjson", type=Path, help="Optional NDJSON findings path")
    parser.add_argument("--summary", type=Path, help="Optional Markdown summary output path")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4()))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", ""))
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA", ""))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    log_files = discover_log_files(args.logs)
    rules = load_rules(args.rules)
    findings = analyze_logs(log_files, rules)
    report = build_report(
        findings=findings,
        repo=args.repo,
        branch=args.branch,
        commit_sha=args.commit_sha,
        run_id=str(args.run_id),
        sources=log_files,
    )
    write_report(report, args.output)
    if args.ndjson:
        write_ndjson(findings, args.ndjson)
    if args.summary:
        write_summary(report, args.summary)
    print(f"[autopsy] analyzed {len(log_files)} log files, findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
