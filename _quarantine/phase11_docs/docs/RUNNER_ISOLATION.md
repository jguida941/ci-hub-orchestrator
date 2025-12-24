# Runner Isolation & Fairness Playbook

This playbook defines how the CI Intelligence Hub keeps build runners ephemeral, applies
concurrency budgets, and captures evidence that fairness safeguards are enforced.

## Objectives

- **Isolation**: every workflow runs on disposable GitHub-hosted runners so secrets and
  artifacts never persist between jobs.
- **Fairness**: long-lived workflows cannot starve shared runners — per-workflow and
  per-job budgets limit concurrency and enforce cancellation semantics.
- **Evidence**: automation verifies runner assignments, concurrency settings, and
  matrix `max-parallel` caps on every pull request via `scripts/check_runner_isolation.py`.

## Operational Controls

1. **Budget configuration** – `config/runner-isolation.yaml` lists the allowed runner
   labels, self-hosted profiles, and the maximum concurrency per workflow/job. Update this
   file whenever a new workflow, matrix job, or self-hosted profile is added.
2. **Automation gate** – `security-lint.yml` runs
   `python scripts/check_runner_isolation.py --config config/runner-isolation.yaml`. The
   gate fails if a workflow:
   - lacks a `concurrency` block with `cancel-in-progress: true`,
   - uses runner labels outside the approved list, or
   - omits required `strategy.max-parallel` caps.
3. **Release matrix throttling** – `project-tests` in `release.yml` sets
   `strategy.max-parallel: 2`, matching the budget. Adjust the matrix budget in the config
   file if additional downstream repos are added.

## Updating Budgets

1. Edit `config/runner-isolation.yaml`, adding or modifying the `workflows` ➜ `jobs`
   section for the affected workflow. Specify `runs_on` (string or list) and, for matrix
   jobs, `max_parallel`.
2. Run the guard locally:

   ```bash
   python scripts/check_runner_isolation.py --config config/runner-isolation.yaml
   ```

   To exercise a self-hosted profile, add a temporary workflow in a scratch branch and
   run the guard with `--workflows-dir` pointing at that directory (see
   `tools/tests/test_runner_isolation.py`).

3. Commit changes and ensure `security-lint` passes in CI.

## Evidence Artifacts

- Successful runs append `[runner-isolation] validated …` to the `workflow-guard` job log.
- When budgets change, link the diff in change-management tickets and include the guard
  log snippet in the evidence bundle.
- Self-hosted profiles should reference an egress policy document (e.g.,
  `policies/egress-allowlist.md`) and cache provenance evidence (`scripts/cache_provenance.sh`
  and `tools/cache_sentinel.py`). Capture those artifact URIs in the change record so
  auditors can prove the self-hosted runner followed the same controls as hosted runners.

## Troubleshooting

- **Guard fails (missing concurrency)**: add or fix the `concurrency` block in the
  offending workflow and ensure `cancel-in-progress: true`.
- **Guard fails (max-parallel mismatch)**: update the workflow’s `strategy.max-parallel`
  to match the configured budget or adjust the budget after reviewing capacity.
- **Guard fails (self-hosted labels)**: confirm the job’s `runs-on` includes every label
  listed in the referenced `self_hosted_profile` (e.g., `self-hosted`, `build-fips`, `linux`).
- **Need higher throughput**: raise the budget in `config/runner-isolation.yaml`, update
  the workflow, and record the new concurrency SLO in this playbook.
