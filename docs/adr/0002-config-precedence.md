# ADR-0002: Config Precedence Hierarchy

**Status**: Accepted  
**Date:** 2025-12-14  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The hub needs a consistent way to merge configuration from multiple sources. Users may want:
- Global defaults for all repos
- Hub-side overrides for specific repos (without touching target repos)
- Repo-local config for repos that want full control

Questions:
- Which source wins when there's a conflict?
- How deep does merging go (shallow vs deep)?
- Where does schema validation occur?

## Decision

Three-tier hierarchy (highest precedence wins):

```
1. Repo-local .ci-hub.yml       (in target repo root)
2. Hub config/repos/<repo>.yaml (hub-side per-repo override)
3. Hub config/defaults.yaml     (global defaults)
```

**Merge strategy:** Deep merge. Nested objects merge recursively; scalar values are replaced.

**Schema validation:** Occurs in:
- `scripts/load_config.py` on config load
- `hub-orchestrator.yml` load-config job before dispatch
- `config-validate.yml` workflow on config/schema changes

## Alternatives Considered

1. **Single source (hub only):** Rejected. Repos lose autonomy; every change requires hub PR.
2. **Repo-only config:** Rejected. Can't set global defaults; every repo must configure everything.
3. **Shallow merge:** Rejected. Would require full tool blocks instead of just `enabled: false`.
4. **Environment-based overrides:** Rejected as primary mechanism. Too implicit; hard to track.

## Consequences

**Positive:**
- Repos can override specific settings without duplicating entire config
- Hub admins can set sensible defaults centrally
- Changes to defaults propagate to all repos automatically
- Repo-local config allows full repo autonomy when needed

**Negative:**
- Three places to check when debugging config issues
- Deep merge can be surprising (nested keys override, not replace)
- Repo-local config requires target repo changes

**Implementation notes:**
- `load_config.py` uses recursive dict merge
- Validation runs on merged config, not individual sources
- Config hierarchy documented in CONFIG.md

**Dispatch-time overrides:**

There is no dispatch-time threshold override. Thresholds are config-only and resolved by the CLI from `.ci-hub.yml` and hub defaults. The orchestrator dispatches only minimal metadata (for example, a correlation ID). See ADR-0024 for details.
