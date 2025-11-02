#!/usr/bin/env bash
# Generate docs/index.md master index from all documentation files
# Parses frontmatter where available, falls back to file metadata

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INDEX_FILE="$REPO_ROOT/docs/index.md"

log() {
  echo "[generate-index] $*" >&2
}

# Extract frontmatter or first heading from markdown file
extract_metadata() {
  local file="$1"
  local rel_path="${file#$REPO_ROOT/}"
  local title=""
  local status="Active"
  local owner="@team"
  local last_reviewed="Unknown"

  # Try to extract title from first # heading
  if [[ -f "$file" ]]; then
    title=$(grep -m1 "^# " "$file" 2>/dev/null | sed 's/^# //' || echo "")

    # Try to extract status from structured header
    if grep -q "^**Status:" "$file" 2>/dev/null; then
      status=$(grep -m1 "^**Status:" "$file" | sed 's/.*Status:[[:space:]]*//' | cut -d' ' -f1)
    fi

    # Try to extract date from snapshot line
    if grep -q "^**Snapshot:" "$file" 2>/dev/null; then
      last_reviewed=$(grep -m1 "^**Snapshot:" "$file" | sed 's/.*Snapshot:[[:space:]]*//' | cut -d' ' -f1)
    elif grep -q "^Last updated:" "$file" 2>/dev/null; then
      last_reviewed=$(grep -m1 "^Last updated:" "$file" | sed 's/.*Last updated:[[:space:]]*//' | cut -d' ' -f1)
    fi
  fi

  # Fallback to filename if no title found
  if [[ -z "$title" ]]; then
    title=$(basename "$file" .md | tr '_-' ' ' | sed 's/\b\(.\)/\u\1/g')
  fi

  echo "$rel_path|$title|$status|$last_reviewed"
}

# Generate the index
{
  cat << 'HEADER'
# Documentation Index

This is the master index for all CI/CD Hub documentation. All documents should be linked from here or from plan.md.

---

## Quick Links

- [README](../README.md) - Project overview and quick start
- [Plan](../plan.md) - Strategic roadmap and architecture
- [Start Here](start-here.md) - Day 1 action plan
- [Structure](../STRUCTURE.md) - Repository file tree

---

## Documentation by Category

HEADER

  # Status Documents
  echo "### 📊 Status & Implementation"
  echo ""
  echo "| Document | Title | Status | Last Reviewed |"
  echo "|----------|-------|--------|---------------|"

  for file in "$REPO_ROOT"/docs/status/*.md; do
    if [[ -f "$file" ]]; then
      metadata=$(extract_metadata "$file")
      IFS='|' read -r path title status reviewed <<< "$metadata"
      # Make path relative to docs/
      rel_path="${path#docs/}"
      echo "| [$title]($rel_path) | $title | $status | $reviewed |"
    fi
  done

  echo ""

  # Analysis Documents
  echo "### 🔍 Analysis & Architecture"
  echo ""
  echo "| Document | Title | Status | Last Reviewed |"
  echo "|----------|-------|--------|---------------|"

  for file in "$REPO_ROOT"/docs/analysis/*.md; do
    if [[ -f "$file" ]]; then
      metadata=$(extract_metadata "$file")
      IFS='|' read -r path title status reviewed <<< "$metadata"
      rel_path="${path#docs/}"
      echo "| [$title]($rel_path) | $title | $status | $reviewed |"
    fi
  done

  echo ""

  # Operations Documents
  echo "### 🔧 Operations"
  echo ""
  echo "| Document | Title | Status | Last Reviewed |"
  echo "|----------|-------|--------|---------------|"

  for file in "$REPO_ROOT"/docs/ops/*.md "$REPO_ROOT"/docs/*.md; do
    if [[ -f "$file" ]] && [[ "$file" != "$INDEX_FILE" ]]; then
      # Skip if it's a subdirectory file we already processed
      if [[ "$file" =~ /docs/(status|analysis|audit|reference|adr|versions|modules)/ ]]; then
        continue
      fi
      metadata=$(extract_metadata "$file")
      IFS='|' read -r path title status reviewed <<< "$metadata"
      rel_path="${path#docs/}"
      echo "| [$title]($rel_path) | $title | $status | $reviewed |"
    fi
  done

  echo ""

  # Module Documents
  if [[ -d "$REPO_ROOT/docs/modules" ]]; then
    echo "### 📦 Module Documentation"
    echo ""
    echo "| Module | Description |"
    echo "|--------|-------------|"

    for file in "$REPO_ROOT"/docs/modules/*.md; do
      if [[ -f "$file" ]]; then
        title=$(basename "$file" .md | tr '_' ' ' | sed 's/\b\(.\)/\u\1/g')
        desc=$(grep -m1 "^#" "$file" 2>/dev/null | sed 's/^#[[:space:]]*//' || echo "$title")
        rel_path="modules/$(basename "$file")"
        echo "| [$title]($rel_path) | $desc |"
      fi
    done
    echo ""
  fi

  # Audit Trail (if exists)
  if [[ -d "$REPO_ROOT/docs/audit" ]] && ls "$REPO_ROOT"/docs/audit/*.md &>/dev/null; then
    echo "### 🔐 Audit Trail"
    echo ""
    for file in "$REPO_ROOT"/docs/audit/*.md; do
      if [[ -f "$file" ]]; then
        title=$(basename "$file" .md | tr '_-' ' ' | sed 's/\b\(.\)/\u\1/g')
        rel_path="audit/$(basename "$file")"
        echo "- [$title]($rel_path)"
      fi
    done
    echo ""
  fi

  # ADRs (if exists)
  if [[ -d "$REPO_ROOT/docs/adr" ]] && ls "$REPO_ROOT"/docs/adr/*.md &>/dev/null; then
    echo "### 📝 Architecture Decision Records"
    echo ""
    for file in "$REPO_ROOT"/docs/adr/*.md; do
      if [[ -f "$file" ]] && [[ "$(basename "$file")" != "README.md" ]] && [[ "$(basename "$file")" != "template.md" ]]; then
        title=$(grep -m1 "^#" "$file" 2>/dev/null | sed 's/^#[[:space:]]*//' || basename "$file" .md)
        rel_path="adr/$(basename "$file")"
        echo "- [$title]($rel_path)"
      fi
    done
    echo ""
  fi

  # Footer
  cat << 'FOOTER'
---

## Document Governance

All documentation in this repository follows these standards:

- **Review Cycle**: Monthly for critical docs (plan.md, status/), quarterly for others
- **Ownership**: See CODEOWNERS file for document owners
- **Updates**: All changes require PR review
- **Validation**: Automated link checking and orphan detection in CI

To add a new document:
1. Place it in the appropriate docs/ subdirectory
2. Add a link from this index or from plan.md
3. Run `scripts/docs/check_orphan_docs.py` to verify linkage
4. Submit PR for review

---

*Generated by scripts/docs/generate_index.sh*
*Last updated: $(date +%Y-%m-%d)*
FOOTER

} > "$INDEX_FILE"

log "✅ Generated $INDEX_FILE"