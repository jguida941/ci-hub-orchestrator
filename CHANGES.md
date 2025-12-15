# CI/CD Hub – Recent Changes

## Unreleased
- Replaced `hub-run-all.yml` matrix builder with `scripts/load_config.py` to honor `run_group`, dispatch toggles, and all tool flags/thresholds from schema-validated configs.
- Added `scripts/verify_hub_matrix_keys.py` to fail fast when workflows reference matrix keys that the builder does not emit.
- Hardened reusable workflows: Java/Python CI now enforce coverage, mutation, dependency, SAST, and formatting gates based on run_* flags and threshold inputs.
- Stabilized smoke test verifier script (no early exit, no eval) and anchored checks for workflow/config presence.
- Added `hub-self-check` workflow (matrix verifier, smoke setup check, matrix dry-run) and unit tests for config loading/generation.
- Installed `jq` in reusable workflows and reordered gates to upload artifacts even when enforcement fails.
