# CI/CD Hub: Architectural Overview
> **Status:** Audited
> **Last Updated:** 2025-12-25
> **Author:** Justin Guida
>
This document provides a comprehensive overview of the CI/CD Hub platform,
detailing its architecture, core components, execution modes, toolchains,
reporting mechanisms, and current status.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CI/CD HUB (hub-release)                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   CONFIG     │   │   SCHEMAS    │   │  WORKFLOWS   │   │     CLI      │ │
│  │   LAYER      │   │   LAYER      │   │    LAYER     │   │    TOOL      │ │
│  │              │   │              │   │              │   │   (cihub)    │ │
│  │ defaults.yaml│   │ ci-hub-*.json│   │ hub-run-all  │   │              │ │
│  │ repos/*.yaml │   │ ci-report.v2 │   │ java-ci.yml  │   │ 11 commands  │ │
│  │ templates/   │   │              │   │ python-ci.yml│   │ 132 funcs    │ │
│  │ profiles/    │   │              │   │              │   │              │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│          │                  │                  │                  │        │
│          └──────────────────┴──────────────────┴──────────────────┘        │
│                                      │                                     │
│                             ┌────────▼────────┐                            │
│                             │   AGGREGATION   │                            │
│                             │     ENGINE      │                            │
│                             │ (summary.json)  │                            │
│                             └─────────────────┘                            │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
   ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
   │  Java Repo  │              │ Python Repo │              │ Monorepo    │
   │ (11 tools)  │              │ (13 tools)  │              │ (multi-lang)│
   └─────────────┘              └─────────────┘              └─────────────┘
```

**Primary Hub Workflows:**
- `hub-run-all.yml` - central execution for all repos
- `hub-orchestrator.yml` - dispatch execution into repo callers
- `hub-security.yml` - scheduled security scans
- `hub-production-ci.yml` - CI for the hub repository itself

---

## Core Components

### 1. Configuration Management (3-Tier Hierarchy)

```
Priority (Highest → Lowest):
┌─────────────────────────────────────┐
│ .ci-hub.yml (in target repo)        │  ← Developer overrides
├─────────────────────────────────────┤
│ config/repos/<repo>.yaml            │  ← Hub admin settings
├─────────────────────────────────────┤
│ config/defaults.yaml                │  ← Global baseline
└─────────────────────────────────────┘
```

**Key Features:**
- Deep merge algorithm for nested overrides
- Protected fields (`owner`, `name`, `language`, `dispatch_workflow`,
  `dispatch_enabled`) prevent accidental override
- JSON Schema v7 validation on all configs
- 12 pre-built profiles (java/python × minimal, fast, quality, coverage-gate,
  compliance, security) stored under `templates/profiles/`
- Hub CI config (`hub_ci`) governs `hub-production-ci.yml` using the same
  boolean toggle pattern as repo configs

---

### 2. Dual Execution Modes

| Mode            | Workflow               | How                 | Use Case        |
|-----------------|------------------------|---------------------|-----------------|
| **Central**     | `hub-run-all.yml`      | Run in hub          | No repo changes |
| **Distributed** | `hub-orchestrator.yml` | Dispatch repo calls | Repo autonomy   |

```
CENTRAL MODE                          DISTRIBUTED MODE
┌─────────────┐                       ┌─────────────┐
│  Hub Repo   │                       │  Hub Repo   │
│ (run-all)   │                       │(orchestrator)│
└──────┬──────┘                       └──────┬──────┘
       │ clone & test                        │ dispatch
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│  Matrix Job │                       │ Target Repo │
│ (per repo)  │                       │ (hub-ci.yml)│
└─────────────┘                       └──────┬──────┘
                                             │ calls
                                             ▼
                                      ┌─────────────┐
                                      │  Reusable   │
                                      │ java/python │
                                      │    -ci.yml  │
                                      └─────────────┘
```

---

### 3. Language-Specific Toolchains

**Java (11 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ DEFAULT ON   │ OPT-IN           │ EXPENSIVE (OPT-IN)           │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • JaCoCo     │ • jqwik          │ • Semgrep                    │
│ • Checkstyle │                  │ • Trivy                      │
│ • SpotBugs   │                  │ • CodeQL                     │
│ • PMD        │                  │ • Docker                     │
│ • OWASP DC   │                  │                              │
│ • PITest     │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Python (13 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ DEFAULT ON   │ OPT-IN           │ EXPENSIVE (OPT-IN)           │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • pytest     │ • mypy           │ • Semgrep                    │
│ • Ruff       │                  │ • Trivy                      │
│ • Black      │                  │ • CodeQL                     │
│ • isort      │                  │ • Docker                     │
│ • Bandit     │                  │                              │
│ • pip-audit  │                  │                              │
│ • mutmut     │                  │                              │
│ • Hypothesis │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Java Tool Details:**

| Tool       | Purpose                | Config Key                   | Plugin                  |
|------------|------------------------|------------------------------|-------------------------|
| JaCoCo     | Code coverage          | `jacoco.min_coverage`        | `jacoco-maven-plugin`   |
| Checkstyle | Code style             | `checkstyle.fail_on_violation` | `maven-checkstyle-plugin` |
| SpotBugs   | Bug detection          | `spotbugs.effort`            | `spotbugs-maven-plugin` |
| PMD        | Static analysis        | `pmd.max_violations`         | `maven-pmd-plugin`      |
| OWASP DC   | Dependency vulns       | `owasp.fail_on_cvss`         | `dependency-check-maven` |
| PITest     | Mutation testing       | `pitest.min_mutation_score`  | `pitest-maven`          |
| jqwik      | Property-based testing | `jqwik.enabled`              | `net.jqwik:jqwik`       |

**Python Tool Details:**

| Tool      | Purpose          | Config                                            |
|-----------|------------------|---------------------------------------------------|
| pytest    | Tests + coverage | `python.tools.pytest.min_coverage: 70`            |
| Ruff      | Fast linting     | `python.tools.ruff.fail_on_error: true`           |
| Black     | Code formatting  | `python.tools.black.fail_on_format_issues: false` |
| isort     | Import sorting   | `python.tools.isort.fail_on_issues: false`        |
| Bandit    | Security linting | `python.tools.bandit.fail_on_high: true`          |
| pip-audit | Dependency vulns | `python.tools.pip_audit.fail_on_vuln: true`       |
| mypy      | Type checking    | `python.tools.mypy.enabled`                       |
| mutmut    | Mutation testing | `python.tools.mutmut.min_mutation_score: 70`      |

All tools are simple booleans: `enabled: true/false` with optional thresholds.

---

### 4. Report & Aggregation Pipeline

```
Per-Repository Run                      Hub Aggregation
┌─────────────────┐                    ┌─────────────────┐
│   Tool Outputs  │                    │  All report.json│
│  (XML, JSON)    │                    │     files       │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│  report.json    │───────────────────▶│   Validate      │
│  (schema v2.0)  │                    │   Against       │
│                 │                    │   Schema        │
│ • coverage      │                    └────────┬────────┘
│ • mutation_score│                             │
│ • tests_passed  │                             ▼
│ • tool_metrics  │                    ┌─────────────────┐
│ • tools_ran     │                    │  summary.json   │
│ • tools_success │                    │                 │
└─────────────────┘                    │ • avg coverage  │
                                       │ • avg mutation  │
                                       │ • total vulns   │
                                       │ • pass/fail     │
                                       └─────────────────┘
```

---

### 5. CLI Tool (`cihub`) - v0.2.0

| Command          | Purpose                                     |
|------------------|---------------------------------------------|
| `detect`         | Auto-detect Java/Python from project files  |
| `new`            | Create hub-side repo config                 |
| `init`           | Generate `.ci-hub.yml` + caller workflow    |
| `update`         | Refresh existing config and caller workflow |
| `validate`       | Validate config + check POM plugins         |
| `setup-secrets`  | Configure `HUB_DISPATCH_TOKEN`              |
| `setup-nvd`      | Configure `NVD_API_KEY` for OWASP           |
| `fix-pom`        | Auto-add missing Maven plugins              |
| `fix-deps`       | Auto-add missing Maven dependencies         |
| `sync-templates` | Push caller workflows to target repos       |
| `config`         | Edit/show/set/enable/disable config values  |

---

### 6. Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION FLOW                               │
│                                                                          │
│   defaults.yaml ──▶ repos/*.yaml ──▶ .ci-hub.yml ──▶ Schema Validation   │
│                        (merge)          (merge)          (validate)      │
│                                                              │           │
│                                                              ▼           │
│                                                     Effective Config     │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          EXECUTION FLOW                                  │
│                                                                          │
│   hub-run-all.yml ──▶ Matrix Jobs ──▶ java/python-ci.yml ──▶ Tool Runs   │
│   (or orchestrator)                    (reusable)                        │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         REPORTING FLOW                                   │
│                                                                          │
│   Tool Outputs ──▶ report.json ──▶ Aggregation ──▶ summary.json/dashboard│
│                    (per repo)                      (cross-repo)          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Stats

| Metric             | Count                        |
|--------------------|------------------------------|
| Workflow YAML      | ~8,740 lines across 13 files |
| CLI Tool           | 3,326 lines, 132 functions   |
| Configured Repos   | 22                           |
| Pre-built Profiles | 12                           |
| ADRs               | 27                           |
| Unit Tests         | 80                           |
| User Guides        | 9                            |

---

## Current Status

See `docs/development/CURRENT_STATUS.md` for the authoritative status log.

| Component                        | Status      |
|----------------------------------|-------------|
| Central Mode (`hub-run-all.yml`) | ✅ Passing   |
| Reusable Workflows               | ✅ Working   |
| CLI Tool                         | ✅ v0.2.0    |
| Report Schema                    | ✅ v2.0      |
| Smoke Tests                      | ✅ Passing   |
| Orchestrator (Distributed)       | ❌ Needs fix |
| Hub Security Workflow            | ❌ Needs fix |

---

## Simple CI/CD-Hub Architecture Summary for Quick Reference
