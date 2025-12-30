"""ADR (Architecture Decision Records) management commands."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult, hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

ADR_DIR = "docs/adr"
ADR_PATTERN = re.compile(r"^(\d{4})-(.+)\.md$")
STATUS_PATTERN = re.compile(
    r"^\*\*Status:?\*\*:?\s*(.+)$", re.MULTILINE | re.IGNORECASE
)
DATE_PATTERN = re.compile(r"^\*\*Date:?\*\*:?\s*(\S+)", re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCED_BLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
REFERENCE_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)


def _strip_fenced_blocks(content: str) -> str:
    return FENCED_BLOCK_RE.sub("", content)


def _link_is_external(link_target: str) -> bool:
    return link_target.startswith(("http://", "https://", "mailto:", "tel:"))


def _normalize_link_target(link_target: str) -> str:
    cleaned = link_target.split("#", 1)[0]
    return cleaned.split("?", 1)[0]


def _resolve_link(adr_path: Path, repo_root: Path, link_target: str) -> Path:
    if link_target.startswith("/"):
        return (repo_root / link_target.lstrip("/")).resolve()
    return (adr_path.parent / link_target).resolve()


def _get_adr_dir() -> Path:
    """Return the ADR directory path."""
    return hub_root() / ADR_DIR


def _get_next_number() -> int:
    """Get the next ADR number based on existing files."""
    adr_dir = _get_adr_dir()
    if not adr_dir.exists():
        return 1

    max_num = 0
    for f in adr_dir.glob("*.md"):
        match = ADR_PATTERN.match(f.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    return max_num + 1


def _slugify(title: str) -> str:
    """Convert title to filename-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _parse_adr(path: Path) -> dict[str, Any]:
    """Parse ADR metadata from a file."""
    content = path.read_text(encoding="utf-8")

    status_match = STATUS_PATTERN.search(content)
    date_match = DATE_PATTERN.search(content)
    name_match = ADR_PATTERN.match(path.name)

    # Extract title from first H1
    title_match = re.search(r"^#\s+ADR-\d+:\s*(.+)$", content, re.MULTILINE)

    return {
        "file": path.name,
        "number": int(name_match.group(1)) if name_match else 0,
        "title": title_match.group(1).strip() if title_match else path.stem,
        "status": status_match.group(1).strip() if status_match else "unknown",
        "date": date_match.group(1).strip() if date_match else "",
        "path": str(path),
    }


def _check_adr_links(adr_path: Path) -> list[dict[str, Any]]:
    """Check that all internal links in an ADR are valid."""
    problems: list[dict[str, Any]] = []
    repo_root = adr_path.parents[2]
    content = adr_path.read_text(encoding="utf-8")
    content = _strip_fenced_blocks(content)

    for match in REFERENCE_DEF_RE.finditer(content):
        ref_id, link_target = match.groups()
        if link_target.startswith("#") or _link_is_external(link_target):
            continue
        target_path = _normalize_link_target(link_target)
        if not target_path:
            continue
        resolved = _resolve_link(adr_path, repo_root, target_path)
        if not resolved.exists():
            problems.append(
                {
                    "severity": "error",
                    "message": f"Broken link in {adr_path.name}: [{ref_id}]: {link_target}",
                    "code": "CIHUB-ADR-BROKEN-LINK",
                    "file": str(adr_path),
                    "target": link_target,
                }
            )

    for match in MARKDOWN_LINK_RE.finditer(content):
        link_text, link_target = match.groups()

        # Skip external links, anchors-only, and mailto
        if link_target.startswith("#") or _link_is_external(link_target):
            continue

        # Handle anchor in link
        target_path = _normalize_link_target(link_target)
        if not target_path:
            continue

        # Resolve relative to the ADR file's directory
        resolved = _resolve_link(adr_path, repo_root, target_path)

        if not resolved.exists():
            problems.append(
                {
                    "severity": "error",
                    "message": f"Broken link in {adr_path.name}: [{link_text}]({link_target})",
                    "code": "CIHUB-ADR-BROKEN-LINK",
                    "file": str(adr_path),
                    "target": link_target,
                }
            )

    return problems


def cmd_adr_new(args: argparse.Namespace) -> int | CommandResult:
    """Create a new ADR from template with auto-numbering."""
    json_mode = getattr(args, "json", False)
    title = getattr(args, "title", "")
    dry_run = getattr(args, "dry_run", False)

    if not title:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Title is required",
                problems=[{"severity": "error", "message": "Title is required", "code": "CIHUB-ADR-NO-TITLE"}],
            )
        print("Error: title is required", file=sys.stderr)
        return EXIT_FAILURE

    adr_dir = _get_adr_dir()
    adr_dir.mkdir(parents=True, exist_ok=True)

    number = _get_next_number()
    slug = _slugify(title)
    filename = f"{number:04d}-{slug}.md"
    filepath = adr_dir / filename

    today = date.today().isoformat()
    content = f"""# ADR-{number:04d}: {title}

**Status**: Proposed
**Date:** {today}
**Developer:**
**Last Reviewed:** {today}

## Context

<!-- Describe the context and problem that led to this decision. -->

## Decision

<!-- Describe the decision that was made. -->

## Consequences

Positive:
-

Negative:
-

## Alternatives Considered

1. **Alternative 1**
   - Rejected:
"""

    if dry_run:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Would create: {filepath}",
                data={"file": str(filepath), "number": number, "title": title},
            )
        print(f"Would create: {filepath}")
        print("---")
        print(content)
        return EXIT_SUCCESS

    filepath.write_text(content, encoding="utf-8")

    # Update README.md index
    readme_path = adr_dir / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        # Find the template starter line and insert before it
        new_entry = f"- [ADR-{number:04d}: {title}]({filename})"

        template_marker = "Template starter:"
        if template_marker in readme_content:
            readme_content = readme_content.replace(
                template_marker,
                f"{new_entry}\n\n{template_marker}",
            )
            readme_path.write_text(readme_content, encoding="utf-8")

    summary = f"Created ADR: {filename}"
    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=summary,
            files_generated=[str(filepath)],
            data={"file": str(filepath), "number": number, "title": title},
        )

    print(summary)
    print(f"  Path: {filepath}")
    return EXIT_SUCCESS


def cmd_adr_list(args: argparse.Namespace) -> int | CommandResult:
    """List all ADRs with their status."""
    json_mode = getattr(args, "json", False)
    status_filter = getattr(args, "status", None)

    adr_dir = _get_adr_dir()
    if not adr_dir.exists():
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="No ADRs found",
                data={"adrs": []},
            )
        print("No ADRs found")
        return EXIT_SUCCESS

    adrs: list[dict[str, Any]] = []
    for f in sorted(adr_dir.glob("*.md")):
        if f.name == "README.md":
            continue
        if not ADR_PATTERN.match(f.name):
            continue

        adr = _parse_adr(f)
        if status_filter and adr["status"].lower() != status_filter.lower():
            continue
        adrs.append(adr)

    summary = f"Found {len(adrs)} ADRs"
    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=summary,
            data={"adrs": adrs},
        )

    if not adrs:
        print("No ADRs found")
        return EXIT_SUCCESS

    # Print table header
    print(f"{'#':>4}  {'Status':<12}  {'Date':<12}  Title")
    print("-" * 70)

    for adr in adrs:
        print(f"{adr['number']:>4}  {adr['status']:<12}  {adr['date']:<12}  {adr['title']}")

    print(f"\nTotal: {len(adrs)} ADRs")
    return EXIT_SUCCESS


def cmd_adr_check(args: argparse.Namespace) -> int | CommandResult:
    """Validate ADRs: check for broken links and required fields."""
    json_mode = getattr(args, "json", False)

    adr_dir = _get_adr_dir()
    if not adr_dir.exists():
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="No ADRs to check",
            )
        print("No ADRs to check")
        return EXIT_SUCCESS

    problems: list[dict[str, Any]] = []
    checked = 0

    for f in sorted(adr_dir.glob("*.md")):
        if f.name == "README.md":
            continue
        if not ADR_PATTERN.match(f.name):
            continue

        checked += 1
        adr = _parse_adr(f)

        # Check required fields
        if adr["status"] == "unknown":
            problems.append({
                "severity": "warning",
                "message": f"{f.name}: Missing Status field",
                "code": "CIHUB-ADR-MISSING-STATUS",
                "file": str(f),
            })

        if not adr["date"]:
            problems.append({
                "severity": "warning",
                "message": f"{f.name}: Missing Date field",
                "code": "CIHUB-ADR-MISSING-DATE",
                "file": str(f),
            })

        # Check internal links
        link_problems = _check_adr_links(f)
        problems.extend(link_problems)

    # Check README.md exists
    readme_path = adr_dir / "README.md"
    if not readme_path.exists():
        problems.append({
            "severity": "warning",
            "message": "ADR README.md is missing",
            "code": "CIHUB-ADR-MISSING-README",
        })

    errors = [p for p in problems if p["severity"] == "error"]
    warnings = [p for p in problems if p["severity"] == "warning"]

    if problems:
        summary = f"ADR check: {len(errors)} errors, {len(warnings)} warnings ({checked} checked)"
    else:
        summary = f"ADR check: OK ({checked} checked)"

    if json_mode:
        return CommandResult(
            exit_code=EXIT_FAILURE if errors else EXIT_SUCCESS,
            summary=summary,
            problems=problems,
            data={"checked": checked, "errors": len(errors), "warnings": len(warnings)},
        )

    if problems:
        print(summary)
        for problem in problems:
            severity = problem["severity"].upper()
            print(f"  [{severity}] {problem['message']}")
        return EXIT_FAILURE if errors else EXIT_SUCCESS

    print(summary)
    return EXIT_SUCCESS


def cmd_adr(args: argparse.Namespace) -> int | CommandResult:
    """Router for ADR subcommands."""
    subcommand = getattr(args, "subcommand", None)

    if subcommand == "new":
        return cmd_adr_new(args)
    elif subcommand == "list":
        return cmd_adr_list(args)
    elif subcommand == "check":
        return cmd_adr_check(args)
    else:
        # Default to list
        return cmd_adr_list(args)
