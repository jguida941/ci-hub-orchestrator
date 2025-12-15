# ADR-0007: Templates and Profiles Strategy

- Status: Accepted
- Date: 2026-01-02

## Context

Users need a fast way to onboard repos to the hub with sane defaults and repeatable tool mixes. We recently added:
- Repo template (`templates/repo/.ci-hub.yml`)
- Hub-side repo template (`templates/hub/config/repos/repo-template.yaml`)
- Profiles for fast/quality/security plus new minimal, compliance, coverage-gate variants
- Helper to apply a profile onto a repo config (`scripts/apply_profile.py`)

We need to lock in how templates/profiles are structured, merged, and validated so future changes remain compatible and discoverable.

## Decision

1. **Single source of truth for defaults** remains `config/defaults.yaml`; templates must not drift—comments guide usage but do not override defaults unless copied by users.
2. **Profiles are additive overlays**: profiles provide recommended tool toggles and thresholds; when applied, the target config wins on conflicts (overlay then user override). The helper performs a deep merge with user config taking precedence.
3. **Profile catalog** lives under `templates/profiles/` with README matrix; new profiles must be documented there and be schema-valid.
4. **Hub-side template** (`templates/hub/config/repos/repo-template.yaml`) is the blessed starter for per-repo configs; repo template (`templates/repo/.ci-hub.yml`) is the starter for in-repo overrides.
5. **Validation is required**: any profile or template changes must pass `scripts/validate_config.py` against the schema.

## Consequences

Positive:
- Faster onboarding via ready-made profiles and apply helper.
- Clear, discoverable catalog and starters reduce misconfigurations.
- Merge semantics protect existing repo overrides when applying profiles.

Negative:
- Extra maintenance to keep profile README and catalog in sync.
- Schema changes may require profile updates to stay valid.

## Alternatives Considered

- **Manual copy/paste only**: slower, error-prone, and harder to keep consistent.
- **Profiles override user config**: rejected to avoid clobbering repo-specific choices.
- **Multiple template locations**: rejected to reduce drift; keep under `templates/` with a single README.
