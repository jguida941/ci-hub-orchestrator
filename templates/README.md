# Templates Overview

Quick reference for copy/paste assets.

- **Repo template:** `templates/repo/.ci-hub.yml` – drop into target repo for local overrides.
- **Hub config template:** `templates/hub/config/repos/repo-template.yaml` – starting point for hub-side per-repo config.
- **Profiles:** `templates/profiles/*.yaml` – fast/quality/security plus new minimal, compliance, and coverage-gate variants for Java and Python.

## How to use profiles quickly

```bash
# 1) Pick a profile
ls templates/profiles

# 2) Merge it into a repo config (creates file if missing)
python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/my-repo.yaml

# 3) Fill in repo metadata if not present
sed -n '1,20p' config/repos/my-repo.yaml

# 4) Validate
python scripts/validate_config.py config/repos/my-repo.yaml
```

Profiles are additive and can be re-applied; existing repo-specific overrides win over profile defaults.
