# Hub Documentation Index

Welcome to the CI/CD Hub documentation. This index helps you find what you need.

---

## Getting Started

Start here if you're new to the hub:

1. **[guides/ONBOARDING.md](guides/ONBOARDING.md)** - How to connect a repository to the hub
2. **[guides/WORKFLOWS.md](guides/WORKFLOWS.md)** - Overview of all available workflows
3. **[guides/MODES.md](guides/MODES.md)** - Understanding central vs distributed execution
4. **[reference/CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md)** - Complete configuration reference

---

## Documentation Structure

```
docs/
├── guides/          # User guides and tutorials
│   ├── ONBOARDING.md
│   ├── WORKFLOWS.md
│   ├── MODES.md
│   ├── TEMPLATES.md
│   ├── TROUBLESHOOTING.md
│   └── MONOREPOS.md
├── reference/       # Reference documentation
│   ├── CONFIG_REFERENCE.md
│   ├── TOOLS.md
│   └── example.ci-hub.yml
├── development/     # Internal/development docs
│   ├── ROADMAP.md
│   ├── RESEARCH.md
│   ├── SMOKE_TEST.md
│   ├── SMOKE_TEST_REPOS.md
│   ├── SMOKE_TEST_SETUP_SUMMARY.md
│   └── audit.md
├── adr/             # Architecture Decision Records
└── README.md        # This file
```

---

## Guides

User-facing tutorials and how-to guides:

| Document | Description |
|----------|-------------|
| [ONBOARDING.md](guides/ONBOARDING.md) | How to connect a repository to the hub |
| [WORKFLOWS.md](guides/WORKFLOWS.md) | All workflow descriptions |
| [MODES.md](guides/MODES.md) | Central vs distributed execution modes |
| [TEMPLATES.md](guides/TEMPLATES.md) | Ready-to-use config templates |
| [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) | Common issues and solutions |
| [MONOREPOS.md](guides/MONOREPOS.md) | Monorepo support guide |

---

## Reference

Technical reference documentation:

| Document | Description |
|----------|-------------|
| [CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md) | Field-by-field config documentation |
| [TOOLS.md](reference/TOOLS.md) | Documentation for each quality tool |
| [example.ci-hub.yml](reference/example.ci-hub.yml) | Example configuration file |

---

## Development

Internal documentation for hub maintainers:

| Document | Description |
|----------|-------------|
| [ROADMAP.md](development/ROADMAP.md) | Project roadmap and phases |
| [RESEARCH.md](development/RESEARCH.md) | Design decisions and research |
| [SMOKE_TEST.md](development/SMOKE_TEST.md) | How to run smoke tests |
| [SMOKE_TEST_REPOS.md](development/SMOKE_TEST_REPOS.md) | Smoke test repository requirements |
| [audit.md](development/audit.md) | Audit findings and status |
| [adr/](adr/) | Architecture Decision Records |

---

## Quick Links by Task

### I want to...

| Task | Document |
|------|----------|
| Add a new repository to the hub | [guides/ONBOARDING.md](guides/ONBOARDING.md) |
| Understand what tools are available | [reference/TOOLS.md](reference/TOOLS.md) |
| Configure tool thresholds | [reference/CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md#thresholds) |
| Run a smoke test | [development/SMOKE_TEST.md](development/SMOKE_TEST.md) |
| Understand central vs distributed mode | [guides/MODES.md](guides/MODES.md) |
| Troubleshoot a failing workflow | [guides/TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) |
| Create a custom config | [guides/TEMPLATES.md](guides/TEMPLATES.md) |
| Understand workflow inputs | [guides/WORKFLOWS.md](guides/WORKFLOWS.md) |
| Set up a monorepo | [guides/MONOREPOS.md](guides/MONOREPOS.md) |

---

## Documentation by Audience

### For Developers (Adding Repos to Hub)
1. [guides/ONBOARDING.md](guides/ONBOARDING.md) - Connect your repo
2. [reference/CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md) - Configure tools
3. [reference/TOOLS.md](reference/TOOLS.md) - Understand what each tool does
4. [guides/TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) - Fix common issues

### For Hub Maintainers
1. [guides/WORKFLOWS.md](guides/WORKFLOWS.md) - Workflow internals
2. [guides/MODES.md](guides/MODES.md) - Execution modes
3. [development/SMOKE_TEST.md](development/SMOKE_TEST.md) - Pre-release validation
4. [development/RESEARCH.md](development/RESEARCH.md) - Design decisions
5. [development/ROADMAP.md](development/ROADMAP.md) - Future plans

### For AI Assistants
1. **[../AGENTS.md](../AGENTS.md)** - AI context and rules
2. [development/RESEARCH.md](development/RESEARCH.md) - Full context
3. [development/ROADMAP.md](development/ROADMAP.md) - Current focus

---

## Contributing

When adding new documentation:
1. Place user guides in `guides/`
2. Place reference docs in `reference/`
3. Place internal docs in `development/`
4. Update this README.md index
5. Add cross-references to related docs

---

## External Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **JaCoCo**: https://www.jacoco.org/jacoco/
- **PITest**: https://pitest.org/
- **Ruff**: https://github.com/astral-sh/ruff
- **OWASP Dependency Check**: https://owasp.org/www-project-dependency-check/
