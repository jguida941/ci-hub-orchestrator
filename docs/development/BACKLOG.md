# Backlog

Single queue for known issues and near-term work.

## High Priority

| Item                        | Category       | Notes                                                                                                            |
|-----------------------------|----------------|------------------------------------------------------------------------------------------------------------------|
| NVD key setup issue         | Secrets        | Possible whitespace/validation or missing secret propagation; `setup-nvd` may not work end-to-end (docs/development/CHANGELOG.md) |
| Phase 6: Diagnostics module | CLI            | `cihub/diagnostics/` scaffolded but not implemented (models.py, renderer.py, collectors/)                        |
| Token Permissions Hardening | Supply Chain   | Scorecard flagged 12 workflows missing explicit `permissions:` blocks; add to reusable workflow templates        |

## Medium Priority

| Item                                | Category       | Notes                                                              |
|-------------------------------------|----------------|--------------------------------------------------------------------|
| CLI: dispatch + sync in one command | CLI            | Combine dispatch repo update and workflow sync into single command |
| PyQt6 GUI ADR + MVP scope           | Planning       | Define ADR and minimal viable scope for GUI tool                   |
| CLI add/list/lint/apply commands    | CLI            | Partial implementation noted in ARCHITECTURE_PLAN.md               |
| Restore relaxed thresholds          | Fixtures       | ADR-0018 notes some thresholds relaxed due to tool config issues   |
| Dependabot for Satellite Repos      | Supply Chain   | Extend dependabot.yml to Java/Python satellite repos; see ADR-0030 |

## Low Priority / Future

| Item                                  | Category       | Notes                                                              |
|---------------------------------------|----------------|--------------------------------------------------------------------|
| User-facing tool documentation        | Docs           | ADR-0017 lists as TODO                                             |
| Kotlin project support                | CLI            | Mentioned in RESEARCH_LOG.md as TODO                               |
| Validate configs against actual repos | Testing        | audit.md mentions this as incomplete                               |
| Fuzzing Support                       | Supply Chain   | Scorecard flagged; consider OSS-Fuzz for config parsing/validation |

## Completed (Archive)

Move items here when done:

| Item                                 | Completed | PR/Commit |
|--------------------------------------|-----------|-----------|
| CLI modular restructure (Phases 1-5) | 2024-12   | -         |
| Wizard cancellation safety           | 2024-12   | -         |
| Emoji output normalization           | 2024-12   | -         |
