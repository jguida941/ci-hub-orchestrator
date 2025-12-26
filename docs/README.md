# Hub Documentation Index

Welcome to the CI/CD Hub documentation. This index helps you find what you need.

---

## Getting Started

Start here if you're new to the hub:

1. **[guides/ONBOARDING.md](guides/ONBOARDING.md)** - How to connect a repository to the hub
2. **[guides/WORKFLOWS.md](guides/WORKFLOWS.md)** - Overview of all available workflows
3. **[guides/MODES.md](guides/MODES.md)** - Understanding central vs distributed execution
4. **[reference/CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md)** - Complete configuration reference

## Project Policies

- [CONTRIBUTING.md](../.github/CONTRIBUTING.md) - How to contribute
- [SECURITY.md](../.github/SECURITY.md) - Vulnerability reporting policy
- [CODE_OF_CONDUCT.md](../.github/CODE_OF_CONDUCT.md) - Community standards
- [Makefile](../Makefile) - Canonical developer commands

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
│   ├── MONOREPOS.md
│   ├── DISPATCH_SETUP.md
│   ├── INTEGRATION_SMOKE_TEST.md
│   └── KYVERNO.md
├── reference/       # Reference documentation
│   ├── CONFIG_REFERENCE.md
│   ├── TOOLS.md
│   └── example.ci-hub.yml
├── development/     # Internal/development docs
│   ├── CHANGELOG.md
│   ├── BACKLOG.md
│   ├── DEVELOPMENT.md
│   ├── specs/
│   │   ├── P0.md
│   │   ├── P1.md
│   │   ├── nonfunctional.md
│   │   └── README.md
│   ├── status/
│   │   ├── STATUS.md
│   │   ├── INTEGRATION_STATUS.md
│   │   └── SMOKE_TEST_SNAPSHOT_2025-12-14.md
│   ├── architecture/
│   │   ├── ARCHITECTURE_PLAN.md
│   │   ├── ARCH_OVERVIEW.md
│   │   └── SUMMARY_CONTRACT.md
│   ├── execution/
│   │   ├── SMOKE_TEST.md
│   │   └── SMOKE_TEST_REPOS.md
│   ├── research/
│   │   ├── RESEARCH_LOG.md
│   │   └── MUTATION_TESTING_GAPS.md
│   └── archive/
│       ├── ROADMAP.md
│       ├── OUTSTANDING.md
│       ├── FIXTURES_PLAN.md
│       ├── WORKFLOW_MIGRATION.md
│       └── audit.md
├── adr/             # Architecture Decision Records (0001-0028)
└── README.md        # This file
```

---

## Guides

User-facing tutorials and how-to guides:

| Document                                        | Description                                        |
|-------------------------------------------------|----------------------------------------------------|
| [ONBOARDING.md](guides/ONBOARDING.md)           | How to connect a repository to the hub             |
| [WORKFLOWS.md](guides/WORKFLOWS.md)             | All workflow descriptions                          |
| [MODES.md](guides/MODES.md)                     | Central vs distributed execution modes             |
| [TEMPLATES.md](guides/TEMPLATES.md)             | Ready-to-use config templates                      |
| [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) | Common issues and solutions                        |
| [MONOREPOS.md](guides/MONOREPOS.md)             | Monorepo support guide                             |
| [DISPATCH_SETUP.md](guides/DISPATCH_SETUP.md)               | How to set up tokens and dispatchable repos        |
| [INTEGRATION_SMOKE_TEST.md](guides/INTEGRATION_SMOKE_TEST.md) | Integration smoke test guide                       |
| [KYVERNO.md](guides/KYVERNO.md)                               | Optional Kubernetes admission control with Kyverno |

---

## Reference

Technical reference documentation:

| Document                                             | Description                         |
|------------------------------------------------------|-------------------------------------|
| [CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md) | Field-by-field config documentation |
| [TOOLS.md](reference/TOOLS.md)                       | Documentation for each quality tool |
| [example.ci-hub.yml](reference/example.ci-hub.yml)   | Example configuration file          |

---

## Development

Internal documentation for hub maintainers:

| Document | Description |
|----------|-------------|
| [CHANGELOG.md](development/CHANGELOG.md) | Release notes and change history |
| [BACKLOG.md](development/BACKLOG.md) | Feature backlog and priorities |
| [DEVELOPMENT.md](development/DEVELOPMENT.md) | Developer guide and commands |
| [specs/](development/specs/) | P0/P1/nonfunctional requirements |
| [STATUS.md](development/status/STATUS.md) | Current execution plan |
| [INTEGRATION_STATUS.md](development/status/INTEGRATION_STATUS.md) | Quarantine graduation tracking |
| [SMOKE_TEST_SNAPSHOT_2025-12-14.md](development/status/SMOKE_TEST_SNAPSHOT_2025-12-14.md) | Smoke test setup snapshot |
| [ARCHITECTURE_PLAN.md](development/architecture/ARCHITECTURE_PLAN.md) | Master architecture plan |
| [ARCH_OVERVIEW.md](development/architecture/ARCH_OVERVIEW.md) | Architecture overview |
| [SUMMARY_CONTRACT.md](development/architecture/SUMMARY_CONTRACT.md) | Summary format contract |
| [SMOKE_TEST.md](development/execution/SMOKE_TEST.md) | How to run smoke tests |
| [SMOKE_TEST_REPOS.md](development/execution/SMOKE_TEST_REPOS.md) | Smoke test repository requirements |
| [RESEARCH_LOG.md](development/research/RESEARCH_LOG.md) | Design decisions and research |
| [MUTATION_TESTING_GAPS.md](development/research/MUTATION_TESTING_GAPS.md) | Mutation testing gap analysis |
| [archive/](development/archive/) | Archived docs (ROADMAP, OUTSTANDING, etc.) |
| [adr/](adr/) | Architecture Decision Records (0001-0028) |

---

## Quick Links by Task

### I want to...

| Task | Document |
|------|----------|
| Add a new repository to the hub | [guides/ONBOARDING.md](guides/ONBOARDING.md) |
| Understand what tools are available | [reference/TOOLS.md](reference/TOOLS.md) |
| Configure tool thresholds | [reference/CONFIG_REFERENCE.md](reference/CONFIG_REFERENCE.md#thresholds) |
| Run a smoke test | [development/execution/SMOKE_TEST.md](development/execution/SMOKE_TEST.md) |
| Understand central vs distributed mode | [guides/MODES.md](guides/MODES.md) |
| Troubleshoot a failing workflow | [guides/TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) |
| Create a custom config | [guides/TEMPLATES.md](guides/TEMPLATES.md) |
| Understand workflow inputs | [guides/WORKFLOWS.md](guides/WORKFLOWS.md) |
| Set up a monorepo | [guides/MONOREPOS.md](guides/MONOREPOS.md) |
| Add Kubernetes admission control (optional) | [guides/KYVERNO.md](guides/KYVERNO.md) |

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
3. [development/execution/SMOKE_TEST.md](development/execution/SMOKE_TEST.md) - Pre-release validation
4. [development/research/RESEARCH_LOG.md](development/research/RESEARCH_LOG.md) - Design decisions
5. [development/BACKLOG.md](development/BACKLOG.md) - Feature backlog
6. [development/DEVELOPMENT.md](development/DEVELOPMENT.md) - Developer guide and commands
7. [development/specs/](development/specs/) - P0/P1 requirements
7. [Makefile](../Makefile) - Canonical developer commands

### For AI Assistants
1. **[../AGENTS.md](../AGENTS.md)** - AI context and rules
2. [development/research/RESEARCH_LOG.md](development/research/RESEARCH_LOG.md) - Full context
3. [development/BACKLOG.md](development/BACKLOG.md) - Current priorities

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
- **Kyverno**: https://kyverno.io/docs/

## Precedence reminder
- defaults.yaml -> config/repos/<repo>.yaml -> repo-local .ci-hub.yml (repo wins).
- Dispatch mode: hub config is merged with repo-local `.ci-hub.yml` (repo wins).
- Profiles seed hub configs; they are not a runtime layer.
- run_group can filter hub runs (full/fixtures/smoke).
