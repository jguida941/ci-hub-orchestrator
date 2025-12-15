# Hub Documentation Index

Welcome to the CI/CD Hub documentation. This index helps you find what you need.

---

## Getting Started

Start here if you're new to the hub:

1. **[ONBOARDING.md](ONBOARDING.md)** - How to connect a repository to the hub
2. **[WORKFLOWS.md](WORKFLOWS.md)** - Overview of all available workflows
3. **[MODES.md](MODES.md)** - Understanding central vs distributed execution
4. **[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)** - Complete configuration reference

---

## Core Documentation

### Configuration & Setup
- **[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)** - Field-by-field config documentation
- **[TEMPLATES.md](TEMPLATES.md)** - Ready-to-use config templates
- **[TOOLS.md](TOOLS.md)** - Documentation for each quality tool

### Workflows & Execution
- **[WORKFLOWS.md](WORKFLOWS.md)** - All workflow descriptions
- **[MODES.md](MODES.md)** - Central vs distributed execution modes

### Testing & Validation
- **[SMOKE_TEST.md](SMOKE_TEST.md)** - How to run smoke tests
- **[SMOKE_TEST_REPOS.md](SMOKE_TEST_REPOS.md)** - Smoke test repository requirements
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Research & Planning
- **[RESEARCH.md](RESEARCH.md)** - Comprehensive research and design decisions
- **[ROADMAP.md](ROADMAP.md)** - Project roadmap and phases
- **[adr/](adr/)** - Architecture Decision Records

---

## Quick Links by Task

### I want to...

**Add a new repository to the hub**
→ [ONBOARDING.md](ONBOARDING.md)

**Understand what tools are available**
→ [TOOLS.md](TOOLS.md)

**Configure tool thresholds**
→ [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md#thresholds)

**Run a smoke test**
→ [SMOKE_TEST.md](SMOKE_TEST.md)

**Understand central vs distributed mode**
→ [MODES.md](MODES.md)

**Troubleshoot a failing workflow**
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Create a custom config**
→ [TEMPLATES.md](TEMPLATES.md)

**Understand workflow inputs**
→ [WORKFLOWS.md](WORKFLOWS.md)

---

## Documentation by Audience

### For Developers (Adding Repos to Hub)
1. [ONBOARDING.md](ONBOARDING.md) - Connect your repo
2. [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Configure tools
3. [TOOLS.md](TOOLS.md) - Understand what each tool does
4. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Fix common issues

### For Hub Maintainers
1. [WORKFLOWS.md](WORKFLOWS.md) - Workflow internals
2. [MODES.md](MODES.md) - Execution modes
3. [SMOKE_TEST.md](SMOKE_TEST.md) - Pre-release validation
4. [RESEARCH.md](RESEARCH.md) - Design decisions
5. [ROADMAP.md](ROADMAP.md) - Future plans

### For AI Assistants
1. **[../AGENTS.md](../AGENTS.md)** - AI context and rules
2. [RESEARCH.md](RESEARCH.md) - Full context
3. [ROADMAP.md](ROADMAP.md) - Current focus

---

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| ONBOARDING.md | ✅ Complete | 2025-12-14 |
| WORKFLOWS.md | ✅ Complete | 2025-12-14 |
| CONFIG_REFERENCE.md | ✅ Complete | 2025-12-14 |
| TOOLS.md | ✅ Complete | 2025-12-14 |
| MODES.md | ✅ Complete | 2025-12-14 |
| TEMPLATES.md | ✅ Complete | 2025-12-14 |
| TROUBLESHOOTING.md | ✅ Complete | 2025-12-14 |
| SMOKE_TEST.md | ✅ Complete | 2025-12-14 |
| SMOKE_TEST_REPOS.md | ✅ Complete | 2025-12-14 |
| RESEARCH.md | ✅ Complete | 2025-12-14 |
| ROADMAP.md | ✅ Complete | 2025-12-14 |

---

## File Organization

```
hub-release/
├── docs/
│   ├── README.md (this file)
│   ├── ONBOARDING.md - Getting started guide
│   ├── WORKFLOWS.md - Workflow reference
│   ├── CONFIG_REFERENCE.md - Configuration docs
│   ├── TOOLS.md - Tool documentation
│   ├── MODES.md - Execution modes
│   ├── TEMPLATES.md - Config templates
│   ├── TROUBLESHOOTING.md - Common issues
│   ├── SMOKE_TEST.md - Smoke test guide
│   ├── SMOKE_TEST_REPOS.md - Test repo requirements
│   ├── RESEARCH.md - Design research
│   ├── ROADMAP.md - Project roadmap
│   ├── adr/ - Architecture decisions
│   └── example.ci-hub.yml - Example config
├── config/
│   ├── defaults.yaml - Global defaults
│   └── repos/ - Per-repo configs
├── .github/
│   └── workflows/ - Hub workflows
└── requirements/ - P0, P1 checklists
```

---

## Contributing

When adding new documentation:
1. Update this README.md index
2. Follow existing document structure
3. Add cross-references to related docs
4. Update "Last Updated" dates
5. Mark status as complete when done

---

## External Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **JaCoCo**: https://www.jacoco.org/jacoco/
- **PITest**: https://pitest.org/
- **Ruff**: https://github.com/astral-sh/ruff
- **OWASP Dependency Check**: https://owasp.org/www-project-dependency-check/
