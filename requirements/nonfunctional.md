# Non-Functional Requirements

Quality targets for hub-release.

---

## Performance

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Single repo CI (no mutation) | < 15 min | Unknown | [ ] |
| Single repo CI (with mutation) | < 30 min | Unknown | [ ] |
| Config validation | < 5 sec | N/A | [ ] |
| Hub summary generation | < 30 sec | Unknown | [ ] |
| Dashboard page load | < 3 sec | N/A | [ ] |

---

## Usability

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Add repo (with CLI) | < 2 min | N/A | [ ] |
| Add repo (manual) | < 5 min | Unknown | [ ] |
| Find tool docs | < 30 sec | Unknown | [ ] |
| Understand toggle | Immediate | Unknown | [ ] |

---

## Reliability

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Config validation accuracy | 100% | Unknown | [ ] |
| Artifact upload success | 99%+ | Unknown | [ ] |
| Dispatch failure detection | 100% | 0% (stub) | [ ] |

---

## Documentation Coverage

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Tools documented | 100% | ~80% (RESEARCH.md) | [~] |
| Toggles documented | 100% | ~60% (defaults.yaml) | [~] |
| Workflows documented | 100% | 0% | [ ] |
| Templates commented | 100% | 0% | [ ] |

---

## Artifact Retention

| Artifact | Target | Configured | Status |
|----------|--------|------------|--------|
| Coverage reports | 30 days | Unknown | [~] |
| Security reports | 30 days | Unknown | [~] |
| Hub summary JSON | 90 days | N/A | [ ] |
| Dashboard data | 90 days | N/A | [ ] |

---

## Validation Gates

| Check | When | Failure Action | Status |
|-------|------|----------------|--------|
| Config schema | Before run | Fail fast | [ ] |
| Required fields | Before run | Fail fast | [ ] |
| YAML syntax | Before run | Fail fast | [~] |
| Tool availability | During run | Warn in summary | [~] |

---

## Status Legend
- `[ ]` - Not implemented/verified
- `[~]` - Partially implemented
- `[x]` - Verified complete

**Last Updated:** 2025-12-14
**Status:** MOSTLY UNVERIFIED — needs baseline measurements
