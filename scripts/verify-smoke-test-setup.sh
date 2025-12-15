#!/bin/bash
# ============================================================================
# Smoke Test Setup Verification Script
# ============================================================================
# This script verifies that the smoke test setup is complete and ready to run.
#
# Usage:
#   ./scripts/verify-smoke-test-setup.sh
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================================================"
echo "Smoke Test Setup Verification"
echo "============================================================================"
echo ""

PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
    local name="$1"
    shift
    echo -n "Checking: $name... "
    if bash -c "$*" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

# ============================================================================
# Check 1: Documentation Files
# ============================================================================
echo "1. Documentation Files"
echo "----------------------"

check "SMOKE_TEST.md exists" "[ -f '$REPO_ROOT/docs/development/SMOKE_TEST.md' ]"
check "SMOKE_TEST_REPOS.md exists" "[ -f '$REPO_ROOT/docs/development/SMOKE_TEST_REPOS.md' ]"
check "docs/README.md index exists" "[ -f '$REPO_ROOT/docs/README.md' ]"
check "WORKFLOWS.md mentions Smoke Test" "grep -Eq '^Smoke Test' '$REPO_ROOT/docs/guides/WORKFLOWS.md' || grep -q 'Smoke Test' '$REPO_ROOT/docs/guides/WORKFLOWS.md'"

echo ""

# ============================================================================
# Check 2: Workflow File
# ============================================================================
echo "2. Smoke Test Workflow"
echo "----------------------"

check "smoke-test.yml exists" "[ -f '$REPO_ROOT/.github/workflows/smoke-test.yml' ]"
check "workflow has workflow_dispatch trigger" "grep -Eq '^on:\\s*\\n(.*\\n)*\\s*workflow_dispatch:' '$REPO_ROOT/.github/workflows/smoke-test.yml'"
check "workflow has discover job" "grep -Eq '^  discover:' '$REPO_ROOT/.github/workflows/smoke-test.yml'"
check "workflow has test-repo job" "grep -Eq '^  test-repo:' '$REPO_ROOT/.github/workflows/smoke-test.yml'"
check "workflow has summary job" "grep -Eq '^  summary:' '$REPO_ROOT/.github/workflows/smoke-test.yml'"

echo ""

# ============================================================================
# Check 3: Smoke Test Repository Configs
# ============================================================================
echo "3. Smoke Test Repository Configs"
echo "----------------------------------"

check "smoke-test-java.yaml exists" "[ -f '$REPO_ROOT/config/repos/smoke-test-java.yaml' ]"
check "smoke-test-python.yaml exists" "[ -f '$REPO_ROOT/config/repos/smoke-test-python.yaml' ]"

if [ -f "$REPO_ROOT/config/repos/smoke-test-java.yaml" ]; then
    check "Java config has repo.owner" "grep -Eq '^repo:\\s*$|^repo:' '$REPO_ROOT/config/repos/smoke-test-java.yaml' && grep -Eq '^\\s*owner:' '$REPO_ROOT/config/repos/smoke-test-java.yaml'"
    check "Java config has repo.name" "grep -Eq '^\\s*name:' '$REPO_ROOT/config/repos/smoke-test-java.yaml'"
    check "Java config has language: java" "grep -Eq '^language:\\s*java' '$REPO_ROOT/config/repos/smoke-test-java.yaml'"
fi

if [ -f "$REPO_ROOT/config/repos/smoke-test-python.yaml" ]; then
    check "Python config has repo.owner" "grep -Eq '^repo:\\s*$|^repo:' '$REPO_ROOT/config/repos/smoke-test-python.yaml' && grep -Eq '^\\s*owner:' '$REPO_ROOT/config/repos/smoke-test-python.yaml'"
    check "Python config has repo.name" "grep -Eq '^\\s*name:' '$REPO_ROOT/config/repos/smoke-test-python.yaml'"
    check "Python config has language: python" "grep -Eq '^language:\\s*python' '$REPO_ROOT/config/repos/smoke-test-python.yaml'"
fi

echo ""

# ============================================================================
# Check 4: GitHub CLI Available (optional)
# ============================================================================
echo "4. GitHub CLI (optional)"
echo "------------------------"

if command -v gh &> /dev/null; then
    echo -e "${GREEN}✓${NC} gh CLI is installed"
    ((PASSED++))

    # Check if authenticated
    if gh auth status &> /dev/null; then
        echo -e "${GREEN}✓${NC} gh CLI is authenticated"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} gh CLI is not authenticated (run: gh auth login)"
        echo "  (Not required, but needed to run smoke test via CLI)"
    fi
else
    echo -e "${YELLOW}⚠${NC} gh CLI is not installed (optional)"
    echo "  Install from: https://cli.github.com/"
    echo "  (Not required, but needed to run smoke test via CLI)"
fi

echo ""

# ============================================================================
# Check 5: Smoke Test Repos Accessible (requires gh)
# ============================================================================
echo "5. Test Repository Accessibility (requires gh)"
echo "-----------------------------------------------"

if command -v gh &> /dev/null && gh auth status &> /dev/null; then
    # Extract repo owner and name from configs (strip comments)
    if [ -f "$REPO_ROOT/config/repos/smoke-test-java.yaml" ]; then
        JAVA_OWNER=$(grep -m1 'owner:' "$REPO_ROOT/config/repos/smoke-test-java.yaml" | sed 's/.*owner:\s*//' | sed 's/#.*//' | tr -d '"' | tr -d "'" | xargs)
        JAVA_NAME=$(grep -m1 'name:' "$REPO_ROOT/config/repos/smoke-test-java.yaml" | sed 's/.*name:\s*//' | sed 's/#.*//' | tr -d '"' | tr -d "'" | xargs)

        check "Java repo accessible ($JAVA_OWNER/$JAVA_NAME)" "gh repo view '$JAVA_OWNER/$JAVA_NAME' --json name > /dev/null 2>&1"
    fi

    if [ -f "$REPO_ROOT/config/repos/smoke-test-python.yaml" ]; then
        PYTHON_OWNER=$(grep -m1 'owner:' "$REPO_ROOT/config/repos/smoke-test-python.yaml" | sed 's/.*owner:\s*//' | sed 's/#.*//' | tr -d '"' | tr -d "'" | xargs)
        PYTHON_NAME=$(grep -m1 'name:' "$REPO_ROOT/config/repos/smoke-test-python.yaml" | sed 's/.*name:\s*//' | sed 's/#.*//' | tr -d '"' | tr -d "'" | xargs)

        check "Python repo accessible ($PYTHON_OWNER/$PYTHON_NAME)" "gh repo view '$PYTHON_OWNER/$PYTHON_NAME' --json name > /dev/null 2>&1"
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping repository accessibility checks (gh CLI not available or not authenticated)"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo "============================================================================"
echo "Summary"
echo "============================================================================"
echo ""
echo "Checks passed: $PASSED"
echo "Checks failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run smoke test: gh workflow run smoke-test.yml"
    echo "  2. Or via GitHub UI: Actions → Smoke Test → Run workflow"
    echo "  3. Review docs/development/SMOKE_TEST.md for detailed guide"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed!${NC}"
    echo ""
    echo "Please fix the issues above before running the smoke test."
    echo "See docs/development/SMOKE_TEST.md for troubleshooting."
    echo ""
    exit 1
fi
