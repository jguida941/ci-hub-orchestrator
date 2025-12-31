# ADR-0035: Centralized Registry, Triage Bundle, and LLM-Ready Reports

**Status**: Proposed
**Date:** 2025-12-31
**Developer:** Justin Guida
**Last Reviewed:** 2025-12-31

## Context

The hub manages multiple repositories with varying quality standards (coverage thresholds, mutation testing, vulnerability tolerance). Currently:

- Repo configs are scattered across individual `.ci-hub.yml` files
- No central view of all repo settings
- No structured output for LLM consumption (Claude, ChatGPT, Codex)
- CI failures require manual log parsing
- No priority/severity ranking for issues
- Drift between repos goes undetected

We need:
1. **Central registry** - Single JSON file with all repo configs and tiers
2. **Triage bundle** - Structured JSON + markdown output from CI runs
3. **LLM-ready format** - Standard formats (SARIF, Stryker, pytest-json) that LLMs understand
4. **Severity ranking** - Priority levels (0-10) so LLMs fix critical issues first
5. **CLI-driven sync** - Update repos from registry, not manual edits

## Decision

### 1. Centralized Registry (`config/registry.json`)

Single source of truth for all repo configurations:

```json
{
  "schema": "cihub-registry-v1",

  "tiers": {
    "strict":   {"coverage": 90, "mutation": 90, "vulns_max": 0},
    "standard": {"coverage": 70, "mutation": 70, "vulns_max": 0},
    "relaxed":  {"coverage": 50, "mutation": 0,  "vulns_max": 5},
    "legacy":   {"coverage": 30, "mutation": 0,  "vulns_max": 20}
  },

  "repos": {
    "jguida941/ci-cd-hub-canary-python": {
      "language": "python",
      "tier": "standard",
      "dispatch_enabled": true,
      "overrides": {}
    },
    "jguida941/ci-cd-hub-canary-java": {
      "language": "java",
      "tier": "standard",
      "dispatch_enabled": true,
      "overrides": {"mutation": 50}
    }
  },

  "changelog": [
    {"date": "2025-12-31", "repo": "canary-python", "change": "tier: relaxed → standard", "by": "claude"}
  ]
}
```

### 2. Triage Bundle (`.cihub/triage.json`)

Structured output from every CI run:

```json
{
  "schema": "cihub-triage-v1",
  "timestamp": "2025-12-31T08:00:00Z",
  "repo": {
    "name": "jguida941/ci-cd-hub-canary-python",
    "commit": "abc123",
    "branch": "main"
  },
  "env": {
    "python": "3.12",
    "os": "ubuntu-latest"
  },
  "summary": {
    "passed": 15,
    "failed": 3,
    "skipped": 2,
    "fixable_auto": 2,
    "fixable_llm": 1
  },
  "checks": [
    {
      "name": "ruff",
      "category": "lint",
      "status": "failed",
      "severity": 3,
      "blocker": false,
      "exit_code": 1,
      "command": "ruff check .",
      "duration_ms": 1200,
      "tool": {"name": "ruff", "version": "0.8.6"},
      "artifacts": [{"path": ".cihub/artifacts/ruff.sarif", "format": "sarif"}],
      "summary": {"issues": 12},
      "fix": {"safe": true, "commands": ["ruff check --fix ."]}
    },
    {
      "name": "gitleaks",
      "category": "secrets",
      "status": "failed",
      "severity": 10,
      "blocker": true,
      "artifacts": [{"path": ".cihub/artifacts/gitleaks.json", "format": "json"}],
      "summary": {"leaks": 2},
      "fix": {"safe": false}
    }
  ]
}
```

### 3. Severity Mapping (Built into CLI)

| Severity | Category | Examples |
|----------|----------|----------|
| 10 | Secrets | gitleaks, credential exposure |
| 9 | Supply Chain | zizmor HIGH, workflow injection |
| 8 | Security HIGH | bandit high, pip-audit critical |
| 7 | Build/Test | pytest failures, build errors |
| 6 | Types | mypy errors |
| 5 | Coverage | Below threshold |
| 4 | Mutation | Below threshold |
| 3 | Lint | ruff errors |
| 2 | Format | black, isort issues |
| 1 | Docs | Link check, docs drift |
| 0 | Optional | Missing optional tools |

### 4. Standard Report Formats

| Report Type | Format | Tools |
|-------------|--------|-------|
| Static Analysis | SARIF 2.1.0 | ruff, bandit, semgrep, trivy, CodeQL, zizmor |
| Mutation Testing | Stryker Schema | mutmut (via adapter), pitest |
| Test Results | pytest-json-report | pytest |
| Coverage | Cobertura XML | pytest-cov, jacoco |
| Dependencies | CycloneDX SBOM | pip-audit, OWASP |

### 5. LLM Prompt Pack (`.cihub/triage.md`)

Human/LLM readable summary with artifact links (not inline logs):

```markdown
# CI Triage Report
**Repo:** jguida941/ci-cd-hub-canary-python
**Commit:** abc123 (main)
**Time:** 2025-12-31T08:00:00Z

## Summary
- ✅ Passed: 15
- ❌ Failed: 3 (2 auto-fixable, 1 needs review)
- ⏭️ Skipped: 2

## Critical Issues (fix first)
| Sev | Check | Status | Action |
|-----|-------|--------|--------|
| 10 | gitleaks | 2 leaks | Manual review required |
| 7 | pytest | 3 failures | See `.cihub/artifacts/pytest.json` |
| 3 | ruff | 12 issues | Auto-fix: `ruff check --fix .` |

## Auto-Fixable
```bash
ruff check --fix .
black .
isort .
```

## Artifacts
- `.cihub/artifacts/ruff.sarif` (SARIF)
- `.cihub/artifacts/pytest.json` (pytest-json-report)
- `.cihub/artifacts/gitleaks.json` (JSON)
```

### 6. CLI Commands

```bash
# Registry management
cihub registry list                    # Show all repos
cihub registry show <repo>             # Show repo config
cihub registry set <repo> --tier X     # Update tier
cihub registry set <repo> --coverage X # Override threshold
cihub registry diff                    # Show pending changes
cihub registry sync --dry-run          # Preview sync
cihub registry sync --yes              # Push to repos

# Triage (runs checks, outputs bundle)
cihub triage                           # Run all checks, output bundle
cihub triage --min-severity 6          # Only failures >= severity 6
cihub triage --category security       # Only security checks
cihub triage --json                    # JSON output only
cihub triage --llm-pack                # Generate markdown prompt

# Fix (apply safe fixes)
cihub fix --safe                       # Auto-fix: ruff, black, isort, badges
cihub fix --safe --dry-run             # Preview fixes

# Assist (generate LLM prompt)
cihub assist --prompt                  # Generate prompt pack from triage
```

### 7. Output Paths

```
.cihub/
├── triage.json           # Full structured bundle
├── triage.md             # LLM prompt pack
├── priority.json         # Sorted failures only
├── history.jsonl         # Append-only run log
└── artifacts/
    ├── ruff.sarif
    ├── bandit.json
    ├── pytest.json
    ├── mutation.json
    └── coverage.xml
```

### 8. Validation and Lifecycle (Added)

**Schema validation** ensures the triage bundle stays stable for LLMs and downstream tools:

```bash
cihub triage --validate-schema
```

Schema file (v1): `schema/triage.schema.json`

**Registry versioning** makes changes immutable and reversible:

```json
{
  "schema": "cihub-registry-v1",
  "version": 42,
  "previous_version": 41
}
```

Rollback:

```bash
cihub registry rollback --to 41
```

**Retention policies** keep history and artifacts bounded:

```bash
cihub triage prune --days 30
```

### 9. Aggregate Pass Rules (Planned)

Allow composite pass/fail logic over triage output:

```json
{
  "pass_rules": {
    "require": "avg_severity < 5 AND no_blockers",
    "warn": "any_severity >= 3"
  }
}
```

### 10. Post-Mortem Logging (Planned)

Capture root-cause notes alongside drift events (in `history.jsonl`):

```json
{
  "postmortem": {
    "why": "threshold raised without backfilling tests",
    "owner": "jguida941",
    "link": "docs/adr/00xx-incident.md"
  }
}
```

### 11. Continuous Reconciliation (Planned, Opt-In)

GitOps-style drift correction:

```bash
cihub registry sync --auto
cihub registry sync --interval 3m
```

Modes:
- warn (default)
- fail (strict)
- auto (push fixes)

### 12. RBAC (Deferred)

Prefer GitHub permissions for the MVP. Custom role enforcement can be layered later.

### 13. DORA Metrics (Deferred)

Derived from `history.jsonl` for trend tracking:

```json
{
  "dora": {
    "deploy_frequency": 3.2,
    "lead_time_hours": 1.5,
    "change_failure_rate": 0.08,
    "mttr_hours": 0.5
  }
}
```

## Alternatives Considered

1. **Store configs in each repo**: Rejected - leads to drift, no central view
2. **Database (Postgres/SQLite)**: Deferred - JSON is simpler for MVP, schema supports future DB migration
3. **Inline artifacts in triage.json**: Rejected - bloats file, LLMs work better with links
4. **Per-repo drift baselines**: Rejected - CLI compares against registry tiers, no extra config files

## Consequences

### Positive
- Single registry.json controls all repos
- LLMs get structured, prioritized data without parsing logs
- Severity ranking ensures critical issues (secrets) fixed first
- Standard formats (SARIF, Stryker) are well-documented for LLMs
- CLI-driven workflow: `cihub registry set` + `cihub registry sync`
- Changelog provides audit trail

### Negative
- New CLI commands to maintain
- Registry must stay in sync (mitigated by `cihub registry diff`)
- Tool output normalization required for non-JSON tools (mutmut, actionlint)

### Migration Path
1. Create `config/registry.json` from existing `config/repos.yml`
2. Implement `cihub registry` commands
3. Implement `cihub triage` with SARIF/JSON output
4. Add `cihub fix --safe` for auto-fixes
5. Add `cihub assist` for LLM prompt generation
6. Deprecate manual `.ci-hub.yml` edits in favor of registry sync

## References

- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Stryker Mutation Testing Schema](https://github.com/stryker-mutator/mutation-testing-elements/blob/master/packages/report-schema/src/mutation-testing-report-schema.json)
- [pytest-json-report](https://pypi.org/project/pytest-json-report/)
- [CodeRabbit + LanceDB Case Study](https://lancedb.com/blog/case-study-coderabbit/)
- [AI Secure Code Review Pipeline](https://github.com/247arjun/ai-secure-code-review)
