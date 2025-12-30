# ADR-0034: Repo Template Includes Both Language Sections

**Status**: Accepted  
**Date:** 2025-12-30  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-30  

## Context

`templates/repo/.ci-hub.yml` is the base template used by `cihub init` and
`cihub update`. The schema requires a language-specific block (`java` or
`python`) based on the configured `language`. Keeping one section commented
out means `cihub init` can generate configs that are missing the required
block for that language unless a user manually edits the file.

## Decision

- Keep a single repo template (`templates/repo/.ci-hub.yml`).
- Include both `python` and `java` sections in the template.
- `cihub init/update` set `language` and remove the unused block in
  `build_repo_config` so generated configs contain only the relevant section.
- Manual users can delete the unused block; behavior is keyed off `language`.

## Consequences

Positive:
- Generated configs are schema-complete for either language.
- No new CLI selection logic or template drift risk.
- Clearer onboarding for Java repos without extra steps.

Negative:
- Template is longer and shows unused options for a given language.
- Manual editors must ignore or delete the irrelevant section.

## Alternatives Considered

1. **Separate per-language templates**
   - Rejected: duplicates template maintenance and requires CLI/doc/test updates.
2. **Keep one section commented out**
   - Rejected: Java init can produce invalid configs without manual edits.
