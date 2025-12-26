# Mutation Testing & Test Framework Guide

**Last Updated:** 2025-12-26

This guide covers mutation testing setup, test frameworks, and best practices for the cihub project.

---

## Current Coverage

| Metric | Value |
|--------|-------|
| **Overall Coverage** | 66% |
| **Tests** | 413 |
| **Target** | 70% |

### Coverage by Module

| Module | Coverage | Mutation Score | Status |
|--------|----------|----------------|--------|
| `config/merge.py` | 73% | **100%** | Excellent |
| `config/io.py` | 92% | 93% | Good |
| `commands/detect.py` | 100% | 85% | Good |
| `commands/secrets.py` | 87% | 0% (mock issue) | Needs work |
| `commands/validate.py` | 72% | Pending | Next target |
| `cli.py` | 80% | ~5% | Critical gap |
| `commands/new.py` | 0% | N/A | No tests |
| `wizard/*` | 0% | N/A | No tests |
| `diagnostics/*` | 0% | N/A | No tests |

### Detailed Mutation Results (2025-12-26)

Mutation testing reveals where bugs can hide undetected by measuring if tests catch code changes.

| Module | Lines | Mutants | Killed | Survived | No Tests | Score |
|--------|-------|---------|--------|----------|----------|-------|
| `commands/detect.py` | 20 | 20 | 17 | 3 | 0 | **85%** ✅ |
| `config/io.py` | 182 | 94 | 75 | 6 | 13 | **93%** ✅ |
| `config/merge.py` | 26 | 14 | 14 | 0 | 0 | **100%** ✅ |
| `commands/secrets.py` | 251 | N/A | 0 | 0 | ALL | **0%** ❌ |
| `cli.py` | 1199 | 2480 | ~17 | ~314+ | ~2000+ | **~5%** ❌ |

### Legend
- 🎉 **Killed**: Test failed when mutation applied (good!)
- 🫥 **Survived**: Test passed despite mutation (gap!)
- 🙁 **No Tests**: No tests cover this code at all
- ⏰ **Timeout**: Mutation caused infinite loop
- 🤔 **Suspicious**: Mutation caused unexpected behavior

### Critical Gaps Found

1. **`cli.py` (1199 lines)** - Main CLI module
   - Only ~5% mutation score
   - ~2000+ mutants with no test coverage
   - **Highest priority** for test improvement

2. **`commands/secrets.py` (251 lines)** - Security-critical module
   - Tests exist but mocks prevent mutation detection
   - Need integration-style tests

3. **`config/io.py`** - Gaps in specific functions
   - `load_profile_strict()` - 0 tests (6 mutations)
   - `save_yaml_file()` - 8 mutations untested

---

## Mutation Testing with mutmut 3.x

### Configuration (pyproject.toml)

```toml
[tool.mutmut]
paths_to_mutate = ["cihub/"]
tests_dir = ["tests/"]
also_copy = ["cihub/", "scripts/", "config/", "schema/", "templates/", ".github/", "pyproject.toml"]
mutate_only_covered_lines = true  # Only mutate lines with test coverage
```

### macOS Fix (Required)

mutmut 3.x fails on macOS with `RuntimeError: context has already been set`. Fix:

```bash
# Patch mutmut to use force=True
sed -i '' "s/set_start_method('fork')/set_start_method('fork', force=True)/" \
  .venv/lib/python3.12/site-packages/mutmut/__main__.py
```

### Running Targeted Tests

```bash
# Edit pyproject.toml to target specific module
# paths_to_mutate = ["cihub/config/merge.py"]

# Run mutation tests
mutmut run

# View results
mutmut results

# Show specific mutation
mutmut show cihub.config.merge.x_deep_merge__mutmut_5
```

### Interpreting Results

| Emoji | Meaning | Action |
|-------|---------|--------|
| 🎉 | Killed | Good - test caught the bug |
| 🫥 | Survived | Bad - add assertion to catch it |
| ⏰ | Timeout | Mutation caused infinite loop |
| 🤔 | Suspicious | Unexpected behavior |
| 🙁 | No tests | No tests cover this code |

### Target Scores

| Score | Rating | Action |
|-------|--------|--------|
| 80-100% | Excellent | Maintain |
| 60-79% | Good | Improve edge cases |
| 40-59% | Needs work | Add missing tests |
| <40% | Poor | Major test gaps |

---

## Test Framework Guide

### 1. CLI Integration Tests (pytest + capsys)

**What it does**: Tests CLI commands by capturing stdout/stderr output.

```python
def test_detect_command(tmp_path, capsys):
    # Setup: create a Python project
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'")

    # Execute: call the command handler
    args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
    result = cmd_detect(args)

    # Assert: check output and return code
    captured = capsys.readouterr()
    assert result == 0
    assert "python" in captured.out.lower()
```

**Best for**: `cli.py`, `commands/*.py`

**Best Practices**:
- Design `main()` to accept optional argv list for testability
- Use `capsys.readouterr()` after the command completes
- Test both stdout and stderr
- Always check return codes
- Use `tmp_path` fixture for file-based tests
- Mock external calls at the boundary

---

### 2. Property-Based Testing (Hypothesis)

**What it does**: Generates hundreds of random inputs to find edge cases.

```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.integers()))
def test_deep_merge_handles_any_dict(random_config):
    """deep_merge should handle ANY valid dict without crashing."""
    result = deep_merge({}, random_config)
    assert isinstance(result, dict)
    for key in random_config:
        assert key in result
```

**Common strategies**:
- `st.text()` - random strings
- `st.integers()` - random ints
- `st.dictionaries(key_strat, value_strat)` - random dicts
- `st.lists(element_strat)` - random lists

**Best for**: `config/merge.py`, pure functions, input validation

**Best Practices**:
- Use `assume()` to filter invalid examples
- Create modular strategies for reuse
- Use `@example()` to ensure specific edge cases
- Test inverse properties: `decode(encode(x)) == x`
- Use `@settings(max_examples=500)` for thorough CI testing

**Install**: `pip install hypothesis`

---

### 3. Snapshot Testing (Syrupy)

**What it does**: Saves expected output to files, fails if output changes.

```python
def test_workflow_generation(snapshot):
    config = {"repo": {"owner": "x", "name": "y"}, "language": "python"}
    workflow_yaml = generate_workflow_content(config)
    assert workflow_yaml == snapshot
```

**Best for**: `commands/update.py`, workflow generation, CLI help text

**Best Practices**:
- Review diffs carefully before updating
- Use `--snapshot-update` only when changes are intentional
- Commit snapshots alongside test code
- Keep snapshots small and focused

**Install**: `pip install syrupy`

---

### 4. Schema/Contract Testing (jsonschema)

**What it does**: Validates data structures against defined schemas.

```python
@pytest.mark.parametrize("config", VALID_CONFIGS)
def test_valid_config_passes_schema(config, schema):
    validate(config, schema)  # Should not raise

@pytest.mark.parametrize("config,reason", INVALID_CONFIGS)
def test_invalid_config_fails_schema(config, reason, schema):
    with pytest.raises(ValidationError):
        validate(config, schema)
```

**Best for**: Config validation, API responses, YAML structure tests

**Best Practices**:
- Use `additionalProperties: false` to catch unexpected fields
- Test both valid AND invalid configs
- Use `format` validators for emails, URIs, dates

---

### 5. Parameterized Tests

**What it does**: Runs same test with different inputs.

```python
@pytest.mark.parametrize("language,files,expected", [
    ("python", ["pyproject.toml"], True),
    ("java", ["pom.xml"], True),
    ("unknown", [], False),
])
def test_language_detection(tmp_path, language, files, expected):
    for f in files:
        (tmp_path / f).touch()
    detected, _ = resolve_language(tmp_path, None)
    assert (detected == language) == expected
```

**Best Practices**:
- Use descriptive IDs: `ids=["empty", "single", "many"]`
- Include edge cases: empty, None, negative, boundary
- Use `pytest.param(..., marks=pytest.mark.xfail)` for known failures

---

## YAML & GitHub Actions Testing

### 6. YAML Schema Validation (Yamale)

```python
import yamale

def test_config_validates():
    schema = yamale.make_schema('schema.yaml')
    data = yamale.make_data('config/repos/my-repo.yaml')
    yamale.validate(schema, data)
```

**Install**: `pip install yamale`

---

### 7. GitHub Actions Local Testing (act)

```bash
# Run all workflows
act

# Run specific job
act -j build

# Dry run
act -n
```

**Best Practices**:
- Create `.actrc` file for default flags
- Use `.secrets` file for tokens (add to .gitignore!)
- Start with medium image: `-P ubuntu-latest=catthehacker/ubuntu:act-22.04`

**Install**: `brew install act`

---

### 8. Workflow Linting (actionlint)

```bash
# Check all workflows
actionlint

# Output as JSON for CI
actionlint -format json
```

**Best Practices**:
- Run `actionlint -init-config` to generate config
- Use as pre-commit hook
- Integrates with shellcheck for `run:` scripts

**Install**: `brew install actionlint`

---

### 9. Workflow Security (zizmor)

```bash
# Scan with high sensitivity
zizmor --persona=pedantic .

# Output SARIF for GitHub Security
zizmor --format sarif . > results.sarif
```

**Best Practices**:
- Fix script injection by using environment variables
- Always pin actions to full SHA
- Use minimal `permissions:` in workflows

**Install**: `pip install zizmor`

---

### 10. Type-Safe YAML (StrictYAML)

**What it does**: Parses a restricted, safe subset of YAML with type enforcement.

**How it works**:
- Rejects dangerous YAML features (the "Norway problem", code execution)
- Enforces types via schema validators
- Preserves comments during round-trips

```python
from strictyaml import load, Map, Str, Int, Seq

schema = Map({
    "repo": Map({"owner": Str(), "name": Str()}),
    "tools": Seq(Str()),
    "coverage_min": Int(),
})

def test_config_type_safe():
    yaml_content = """
    repo:
      owner: myorg
      name: myrepo
    tools:
      - pytest
      - ruff
    coverage_min: 80
    """
    config = load(yaml_content, schema)
    assert config["coverage_min"] == 80  # Returns int, not string!
```

**Best for**: Config parsing where type safety matters, security-conscious YAML handling

**Best Practices**:
- Always define explicit schemas (never parse unvalidated YAML)
- Use `Optional()` for fields that may be missing
- Leverage comment preservation for round-trip editing
- Prefer StrictYAML over PyYAML for user-facing configs (prevents code injection)
- Use `revalidate()` after programmatic modifications

**Install**: `pip install strictyaml`

**Source**: [StrictYAML Docs](https://hitchdev.com/strictyaml/)

---

### 11. YAML/JSON Schema Validation (pyKwalify)

**What it does**: Validates YAML/JSON against Kwalify-style schemas.

**How it works**:
- Define schemas using type, pattern, required, enum constraints
- Validate from CLI or Python code
- Supports YAML 1.2 with ruamel.yaml

```python
from pykwalify.core import Core

def test_workflow_schema():
    c = Core(
        source_file=".github/workflows/ci.yml",
        schema_files=["schema/workflow-schema.yaml"]
    )
    c.validate(raise_exception=True)
```

**Best for**: Workflow validation, complex nested structures, Kwalify compatibility

**Best Practices**:
- Use `pykwalify[ruamel]` for YAML 1.2 support
- Define `pattern:` constraints for string formats (URLs, repo names)
- Use `enum:` for fixed value sets
- Combine with pytest fixtures to validate all configs in a directory
- Keep schemas versioned alongside config files

**Install**: `pip install pykwalify`

**Source**: [pyKwalify Docs](https://pykwalify.readthedocs.io/)

---

### 12. YAML-Driven Workflow Testing (pytest-workflow)

**What it does**: Test pipelines/workflows using YAML configuration files.

**How it works**:
- Define test cases in YAML
- Specify commands, expected outputs, exit codes
- Works with any workflow system (bash, Snakemake, Nextflow)

```yaml
# tests/test_workflows.yml
- name: Test hub-config command
  command: hub-config load config/repos/test.yaml
  exit_code: 0
  stdout:
    contains:
      - "language:"
      - "repo:"

- name: Test invalid config fails
  command: hub-config load nonexistent.yaml
  exit_code: 1
  stderr:
    contains:
      - "not found"
```

```python
# conftest.py
pytest_plugins = ["pytest_workflow"]
```

**Best for**: CLI command testing, pipeline testing, integration tests

**Best Practices**:
- Use unique workflow names (duplicates cause crashes)
- Use `--kwd` flag to keep working directory for debugging failures
- Use `tags:` to organize and selectively run tests (`pytest --tag smoke`)
- Use single quotes for `contains_regex:` patterns (avoids YAML escaping issues)
- Check both `stdout:` and `stderr:` for complete validation
- Use `files:` to verify expected outputs exist
- Combine with pytest fixtures for setup/teardown

**Install**: `pip install pytest-workflow`

**Source**: [pytest-workflow Docs](https://pytest-workflow.readthedocs.io/)

---

### 13. API Testing with YAML (Tavern)

**What it does**: Automated API testing with YAML-based test definitions.

**How it works**:
- Define API requests and expected responses in YAML
- Supports REST and MQTT
- Chain requests, use variables, validate JSON schemas

```yaml
# tests/test_github_api.tavern.yaml
test_name: Verify GitHub API response

stages:
  - name: Get user info
    request:
      url: https://api.github.com/users/octocat
      method: GET
    response:
      status_code: 200
      json:
        login: octocat
        type: User
```

**Best for**: GitHub API testing, webhook testing, external service mocking

**Best Practices**:
- Name files `test_*.tavern.yaml` for pytest auto-discovery
- Use `{tavern.env_vars.VAR}` for sensitive data (API keys, tokens)
- Chain requests using `save:` to capture values between stages
- Use YAML anchors (`&anchor` / `*anchor`) to reuse request templates
- Use `strict: false` for JSON bodies when you only care about specific fields
- Parametrize tests with `marks: - parametrize:` for data-driven testing
- Use `usefixtures:` to integrate with pytest fixtures
- Use `-k` flag to run specific tests by name

**Install**: `pip install tavern`

**Source**: [Tavern Testing](https://taverntesting.github.io/)

---

### YAML/GitHub Actions Tool Summary

| Tool | Purpose | Install |
|------|---------|---------|
| `yamale` | YAML schema validation | `pip install yamale` |
| `strictyaml` | Type-safe YAML parsing | `pip install strictyaml` |
| `pykwalify` | Kwalify-style validation | `pip install pykwalify` |
| `act` | Local Actions execution | `brew install act` |
| `actionlint` | Workflow linting | `brew install actionlint` |
| `zizmor` | Workflow security scanning | `pip install zizmor` |
| `pytest-workflow` | YAML-driven CLI tests | `pip install pytest-workflow` |
| `tavern` | YAML API testing | `pip install tavern` |

### Already Used in This Project

| Tool | Location | Purpose |
|------|----------|---------|
| `yamllint` | hub-production-ci.yml | YAML syntax linting |
| `actionlint` | hub-production-ci.yml | Workflow validation |
| `zizmor` | hub-production-ci.yml | Security scanning |
| `jsonschema` | config/schema.py | Config validation |

---

## Recommended Test Stack

| Package | Purpose | Install |
|---------|---------|---------|
| `pytest` | Test runner | Already have |
| `pytest-cov` | Coverage | Already have |
| `hypothesis` | Property-based | `pip install hypothesis` |
| `syrupy` | Snapshots | `pip install syrupy` |
| `yamale` | YAML schemas | `pip install yamale` |
| `pytest-xdist` | Parallel | `pip install pytest-xdist` |

---

## Boundary/Edge Case Tests (from Mutation Testing)

Specific tests for mutations that survived:

| Survived Mutation | Test Needed | Priority |
|-------------------|-------------|----------|
| `encoding="utf-8"` → `None` | Test non-ASCII file content | High |
| `indent=2` → `indent=None` | Assert on JSON structure, not formatting | Low (cosmetic) |
| `load_profile_strict` untested | Test `FileNotFoundError` path | High |
| `save_yaml_file` gaps | Test actual file content written | Medium |

### Example: UTF-8 Encoding Test

```python
def test_load_yaml_handles_utf8(tmp_path):
    """Ensure UTF-8 encoding is used for non-ASCII content."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("name: 日本語テスト\n", encoding="utf-8")

    result = load_yaml_file(yaml_file)
    assert result["name"] == "日本語テスト"
```

### Example: FileNotFoundError Test

```python
def test_load_profile_strict_raises_on_missing():
    """load_profile_strict should raise FileNotFoundError for missing profiles."""
    with pytest.raises(FileNotFoundError):
        load_profile_strict(paths, "nonexistent-profile")
```

---

## Security-Focused Tests (for secrets.py)

Since `secrets.py` has 0% mutation coverage due to mocking:

```python
class TestSecretsCommand:
    def test_secrets_not_logged(self, caplog):
        """Secrets should never appear in logs."""
        # Run command with a known secret value
        # Assert secret value NOT in caplog.text
        ...

    def test_secrets_masked_in_output(self, capsys):
        """Secrets should be masked (****) in CLI output."""
        # Run command
        captured = capsys.readouterr()
        assert "ghp_" not in captured.out
        assert "****" in captured.out or "REDACTED" in captured.out

    def test_secrets_file_permissions(self, tmp_path):
        """Secrets files should be created with 0600 permissions."""
        secrets_file = tmp_path / ".secrets"
        # Create secrets file
        assert (secrets_file.stat().st_mode & 0o777) == 0o600

    def test_token_validation_401(self, mocker):
        """401 response should indicate invalid token."""
        mock_response = mocker.Mock()
        mock_response.status_code = 401
        mocker.patch("urllib.request.urlopen", side_effect=HTTPError(..., 401, ...))
        # Assert appropriate error handling

    def test_token_validation_403(self, mocker):
        """403 response should indicate insufficient permissions."""
        # Test 403 forbidden handling

    def test_token_validation_rate_limited(self, mocker):
        """429 response should indicate rate limiting."""
        # Test rate limit handling
```

---

## Targeted Mutation Testing Plan

### Priority Order (by ROI)

| Tier | Module | Lines | Why | Test Approach |
|------|--------|-------|-----|---------------|
| **1** | `config/merge.py` | 104 | Pure functions, property-based ideal | Hypothesis |
| **1** | `commands/validate.py` | 48 | Small, clear validation logic | Parametrized |
| **2** | `config/io.py` gaps | 182 | Fill `load_profile_strict`, `save_yaml_file` | Unit tests |
| **2** | `config/paths.py` | 46 | Pure path utilities | Parametrized |
| **3** | `commands/templates.py` | 152 | Template syncing | Snapshot + mocks |
| **3** | `commands/init.py` | 106 | Project initialization | tmp_path fixtures |
| **4** | `cli.py` (by function) | 1197 | Break down systematically | Capsys + mocks |
| **4** | `commands/secrets.py` | 251 | Security-critical, needs integration | Capsys + mocks |

### Tier 1: Quick Wins (Pure Functions)

**`config/merge.py`** - Ideal for property-based testing:
```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.integers()))
def test_deep_merge_preserves_base_keys(base):
    """Merging with empty dict preserves all keys."""
    result = deep_merge(base, {})
    assert result.keys() == base.keys()

@given(st.dictionaries(st.text(), st.integers()),
       st.dictionaries(st.text(), st.integers()))
def test_deep_merge_overlay_wins(base, overlay):
    """Overlay values take precedence."""
    result = deep_merge(base, overlay)
    for key in overlay:
        if not isinstance(overlay[key], dict):
            assert result[key] == overlay[key]
```

**`commands/validate.py`** - Parametrized edge cases:
```python
@pytest.mark.parametrize("config,valid", [
    ({"language": "python"}, True),
    ({"language": "java"}, True),
    ({"language": "rust"}, False),  # unsupported
    ({}, False),  # missing required
])
def test_validate_config(config, valid):
    if valid:
        validate_config(config)
    else:
        with pytest.raises(ValidationError):
            validate_config(config)
```

### Tier 2: Fill Existing Gaps

**`config/io.py`** - Specific functions to test:
- `load_profile_strict()` - Never called in tests (6 mutants)
- `save_yaml_file()` - 8 mutants untested
- Add UTF-8 test data to catch encoding mutations

```python
def test_load_profile_strict_raises_on_missing(paths):
    """load_profile_strict should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_profile_strict(paths, "nonexistent-profile")

def test_save_yaml_file_creates_file(tmp_path):
    """save_yaml_file should create file with correct content."""
    output = tmp_path / "test.yaml"
    save_yaml_file(output, {"key": "value"})
    assert output.exists()
    assert "key: value" in output.read_text()
```

### Tier 3: Command Handlers

**`commands/templates.py`** - Use snapshot testing:
```python
def test_sync_template(snapshot, tmp_path):
    # Setup repo structure
    result = sync_template(tmp_path, "python")
    assert (tmp_path / ".ci-hub.yml").read_text() == snapshot
```

### Tier 4: Large Modules (Systematic)

**`cli.py`** - Break into testable chunks:
1. **POM parsing** - Already has 46 tests, good coverage
2. **Language detection** - `resolve_language()`, `detect_language()`
3. **Command dispatch** - `main()`, argument parsing
4. **Error handling** - Invalid inputs, missing files

**`commands/secrets.py`** - Integration-style:
- Current mocks prevent mutation detection
- Test actual token validation logic with fake responses
- Test error paths (401, 403, 404, 500)

### Running Targeted Mutation Tests

```bash
# Step 1: Edit pyproject.toml to target specific module
# [tool.mutmut]
# paths_to_mutate = ["cihub/config/merge.py"]

# Step 2: Run mutmut
mutmut run

# Step 3: Review results
mutmut results

# Step 4: Fix gaps, repeat
```

---

## Priority Test Targets (Summary)

| Tier | Module | Lines | Approach |
|------|--------|-------|----------|
| **1** | `config/merge.py` | 26 | **DONE** - 100% mutation |
| **1** | `commands/validate.py` | 36 | Parametrized tests |
| **2** | `config/io.py` gaps | 52 | Fill `load_profile_strict` |
| **3** | `commands/templates.py` | 93 | Snapshot + mocks |
| **4** | `cli.py` | 734 | Systematic breakdown |
| **4** | `commands/new.py` | 77 | Basic coverage first |

---

## References

- [mutmut docs](https://mutmut.readthedocs.io/)
- [Hypothesis docs](https://hypothesis.readthedocs.io/)
- [Syrupy GitHub](https://github.com/syrupy-project/syrupy)
- [actionlint GitHub](https://github.com/rhysd/actionlint)
- [zizmor.sh](https://zizmor.sh/)
- [act GitHub](https://github.com/nektos/act)
