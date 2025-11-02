#!/usr/bin/env python3
"""
Validate YAML frontmatter in documentation files.
Opt-in validation - initially only validates docs/, excludes legacy files.
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("ERROR: pyyaml is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

def log(message: str):
    """Log message to stderr."""
    print(f"[frontmatter-validate] {message}", file=sys.stderr)

# Files to exclude from validation (large legacy files)
EXCLUDED_FILES = {
    'README.md',
    'plan.md',
    'STRUCTURE.md',
    'CHANGELOG.md',
    'LICENSE.md',
    'SECURITY.md',
    'CONTRIBUTING.md',
}

# Required frontmatter fields
REQUIRED_FIELDS = ['status', 'owner', 'last-reviewed', 'next-review']

# Valid status values
VALID_STATUSES = ['Draft', 'Active', 'Deprecated', 'Review']

def extract_frontmatter(content: str) -> Optional[Dict]:
    """
    Extract YAML frontmatter from markdown content.
    Frontmatter must be at the start of the file, surrounded by ---
    """
    if not content.startswith('---\n'):
        return None

    # Find the closing ---
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter if isinstance(frontmatter, dict) else None
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

def validate_date_format(date_str: str) -> bool:
    """Validate date is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_owner_format(owner: str) -> bool:
    """Validate owner is in @username format or @team format."""
    return owner.startswith('@') and len(owner) > 1

def validate_frontmatter(frontmatter: Dict, file_path: Path) -> List[str]:
    """
    Validate frontmatter fields.
    Returns list of validation errors.
    """
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")

    # Validate status
    if 'status' in frontmatter:
        if frontmatter['status'] not in VALID_STATUSES:
            errors.append(f"Invalid status '{frontmatter['status']}'. Must be one of: {', '.join(VALID_STATUSES)}")

    # Validate owner
    if 'owner' in frontmatter:
        if not validate_owner_format(str(frontmatter['owner'])):
            errors.append(f"Invalid owner format '{frontmatter['owner']}'. Must start with @")

    # Validate dates
    for date_field in ['last-reviewed', 'next-review']:
        if date_field in frontmatter:
            if not validate_date_format(str(frontmatter[date_field])):
                errors.append(f"Invalid date format for {date_field}: '{frontmatter[date_field]}'. Use YYYY-MM-DD")

    # Check if next-review is in the future
    if 'next-review' in frontmatter and validate_date_format(str(frontmatter['next-review'])):
        next_review = datetime.strptime(str(frontmatter['next-review']), '%Y-%m-%d').date()
        today = datetime.now().date()
        if next_review < today:
            errors.append(f"next-review date {frontmatter['next-review']} is in the past")

    return errors

def should_validate_file(file_path: Path, repo_root: Path) -> bool:
    """
    Determine if a file should be validated.
    Initially only validates files in docs/, excludes legacy files.
    """
    rel_path = file_path.relative_to(repo_root)

    # Skip excluded files
    if file_path.name in EXCLUDED_FILES:
        return False

    # Skip files not in docs/ (opt-in approach)
    if not str(rel_path).startswith('docs/'):
        return False

    # Skip template files
    if 'template' in file_path.name.lower():
        return False

    return True

def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent.resolve()

    # Check if validation is enabled (via environment variable)
    if os.getenv('VALIDATE_FRONTMATTER', 'false').lower() != 'true':
        log("Frontmatter validation is disabled. Set VALIDATE_FRONTMATTER=true to enable.")
        sys.exit(0)

    log(f"Validating frontmatter in {repo_root}/docs/")

    # Find all markdown files
    all_errors = []
    files_checked = 0
    files_with_frontmatter = 0
    files_missing_frontmatter = []

    for md_file in repo_root.rglob('*.md'):
        # Skip files we shouldn't validate
        if not should_validate_file(md_file, repo_root):
            continue

        files_checked += 1
        rel_path = md_file.relative_to(repo_root)

        try:
            content = md_file.read_text(encoding='utf-8')
            frontmatter = extract_frontmatter(content)

            if frontmatter is None:
                # No frontmatter found
                files_missing_frontmatter.append(rel_path)
                log(f"Warning: No frontmatter in {rel_path}")
            else:
                files_with_frontmatter += 1
                # Validate the frontmatter
                errors = validate_frontmatter(frontmatter, md_file)
                if errors:
                    all_errors.append((rel_path, errors))

        except ValueError as e:
            # Malformed YAML
            all_errors.append((rel_path, [f"Malformed frontmatter: {e}"]))
        except Exception as e:
            log(f"Error reading {rel_path}: {e}")

    # Report results
    log(f"Checked {files_checked} files")
    log(f"Files with frontmatter: {files_with_frontmatter}")
    log(f"Files missing frontmatter: {len(files_missing_frontmatter)}")

    # Report missing frontmatter (warning only)
    if files_missing_frontmatter:
        print("\n⚠️  Files missing frontmatter (warning only):")
        for file_path in sorted(files_missing_frontmatter):
            print(f"  - {file_path}")
        print("\nTo add frontmatter, use this template:")
        print("---")
        print("status: Active")
        print("owner: @username")
        print("last-reviewed: 2025-11-02")
        print("next-review: 2025-12-02")
        print("---")

    # Report validation errors (these cause failure)
    if all_errors:
        print("\n❌ Frontmatter validation errors:")
        for file_path, errors in all_errors:
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ All frontmatter validation passed")
        sys.exit(0)

if __name__ == "__main__":
    import os
    main()