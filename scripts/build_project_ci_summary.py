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
from typing import Dict, List, Optional

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
    line_coverage: Optional[float] = None
    spotbugs: Optional[int] = None
    bandit: Optional[Dict[str, int]] = None
    ruff_issues: Optional[int] = None
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "repo": self.repo,
            "language": self.language,
            "status": self.status,
            "artifact": self.artifact,
            "junit": self.junit.as_dict() if self.junit else None,
            "line_coverage": self.line_coverage,
            "spotbugs": self.spotbugs,
            "bandit": self.bandit,
            "ruff_issues": self.ruff_issues,
            "notes": self.notes,
        }


def _glob_files(base: Path, pattern: str) -> List[Path]:
    return list(base.glob(pattern))


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


def load_repo_entries(summary_dir: Path) -> List[Dict[str, object]]:
    entries = []
    for file in sorted(summary_dir.glob("*.json")):
        with open(file) as f:
            entries.append(json.load(f))
    return entries


def build_summaries(entries: List[Dict[str, object]], artifacts_root: Path) -> List[RepoSummary]:
    summaries: List[RepoSummary] = []
    for entry in entries:
        name = entry.get("name") or entry.get("repo", "").split("/")[-1]
        artifact = entry.get("artifact") or f"project-ci-{name}"
        base = artifacts_root / artifact

        junit_files = _glob_files(base, "**/junit.xml")
        jacoco_files = _glob_files(base, "**/jacoco.xml")
        spotbugs_files = _glob_files(base, "**/spotbugsXml.xml")
        bandit_files = _glob_files(base, "**/bandit.json")
        ruff_files = _glob_files(base, "**/ruff.json")

        junit_stats = parse_junit(junit_files)
        line_cov = parse_jacoco(jacoco_files) if jacoco_files else None
        spotbugs = parse_spotbugs(spotbugs_files)
        bandit = parse_bandit(bandit_files)
        ruff_issues = parse_ruff(ruff_files)

        summary = RepoSummary(
            name=name,
            repo=entry.get("repo", name),
            language=entry.get("language", "unknown"),
            status=entry.get("status", "unknown"),
            artifact=artifact,
            junit=junit_stats,
            line_coverage=line_cov,
            spotbugs=spotbugs,
            bandit=bandit,
            ruff_issues=ruff_issues,
        )

        if not junit_files:
            summary.notes.append("No JUnit XML found")
        if entry.get("language") == "java" and not jacoco_files:
            summary.notes.append("Jacoco XML missing")
        if entry.get("language") == "java" and not spotbugs_files:
            summary.notes.append("SpotBugs XML missing")
        if entry.get("language") == "python" and not bandit_files:
            summary.notes.append("Bandit report missing")
        if entry.get("language") == "python" and not ruff_files:
            summary.notes.append("Ruff report missing")

        summaries.append(summary)
    return summaries


def render_markdown(summaries: List[RepoSummary]) -> str:
    lines = ["## Project CI Summary", ""]
    lines.append("| Repo | Lang | Status | Tests (pass/fail/error/skip) | Line Cov | SpotBugs | Bandit | Ruff | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for s in summaries:
        if s.junit:
            tests_str = f"{s.junit.passed}/{s.junit.failures}/{s.junit.errors}/{s.junit.skipped} (total {s.junit.tests})"
        else:
            tests_str = "n/a"
        cov_str = f"{s.line_coverage:.1f}%" if s.line_coverage is not None else "n/a"
        spotbugs_str = str(s.spotbugs) if s.spotbugs is not None else "n/a"
        if s.bandit:
            bandit_str = f"L{s.bandit.get('LOW', 0)}/M{s.bandit.get('MEDIUM', 0)}/H{s.bandit.get('HIGH', 0)}"
        else:
            bandit_str = "n/a"
        ruff_str = str(s.ruff_issues) if s.ruff_issues is not None else "n/a"
        notes = "; ".join(s.notes) if s.notes else ""
        lines.append(
            f"| {s.repo} | {s.language} | {s.status} | {tests_str} | {cov_str} | {spotbugs_str} | {bandit_str} | {ruff_str} | {notes} |"
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
    Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown_output).parent.mkdir(parents=True, exist_ok=True)

    if not summary_dir.exists():
        empty_msg = "No summary artifacts found."
        json.dump([], open(args.json_output, "w"), indent=2)
        with open(args.markdown_output, "w") as f:
            f.write("## Project CI Summary\n\n_No summary artifacts found._\n")
        print(empty_msg, file=sys.stderr)
        return 0

    entries = load_repo_entries(summary_dir)
    summaries = build_summaries(entries, artifacts_root)

    with open(args.json_output, "w") as f:
        json.dump([s.as_dict() for s in summaries], f, indent=2)

    md = render_markdown(summaries)
    with open(args.markdown_output, "w") as f:
        f.write(md)

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
