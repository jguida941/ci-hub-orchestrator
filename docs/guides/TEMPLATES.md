# Templates

Copy/paste starters that align with current workflows and schema.

## Locations
- Hub-side configs live in `config/repos/` (this repo).
- Repo-local overrides live in `.ci-hub.yml` inside each target repo (highest precedence).
- Profiles and examples are under `templates/`.
- Repo caller templates are under `templates/repo/` (recommended).
- Legacy dispatch templates are archived under `templates/legacy/` (deprecated).

## Repo Caller Templates (Recommended)

For orchestrator mode, copy these to target repos and name the workflow `hub-ci.yml`:

| Template | Location | Usage |
|----------|----------|-------|
| Java caller | `templates/repo/hub-java-ci.yml` | Copy to `.github/workflows/hub-ci.yml` in Java repos |
| Python caller | `templates/repo/hub-python-ci.yml` | Copy to `.github/workflows/hub-ci.yml` in Python repos |

These templates:
- Only trigger on `workflow_dispatch` (won't affect existing CI)
- Accept all inputs the orchestrator sends
- Generate `ci-report` artifacts for aggregation

See [GETTING_STARTED.md](GETTING_STARTED.md#central-mode-hub-config-5-minutes) for full setup instructions.

## Legacy Dispatch Templates (Archived)

These full dispatch workflows are preserved for historical reference only:
- `templates/legacy/java-ci-dispatch.yml`
- `templates/legacy/python-ci-dispatch.yml`

## Hub-side Repo Config Template
`templates/hub/config/repos/repo-template.yaml` → copy to `config/repos/<repo>.yaml`
- Includes repo metadata, language, default_branch.
- Java/Python tool toggles with thresholds and Docker options.
- Edit owner/name/branch/subdir and toggles; keep Docker off unless needed.

## Repo-local Override
`templates/repo/.ci-hub.yml` → copy to target repo (optional)
- Same keys as hub-side; higher precedence if present.
- Good for repos that want local control while using the hub.

## Profiles
See `templates/profiles/*.yaml` (fast, quality, security, minimal, compliance, coverage-gate for Java/Python).
- Quick reference: `templates/profiles/README.md`
- Apply helper: `python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/my-repo.yaml`
- Edit `repo:` block afterward to set owner/name/language/subdir.

## Guidance
- Use one source of truth for thresholds (`thresholds.*`), let tool `min_*` act as defaults.
- Only change the language block that matches `repo.language`; ignore/remove the other.
- CodeQL is heavy and may need org permissions; enable intentionally.
- Mutation/PITest adds runtime; disable if not required.
- Docker adds time and health checks; leave disabled unless needed.
