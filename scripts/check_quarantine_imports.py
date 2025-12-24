#!/usr/bin/env python3
"""
CI Guardrail: Fail if any file imports from _quarantine.

This script ensures quarantine remains cold storage, not executable code.
Run in CI before any other checks.

Usage:
    python scripts/check_quarantine_imports.py

Exit codes:
    0 - No quarantine imports found (safe)
    1 - Quarantine imports detected (FAIL)
"""

import os
import re
import sys
from pathlib import Path

# Match actual import statements, not comments or strings
# These patterns require the import keyword to be at the start of a line (after optional whitespace)
QUARANTINE_PATTERNS = [
    r"^\s*from\s+_quarantine\b",
    r"^\s*import\s+_quarantine\b",
    r"^\s*from\s+hub_release\._quarantine\b",
    r"^\s*import\s+hub_release\._quarantine\b",
    r"^\s*from\s+cihub\._quarantine\b",
    r"^\s*import\s+cihub\._quarantine\b",
    r"^\s*from\s+\.+_quarantine\b",
]

SCAN_EXTENSIONS = {".py"}

# Configurable via QUARANTINE_EXCLUDE_DIRS env var (comma-separated)
_DEFAULT_EXCLUDES = {"_quarantine", ".git", "__pycache__", ".pytest_cache", "node_modules", ".ruff_cache", "vendor", "generated"}
_env_excludes = os.environ.get("QUARANTINE_EXCLUDE_DIRS", "")
EXCLUDE_DIRS = _DEFAULT_EXCLUDES | (set(_env_excludes.split(",")) if _env_excludes else set())


def find_quarantine_imports(root: Path) -> list[tuple[Path, int, str]]:
    """Find all files that import from _quarantine."""
    violations = []

    for path in root.rglob("*"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue

        # Only check Python files
        if path.suffix not in SCAN_EXTENSIONS:
            continue

        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in QUARANTINE_PATTERNS:
                if re.search(pattern, line):
                    violations.append((path, line_num, line.strip()))

    return violations


def main() -> int:
    root = Path(__file__).parent.parent  # hub-release/
    violations = find_quarantine_imports(root)

    if not violations:
        print("Quarantine check PASSED - no imports from _quarantine found")
        return 0

    print("=" * 60)
    print("QUARANTINE IMPORT VIOLATION")
    print("=" * 60)
    print()
    print("Files importing from _quarantine detected!")
    print("_quarantine is COLD STORAGE - it must not be imported.")
    print()
    print("Violations:")
    print("-" * 60)

    for path, line_num, line in violations:
        rel_path = path.relative_to(root)
        print(f"  {rel_path}:{line_num}")
        print(f"    {line}")
        print()

    print("-" * 60)
    print(f"Total: {len(violations)} violation(s)")
    print()
    print("To fix:")
    print("  1. Graduate the file from _quarantine to its final location")
    print("  2. Update your import to use the new location")
    print("  3. See _quarantine/README.md for graduation process")
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
