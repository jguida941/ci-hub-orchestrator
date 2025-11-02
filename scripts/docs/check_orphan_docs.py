#!/usr/bin/env python3
"""
Detect orphan documentation (not linked from anywhere).
Uses existing pyyaml from requirements-dev.txt.
"""

import sys
import re
from pathlib import Path
from typing import Set, List, Tuple

def log(message: str):
    """Log message to stderr."""
    print(f"[orphan-check] {message}", file=sys.stderr)

def find_markdown_links(content: str) -> List[str]:
    """Extract all markdown links from content."""
    # Match [text](link.md) patterns
    pattern = r'\[.*?\]\((.*?\.md[#\w-]*)\)'
    links = re.findall(pattern, content)

    # Also match raw references like "See START_HERE.md"
    raw_pattern = r'(?:See|see|refer to|Refer to)\s+([A-Z_]+\.md)'
    links.extend(re.findall(raw_pattern, content))

    # Also match quoted references like "docs/start-here.md"
    quoted_pattern = r'["\'`]([^"\'`]*\.md)["\'`]'
    links.extend(re.findall(quoted_pattern, content))

    return links

def resolve_link(source_file: Path, link: str) -> Path:
    """Resolve a relative link from a source file."""
    # Remove anchors (#section)
    link = link.split('#')[0]

    # Handle absolute paths from repo root
    if link.startswith('/'):
        return (source_file.parent / link.lstrip('/')).resolve()

    # Handle relative paths
    return (source_file.parent / link).resolve()

def find_all_markdown_files(root_dir: Path) -> Set[Path]:
    """Find all markdown files in the repository."""
    markdown_files = set()

    # Exclude certain directories
    exclude_dirs = {'.git', 'node_modules', '.venv', 'venv', '__pycache__'}

    for md_file in root_dir.rglob('*.md'):
        # Skip files in excluded directories
        if any(excluded in md_file.parts for excluded in exclude_dirs):
            continue
        markdown_files.add(md_file.resolve())

    return markdown_files

def find_referenced_files(markdown_files: Set[Path]) -> Set[Path]:
    """Find all markdown files that are referenced from somewhere."""
    referenced = set()

    for md_file in markdown_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            links = find_markdown_links(content)

            for link in links:
                try:
                    resolved = resolve_link(md_file, link)
                    if resolved.exists() and resolved.suffix == '.md':
                        referenced.add(resolved)
                except Exception:
                    # Skip invalid links
                    continue
        except Exception as e:
            log(f"Warning: Could not read {md_file}: {e}")

    return referenced

def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent.resolve()
    log(f"Checking for orphan documentation in {repo_root}")

    # Find all markdown files
    all_docs = find_all_markdown_files(repo_root)
    log(f"Found {len(all_docs)} markdown files")

    # Find all referenced docs
    referenced = find_referenced_files(all_docs)
    log(f"Found {len(referenced)} referenced markdown files")

    # Files that should never be considered orphans (entry points)
    never_orphan = {
        repo_root / 'README.md',
        repo_root / 'plan.md',
        repo_root / 'LICENSE.md',
        repo_root / 'SECURITY.md',
        repo_root / 'CONTRIBUTING.md',
        repo_root / 'CHANGELOG.md',
        repo_root / 'STRUCTURE.md',
        repo_root / 'docs' / 'index.md',
    }

    # Find orphans (files not referenced from anywhere)
    orphans = all_docs - referenced - never_orphan

    # Separate orphans by location
    root_orphans = []
    docs_orphans = []

    for orphan in orphans:
        rel_path = orphan.relative_to(repo_root)
        if rel_path.parent == Path('.'):
            root_orphans.append(rel_path)
        elif str(rel_path).startswith('docs/'):
            docs_orphans.append(rel_path)

    # Report findings
    exit_code = 0

    if docs_orphans:
        print("❌ Orphan documents in docs/ (not linked from anywhere):")
        for orphan in sorted(docs_orphans):
            print(f"  - {orphan}")
        print("\nFix suggestions:")
        print("  1. Add links to these files from docs/index.md or plan.md")
        print("  2. If obsolete, remove the files")
        print("  3. If intentionally standalone, add to never_orphan list")
        exit_code = 1

    if root_orphans:
        print("\n⚠️  Potential orphan documents in root (consider moving to docs/):")
        for orphan in sorted(root_orphans):
            print(f"  - {orphan}")

    if exit_code == 0:
        print("✅ No orphan documents found in docs/")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()