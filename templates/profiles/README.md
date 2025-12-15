# CI/CD Hub Profiles

Pre-configured tool combinations for common CI/CD scenarios.

## Available Profiles

| Profile | Language | Description | Expected Runtime |
|---------|----------|-------------|------------------|
| `java-minimal.yaml` | Java | Fastest sanity check (tests only) | ~3-6 min |
| `java-fast.yaml` | Java | Quick feedback for PRs | ~5-10 min |
| `java-quality.yaml` | Java | Thorough analysis for releases | ~15-30 min |
| `java-coverage-gate.yaml` | Java | High coverage/mutation bars | ~15-25 min |
| `java-compliance.yaml` | Java | Security/compliance focus | ~20-40 min |
| `java-security.yaml` | Java | Full security scanning | ~20-40 min |
| `python-minimal.yaml` | Python | Fastest sanity check (lint+tests) | ~2-5 min |
| `python-fast.yaml` | Python | Quick feedback for PRs | ~3-8 min |
| `python-quality.yaml` | Python | Thorough analysis for releases | ~15-30 min |
| `python-coverage-gate.yaml` | Python | High coverage/mutation bars | ~12-20 min |
| `python-compliance.yaml` | Python | Security/compliance focus | ~15-30 min |
| `python-security.yaml` | Python | Full security scanning | ~15-30 min |

## When to Use Each Profile

### Minimal Profile
- **Use for:** Docs-only PRs, tiny repos, fast sanity checks
- **Enables:** Bare-minimum tests/lint
- **Disables:** Coverage gates, mutation, SAST, dependency/container scanning

### Fast Profile
- **Use for:** PR checks, development iteration, quick feedback
- **Enables:** Core lint/test/coverage only
- **Disables:** Mutation testing, SAST, container scanning

### Quality Profile
- **Use for:** Pre-merge checks, release candidates, nightly builds
- **Enables:** All quality tools including mutation testing
- **Disables:** Heavy security scanning (use security profile)

### Coverage Gate Profile
- **Use for:** Release branches that must meet bars
- **Enables:** High coverage/mutation thresholds, lint
- **Disables:** Security tools (pair with security/compliance profiles)

### Compliance Profile
- **Use for:** Security/compliance gates where scan coverage matters most
- **Enables:** Dependency + SAST + container scanning with stricter thresholds
- **Disables:** Most quality-focused tools (coverage, mutation)

### Security Profile
- **Use for:** Security audits, compliance checks, release gates
- **Enables:** All security scanners (SAST, SCA, container)
- **Disables:** Quality-focused tools (coverage, formatting)

## How to Apply a Profile

### Option 0: Use the apply_profile helper

```bash
python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/my-repo.yaml
python scripts/validate_config.py config/repos/my-repo.yaml
```

### Option 1: Copy Profile to Repo Config

```bash
# Copy profile as your repo config
cp templates/profiles/python-fast.yaml config/repos/my-repo.yaml

# Edit to add repo details
cat >> config/repos/my-repo.yaml << 'EOF'
repo:
  owner: your-username
  name: my-repo
  language: python
EOF
```

### Option 2: Merge Profile with Existing Config

Copy the `tools:` section from a profile into your existing config.

### Option 3: Use Multiple Profiles per Branch

Configure different workflows for different branches:
- `main`: security profile (thorough checks)
- `develop`: quality profile (pre-merge)
- PRs: fast profile (quick feedback)

## Customizing Profiles

Feel free to modify these profiles for your needs:

```yaml
# Start with fast profile, add one expensive tool
python:
  tools:
    # ... fast profile defaults ...

    # Add mypy for type checking
    mypy:
      enabled: true
```

## Profile Tool Matrix

### Java Profiles

| Tool | Minimal | Fast | Quality | Coverage Gate | Compliance | Security |
|------|---------|------|---------|---------------|------------|----------|
| JaCoCo | N | Y | Y | Y (90%) | N | N |
| Checkstyle | N | Y | Y | Y | N | N |
| SpotBugs | N | Y | Y | Y | Y | Y |
| PMD | N | N | Y | Y | N | N |
| PITest | N | N | Y | Y (80%) | N | N |
| OWASP | N | N | Y | N | Y | Y |
| Semgrep | N | N | N | N | Y | Y |
| Trivy | N | N | N | N | Y | Y |
| CodeQL | N | N | N | N | Y | Y |

### Python Profiles

| Tool | Minimal | Fast | Quality | Coverage Gate | Compliance | Security |
|------|---------|------|---------|---------------|------------|----------|
| pytest | Y | Y | Y | Y (90%) | N | N |
| ruff | Y | Y | Y | Y | N | N |
| black | N | Y | Y | Y | N | N |
| isort | N | Y | Y | Y | N | N |
| bandit | N | Y | Y | N | Y | Y |
| pip-audit | N | Y | Y | N | Y | Y |
| mypy | N | N | Y | N | N | N |
| mutmut | N | N | Y | Y (80%) | N | N |
| Semgrep | N | N | N | N | Y | Y |
| Trivy | N | N | N | N | Y | Y |
| CodeQL | N | N | N | N | Y | Y |
