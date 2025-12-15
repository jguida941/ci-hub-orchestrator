# Templates

Copy/paste starters that align with current workflows and schema.

## Hub-side Repo Config Template
`templates/hub/config/repos/repo-template.yaml` → copy to `config/repos/<repo>.yaml`
- Includes repo metadata, language, default_branch.
- Java/Python tool toggles with thresholds and Docker options.
- Commented for quick edits; change owner/name/branch and tweak toggles.

## Repo-local Override
`templates/repo/.ci-hub.yml` → copy to target repo (optional)
- Same keys as hub-side; higher precedence if present.
- Good for repos that want local control while using the hub.

## Profiles (planned)
- `templates/profiles/java-quality.yml`
- `templates/profiles/java-security.yml`
- `templates/profiles/python-quality.yml`
- `templates/profiles/python-security.yml`

## Dispatch Agent (planned)
- `templates/repo-agent/.github/workflows/hub-agent.yml` for distributed mode (not added yet).

## Guidance
- Only change owner/name/branch and the toggles you care about.
- Keep docker disabled unless needed; it adds time and requires health endpoints.
- For mutation/PITest, expect longer runtimes; disable if not required.
- Use CodeQL only where supported; ensure repo permissions allow it.
