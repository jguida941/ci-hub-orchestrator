# Fixtures Plan

> **Status:** Legacy archive (2025-12-26). Fixture matrix has been consolidated into `docs/development/execution/SMOKE_TEST.md`.

## Goals

- Provide deterministic, repeatable fixtures for all supported repo layouts.
- Validate central and distributed modes using boolean tool toggles.
- Ensure core tool families have pass and fail coverage (heavy tools like Trivy/CodeQL are off by default for speed).

## Fixture Repo

- Repo: `ci-cd-hub-fixtures`
- Structure: subdirs per fixture scenario
- Each fixture is used by one or more hub configs in `config/repos/`.

## Fixture Matrix

| Fixture Subdir           | Language | Config File                                            | Purpose                     |
|--------------------------|----------|--------------------------------------------------------|-----------------------------|
| `java-maven-pass`        | Java     | `config/repos/fixtures-java-passing.yaml`              | Maven, all Java tools pass  |
| `java-maven-fail`        | Java     | `config/repos/fixtures-java-failing.yaml`              | Maven, controlled failures  |
| `java-gradle-pass`       | Java     | `config/repos/fixtures-java-gradle-passing.yaml`       | Gradle coverage             |
| `java-gradle-fail`       | Java     | `config/repos/fixtures-java-gradle-failing.yaml`       | Gradle failure paths        |
| `java-multi-module-pass` | Java     | `config/repos/fixtures-java-multi-module-passing.yaml` | Parent/child modules        |
| `python-pyproject-pass`  | Python   | `config/repos/fixtures-python-passing.yaml`            | pyproject layout            |
| `python-pyproject-fail`  | Python   | `config/repos/fixtures-python-failing.yaml`            | pyproject failures          |
| `python-setup-pass`      | Python   | `config/repos/fixtures-python-setup-passing.yaml`      | setup.py layout             |
| `python-setup-fail`      | Python   | `config/repos/fixtures-python-setup-failing.yaml`      | setup.py failures           |
| `python-src-layout-pass` | Python   | `config/repos/fixtures-python-src-layout-passing.yaml` | src/ layout                 |
| `monorepo-pass/java`     | Java     | `config/repos/fixtures-monorepo-java-passing.yaml`     | Mixed repo, Java subdir     |
| `monorepo-fail/java`     | Java     | `config/repos/fixtures-monorepo-java-failing.yaml`     | Mixed repo, Java failures   |
| `monorepo-pass/python`   | Python   | `config/repos/fixtures-monorepo-python-passing.yaml`   | Mixed repo, Python subdir   |
| `monorepo-fail/python`   | Python   | `config/repos/fixtures-monorepo-python-failing.yaml`   | Mixed repo, Python failures |

## Expectations

- All fixture configs use boolean tool toggles with explicit `enabled` values.
- Core fixtures use default tool sets (fast, runs on every PR).
- Pass fixtures should produce green runs under default thresholds.
- Fail fixtures should produce deterministic failures (tests, lint, or security findings).

## Heavy Tool Fixtures (Optional)

Heavy tools (Trivy, CodeQL) are **off by default** for speed. For nightly/release validation:

| Fixture Config               | Purpose                 | When to Run          |
|------------------------------|-------------------------|----------------------|
| `fixtures-java-heavy.yaml`   | Java + Trivy + CodeQL   | Nightly, pre-release |
| `fixtures-python-heavy.yaml` | Python + Trivy + CodeQL | Nightly, pre-release |

> **Note:** These fixtures are NOT part of the default smoke test. Run them intentionally when you need to verify heavy tool pipelines.

To create these configs:
```yaml
# fixtures-java-heavy.yaml
java:
  tools:
    trivy:
      enabled: true
    codeql:
      enabled: true
```

## Naming Convention

- **Fixture subdirs** (e.g., `java-maven-pass`) are the canonical identifiers and must match exactly between the fixtures repo and the `repo.subdir` field in hub configs.
- **Config filenames** (e.g., `fixtures-java-passing.yaml`) are internal hub identifiers and do not need to match fixture subdir names.
- The `repo.subdir` field in each config is the source of truth for fixture mapping.

## Maintenance Rules

- Add new fixtures only when they represent a distinct layout or tool behavior.
- Keep fixture subdir names stable to avoid breaking configs and docs.
- Update this matrix whenever new fixture subdirs are added.
