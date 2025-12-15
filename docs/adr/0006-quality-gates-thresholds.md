# ADR-0006: Quality Gates and Thresholds

- Status: Accepted
- Date: 2025-12-14

## Context

CI pipelines need pass/fail criteria. Questions:
- What metrics should have thresholds?
- Should thresholds be global or per-repo configurable?
- What happens when thresholds are violated?
- How do we handle security vulnerabilities?

## Decision

**Threshold Types:**

| Metric | Default | Configurable | Enforcement |
|--------|---------|--------------|-------------|
| Coverage (min %) | 70 | Yes | Per-tool plugin (JaCoCo/pytest-cov) |
| Mutation score (min %) | 70 | Yes | Warning only (not blocking) |
| OWASP CVSS (fail >=) | 7 | Yes | OWASP plugin fails build |
| Critical vulns (max) | 0 | Yes | Pending implementation |
| High vulns (max) | 0 | Yes | Pending implementation |

**Configuration Hierarchy:**
1. Per-tool settings (e.g., `java.tools.jacoco.min_coverage: 80`)
2. Global thresholds (e.g., `thresholds.coverage_min: 70`)
3. Hub defaults (`config/defaults.yaml`)

Per-tool settings take precedence over global thresholds.

**Enforcement Behavior:**

1. **Coverage:**
   - JaCoCo: `check` goal with `<minimum>` rule
   - pytest-cov: `--cov-fail-under` flag
   - Enforced at build time, fails the job

2. **Mutation score:**
   - PITest: `mutationThreshold` in pom.xml
   - mutmut: reported but not blocking
   - Currently warning only in hub (too slow for PR checks)

3. **OWASP:**
   - `failBuildOnCVSS` parameter
   - Fails if any dependency has CVSS >= threshold
   - Enforced at build time

4. **Vulnerability counts:**
   - Config keys exist (`thresholds.max_critical_vulns`, `thresholds.max_high_vulns`)
   - **Enforcement NOT yet implemented**
   - Currently: OWASP fails on individual CVSS, not counts

## Alternatives Considered

1. **Hard-fail on all thresholds:** Rejected. Mutation testing too slow for PR checks.
2. **No thresholds (advisory only):** Rejected. Quality would degrade over time.
3. **Aggregate thresholds:** Rejected. Per ADR-0004, per-repo metrics are primary.
4. **External quality gate (SonarQube):** Rejected for MVP. Adds infrastructure.

## Consequences

**Positive:**
- Consistent quality standards across repos
- Configurable per-repo for different needs
- Fast feedback via build-time enforcement
- Mutation score as advisory prevents slow PR builds

**Negative:**
- Vuln count thresholds not yet enforced
- Different tools enforce differently (some warn, some fail)
- Repos must configure plugins to respect thresholds

## Implementation Notes

- Threshold config: `config/defaults.yaml` thresholds section
- JaCoCo enforcement: requires `check` goal in pom.xml
- OWASP enforcement: `failBuildOnCVSS` parameter
- Mutation score: reported in step summary, not blocking

**Current Limitations:**

1. **Vulnerability counts pending aggregation implementation:**
   - `thresholds.max_critical_vulns` and `thresholds.max_high_vulns` exist in config
   - Schema accepts these values
   - However, counting and enforcement NOT implemented
   - Future: aggregate vuln counts from OWASP, pip-audit, Trivy

2. **No quality gate summary job:**
   - Individual tools enforce their thresholds
   - No unified "quality gate" job that checks all thresholds
   - Consider adding for clearer pass/fail signal

## Future Work

- Implement vulnerability count aggregation and enforcement
- Add Semgrep/Trivy findings to vuln counts
- Consider unified "quality gate" summary job
- Add threshold trend tracking (is coverage improving?)

