# Monorepo Support

Use `repo.subdir` when your project lives in a subfolder of a repository (e.g., fixtures monorepo).

## How to configure
1. Set `repo.subdir` in the repo config (e.g., `config/repos/fixtures-java-passing.yaml`):
   ```yaml
   repo:
     owner: jguida941
     name: ci-cd-hub-fixtures
     language: java
     default_branch: main
     subdir: java-passing
   ```
2. Central mode (`hub-run-all.yml`) now rewrites the checkout to that subfolder automatically.
3. Distributed mode (`hub-orchestrator.yml` -> `java-ci.yml` / `python-ci.yml`) passes `workdir` to reusable workflows, which run all steps in that subdir.

## Templates
- Hub config starter: `templates/hub/config/repos/monorepo-template.yaml`

## Notes
- If `subdir` is empty/missing, behavior is unchanged (repo root).
- Currently supported languages: Java, Python.
- Keep subdirs minimal and stable for predictable smoke tests.
