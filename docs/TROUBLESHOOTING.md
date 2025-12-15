# Troubleshooting

Common issues and their solutions, organized by category.

---

## Configuration Issues

### Schema validation fails

**Symptom:** `Config validation failed for config/repos/my-app.yaml`

**Cause:** Config file has invalid fields or values.

**Fix:**
1. Run locally: `python scripts/load_config.py config/repos/my-app.yaml`
2. Check error messages for specific field issues
3. Reference [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) for valid fields
4. Common issues:
   - `min_coverage: 150` → must be 0-100
   - `language: ruby` → must be `java` or `python`
   - Typo in field name

---

### Config not taking effect

**Symptom:** Changed config but workflow uses old values.

**Cause:** Config hierarchy or caching.

**Fix:**
1. Check precedence: `.ci-hub.yml` (repo) > `config/repos/*.yaml` (hub) > `defaults.yaml`
2. If repo has `.ci-hub.yml`, it overrides hub configs
3. Ensure file name matches: `config/repos/<repo-name>.yaml`
4. Re-run workflow after config changes

---

### Wrong language detected

**Symptom:** Java repo running Python tools (or vice versa).

**Cause:** `repo.language` not set correctly.

**Fix:**
```yaml
repo:
  name: my-app
  language: java  # or python
```

---

## Repository Access Issues

### Repo fails to checkout

**Symptom:** `fatal: could not read from remote repository`

**Cause:** Token lacks permissions.

**Fix:**
1. For public repos: Should work with default `GITHUB_TOKEN`
2. For private repos: Use PAT with `repo` scope
3. For org repos: Ensure token has org access
4. Check if repo exists and name is spelled correctly

---

### Default branch mismatch

**Symptom:** Workflow targets wrong branch, or dispatch fails.

**Cause:** `default_branch` not set or incorrect.

**Fix:**
```yaml
repo:
  name: my-app
  default_branch: main  # or master, develop, etc.
```

---

## Build Issues

### Java build fails - plugin not found

**Symptom:** `Plugin not found` or `Goal not found`

**Cause:** Tool requires Maven/Gradle plugin not in pom.xml/build.gradle.

**Fix:** Add required plugins:

```xml
<!-- pom.xml for JaCoCo -->
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.11</version>
</plugin>

<!-- pom.xml for PITest -->
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <version>1.15.0</version>
</plugin>
```

Or disable the tool:
```yaml
java:
  tools:
    jacoco:
      enabled: false
```

---

### Python build fails - module not found

**Symptom:** `ModuleNotFoundError` or `No module named X`

**Cause:** Dependencies not installed.

**Fix:**
1. Ensure `requirements.txt` or `pyproject.toml` exists
2. Check internet connectivity for pip
3. Hub installs from: `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`

---

### Gradle build fails

**Symptom:** `Could not find method` or task not found

**Cause:** Gradle version mismatch or missing wrapper.

**Fix:**
1. Include `gradlew` and `gradle/wrapper/` in repo
2. Ensure `build.gradle` is valid
3. Set `java.build_tool: gradle` in config

---

## Coverage Issues

### Coverage shows 0%

**Symptom:** JaCoCo/pytest reports 0% coverage.

**Cause:** Reports not generated or path mismatch.

**Fix for Java:**
1. Ensure JaCoCo plugin configured with `prepare-agent` and `report` goals
2. Check `target/site/jacoco/jacoco.xml` exists
3. Run `mvn verify` locally to confirm report generation

**Fix for Python:**
1. Ensure `pytest-cov` installed
2. Check `coverage.xml` exists after running
3. Confirm tests actually run (not skipped)

---

### Coverage threshold not enforced

**Symptom:** Build passes despite low coverage.

**Cause:** Threshold is a warning, not failure.

**Current behavior:** Hub warns but doesn't fail on coverage threshold.

**Workaround:** Add coverage enforcement to your build:
```xml
<!-- pom.xml JaCoCo enforcement -->
<execution>
  <id>check</id>
  <goals><goal>check</goal></goals>
  <configuration>
    <rules>
      <rule>
        <limits>
          <limit>
            <counter>LINE</counter>
            <minimum>0.70</minimum>
          </limit>
        </limits>
      </rule>
    </rules>
  </configuration>
</execution>
```

---

## Tool-Specific Issues

### OWASP Dependency-Check times out

**Symptom:** OWASP step hangs or times out after 10+ minutes.

**Cause:** NVD database download without API key.

**Fix:**
1. Get API key: https://nvd.nist.gov/developers/request-an-api-key
2. Add secret `NVD_API_KEY` to hub repo
3. OWASP will use API key for faster, more reliable updates

---

### PITest takes too long

**Symptom:** Mutation testing runs for 30+ minutes.

**Cause:** Large codebase or many tests.

**Fix:**
1. Use `skip_mutation: true` for PR checks
2. Run mutation testing only on nightly builds
3. Configure PITest to target specific packages:
   ```xml
   <targetClasses>
     <param>com.myapp.core.*</param>
   </targetClasses>
   ```

---

### SpotBugs finds too many issues

**Symptom:** Build fails with hundreds of SpotBugs warnings.

**Cause:** Threshold too low.

**Fix:**
```yaml
java:
  tools:
    spotbugs:
      threshold: high  # Only report HIGH priority bugs
      effort: min      # Less thorough analysis
```

---

### Ruff reports many errors

**Symptom:** Hundreds of Ruff lint errors.

**Cause:** Default rules catch many issues.

**Fix:** Add `ruff.toml` to repo:
```toml
[lint]
select = ["E", "F"]  # Only errors and pyflakes
ignore = ["E501"]    # Ignore line length

[lint.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert in tests
```

---

### mypy fails on third-party imports

**Symptom:** `Cannot find implementation or library stub for module`

**Cause:** Type stubs not installed.

**Fix:**
1. Add `--ignore-missing-imports` (hub does this by default)
2. Or install stubs: `pip install types-requests types-PyYAML`
3. Or disable mypy:
   ```yaml
   python:
     tools:
       mypy:
         enabled: false
   ```

---

### CodeQL initialization fails

**Symptom:** `CodeQL failed to initialize`

**Cause:** Language not supported or permissions issue.

**Fix:**
1. Ensure `security-events: write` permission in workflow
2. Check language is supported (java, python, javascript, etc.)
3. For private repos, ensure GitHub Advanced Security is enabled

---

### Bandit security warnings

**Symptom:** Bandit reports false positives.

**Cause:** Common patterns flagged incorrectly.

**Fix:** Add `.bandit` config file:
```ini
[bandit]
skips = B101,B601
exclude_dirs = tests,docs
```

---

### pip-audit finds vulnerabilities

**Symptom:** `pip-audit found N vulnerabilities`

**Cause:** Dependencies have known CVEs.

**Fix:**
1. Update vulnerable packages: `pip install --upgrade <package>`
2. Check if fix is available: https://pypi.org/project/<package>/
3. If no fix, evaluate if risk is acceptable for your use case

---

## Distributed Mode Issues

### Dispatch fails - workflow not found

**Symptom:** `Workflow does not exist` error.

**Cause:** Target repo missing workflow file.

**Fix:**
1. Add `java-ci.yml` or `python-ci.yml` to target repo's `.github/workflows/`
2. Ensure workflow has `workflow_dispatch` trigger
3. Check file name matches exactly

---

### Dispatch fails - permission denied

**Symptom:** `Resource not accessible by integration`

**Cause:** Token lacks `actions:write` permission.

**Fix:**
1. Use PAT with `repo` scope
2. Add as secret and reference in workflow
3. Ensure PAT has access to target repo's org

---

### Run ID not captured

**Symptom:** `could not determine run id yet` warning.

**Cause:** Timing issue - workflow started but not found in API.

**Impact:** Aggregation may miss this repo's results.

**Workaround:** This is best-effort. Run will still execute. Re-run orchestrator if needed.

---

### Aggregation shows incomplete data

**Symptom:** `hub-report.json` missing coverage/mutation for some repos.

**Cause:** Artifact not found or download failed.

**Fix:**
1. Check target workflow uploaded `ci-report` artifact
2. Verify artifact naming matches expected pattern
3. Check target workflow completed successfully

---

### Timeout waiting for dispatch

**Symptom:** Orchestrator times out after 30 minutes.

**Cause:** Target workflow took too long.

**Fix:**
1. Optimize target workflow (skip slow tools)
2. Increase timeout in hub-orchestrator.yml
3. Consider central mode instead

---

## Docker Issues

### Docker health check fails

**Symptom:** `Service is not healthy` after 30 attempts.

**Cause:** Health endpoint not responding.

**Fix:**
1. Verify health endpoint path:
   ```yaml
   java:
     tools:
       docker:
         health_endpoint: /health  # or /actuator/health
   ```
2. Increase timeout:
   ```yaml
   java:
     tools:
       docker:
         health_timeout: 600  # 10 minutes
   ```
3. Disable Docker if not needed:
   ```yaml
   java:
     tools:
       docker:
         enabled: false
   ```

---

### Docker build fails

**Symptom:** `Cannot connect to Docker daemon`

**Cause:** Docker not available on runner.

**Fix:** Hub uses GitHub-hosted runners which have Docker. If using self-hosted runners, ensure Docker is installed.

---

## Artifact Issues

### Artifacts not uploaded

**Symptom:** No artifacts in workflow summary.

**Cause:** Files not generated or path mismatch.

**Fix:**
1. Check tool actually ran (not skipped)
2. Verify output paths match what workflow expects
3. Check for `if-no-files-found: ignore` - this silently skips missing files

---

### Artifacts expired

**Symptom:** Can't download old artifacts.

**Cause:** Retention period exceeded.

**Fix:**
```yaml
reports:
  retention_days: 90  # Increase from default 30
```

---

## Getting More Help

1. **Check workflow logs:** Actions → Select run → Click job → Expand step
2. **Run locally:** Clone hub and run scripts locally to debug
3. **Check RESEARCH.md:** Deep dive on tool configuration
4. **File an issue:** Document steps to reproduce

---

## See Also

- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Config options
- [TOOLS.md](TOOLS.md) - Tool details
- [MODES.md](MODES.md) - Central vs Distributed
- [WORKFLOWS.md](WORKFLOWS.md) - Workflow documentation
