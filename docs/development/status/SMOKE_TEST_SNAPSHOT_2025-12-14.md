# Smoke Test Setup - Summary

This document summarizes the smoke test setup completed on 2025-12-14.

---

## Latest Smoke Test Run

- Status: Success
- Run URL: https://github.com/jguida941/ci-cd-hub/actions/runs/20424144678

---

## What Was Created

### 1. Documentation

#### Primary Smoke Test Guide
**File:** `/hub-release/docs/development/execution/SMOKE_TEST.md`

Comprehensive guide covering:
- Overview of smoke test purpose and scope
- Prerequisites (secrets, permissions, test repositories)
- Three methods to run smoke tests (workflow dispatch, GitHub CLI, hub-run-all)
- Expected outcomes and success criteria
- Detailed verification steps
- Troubleshooting guide for common issues
- Manual testing procedures
- Configuration file references

#### Smoke Test Repository Requirements
**File:** `/hub-release/docs/development/execution/SMOKE_TEST_REPOS.md`

Detailed documentation about:
- Current smoke test repositories (Java and Python)
- Repository accessibility verification
- Requirements for alternative smoke test repos
- Suggestions for purpose-built fixture repos
- Configuration templates
- Verification procedures

#### Documentation Index
**File:** `/hub-release/docs/README.md`

Central index for all hub documentation with:
- Quick links organized by task
- Documentation organized by audience
- Document status tracking
- File organization overview

### 2. Smoke Test Workflow

**File:** `/hub-release/.github/workflows/smoke-test.yml`

Automated smoke test workflow featuring:
- Manual trigger via workflow_dispatch
- Automatic trigger on PR changes to smoke test configs
- Repository discovery (only smoke-test-*.yaml configs)
- Validation that at least 2 repos are configured
- Separate test jobs for Java and Python
- Core tool execution (JaCoCo, Checkstyle, SpotBugs, pytest, Ruff, Black)
- Heavy tools disabled (OWASP, PITest, mutation testing)
- Detailed step summaries with pass/fail status
- Artifact upload (7-day retention)
- Overall smoke test summary with validation

### 3. Repository Configurations

Existing smoke test configs verified:

**Java:** `/hub-release/config/repos/smoke-test-java.yaml`
- Repository: `jguida941/java-spring-tutorials`
- Tools: JaCoCo, Checkstyle, SpotBugs
- Threshold: 50% coverage

**Python:** `/hub-release/config/repos/smoke-test-python.yaml`
- Repository: `jguida941/ci-cd-bst-demo-github-actions`
- Tools: pytest, Ruff, Black
- Threshold: 50% coverage

Both repositories verified as:
- Publicly accessible
- Default branch is `main`
- Ready for testing

### 4. Updated Documentation

**Updated:** `/hub-release/docs/guides/WORKFLOWS.md`
- Added smoke test workflow section
- Documented triggers, inputs, outputs, and notes

---

## How to Run the Smoke Test

### Quick Start

1. **Via GitHub UI:**
   - Go to Actions → Smoke Test → Run workflow
   - Leave defaults (skip_mutation: true)
   - Click "Run workflow"

2. **Via GitHub CLI:**
   ```bash
   gh workflow run smoke-test.yml
   ```

3. **Via Hub Run All (specific repos):**
   ```bash
   gh workflow run hub-run-all.yml \
     --field repos="smoke-test-java,smoke-test-python" \
     --field skip_mutation=true
   ```

---

## Expected Results

A successful smoke test will:

1. Discover 2 repositories (Java + Python)
2. Execute tests for both languages
3. Generate coverage reports
4. Run linting/style checks
5. Upload artifacts
6. Generate step summaries
7. Complete with overall success status

---

## Verification Checklist

After running smoke test:

- [x] Workflow status shows "Success"
- [x] Both test-repo jobs completed
- [x] Java job shows:
  - [x] Tests executed (count > 0)
  - [x] Coverage calculated (% > 0)
  - [x] Checkstyle ran
  - [x] SpotBugs ran
- [x] Python job shows:
  - [x] pytest ran (count > 0)
  - [x] Coverage calculated (% > 0)
  - [x] Ruff linting ran
  - [x] Black format check ran
- [x] Artifacts uploaded for both repos
- [x] Step summaries show metrics tables
- [x] Summary job shows total repo count = 2

---

## Next Steps

### Immediate
1. Record the run URL in this summary (done)
2. Mark smoke test checkbox in `docs/development/specs/P0.md` if successful

### Future Improvements
1. Consider creating dedicated fixture repositories for more predictable results
2. Add smoke test to PR checks (on config changes)
3. Include smoke test in pre-release checklist
4. Add smoke test badge to README

---

## Files Changed/Created

```
hub-release/
├── .github/workflows/
│   └── smoke-test.yml (NEW)
├── config/repos/
│   ├── smoke-test-java.yaml (EXISTING - verified)
│   └── smoke-test-python.yaml (EXISTING - verified)
└── docs/
    ├── README.md (index)
    ├── guides/WORKFLOWS.md (UPDATED)
    ├── development/execution/SMOKE_TEST.md
    └── development/execution/SMOKE_TEST_REPOS.md
```

---

## Documentation References

- **Primary Guide:** [SMOKE_TEST.md](SMOKE_TEST.md)
- **Repository Info:** [SMOKE_TEST_REPOS.md](SMOKE_TEST_REPOS.md)
- **Workflow Reference:** [../guides/WORKFLOWS.md](../guides/WORKFLOWS.md#smoke-test)
- **All Docs:** [../README.md](../README.md)

---

## P0 Requirement Status

From `docs/development/specs/P0.md`:

```
## 4. Smoke Test

- [x] Run hub against 2-3 fixture repos (Java + Python)
- [x] Verify pass/fail detection works
- [x] Verify artifacts generated
- [x] Verify step summary accurate
```

**Status:** Ready to test
- ✅ Smoke test workflow created
- ✅ 2 fixture repos configured (Java + Python)
- ✅ Documentation complete
- ⏳ Awaiting first successful run to mark complete

---

## Contact & Support

For issues or questions:
1. Check [../guides/TROUBLESHOOTING.md](../guides/TROUBLESHOOTING.md)
2. Review [SMOKE_TEST.md](SMOKE_TEST.md)
3. Check workflow logs in GitHub Actions
