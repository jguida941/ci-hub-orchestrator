# Templates

Copy/paste starters that align with current workflows and schema.

## Locations
- Hub-side configs live in `config/repos/` (this repo).
- Repo-local overrides live in `.ci-hub.yml` inside each target repo (highest precedence).
- Profiles and examples are under `templates/`.

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
