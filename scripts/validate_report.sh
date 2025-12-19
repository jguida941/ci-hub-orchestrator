#!/bin/bash
# =============================================================================
# validate_report.sh - Reusable CI Report Validator
# =============================================================================
# Usage:
#   ./validate_report.sh --report <path> --stack <python|java> [OPTIONS]
#
# Options:
#   --report <path>      Path to report.json (required)
#   --stack <stack>      Stack type: python or java (required)
#   --expect-clean       Expect zero issues (passing fixture) [default]
#   --expect-issues      Expect issues detected (failing fixture)
#   --coverage-min <n>   Minimum coverage threshold (default: 70)
#   --verbose            Show all checks, not just failures
#   --help               Show this help message
#
# Examples:
#   # Validate passing fixture (strict - zero issues expected)
#   ./validate_report.sh --report ./report/report.json --stack python --expect-clean
#
#   # Validate failing fixture (must detect issues)
#   ./validate_report.sh --report ./report/report.json --stack java --expect-issues
#
# Exit Codes:
#   0 - Validation passed
#   1 - Validation failed
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration: Tool Metrics by Stack
# =============================================================================

# Python tool_metrics fields (map to report.json keys)
PYTHON_METRICS=(
  "ruff_errors"
  "black_issues"
  "isort_issues"
  "bandit_high"
  "bandit_medium"
  "pip_audit_vulns"
  "semgrep_findings"
  "trivy_critical"
  "trivy_high"
)

# Python lint metrics (must be 0 for clean builds)
PYTHON_LINT_METRICS=(
  "ruff_errors"
  "black_issues"
  "isort_issues"
)

# Python security metrics (must be 0 for clean builds)
PYTHON_SECURITY_METRICS=(
  "bandit_high"
  "pip_audit_vulns"
)

# Java tool_metrics fields
JAVA_METRICS=(
  "checkstyle_issues"
  "spotbugs_issues"
  "pmd_violations"
  "owasp_critical"
  "owasp_high"
  "semgrep_findings"
  "trivy_critical"
  "trivy_high"
)

# Java lint metrics (must be 0 for clean builds)
JAVA_LINT_METRICS=(
  "checkstyle_issues"
  "spotbugs_issues"
  "pmd_violations"
)

# Java security metrics (must be 0 for clean builds)
JAVA_SECURITY_METRICS=(
  "owasp_critical"
  "owasp_high"
)

# =============================================================================
# Argument Parsing
# =============================================================================

REPORT=""
STACK=""
EXPECT_MODE="clean"  # clean or issues
COVERAGE_MIN=70
VERBOSE=false

show_help() {
  head -40 "$0" | tail -35 | sed 's/^#//' | sed 's/^ //'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --report)
      REPORT="$2"
      shift 2
      ;;
    --stack)
      STACK="$2"
      shift 2
      ;;
    --expect-clean)
      EXPECT_MODE="clean"
      shift
      ;;
    --expect-issues)
      EXPECT_MODE="issues"
      shift
      ;;
    --coverage-min)
      COVERAGE_MIN="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      show_help
      ;;
    *)
      echo "::error::Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required args
if [ -z "$REPORT" ]; then
  echo "::error::--report is required"
  exit 1
fi

if [ -z "$STACK" ]; then
  echo "::error::--stack is required"
  exit 1
fi

if [[ "$STACK" != "python" && "$STACK" != "java" ]]; then
  echo "::error::--stack must be 'python' or 'java'"
  exit 1
fi

if [ ! -f "$REPORT" ]; then
  echo "::error::Report file not found: $REPORT"
  exit 1
fi

# =============================================================================
# Utility Functions
# =============================================================================

ERRORS=0
WARNINGS=0

pass() {
  if [ "$VERBOSE" = true ]; then
    echo "  [PASS] $1"
  fi
}

fail() {
  echo "::error::$1"
  ERRORS=$((ERRORS + 1))
}

warn() {
  echo "::warning::$1"
  WARNINGS=$((WARNINGS + 1))
}

info() {
  echo "  [INFO] $1"
}

# Get JSON value, return "null" if missing
jq_val() {
  local path="$1"
  jq -r "$path // \"null\"" "$REPORT"
}

# Get JSON value, return 0 if missing
jq_num() {
  local path="$1"
  jq -r "$path // 0" "$REPORT"
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_schema_version() {
  echo ""
  echo "--- Schema Version ---"
  local version
  version=$(jq_val '.schema_version')
  if [ "$version" = "2.0" ]; then
    pass "schema_version: $version"
  else
    fail "schema_version is '$version', expected '2.0'"
  fi
}

validate_test_results() {
  echo ""
  echo "--- Test Results ---"

  local tests_passed tests_failed
  tests_passed=$(jq_num '.results.tests_passed')
  tests_failed=$(jq_num '.results.tests_failed')

  # Tests must have run
  if [ "$tests_passed" = "null" ]; then
    fail "results.tests_passed is null - tests may not have run"
  elif [ "$tests_passed" -gt 0 ]; then
    pass "tests_passed: $tests_passed"
  else
    fail "tests_passed is 0 - at least some tests should pass"
  fi

  # For clean builds, no test failures
  if [ "$EXPECT_MODE" = "clean" ]; then
    if [ "$tests_failed" = "null" ]; then
      fail "results.tests_failed is null"
    elif [ "$tests_failed" -eq 0 ]; then
      pass "tests_failed: $tests_failed"
    else
      fail "tests_failed is $tests_failed, expected 0 for clean build"
    fi
  else
    # For failing fixtures, test failures are expected but not required
    if [ "$tests_failed" = "null" ]; then
      fail "results.tests_failed is null"
    else
      info "tests_failed: $tests_failed (acceptable for failing fixture)"
    fi
  fi
}

validate_coverage() {
  echo ""
  echo "--- Coverage ---"

  local coverage
  coverage=$(jq_num '.results.coverage')

  if [ "$coverage" = "null" ]; then
    fail "results.coverage is null"
  elif [ "$EXPECT_MODE" = "clean" ]; then
    if [ "$coverage" -ge "$COVERAGE_MIN" ]; then
      pass "coverage: ${coverage}% (threshold: ${COVERAGE_MIN}%)"
    else
      fail "coverage is ${coverage}%, expected >= ${COVERAGE_MIN}%"
    fi
  else
    info "coverage: ${coverage}% (no threshold for failing fixture)"
  fi
}

validate_tools_ran() {
  echo ""
  echo "--- Tools Ran ---"

  local tools_ran
  tools_ran=$(jq_val '.tools_ran')

  if [ "$tools_ran" = "null" ]; then
    fail "tools_ran is null - should be an object"
    return
  fi

  # Check that tools_ran is an object with boolean values
  local tool_count
  tool_count=$(jq '.tools_ran | keys | length' "$REPORT")

  if [ "$tool_count" -eq 0 ]; then
    fail "tools_ran is empty - no tools recorded"
  else
    pass "tools_ran has $tool_count tools recorded"
  fi

  # List enabled tools
  if [ "$VERBOSE" = true ]; then
    jq -r '.tools_ran | to_entries[] | select(.value == true) | "  [ENABLED] \(.key)"' "$REPORT"
  fi
}

validate_tool_metrics_populated() {
  echo ""
  echo "--- Tool Metrics (populated check) ---"

  local metrics
  if [ "$STACK" = "python" ]; then
    metrics=("${PYTHON_METRICS[@]}")
  else
    metrics=("${JAVA_METRICS[@]}")
  fi

  for metric in "${metrics[@]}"; do
    local val
    val=$(jq_val ".tool_metrics.$metric")
    if [ "$val" = "null" ]; then
      # Check if tool was disabled via tools_ran
      local tool_base tool_enabled
      tool_base="${metric%%_*}"  # Get first part before underscore
      tool_enabled=$(jq_val ".tools_ran.$tool_base")

      if [ "$tool_enabled" = "false" ]; then
        if [ "$VERBOSE" = true ]; then
          info "tool_metrics.$metric is null (tool disabled)"
        fi
      else
        fail "tool_metrics.$metric is null - should be populated"
      fi
    else
      pass "tool_metrics.$metric: $val"
    fi
  done
}

validate_clean_build() {
  echo ""
  echo "--- Clean Build Checks (zero issues expected) ---"

  local lint_metrics security_metrics
  if [ "$STACK" = "python" ]; then
    lint_metrics=("${PYTHON_LINT_METRICS[@]}")
    security_metrics=("${PYTHON_SECURITY_METRICS[@]}")
  else
    lint_metrics=("${JAVA_LINT_METRICS[@]}")
    security_metrics=("${JAVA_SECURITY_METRICS[@]}")
  fi

  # Check lint metrics are 0
  echo "  Lint checks:"
  for metric in "${lint_metrics[@]}"; do
    local val
    val=$(jq_num ".tool_metrics.$metric")
    if [ "$val" -eq 0 ]; then
      pass "$metric: $val"
    else
      fail "$metric is $val, expected 0 for clean build"
    fi
  done

  # Check security metrics are 0
  echo "  Security checks:"
  for metric in "${security_metrics[@]}"; do
    local val
    val=$(jq_num ".tool_metrics.$metric")
    if [ "$val" -eq 0 ]; then
      pass "$metric: $val"
    else
      fail "$metric is $val, expected 0 for clean build"
    fi
  done
}

validate_issues_detected() {
  echo ""
  echo "--- Issue Detection Checks (must find issues) ---"

  local lint_metrics
  if [ "$STACK" = "python" ]; then
    lint_metrics=("${PYTHON_LINT_METRICS[@]}")
  else
    lint_metrics=("${JAVA_LINT_METRICS[@]}")
  fi

  # At least ONE lint metric must be > 0
  local total_issues=0
  for metric in "${lint_metrics[@]}"; do
    local val
    val=$(jq_num ".tool_metrics.$metric")
    total_issues=$((total_issues + val))
    info "$metric: $val"
  done

  if [ "$total_issues" -eq 0 ]; then
    fail "No lint issues detected - failing fixture MUST have issues"
  else
    pass "Total lint issues detected: $total_issues"
  fi
}

# =============================================================================
# Main Execution
# =============================================================================

echo "========================================"
echo "Report Validation: $STACK ($EXPECT_MODE)"
echo "========================================"
echo "Report: $REPORT"
echo "Stack:  $STACK"
echo "Mode:   --expect-$EXPECT_MODE"

# Run validations
validate_schema_version
validate_test_results
validate_coverage
validate_tools_ran
validate_tool_metrics_populated

# Mode-specific validations
if [ "$EXPECT_MODE" = "clean" ]; then
  validate_clean_build
else
  validate_issues_detected
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "::error::Validation FAILED with $ERRORS errors"
  exit 1
else
  echo ""
  echo "Validation PASSED"
  exit 0
fi
