# CI/CD Hub Release Roadmap

> ⚠️ **Historical Reference** - Phases 0-3 context only.
>
> **Active Execution Plan:** See `REUSABLE_WORKFLOW_MIGRATION.md` for current work.
>
> This document discovered that dispatch templates drift, leading to the migration plan.
> Phases 4-8 have been superseded by the migration plan's Parts 1-6.

**Version:** 1.0.0
**Date:** 2025-12-15
**Status:** Phases 0-3 Complete; Phases 4-8 superseded by migration plan
**References:** See `requirements/` (P0/P1/nonfunctional) for current checklists.
**Active Plan:** `docs/development/REUSABLE_WORKFLOW_MIGRATION.md`

---

## Table of Contents

1. [Vision & Goals](#1-vision--goals)
2. [Requirements Summary](#2-requirements-summary)
3. [Architecture Decisions](#3-architecture-decisions)
4. [Phased Implementation Plan](#4-phased-implementation-plan)
5. [SDLC Alignment](#5-sdlc-alignment)
6. [Success Criteria](#6-success-criteria)
7. [Risk Register](#7-risk-register)

---

## 1. Vision & Goals

### 1.1 Vision Statement

A **user-friendly CI/CD template repository** that can run pipelines for **any language** with **easy-to-change templates** and **boolean toggles**, making CI/CD accessible to anyone.

### 1.2 Core Principles

| Principle | Description |
|-----------|-------------|
| **Repos Stay Clean** | Target repos don't need workflow files (central mode default) |
| **Config-Driven** | All behavior controlled by YAML config, not workflow edits |
| **Template-Driven** | Copy/paste templates with heavy comments for easy onboarding |
| **Boolean Toggles** | Enable/disable tools with simple `enabled: true/false` |
| **Sensible Defaults** | Works out-of-the-box, customize only what you need |

### 1.3 Target Users

1. **Repo owners** - Want standard CI without writing workflows
2. **Engineering leads** - Want consistent policy across repos
3. **Students/learners** - Want to learn CI/CD from a working example
4. **DevOps engineers** - Want centralized control and visibility

---

## 2. Requirements Summary

### 2.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Hub clones and tests repos without requiring workflow files in target repos | P0 | Implemented |
| FR-02 | Support Java projects (Maven/Gradle) | P0 | Implemented |
| FR-03 | Support Python projects | P0 | Implemented |
| FR-04 | Per-tool boolean toggles (enabled: true/false) | P0 | Implemented |
| FR-05 | Per-repo config overrides | P0 | Implemented |
| FR-06 | Global defaults with config hierarchy | P0 | Implemented |
| FR-07 | Generate step summary with metrics table | P0 | Implemented |
| FR-08 | Upload artifacts (coverage, reports) | P0 | Implemented |
| FR-09 | Distributed mode (dispatch to repos) | P1 | Implemented |
| FR-10 | Real aggregation across repos | P1 | Partial |
| FR-11 | GitHub Pages dashboard | P2 | Not Started |
| FR-12 | Comprehensive documentation | P1 | Implemented |
| FR-13 | Template files with heavy comments | P1 | Implemented |
| FR-14 | ADR documentation | P1 | Implemented |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Single repo CI run completes in < 15 min (without mutation) | < 15 min |
| NFR-02 | Config validation fails fast with clear error | < 5 sec |
| NFR-03 | Documentation covers all tools and toggles | 100% |
| NFR-04 | Templates are copy/paste ready | No edits required beyond repo name |

### 2.3 Tool Support Requirements

#### Java Tools (17 total)
| Tool | Status | Toggle Key |
|------|--------|------------|
| JUnit | Implemented | Built-in |
| JaCoCo | Implemented | `java.tools.jacoco.enabled` |
| Checkstyle | Implemented | `java.tools.checkstyle.enabled` |
| SpotBugs | Implemented | `java.tools.spotbugs.enabled` |
| PMD | Implemented | `java.tools.pmd.enabled` |
| OWASP DC | Implemented | `java.tools.owasp.enabled` |
| PITest | Implemented | `java.tools.pitest.enabled` |
| CodeQL | Implemented | `java.tools.codeql.enabled` |
| Docker | Implemented | `java.tools.docker.enabled` |
| Semgrep | Implemented | Auto |
| Trivy | Implemented | Auto (if Dockerfile) |

#### Python Tools (14 total)
| Tool | Status | Toggle Key |
|------|--------|------------|
| pytest | Implemented | `python.tools.pytest.enabled` |
| coverage | Implemented | With pytest |
| Ruff | Implemented | `python.tools.ruff.enabled` |
| Black | Implemented | `python.tools.black.enabled` |
| isort | Implemented | `python.tools.isort.enabled` |
| Bandit | Implemented | `python.tools.bandit.enabled` |
| pip-audit | Implemented | `python.tools.pip_audit.enabled` |
| mypy | Implemented | `python.tools.mypy.enabled` |
| Hypothesis | Implemented | Auto |
| mutmut | Implemented | `skip_mutation` input |
| CodeQL | Implemented | `python.tools.codeql.enabled` |
| Semgrep | Implemented | Auto |
| Trivy | Implemented | Auto (if Dockerfile) |

---

## 3. Architecture Decisions

### 3.1 ADRs (All Accepted)

| ADR | Title | Status | Decision |
|-----|-------|--------|----------|
| ADR-0001 | Central vs Distributed Execution | Accepted | Central = default |
| ADR-0002 | Config Precedence Hierarchy | Accepted | Repo > Hub > Defaults |
| ADR-0003 | Dispatch Orchestration | Accepted | workflow_dispatch for distributed |
| ADR-0004 | Aggregation Reporting | Accepted | Same-run preferred |
| ADR-0005 | Dashboard Approach | Accepted | GitHub Pages static |
| ADR-0006 | Quality Gates/Thresholds | Accepted | enabled: true/false |
| ADR-0007 | Templates and Profiles Strategy | Accepted | Profiles for config presets |
| ADR-0008 | Hub Fixtures Strategy | Accepted | Dedicated fixtures repo |
| ADR-0009 | Monorepo Support | Accepted | subdir config field |
| ADR-0010 | Dispatch Token and Skip | Accepted | PAT for cross-repo dispatch |
| ADR-0011 | Dispatchable Workflow Requirement | Accepted | Target repos need dispatch workflow |
| ADR-0012 | Kyverno Policies | Accepted | Optional policy enforcement |
| ADR-0013 | Dispatch Workflow Templates | Accepted | Official templates provided |

### 3.2 Two Operating Modes

| Mode | Description | When to Use | Default |
|------|-------------|-------------|---------|
| **Central** | Hub clones repos, runs tests directly | Most repos | YES |
| **Distributed** | Hub dispatches to repo workflows | Special runners, secrets | NO |

### 3.3 Config Hierarchy (Highest Wins)

```
1. Repo's .ci-hub.yml (if exists) ← Highest
2. Hub's config/repos/<repo>.yaml
3. Hub's config/defaults.yaml      ← Lowest
```

---

## 4. Phased Implementation Plan

### Phase 0: Foundation (Current State Assessment)
**SDLC: Planning**

| Task | Status | Notes |
|------|--------|-------|
| Audit existing codebase | Done | See RESEARCH.md |
| Research best practices | Done | See RESEARCH.md |
| Create ROADMAP.md | Done | This document |
| Create RESEARCH.md | Done | Comprehensive |

**Deliverables:**
- [x] RESEARCH.md with all findings
- [x] ROADMAP.md with phases
- [x] ADR directory structure (`docs/adr/`)
- [x] First 3 ADRs written (0001-0003)
- [x] All 13 ADRs written (0001-0013)

---

### Phase 1: Documentation Foundation
**SDLC: Requirements + Design**

| Task | Priority | Depends On |
|------|----------|------------|
| Create `docs/adr/` directory | P0 | None |
| Write ADR-0001: Central vs Distributed | P0 | None |
| Write ADR-0002: Config Precedence | P0 | None |
| Write ADR-0003: Reusable vs Dispatch | P0 | None |
| Create `docs/MODES.md` | P0 | ADR-0001 |
| Create `docs/CONFIG_REFERENCE.md` | P0 | ADR-0002 |
| Create `docs/TOOLS.md` | P1 | None |
| Create `docs/WORKFLOWS.md` | P1 | None |
| Create `docs/TROUBLESHOOTING.md` | P1 | None |
| Update `docs/ONBOARDING.md` | P1 | All above |

**Deliverables:**
- [x] 13 ADRs written (MADR format) - exceeds target
- [x] 8+ documentation files created (MODES, CONFIG_REFERENCE, TOOLS, WORKFLOWS, TROUBLESHOOTING, ONBOARDING, DISPATCH_SETUP, MONOREPOS, KYVERNO, TEMPLATES)
- [x] All docs cross-linked

**Acceptance Criteria:**
- [x] Every tool has documentation (see `docs/reference/TOOLS.md`)
- [x] Every toggle is documented (see `docs/reference/CONFIG_REFERENCE.md`)
- [x] Config hierarchy is clear (see `docs/guides/MODES.md`)

---

### Phase 2: Templates
**SDLC: Design + Development**

| Task | Priority | Depends On |
|------|----------|------------|
| Create `templates/repo/.ci-hub.yml` | P0 | Phase 1 |
| Create `templates/hub/config/repos/repo-template.yaml` | P0 | Phase 1 |
| Create `templates/profiles/java-quality.yml` | P1 | Phase 1 |
| Create `templates/profiles/java-security.yml` | P1 | Phase 1 |
| Create `templates/profiles/python-quality.yml` | P1 | Phase 1 |
| Create `templates/profiles/python-security.yml` | P1 | Phase 1 |
| Create `templates/repo-agent/.github/workflows/hub-agent.yml` | P2 | ADR-0001 |

**Template Requirements:**
- Every template heavily commented
- Comments explain what each toggle does
- Comments link to docs for more info
- Copy/paste ready (only change repo name)

**Deliverables:**
- [x] Master `.ci-hub.yml` template (`templates/repo/.ci-hub.yml`)
- [x] Hub-side repo template (`templates/hub/config/repos/repo-template.yaml`, `monorepo-template.yaml`)
- [x] 12 profile templates (exceeds target: java-quality, java-security, java-fast, java-minimal, java-compliance, java-coverage-gate, python-quality, python-security, python-fast, python-minimal, python-compliance, python-coverage-gate)
- [x] Dispatch workflow templates (`templates/java/java-ci-dispatch.yml`, `templates/python/python-ci-dispatch.yml`)

**Acceptance Criteria:**
- [x] User can copy template and run without edits (except repo name)
- [x] Every toggle has inline comment explaining it

---

### Phase 3: Production Gaps Fix
**SDLC: Development**

| Task | Priority | Gap Being Fixed |
|------|----------|-----------------|
| Pass computed inputs to dispatch | P0 | Inputs not passed |
| Honor `default_branch` per repo | P0 | Branch hardcoded |
| Add permissions block | P0 | Missing permissions |
| Fail on dispatch errors | P1 | Failures swallowed |
| Implement or remove `force_all_tools` | P1 | Unused input |
| Add config schema validation | P1 | No validation |

**Deliverables:**
- [x] Updated `hub-orchestrator.yml`
- [x] Config validation script (`scripts/validate_config.py`)
- [x] Tests passing (5 tests in `tests/test_config_pipeline.py`)

**Acceptance Criteria:**
- [x] Distributed mode actually uses config toggles (via dispatch templates)
- [x] Repos on `master` branch work
- [x] Bad config fails fast with clear error (schema validation)

---

### Phase 4: Aggregation
**SDLC: Development + Testing**

| Task | Priority | Depends On |
|------|----------|------------|
| Define `hub-report.json` schema | P0 | None |
| Generate real metrics in hub-run-all | P0 | None |
| Implement correlation ID for distributed | P1 | Phase 3 |
| Poll for distributed run completion | P1 | Phase 3 |
| Download artifacts from distributed runs | P2 | Phase 3 |
| Update `aggregate_reports.py` | P1 | All above |

**Deliverables:**
- [ ] Real `hub-report.json` with metrics
- [ ] Aggregation across all repos
- [ ] Historical data collection

**Acceptance Criteria:**
- Hub summary shows real pass/fail per repo
- Coverage and mutation scores aggregated
- Vulnerability counts rolled up

---

### Phase 5: Dashboard
**SDLC: Development + Deployment**

| Task | Priority | Depends On |
|------|----------|------------|
| Create dashboard HTML/JS | P1 | Phase 4 |
| Configure GitHub Pages | P1 | None |
| Generate metrics.json on each run | P1 | Phase 4 |
| Publish to gh-pages branch | P1 | All above |
| Add historical trend charts | P2 | All above |

**Deliverables:**
- [ ] Static dashboard on GitHub Pages
- [ ] Overview page with all repos
- [ ] Drill-down per repo
- [ ] Trend charts

**Acceptance Criteria:**
- Dashboard auto-updates on each hub run
- Shows coverage, mutation, security metrics
- Accessible via public URL

---

### Phase 6: Fixtures & Testing
**SDLC: Testing**

| Task | Priority | Depends On |
|------|----------|------------|
| Create `fixtures/java-passing/` | P1 | None |
| Create `fixtures/java-failing/` | P1 | None |
| Create `fixtures/python-passing/` | P1 | None |
| Create `fixtures/python-failing/` | P1 | None |
| Create `fixtures/edge-cases/` | P2 | None |
| Test hub against fixtures | P0 | All above |
| Publish fixtures repo (ci-cd-hub-fixtures) | P0 | All above |

**Deliverables:**
- [x] Fixture repos for all scenarios (`ci-cd-hub-fixtures` repo with java-passing, java-failing, python-passing, python-failing)
- [x] CI that tests hub against fixtures (`smoke-test.yml` workflow)
- [x] Documentation for fixtures (`docs/development/SMOKE_TEST_REPOS.md`)

**Acceptance Criteria:**
- [x] Hub correctly passes/fails expected repos
- [x] Edge cases handled gracefully
- [x] New contributors can test locally

---

### Phase 7: CLI Tool
**SDLC: Development**

| Task | Priority | Depends On |
|------|----------|------------|
| Set up CLI project structure | P0 | None |
| Implement `hub-cli repo add` | P0 | Phase 2 |
| Implement `hub-cli repo list` | P0 | None |
| Implement `hub-cli config lint` | P0 | Phase 3 |
| Add interactive prompts (questionary) | P1 | repo add |
| Implement `hub-cli profile apply` | P1 | Phase 2 |
| Implement `--dry-run` flag | P1 | repo add |
| Add Pydantic validation models | P1 | Phase 3 |
| Implement `hub-cli config generate` | P2 | Phase 2 |
| Package for pip install | P2 | All above |

**Tech Stack:**
- Typer (CLI framework)
- questionary (interactive prompts)
- Pydantic (validation)
- ruamel.yaml (comment-preserving YAML)
- Rich (pretty output)

**CLI Structure:**
```
hub-cli
├── repo (add, list, show, remove, validate)
├── config (lint, show, generate, diff)
├── profile (list, show, apply)
├── run (all, single)
└── docs (render, serve)
```

**Deliverables:**
- [ ] Working CLI tool
- [ ] Interactive repo onboarding
- [ ] Config validation command
- [ ] Profile application
- [ ] pip-installable package

**Acceptance Criteria:**
- User can add repo in < 2 minutes with prompts
- Validation catches config errors with helpful messages
- Profiles correctly apply tool settings

---

### Phase 8: Polish & Release
**SDLC: Deployment + Maintenance**

| Task | Priority | Depends On |
|------|----------|------------|
| Create CHANGELOG.md | P0 | None |
| Update README.md | P0 | All phases |
| Create release v1.0.0 | P0 | All phases |
| Tag and publish | P0 | All above |
| Announce | P2 | All above |

**Deliverables:**
- [ ] Complete README
- [ ] CHANGELOG with all changes
- [ ] v1.0.0 release
- [ ] Documentation site (optional)

---

### Future: Phase 9 (Post-Release)
**SDLC: Maintenance**

| Task | Priority | Notes |
|------|----------|-------|
| PyQt6 GUI | P3 | Nice-to-have |
| Additional languages (Node, Go, Rust) | P3 | Community request |
| Real-time dashboard | P3 | WebSocket-based |
| Slack/Teams notifications | P3 | Beyond stub |
| Load testing tools | P3 | k6, Locust |

---

## 5. SDLC Alignment

| Phase | SDLC Stage | Activities |
|-------|------------|------------|
| Phase 0 | Planning | Audit, research, define scope |
| Phase 1 | Requirements | ADRs, documentation, requirements |
| Phase 2 | Design | Templates, architecture |
| Phase 3 | Development | Fix gaps, implement features |
| Phase 4 | Development | Aggregation, metrics |
| Phase 5 | Development | Dashboard |
| Phase 6 | Testing | Fixtures, validation |
| Phase 7 | Development | CLI tool |
| Phase 8 | Deployment | Release, publish |
| Phase 9 | Maintenance | Post-release enhancements |

### DevSecOps Integration

Security is integrated throughout:
- **Phase 1:** Document security tools (Bandit, OWASP, CodeQL, etc.)
- **Phase 2:** Security profile templates
- **Phase 3:** Ensure security toggles work
- **Phase 4:** Aggregate security metrics
- **Phase 5:** Security dashboard panels

---

## 6. Success Criteria

### Minimum Viable Product (MVP)
- [ ] Central execution works for Java and Python
- [ ] All tools have boolean toggles
- [ ] Documentation covers all tools
- [ ] Templates are copy/paste ready
- [ ] At least 3 ADRs written

### Full Release (v1.0.0)
- [ ] All phases complete
- [ ] Dashboard live
- [ ] Fixtures tested
- [ ] Distributed mode works
- [ ] CHANGELOG maintained

### Metrics to Track
| Metric | Target |
|--------|--------|
| Docs coverage | 100% of tools documented |
| Template usability | Copy/paste in < 5 min |
| CI run time | < 15 min without mutation |
| Onboarding time | New repo added in < 10 min |

---

## 7. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Distributed mode too complex | High | Medium | Keep central as default, distributed optional |
| Too many tools to document | Medium | High | Prioritize P0 tools first |
| Dashboard scope creep | Medium | Medium | Start with static JSON, iterate |
| Breaking changes to workflows | High | Low | Version workflows, semantic versioning |
| Config schema changes | Medium | Medium | Schema validation, migration docs |

---

## Appendix A: Directory Structure Target

```
hub-release/
├── .github/workflows/
│   ├── hub-run-all.yml
│   ├── hub-orchestrator.yml
│   ├── hub-security.yml
│   ├── java-ci.yml
│   └── python-ci.yml
├── config/
│   ├── defaults.yaml
│   ├── repos/
│   └── optional/
├── docs/
│   ├── ONBOARDING.md
│   ├── WORKFLOWS.md
│   ├── CONFIG_REFERENCE.md
│   ├── TOOLS.md
│   ├── MODES.md
│   ├── TROUBLESHOOTING.md
│   ├── RESEARCH.md
│   ├── ROADMAP.md
│   └── adr/
│       ├── 0001-central-vs-distributed.md
│       ├── 0002-config-precedence.md
│       └── ...
├── templates/
│   ├── repo/.ci-hub.yml
│   ├── hub/config/repos/repo-template.yaml
│   ├── profiles/
│   └── repo-agent/
├── scripts/
├── schema/
├── dashboards/
├── fixtures/
├── policies/
├── README.md
└── CHANGELOG.md
```

---

## Appendix B: Related Documents

| Document | Purpose |
|----------|---------|
| [RESEARCH.md](./RESEARCH.md) | Research findings and best practices |
| [plan.md](../plan.md) | Original planning notes |
| [defaults.yaml](../config/defaults.yaml) | Global configuration |
| [ONBOARDING.md](./ONBOARDING.md) | Getting started guide |

---

**Document History:**
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-14 | Claude | Initial creation from RESEARCH.md + plan.md |
