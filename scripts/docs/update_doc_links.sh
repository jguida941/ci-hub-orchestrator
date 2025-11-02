#!/usr/bin/env bash
# Update all documentation links after reorganization
# Portable script that handles BSD (macOS) and GNU (Linux) sed differences

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log() {
  echo "[update-links] $*" >&2
}

# Detect sed version (BSD vs GNU)
if sed --version 2>/dev/null | grep -q "GNU sed"; then
  SED_TYPE="GNU"
  SED_INPLACE="sed -i"
else
  SED_TYPE="BSD"
  SED_INPLACE="sed -i.bak"
fi

log "Detected $SED_TYPE sed"

# Create backup directory for rollback
BACKUP_DIR="$REPO_ROOT/.doc-link-backup-$(date +%Y%m%d-%H%M%S)"
log "Creating backup at $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup all markdown files before changes
find "$REPO_ROOT" -name "*.md" -type f ! -path "*/node_modules/*" ! -path "*/.git/*" | while read -r file; do
  rel_path="${file#$REPO_ROOT/}"
  backup_file="$BACKUP_DIR/$rel_path"
  mkdir -p "$(dirname "$backup_file")"
  cp "$file" "$backup_file"
done

# Define link mappings (old -> new) without associative array for compatibility
update_specific_link() {
  local file="$1"
  local old_path="$2"
  local new_path="$3"

  # Check if file contains the old reference
  if grep -q "$old_path" "$file" 2>/dev/null; then
    log "  Updating $old_path -> $new_path in $(basename "$file")"

    # Use portable sed syntax
    if [[ "$SED_TYPE" == "GNU" ]]; then
      sed -i "s|($old_path)|($new_path)|g" "$file"
      sed -i "s|\[${old_path}\]|[${new_path}]|g" "$file"
      sed -i "s|\"${old_path}\"|\"${new_path}\"|g" "$file"
      sed -i "s|'${old_path}'|'${new_path}'|g" "$file"
    else
      # BSD sed (macOS)
      sed -i.bak "s|($old_path)|($new_path)|g" "$file"
      sed -i.bak "s|\[${old_path}\]|[${new_path}]|g" "$file"
      sed -i.bak "s|\"${old_path}\"|\"${new_path}\"|g" "$file"
      sed -i.bak "s|'${old_path}'|'${new_path}'|g" "$file"
    fi
    return 0
  fi
  return 1
}

# Update links in all markdown files
update_links() {
  local file="$1"
  local modified=false

  # Update each mapping
  update_specific_link "$file" "START_HERE.md" "docs/start-here.md" && modified=true
  update_specific_link "$file" "HONEST_STATUS.md" "docs/status/honest-status.md" && modified=true
  update_specific_link "$file" "MULTI_REPO_IMPLEMENTATION_STATUS.md" "docs/status/implementation.md" && modified=true
  update_specific_link "$file" "MULTI_REPO_ANALYSIS.md" "docs/analysis/multi-repo-analysis.md" && modified=true
  update_specific_link "$file" "MULTI_REPO_SCALABILITY.md" "docs/analysis/scalability.md" && modified=true
  update_specific_link "$file" "ANALYSIS_INDEX.md" "docs/analysis/index.md" && modified=true
  update_specific_link "$file" "OPS_RUNBOOK.md" "docs/ops/ops-runbook.md" && modified=true
  update_specific_link "$file" "issues.md" "https://github.com/jguida941/ci-cd-hub/issues" && modified=true

  # Special case for relative paths in moved files
  if [[ "$file" =~ docs/status/|docs/analysis/|docs/ops/ ]]; then
    # Update relative references to plan.md
    if grep -q "\.\./plan\.md\|\.\.\/\.\.\/plan\.md" "$file" 2>/dev/null; then
      log "  Fixing relative path to plan.md in $(basename "$file")"
      if [[ "$SED_TYPE" == "GNU" ]]; then
        sed -i 's|\.\./\.\./plan\.md|../../plan.md|g' "$file"
        sed -i 's|\.\./plan\.md|../../plan.md|g' "$file"
      else
        sed -i.bak 's|\.\./\.\./plan\.md|../../plan.md|g' "$file"
        sed -i.bak 's|\.\./plan\.md|../../plan.md|g' "$file"
      fi
    fi
  fi

  # Clean up BSD sed backup files if they were created
  if [[ "$SED_TYPE" == "BSD" ]] && [[ -f "${file}.bak" ]]; then
    rm -f "${file}.bak"
  fi

  echo "$modified"
}

# Process all markdown files
log "Updating links in markdown files..."
FILES_UPDATED=0

find "$REPO_ROOT" -name "*.md" -type f ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/.doc-link-backup*" | while read -r file; do
  log "Checking $(basename "$file")..."
  if [[ "$(update_links "$file")" == "true" ]]; then
    ((FILES_UPDATED++)) || true
  fi
done

# Create rollback script
cat > "$BACKUP_DIR/rollback.sh" << 'ROLLBACK'
#!/usr/bin/env bash
# Rollback documentation link changes
set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$BACKUP_DIR/../.." && pwd)"

echo "Rolling back documentation link changes from $BACKUP_DIR..."

find "$BACKUP_DIR" -name "*.md" -type f | while read -r backup_file; do
  rel_path="${backup_file#$BACKUP_DIR/}"
  original_file="$REPO_ROOT/$rel_path"

  if [[ -f "$original_file" ]]; then
    echo "Restoring $rel_path"
    cp "$backup_file" "$original_file"
  fi
done

echo "✅ Rollback complete"
echo "You can now remove the backup: rm -rf $BACKUP_DIR"
ROLLBACK

chmod +x "$BACKUP_DIR/rollback.sh"

log "✅ Link update complete"
log "📋 Backup created at: $BACKUP_DIR"
log "🔄 To rollback: $BACKUP_DIR/rollback.sh"