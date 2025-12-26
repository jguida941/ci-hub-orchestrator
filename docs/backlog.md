# Hub Backlog

Planned work items for the CI/CD Hub. Items are prioritized by category.

## Supply Chain Security

### Dependabot for Satellite Repos
**Priority**: Medium
**Added**: 2025-12-26
**Reference**: ADR-0030

Extend Dependabot configuration to satellite repositories using hub workflows:

- [ ] Java repos: Add Maven/Gradle ecosystem to dependabot.yml template
- [ ] Python repos: Add pip ecosystem to dependabot.yml template
- [ ] Create reusable dependabot.yml templates in `templates/`
- [ ] Document in guides how repos should adopt Dependabot

### Token Permissions Hardening
**Priority**: High
**Added**: 2025-12-26

Scorecard flagged 12 workflows for missing explicit `permissions:` blocks:

- [ ] Add `permissions: {}` (or minimal required) to all reusable workflow templates
- [ ] Audit each workflow for actual permission needs
- [ ] Update workflow templates in `templates/`

## Testing

### Fuzzing Support
**Priority**: Low
**Added**: 2025-12-26

Scorecard flagged missing fuzzing. Consider for critical parsing code:

- [ ] Evaluate OSS-Fuzz integration for config parsing
- [ ] Add fuzz tests for YAML/JSON schema validation
