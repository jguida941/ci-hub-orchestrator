# Outstanding Work (central CI/CD hub)

## Open fixes to implement
- Orchestrator: use `scripts/load_config.py --output workflow-inputs`, inject run_* flags into the matrix, append entries correctly, and gate dispatch steps on those flags (mirror hub-run-all). Add a sanity assert when configs exist so the matrix isn’t empty.
- Hub-run-all: replace grep parsing with a single Python load to build matrix entries deterministically (repo metadata, run_group, run_* flags, thresholds).
- Reusable workflows (`java-ci.yml`, `python-ci.yml`): add real gate evaluation (fail when thresholds/policies say so); reduce `continue-on-error` where policy requires failing.
- Docs (README, docs/README, ONBOARDING, WORKFLOWS, CONFIG_REFERENCE): clarify precedence defaults -> hub config (`config/repos/*.yaml`) -> repo `.ci-hub.yml` (repo wins); profiles are generation inputs, not a runtime layer; tool gating is config-driven; run_group usage; schema constraints (required language, subdir pattern, enums, additionalProperties: false).
- Dispatch mode: define whether repo-local `.ci-hub.yml` is honored (target workflow loads local config) or hub inputs are authoritative; document the decision.
- Kyverno: keep as optional feature; add guide/index entry and ensure policy + validation workflow are documented; clarify optional usage.
- Add CHANGES.md (or changelog entry) summarizing the current batch (config-driven gating, schema tightening, loader/tool flags).
- apply_profile determinism: fix merge order (no set-union), document/handle list behavior, consider atomic write; optional diff/dry-run; guardrail for mismatched profile vs repo language.
- Validation flow: validate merged configs (or partial schema for defaults/repo overrides); wrap ValidationError cleanly; sort errors for stable CI output; safe_dump/read with UTF-8.
- Smoke test verifier: with set -e, guard checks or make check always return 0; avoid eval; anchor greps.
- Dashboard next steps: add per-repo metrics.json, hub-report.json aggregation, and links in summaries to artifacts; optional static page for filters/trends.

## Already done (pending push)
- `scripts/load_config.py`: emits run flags for all tools (Java: jacoco/checkstyle/spotbugs/owasp/pitest/pmd/semgrep/trivy; Python: pytest/ruff/bandit/pip_audit/black/isort/mypy/mutmut/hypothesis/semgrep/trivy), thresholds, run_group, dispatch.
- `.github/workflows/hub-run-all.yml`: tool steps gated on run_* flags; mutmut TOTAL default; PITest search is repo-wide; Semgrep/Trivy gated by flags.
- `schema/ci-hub-config.schema.json`: tightened (additionalProperties: false, required repo/language, subdir pattern, run_group enum, language conditionals, full tool definitions, bounded thresholds).

## Untracked/staged items to resolve
- Kyverno files (policy, ADR, kyverno-validate workflow, guides/templates) need final placement and docs wiring.
- `hub-orchestrator.yml` still ignores tool flags until updated.
