#!/usr/bin/env python3
"""
Aggregate project-ci workflow results into JSON + Markdown.

This script consumes:
- Per-repo metadata captured in artifacts/summary/*.json
- Downloaded artifacts for each repo (project-ci-<name>/*)

Outputs:
- A consolidated JSON summary file.
- Markdown suitable for GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from defusedxml import ElementTree as ET


@dataclass
class JUnitStats:
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def passed(self) -> int:
        return self.tests - self.failures - self.errors - self.skipped

    def as_dict(self) -> Dict[str, int]:
        return {
            "tests": self.tests,
            "failures": self.failures,
            "errors": self.errors,
            "skipped": self.skipped,
            "passed": self.passed,
        }


@dataclass
class RepoSummary:
    name: str
    repo: str
    language: str
    status: str
    artifact: str
    junit: Optional[JUnitStats] = None
    coverage_py: Optional[float] = None
    line_coverage: Optional[float] = None
    spotbugs: Optional[int] = None
    bandit: Optional[Dict[str, int]] = None
    ruff_issues: Optional[int] = None
    pip_audit: Optional[int] = None
    depcheck: Optional[Dict[str, int]] = None
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "repo": self.repo,
            "language": self.language,
            "status": self.status,
            "artifact": self.artifact,
            "junit": self.junit.as_dict() if self.junit else None,
            "coverage_py": self.coverage_py,
            "line_coverage": self.line_coverage,
            "spotbugs": self.spotbugs,
            "bandit": self.bandit,
            "ruff_issues": self.ruff_issues,
            "pip_audit": self.pip_audit,
            "depcheck": self.depcheck,
            "notes": self.notes,
        }


def _glob_files(base: Path, pattern: str) -> List[Path]:
    pattern = (pattern or "").strip()
    if not pattern:
        return []
    path_pattern = Path(pattern)
    if path_pattern.is_absolute():
        return [path_pattern] if path_pattern.is_file() else []
    normalized = str(path_pattern).lstrip("./")
    if not normalized:
        return []
    return [p for p in base.glob(normalized) if p.is_file()]


def _ensure_str_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, str)]
    return []


def _dedupe_paths(paths: List[Path]) -> List[Path]:
    seen: Set[str] = set()
    deduped: List[Path] = []
    for path in paths:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _collect_artifact_files(
    entry: Dict[str, object],
    key: str,
    artifacts_root: Path,
    artifact_dir: Optional[Path],
    fallback_pattern: Optional[object] = None,
) -> tuple[List[Path], bool]:
    matches: List[Path] = []
    roots: List[Path] = []
    artifact_dir_exists = artifact_dir is not None and artifact_dir.is_dir()
    if artifact_dir_exists:
        roots.append(artifact_dir)
    else:
        roots.append(artifacts_root)

    patterns = _ensure_str_list(entry.get(key))
    expected = bool(patterns)
    for root in roots:
        for pattern in patterns:
            matches.extend(_glob_files(root, pattern))

    fallback_patterns = _ensure_str_list(fallback_pattern)
    if fallback_patterns and artifact_dir_exists:
        for pattern in fallback_patterns:
            matches.extend(_glob_files(artifact_dir, pattern))
        expected = True

    return _dedupe_paths(matches), expected


def parse_junit(files: List[Path]) -> Optional[JUnitStats]:
    """Sum tests/failures/errors/skipped across junit XML files."""
    if not files:
        return None

    stats = JUnitStats()
    for file in files:
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue

        suites = []
        if root.tag == "testsuites":
            suites = root.findall("testsuite")
        elif root.tag == "testsuite":
            suites = [root]

        for suite in suites:
            stats.tests += int(suite.attrib.get("tests", 0))
            stats.failures += int(suite.attrib.get("failures", 0))
            stats.errors += int(suite.attrib.get("errors", 0))
            stats.skipped += int(suite.attrib.get("skipped", 0))

    return stats


def parse_jacoco(files: List[Path]) -> Optional[float]:
    """
    Return line coverage percent from the first JaCoCo report that contains counters.
    """
    for file in files:
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue

        for counter in root.iter("counter"):
            if counter.attrib.get("type") != "LINE":
                continue
            missed = int(counter.attrib.get("missed", 0))
            covered = int(counter.attrib.get("covered", 0))
            total = missed + covered
            if total == 0:
                continue
            return round((covered / total) * 100, 1)
    return None


def parse_coverage_py(files: List[Path]) -> Optional[float]:
    """
    Return line coverage percent from coverage.py XML (first valid file).
    """
    for file in files:
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        lines_valid = root.attrib.get("lines-valid")
        lines_covered = root.attrib.get("lines-covered")
        if lines_valid is None or lines_covered is None:
            continue
        valid = int(float(lines_valid))
        covered = int(float(lines_covered))
        total = valid
        if total == 0:
            continue
        return round((covered / total) * 100, 1)
    return None


def parse_spotbugs(files: List[Path]) -> Optional[int]:
    if not files:
        return None
    total = 0
    for file in files:
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        total += len(root.findall(".//BugInstance"))
    return total


def parse_bandit(files: List[Path]) -> Optional[Dict[str, int]]:
    """Return counts by severity from bandit JSON (first file found)."""
    for file in files:
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        results = data.get("results", [])
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for item in results:
            sev = item.get("issue_severity", "").upper()
            if sev in counts:
                counts[sev] += 1
        return counts
    return None


def parse_ruff(files: List[Path]) -> Optional[int]:
    """Return total ruff issues from JSON output."""
    for file in files:
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, list):
            return len(data)
    return None


def parse_pip_audit(files: List[Path]) -> Optional[int]:
    """Return vulnerability count from pip-audit JSON."""
    for file in files:
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        # pip-audit JSON is a list of packages with vulnerabilities array
        if isinstance(data, list):
            vulns = 0
            for pkg in data:
                vulns += len(pkg.get("vulns", []))
            return vulns
    return None


def parse_depcheck(files: List[Path]) -> Optional[Dict[str, int]]:
    """Return severity counts from OWASP Dependency-Check XML."""
    for file in files:
        suffix = file.suffix.lower()
        if suffix == ".xml":
            try:
                root = ET.parse(file).getroot()
            except ET.ParseError:
                continue
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for vuln in root.findall(".//vulnerability"):
                sev = (vuln.findtext("severity") or "").upper()
                if sev in counts:
                    counts[sev] += 1
            return counts
        if suffix in {".html", ".htm"}:
            counts = _parse_depcheck_html(file)
            if counts:
                return counts
    return None


def _parse_depcheck_html(file: Path) -> Optional[Dict[str, int]]:
    """Parse severity counts from the HTML summary table."""
    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    from html.parser import HTMLParser
    from html import unescape

    class _SummaryParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.in_table = False
            self.in_td_stack: List[str] = []
            self.current_row: List[str] = []
            self.rows: List[List[str]] = []

        def handle_starttag(self, tag: str, attrs: List[tuple[str, str]]) -> None:
            if tag == "table":
                for key, value in attrs:
                    if key == "id" and value == "summaryTable":
                        self.in_table = True
            if self.in_table and tag == "tr":
                self.current_row = []
            if self.in_table and tag == "td":
                self.in_td_stack.append("")

        def handle_data(self, data: str) -> None:
            if not self.in_td_stack:
                return
            self.in_td_stack[-1] += data

        def handle_endtag(self, tag: str) -> None:
            if tag == "td" and self.in_td_stack:
                data = unescape(self.in_td_stack.pop()).strip()
                self.current_row.append(data)
            if tag == "tr" and self.in_table:
                if self.current_row:
                    self.rows.append(self.current_row)
                self.current_row = []
            if tag == "table" and self.in_table:
                self.in_table = False

    parser = _SummaryParser()
    try:
        parser.feed(text)
    except Exception:
        return None

    if not parser.rows:
        return None

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for row in parser.rows:
        if len(row) < 4:
            continue
        severity_text = row[3].upper()
        matched = None
        for key in counts:
            if key in severity_text:
                matched = key
                break
        if matched:
            counts[matched] += 1
    if any(counts.values()):
        return counts
    return None


def load_repo_entries(summary_dir: Path) -> List[Dict[str, object]]:
    entries = []
    for file in sorted(summary_dir.rglob("*.json")):
        with open(file) as f:
            entries.append(json.load(f))
    return entries


def write_empty_summary(json_output: Path, markdown_output: Path) -> None:
    empty_msg = "No summary artifacts found."
    with open(json_output, "w") as f:
        json.dump([], f, indent=2)
    with open(markdown_output, "w") as f:
        f.write("## Project CI Summary\n\n_No summary artifacts found._\n")
    print(empty_msg, file=sys.stderr)


def build_summaries(entries: List[Dict[str, object]], artifacts_root: Path) -> List[RepoSummary]:
    summaries: List[RepoSummary] = []
    for entry in entries:
        name = entry.get("name") or entry.get("repo", "").split("/")[-1]
        artifact_name = entry.get("artifact") or f"project-ci-{name}"
        artifact_dir = artifacts_root / artifact_name if artifact_name else None
        language = entry.get("language", "unknown")
        language_lower = language.lower() if isinstance(language, str) else "unknown"
        python_repo = language_lower == "python"
        java_repo = language_lower == "java"

        junit_files, junit_expected = _collect_artifact_files(
            entry,
            "junit",
            artifacts_root,
            artifact_dir,
            ["**/junit.xml", "**/TEST-*.xml"],
        )
        jacoco_files, jacoco_expected = _collect_artifact_files(
            entry,
            "jacoco",
            artifacts_root,
            artifact_dir,
            ["**/jacoco.xml", "**/jacoco*.xml"] if java_repo else None,
        )
        coverage_py_files, coverage_expected = _collect_artifact_files(
            entry,
            "coverage_py",
            artifacts_root,
            artifact_dir,
            ["**/coverage.xml"] if python_repo else None,
        )
        spotbugs_files, spotbugs_expected = _collect_artifact_files(
            entry,
            "spotbugs",
            artifacts_root,
            artifact_dir,
            ["**/spotbugsXml.xml"] if java_repo else None,
        )
        bandit_files, bandit_expected = _collect_artifact_files(
            entry,
            "bandit",
            artifacts_root,
            artifact_dir,
            ["**/bandit*.json"] if python_repo else None,
        )
        ruff_files, ruff_expected = _collect_artifact_files(
            entry,
            "ruff",
            artifacts_root,
            artifact_dir,
            ["**/ruff*.json"] if python_repo else None,
        )
        pip_audit_files, pip_audit_expected = _collect_artifact_files(
            entry,
            "pip_audit",
            artifacts_root,
            artifact_dir,
            ["**/pip-audit*.json"] if python_repo else None,
        )
        depcheck_files, depcheck_expected = _collect_artifact_files(
            entry,
            "depcheck",
            artifacts_root,
            artifact_dir,
            ["**/dependency-check-report.xml", "**/dependency-check-report.html"] if java_repo else None,
        )

        junit_stats = parse_junit(junit_files)
        line_cov = parse_jacoco(jacoco_files) if jacoco_files else None
        coverage_py = parse_coverage_py(coverage_py_files) if coverage_py_files else None
        spotbugs = parse_spotbugs(spotbugs_files)
        bandit = parse_bandit(bandit_files)
        ruff_issues = parse_ruff(ruff_files)
        pip_audit = parse_pip_audit(pip_audit_files)
        depcheck = parse_depcheck(depcheck_files)

        summary = RepoSummary(
            name=name,
            repo=entry.get("repo", name),
            language=language,
            status=entry.get("status", "unknown"),
            artifact=artifact_name,
            junit=junit_stats,
            coverage_py=coverage_py,
            line_coverage=line_cov,
            spotbugs=spotbugs,
            bandit=bandit,
            ruff_issues=ruff_issues,
            pip_audit=pip_audit,
            depcheck=depcheck,
        )

        if not junit_files and (language_lower in {"python", "java"} or junit_expected):
            summary.notes.append("No JUnit XML found")
        if not jacoco_files and (language_lower == "java" or jacoco_expected):
            summary.notes.append("Jacoco XML missing")
        if not spotbugs_files and (language_lower == "java" or spotbugs_expected):
            summary.notes.append("SpotBugs XML missing")
        if not bandit_files and (language_lower == "python" or bandit_expected):
            summary.notes.append("Bandit report missing")
        if not ruff_files and (language_lower == "python" or ruff_expected):
            summary.notes.append("Ruff report missing")
        if not coverage_py_files and (language_lower == "python" or coverage_expected):
            summary.notes.append("Coverage (coverage.py) missing")
        if not pip_audit_files and (language_lower == "python" or pip_audit_expected):
            summary.notes.append("pip-audit report missing")
        if not depcheck_files and (language_lower == "java" or depcheck_expected):
            summary.notes.append("Dependency-Check report missing")

        summaries.append(summary)
    return summaries


def render_markdown(summaries: List[RepoSummary]) -> str:
    lines = ["## Project CI Summary", ""]
    lines.append("| Repo | Lang | Status | Tests (pass/fail/error/skip) | Line Cov (Java) | Line Cov (Py) | SpotBugs | Bandit | Ruff | pip-audit | DepCheck | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for s in summaries:
        if s.junit:
            tests_str = f"{s.junit.passed}/{s.junit.failures}/{s.junit.errors}/{s.junit.skipped} (total {s.junit.tests})"
        else:
            tests_str = "n/a"
        cov_str = f"{s.line_coverage:.1f}%" if s.line_coverage is not None else "n/a"
        cov_py_str = f"{s.coverage_py:.1f}%" if s.coverage_py is not None else "n/a"
        spotbugs_str = str(s.spotbugs) if s.spotbugs is not None else "n/a"
        if s.bandit:
            bandit_str = f"L{s.bandit.get('LOW', 0)}/M{s.bandit.get('MEDIUM', 0)}/H{s.bandit.get('HIGH', 0)}"
        else:
            bandit_str = "n/a"
        ruff_str = str(s.ruff_issues) if s.ruff_issues is not None else "n/a"
        pip_audit_str = str(s.pip_audit) if s.pip_audit is not None else "n/a"
        if s.depcheck:
            dep_str = f"C{s.depcheck.get('CRITICAL',0)}/H{s.depcheck.get('HIGH',0)}/M{s.depcheck.get('MEDIUM',0)}/L{s.depcheck.get('LOW',0)}"
        else:
            dep_str = "n/a"
        notes = "; ".join(s.notes) if s.notes else ""
        lines.append(
            f"| {s.repo} | {s.language} | {s.status} | {tests_str} | {cov_str} | {cov_py_str} | {spotbugs_str} | {bandit_str} | {ruff_str} | {pip_audit_str} | {dep_str} | {notes} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build aggregated project CI summary.")
    parser.add_argument("--summary-dir", required=True, help="Directory containing per-repo JSON summaries.")
    parser.add_argument("--artifacts-root", required=True, help="Directory containing downloaded artifacts.")
    parser.add_argument("--json-output", required=True, help="Path to write consolidated JSON.")
    parser.add_argument("--markdown-output", required=True, help="Path to write markdown summary.")
    args = parser.parse_args()

    summary_dir = Path(args.summary_dir)
    artifacts_root = Path(args.artifacts_root)
    json_output = Path(args.json_output)
    markdown_output = Path(args.markdown_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    if not summary_dir.exists():
        write_empty_summary(json_output, markdown_output)
        return 0

    entries = load_repo_entries(summary_dir)
    if not entries:
        write_empty_summary(json_output, markdown_output)
        return 0

    summaries = build_summaries(entries, artifacts_root)

    with open(json_output, "w") as f:
        json.dump([s.as_dict() for s in summaries], f, indent=2)

    md = render_markdown(summaries)
    with open(markdown_output, "w") as f:
        f.write(md)

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
