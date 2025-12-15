# Templates

Copy/paste starters that align with current workflows and schema.

## Locations
- Hub-side configs live in `config/repos/` (this repo).
- Repo-local overrides live in `.ci-hub.yml` inside each target repo (highest precedence).
- Profiles and examples are under `templates/`.
- Dispatch workflow templates are under `templates/java/` and `templates/python/`.

## Dispatch Workflow Templates (NEW)

For orchestrator mode, copy these to target repos to enable hub dispatch:

| Template | Location | Usage |
|----------|----------|-------|
| Java dispatch | `templates/java/java-ci-dispatch.yml` | Copy to `.github/workflows/` in Java repos |
| Python dispatch | `templates/python/python-ci-dispatch.yml` | Copy to `.github/workflows/` in Python repos |

These templates:
- Only trigger on `workflow_dispatch` (won't affect existing CI)
- Accept all inputs the orchestrator sends
- Generate `ci-report` artifacts for aggregation

See [DISPATCH_SETUP.md](DISPATCH_SETUP.md) for full setup instructions.

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
