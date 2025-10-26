## Documentation Upgrade Plan

### 0. Summary & metadata

- Execute this doc overhaul after CI is consistently green but before the GA tag so commands/paths match reality.

- Reserve a block at the top of `OVERVIEW.md` with a metadata table:

  | Key | Value |
  | --- | --- |
  | Project | CI Intelligence Hub |
  | Purpose | CI/CD observability + supply-chain assurance |
  | Language | Python 3.12, Bash |
  | License | SPDX-ID (MIT or actual) |


- Add CI badges (placeholder now, real links later) under the table, e.g. `![CI](#) ![Docs](#) ![License](#)`.

- Add a **Scope** sentence clarifying covered areas (e.g., “Docs cover /tools scripts; workflow YAMLs are documented under /docs/workflows”).

- State **Purpose** & **Audience** explicitly before diving into components.

- Add a Mermaid flow diagram for cross-module context:

  ```mermaid
  flowchart TD
    A[Build & Sign] --> B[SBOM/VEX Referrers]
    B --> C[Policy Gates]
    C --> D[Mutation Observatory]
    D --> E[Cache Sentinel]
  ```

### 1. Top-level files

- Create skeleton files now (with headings + stub changelog) to avoid broken links:
  - `docs/OVERVIEW.md`
  - `docs/TESTING.md`
  - `docs/CONTRIBUTING.md`
  - `docs/mkdocs.yml` (if planning MkDocs)

- Keep all doc assets under `/docs`.

- `OVERVIEW.md`: architecture summary, metadata table, badges, flow diagram, module links, dependency matrix (Module | Python deps | CLI | Optional), canonical artifact paths table, verified environment note (“Python 3.12.x / pip 24.x / Ubuntu 22.04”).

- `TESTING.md`: unified matrix describing local vs. CI suites, expected runtime, sample command, plus “Quick validation” snippet:

  ```bash
  pytest -q --disable-warnings | tee results.log
  grep -q "failed" results.log && echo "⚠️ Failures detected" || echo "✅ All tests passed"
  ```

- `CONTRIBUTING.md`: PR conventions, code style (black/ruff), doc expectations. Add “How to update docs” footer:
  1. Update relevant README headings.
  2. Run `markdownlint`.
  3. Commit with `docs:<module>` prefix.

- `mkdocs.yml` skeleton (optional) to future-proof HTML docs:

  ```yaml
  site_name: CI Intelligence Hub
  nav:
    - Overview: OVERVIEW.md
    - Testing: TESTING.md
    - Tools:
        - Mutation Observatory: tools/mutation_observatory/README.md
        - Cache Sentinel: tools/cache_sentinel/README.md
  ```

### 2. Canonical artifact directory table

Document once (in OVERVIEW) and reference from module READMEs:

| Purpose | Path |

| --- | --- |

| Build evidence | artifacts/evidence/ |

| Policy inputs | policy-inputs/ |

| Mutation reports | artifacts/mutation/ |

### 3. Module READMEs (consistent structure)

Every major tool gets a README with sections:

```markdown

## Purpose

## Usage

## Configuration

## Testing

## Dependencies

## Output & Artifacts

## Changelog

## License

```

- Use relative links (`./tools/cache_sentinel/README.md`) for cross-references.

- End with a **Changelog** (e.g., “2025-10-26: Documentation framework initialized”) and license note pointing to root LICENSE/SPDX.

- Include “Back to [Overview](../docs/OVERVIEW.md)” link at the bottom for navigation.

- Mention output directories and include sample JSON/YAML snippets.

Modules to document (non-exhaustive):

- `tools/mutation_observatory`

- `tools/cache_sentinel`

- `tools/generate_vex.py` + `fixtures/supply_chain`

- `tools/build_vuln_input.py`

- `tools/rekor_monitor.sh`

- `tools/scripts/generate_mutation_reports.py`

- Any other critical tooling (e.g., `tools/determinism_check.sh`, `tools/publish_referrers.sh` if applicable)

### 4. Testing references

- Each README links back to `TESTING.md` instead of duplicating full instructions, but still lists module-specific commands.

- Root README includes quick-start commands:

  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements-dev.txt
  pytest
  ```

### 5. Changelog & change-control

- Append `## Changelog` sections to major docs outlining edit history.

- Encourage contributors to update the changelog entries when modifying docs.

### 6. Markdown lint & style

- Add `.markdownlint.json` (e.g., disable MD013/MD033/MD041) to lock formatting.

- After writing docs, run `markdownlint '**/*.md'` (or equivalent) to catch heading/style issues.

- Use imperative voice (“Run,” “Use,” “Record”) for instructions.

- Later, add a CI check that fails if `grep -R "TODO" docs/` finds unfinished sections.

### 7. Doc tooling dependencies

- Add `mkdocs`, `mkdocs-material`, `pdoc` to `requirements-dev.txt` so contributors can preview docs locally.

### 8. Optional automation

- Once the manual docs are in place, evaluate mkdocs/pdoc for automated HTML rendering (ties into the skeleton file).
