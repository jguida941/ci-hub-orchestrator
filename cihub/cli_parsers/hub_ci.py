"""Parser setup for hub-ci commands."""

from __future__ import annotations

from cihub.cli_parsers.types import CommandHandlers


def add_hub_ci_commands(subparsers, _add_json_flag, handlers: CommandHandlers) -> None:
    del _add_json_flag
    hub_ci = subparsers.add_parser("hub-ci", help="Hub production CI helpers")
    hub_ci.set_defaults(func=handlers.cmd_hub_ci)
    hub_ci_sub = hub_ci.add_subparsers(dest="subcommand", required=True)

    hub_ci_actionlint_install = hub_ci_sub.add_parser(
        "actionlint-install",
        help="Download the actionlint binary",
    )
    hub_ci_actionlint_install.add_argument(
        "--version",
        default="latest",
        help="Actionlint version (default: latest)",
    )
    hub_ci_actionlint_install.add_argument("--checksum", help="SHA256 checksum for tarball")
    hub_ci_actionlint_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for actionlint",
    )
    hub_ci_actionlint_install.add_argument("--output", help="Write outputs to file")
    hub_ci_actionlint_install.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_actionlint = hub_ci_sub.add_parser(
        "actionlint",
        help="Run actionlint (optionally with reviewdog)",
    )
    hub_ci_actionlint.add_argument(
        "--workflow",
        default=".github/workflows/hub-production-ci.yml",
        help="Workflow file to lint",
    )
    hub_ci_actionlint.add_argument("--bin", help="Path to actionlint binary")
    hub_ci_actionlint.add_argument(
        "--reviewdog",
        action="store_true",
        help="Pipe output to reviewdog",
    )

    hub_ci_syntax = hub_ci_sub.add_parser(
        "syntax-check",
        help="Compile Python files to catch syntax errors",
    )
    hub_ci_syntax.add_argument("--root", default=".", help="Root directory")
    hub_ci_syntax.add_argument(
        "--paths",
        nargs="+",
        default=["scripts", "cihub"],
        help="Paths to check (files or directories)",
    )

    hub_ci_repo_check = hub_ci_sub.add_parser(
        "repo-check",
        help="Check if a repo checkout is present",
    )
    hub_ci_repo_check.add_argument("--path", default="repo", help="Repo path")
    hub_ci_repo_check.add_argument("--owner", help="Repo owner (for warnings)")
    hub_ci_repo_check.add_argument("--name", help="Repo name (for warnings)")
    hub_ci_repo_check.add_argument("--output", help="Write outputs to file")
    hub_ci_repo_check.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_source_check = hub_ci_sub.add_parser(
        "source-check",
        help="Detect source files for a repo",
    )
    hub_ci_source_check.add_argument("--path", default="repo", help="Repo path")
    hub_ci_source_check.add_argument("--language", required=True, help="Repo language")
    hub_ci_source_check.add_argument("--output", help="Write outputs to file")
    hub_ci_source_check.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_security_pip_audit = hub_ci_sub.add_parser(
        "security-pip-audit",
        help="Run pip-audit for hub-security workflows",
    )
    hub_ci_security_pip_audit.add_argument("--path", default="repo", help="Repo path")
    hub_ci_security_pip_audit.add_argument(
        "--report",
        default="pip-audit-report.json",
        help="Output report path (relative to repo)",
    )
    hub_ci_security_pip_audit.add_argument(
        "--requirements",
        nargs="*",
        default=["requirements.txt"],
        help="Requirements files to install",
    )
    hub_ci_security_pip_audit.add_argument("--output", help="Write outputs to file")
    hub_ci_security_pip_audit.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_security_bandit = hub_ci_sub.add_parser(
        "security-bandit",
        help="Run bandit for hub-security workflows",
    )
    hub_ci_security_bandit.add_argument("--path", default="repo", help="Repo path")
    hub_ci_security_bandit.add_argument(
        "--report",
        default="bandit-report.json",
        help="Output report path (relative to repo)",
    )
    hub_ci_security_bandit.add_argument("--output", help="Write outputs to file")
    hub_ci_security_bandit.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_security_ruff = hub_ci_sub.add_parser(
        "security-ruff",
        help="Run Ruff security rules for hub-security workflows",
    )
    hub_ci_security_ruff.add_argument("--path", default="repo", help="Repo path")
    hub_ci_security_ruff.add_argument(
        "--report",
        default="ruff-security.json",
        help="Output report path (relative to repo)",
    )
    hub_ci_security_ruff.add_argument("--output", help="Write outputs to file")
    hub_ci_security_ruff.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_security_owasp = hub_ci_sub.add_parser(
        "security-owasp",
        help="Run OWASP Dependency-Check for hub-security workflows",
    )
    hub_ci_security_owasp.add_argument("--path", default="repo", help="Repo path")
    hub_ci_security_owasp.add_argument("--output", help="Write outputs to file")
    hub_ci_security_owasp.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_docker_check = hub_ci_sub.add_parser(
        "docker-compose-check",
        help="Check for docker-compose files in a repo",
    )
    hub_ci_docker_check.add_argument("--path", default="repo", help="Repo path")
    hub_ci_docker_check.add_argument("--output", help="Write outputs to file")
    hub_ci_docker_check.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_codeql_build = hub_ci_sub.add_parser(
        "codeql-build",
        help="Run Java build for CodeQL analysis",
    )
    hub_ci_codeql_build.add_argument("--path", default="repo", help="Repo path")

    hub_ci_kyverno_install = hub_ci_sub.add_parser(
        "kyverno-install",
        help="Download the kyverno CLI",
    )
    hub_ci_kyverno_install.add_argument(
        "--version",
        default="v1.16.1",
        help="Kyverno CLI version (default: v1.16.1)",
    )
    hub_ci_kyverno_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for kyverno",
    )
    hub_ci_kyverno_install.add_argument("--output", help="Write outputs to file")
    hub_ci_kyverno_install.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_trivy_install = hub_ci_sub.add_parser(
        "trivy-install",
        help="Download the trivy CLI",
    )
    hub_ci_trivy_install.add_argument(
        "--version",
        default="0.55.0",
        help="Trivy CLI version (default: 0.55.0)",
    )
    hub_ci_trivy_install.add_argument(
        "--dest",
        default=".cihub/tools",
        help="Destination directory for trivy",
    )
    hub_ci_trivy_install.add_argument(
        "--github-path",
        action="store_true",
        help="Append destination dir to GITHUB_PATH",
    )
    hub_ci_trivy_install.add_argument("--output", help="Write outputs to file")
    hub_ci_trivy_install.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_trivy_summary = hub_ci_sub.add_parser(
        "trivy-summary",
        help="Parse Trivy JSON output and generate summary with counts",
    )
    hub_ci_trivy_summary.add_argument(
        "--fs-json",
        help="Path to trivy filesystem scan JSON (vulnerabilities)",
    )
    hub_ci_trivy_summary.add_argument(
        "--config-json",
        help="Path to trivy config scan JSON (misconfigurations)",
    )
    hub_ci_trivy_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    hub_ci_trivy_summary.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_kyverno_validate = hub_ci_sub.add_parser(
        "kyverno-validate",
        help="Validate kyverno policy syntax",
    )
    hub_ci_kyverno_validate.add_argument(
        "--policies-dir",
        default="policies/kyverno",
        help="Policies directory",
    )
    hub_ci_kyverno_validate.add_argument(
        "--templates-dir",
        help="Templates directory",
    )
    hub_ci_kyverno_validate.add_argument("--bin", help="Path to kyverno binary")
    hub_ci_kyverno_validate.add_argument("--output", help="Write outputs to file")
    hub_ci_kyverno_validate.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_kyverno_test = hub_ci_sub.add_parser(
        "kyverno-test",
        help="Test kyverno policies against fixtures",
    )
    hub_ci_kyverno_test.add_argument(
        "--policies-dir",
        default="policies/kyverno",
        help="Policies directory",
    )
    hub_ci_kyverno_test.add_argument(
        "--fixtures-dir",
        default="fixtures/kyverno",
        help="Fixtures directory",
    )
    hub_ci_kyverno_test.add_argument("--bin", help="Path to kyverno binary")
    hub_ci_kyverno_test.add_argument(
        "--fail-on-warn",
        default="false",
        help="Warn if policy tests produce warnings (true/false)",
    )

    hub_ci_smoke_java_build = hub_ci_sub.add_parser(
        "smoke-java-build",
        help="Run Java smoke build/test",
    )
    hub_ci_smoke_java_build.add_argument("--path", default="repo", help="Repo path")

    hub_ci_smoke_java_tests = hub_ci_sub.add_parser(
        "smoke-java-tests",
        help="Extract Java smoke test results",
    )
    hub_ci_smoke_java_tests.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_java_tests.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_java_tests.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_java_coverage = hub_ci_sub.add_parser(
        "smoke-java-coverage",
        help="Extract Java smoke coverage metrics",
    )
    hub_ci_smoke_java_coverage.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_java_coverage.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_java_coverage.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_java_checkstyle = hub_ci_sub.add_parser(
        "smoke-java-checkstyle",
        help="Run Checkstyle and extract violations",
    )
    hub_ci_smoke_java_checkstyle.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_java_checkstyle.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_java_checkstyle.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_java_spotbugs = hub_ci_sub.add_parser(
        "smoke-java-spotbugs",
        help="Run SpotBugs and extract issues",
    )
    hub_ci_smoke_java_spotbugs.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_java_spotbugs.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_java_spotbugs.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_python_install = hub_ci_sub.add_parser(
        "smoke-python-install",
        help="Install dependencies for Python smoke tests",
    )
    hub_ci_smoke_python_install.add_argument("--path", default="repo", help="Repo path")

    hub_ci_smoke_python_tests = hub_ci_sub.add_parser(
        "smoke-python-tests",
        help="Run Python smoke tests and extract metrics",
    )
    hub_ci_smoke_python_tests.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_python_tests.add_argument(
        "--output-file",
        default="test-output.txt",
        help="Output file for pytest logs",
    )
    hub_ci_smoke_python_tests.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_python_tests.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_python_ruff = hub_ci_sub.add_parser(
        "smoke-python-ruff",
        help="Run Ruff for Python smoke tests",
    )
    hub_ci_smoke_python_ruff.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_python_ruff.add_argument(
        "--report",
        default="ruff-report.json",
        help="Output report path (relative to repo)",
    )
    hub_ci_smoke_python_ruff.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_python_ruff.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_smoke_python_black = hub_ci_sub.add_parser(
        "smoke-python-black",
        help="Run Black for Python smoke tests",
    )
    hub_ci_smoke_python_black.add_argument("--path", default="repo", help="Repo path")
    hub_ci_smoke_python_black.add_argument(
        "--output-file",
        default="black-output.txt",
        help="Output file for Black logs",
    )
    hub_ci_smoke_python_black.add_argument("--output", help="Write outputs to file")
    hub_ci_smoke_python_black.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_release_parse = hub_ci_sub.add_parser(
        "release-parse-tag",
        help="Parse tag ref into version outputs",
    )
    hub_ci_release_parse.add_argument("--ref", help="Tag ref (defaults to GITHUB_REF)")
    hub_ci_release_parse.add_argument("--output", help="Write outputs to file")
    hub_ci_release_parse.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )

    hub_ci_release_update = hub_ci_sub.add_parser(
        "release-update-tag",
        help="Update floating major tag",
    )
    hub_ci_release_update.add_argument("--repo", default=".", help="Repo path")
    hub_ci_release_update.add_argument("--major", required=True, help="Major tag name (e.g., v1)")
    hub_ci_release_update.add_argument("--version", required=True, help="Release version")
    hub_ci_release_update.add_argument("--remote", default="origin", help="Git remote name")

    hub_ci_ruff = hub_ci_sub.add_parser("ruff", help="Run ruff and emit issue count")
    hub_ci_ruff.add_argument("--path", default=".", help="Path to lint")
    hub_ci_ruff.add_argument("--force-exclude", action="store_true", help="Force ruff exclude rules")
    hub_ci_ruff.add_argument("--output", help="Write outputs to file")
    hub_ci_ruff.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")

    hub_ci_black = hub_ci_sub.add_parser("black", help="Run black and emit issue count")
    hub_ci_black.add_argument("--path", default=".", help="Path to check")
    hub_ci_black.add_argument("--output", help="Write outputs to file")
    hub_ci_black.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")

    hub_ci_mutmut = hub_ci_sub.add_parser("mutmut", help="Run mutmut and emit summary outputs")
    hub_ci_mutmut.add_argument("--workdir", default=".", help="Workdir to scan")
    hub_ci_mutmut.add_argument("--output-dir", default=".", help="Directory for mutmut logs")
    hub_ci_mutmut.add_argument("--min-score", type=int, default=70, help="Minimum mutation score")
    hub_ci_mutmut.add_argument("--output", help="Write outputs to file")
    hub_ci_mutmut.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")
    hub_ci_mutmut.add_argument("--summary", help="Write summary to file")
    hub_ci_mutmut.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_bandit = hub_ci_sub.add_parser("bandit", help="Run bandit and enforce severity gates")
    hub_ci_bandit.add_argument(
        "--paths",
        nargs="+",
        default=["cihub", "scripts"],
        help="Paths to scan",
    )
    hub_ci_bandit.add_argument("--output", default="bandit.json", help="Bandit JSON output path")
    hub_ci_bandit.add_argument("--severity", default="medium", help="Bandit severity level")
    hub_ci_bandit.add_argument("--confidence", default="medium", help="Bandit confidence level")
    hub_ci_bandit.add_argument(
        "--fail-on-high",
        action="store_true",
        default=True,
        help="Fail if HIGH severity issues found (default: true)",
    )
    hub_ci_bandit.add_argument(
        "--no-fail-on-high",
        dest="fail_on_high",
        action="store_false",
        help="Do not fail on HIGH severity issues",
    )
    hub_ci_bandit.add_argument(
        "--fail-on-medium",
        action="store_true",
        default=False,
        help="Fail if MEDIUM severity issues found (default: false)",
    )
    hub_ci_bandit.add_argument(
        "--fail-on-low",
        action="store_true",
        default=False,
        help="Fail if LOW severity issues found (default: false)",
    )
    hub_ci_bandit.add_argument("--summary", help="Write summary to file")
    hub_ci_bandit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_pip_audit = hub_ci_sub.add_parser("pip-audit", help="Run pip-audit and enforce vulnerability gate")
    hub_ci_pip_audit.add_argument(
        "--requirements",
        nargs="+",
        default=["requirements/requirements.txt", "requirements/requirements-dev.txt"],
        help="Requirements files",
    )
    hub_ci_pip_audit.add_argument("--output", default="pip-audit.json", help="pip-audit JSON output path")
    hub_ci_pip_audit.add_argument("--summary", help="Write summary to file")
    hub_ci_pip_audit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_zizmor_run = hub_ci_sub.add_parser("zizmor-run", help="Run zizmor and produce SARIF (with fallback)")
    hub_ci_zizmor_run.add_argument("--output", "-o", default="zizmor.sarif", help="Path to write SARIF output")
    hub_ci_zizmor_run.add_argument("--workflows", default=".github/workflows/", help="Path to workflows directory")

    hub_ci_zizmor = hub_ci_sub.add_parser("zizmor-check", help="Check zizmor SARIF for high findings")
    hub_ci_zizmor.add_argument("--sarif", default="zizmor.sarif", help="Path to SARIF file")
    hub_ci_zizmor.add_argument("--summary", help="Write summary to file")
    hub_ci_zizmor.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_validate_configs = hub_ci_sub.add_parser("validate-configs", help="Validate hub repo config files")
    hub_ci_validate_configs.add_argument("--configs-dir", help="Directory containing config repos")
    hub_ci_validate_configs.add_argument(
        "--repo",
        help="Validate a single repo config by name (e.g., fixtures-python-passing)",
    )

    hub_ci_validate_profiles = hub_ci_sub.add_parser("validate-profiles", help="Validate profile YAML files")
    hub_ci_validate_profiles.add_argument("--profiles-dir", help="Directory containing profiles")

    hub_ci_license = hub_ci_sub.add_parser("license-check", help="Run license checks for dependencies")
    hub_ci_license.add_argument("--summary", help="Write summary to file")
    hub_ci_license.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_gitleaks = hub_ci_sub.add_parser("gitleaks-summary", help="Summarize gitleaks results")
    hub_ci_gitleaks.add_argument("--outcome", help="Gitleaks outcome")
    hub_ci_gitleaks.add_argument("--summary", help="Write summary to file")
    hub_ci_gitleaks.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_badges = hub_ci_sub.add_parser("badges", help="Generate or validate CI badges")
    hub_ci_badges.add_argument(
        "--check",
        action="store_true",
        help="Validate badges match current metrics",
    )
    hub_ci_badges.add_argument(
        "--config",
        help="Config file to read reports.badges.enabled from (defaults to config/defaults.yaml)",
    )
    hub_ci_badges.add_argument("--output-dir", help="Output directory for badges")
    hub_ci_badges.add_argument(
        "--artifacts-dir",
        help="Directory containing bandit/pip-audit/zizmor artifacts",
    )
    hub_ci_badges.add_argument("--ruff-issues", type=int, help="Ruff issue count")
    hub_ci_badges.add_argument("--mutation-score", type=float, help="Mutation score")
    hub_ci_badges.add_argument("--mypy-errors", type=int, help="Mypy error count")
    hub_ci_badges.add_argument("--black-issues", type=int, help="Black issue count")
    hub_ci_badges.add_argument(
        "--black-status",
        choices=["clean", "failed", "n/a"],
        help="Black formatter status",
    )
    hub_ci_badges.add_argument("--zizmor-sarif", help="Path to zizmor SARIF file")

    hub_ci_sub.add_parser("badges-commit", help="Commit and push badge updates")

    hub_ci_pytest_summary = hub_ci_sub.add_parser(
        "pytest-summary",
        help="Generate pytest test results summary",
    )
    hub_ci_pytest_summary.add_argument(
        "--junit-xml",
        default="test-results.xml",
        help="Path to pytest JUnit XML file",
    )
    hub_ci_pytest_summary.add_argument(
        "--coverage-xml",
        default="coverage.xml",
        help="Path to coverage XML file",
    )
    hub_ci_pytest_summary.add_argument(
        "--coverage-min",
        type=int,
        default=70,
        help="Minimum coverage percentage (default: 70)",
    )
    hub_ci_pytest_summary.add_argument("--summary", help="Write summary to file")
    hub_ci_pytest_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_summary = hub_ci_sub.add_parser("summary", help="Generate hub CI summary")
    hub_ci_summary.add_argument("--summary", help="Write summary to file")
    hub_ci_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_outputs = hub_ci_sub.add_parser("outputs", help="Emit hub CI toggle outputs")
    hub_ci_outputs.add_argument(
        "--config",
        help="Config file with hub_ci settings (defaults to config/defaults.yaml)",
    )
    hub_ci_outputs.add_argument("--output", help="Write outputs to file")
    hub_ci_outputs.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")

    _hub_ci_enforce = hub_ci_sub.add_parser("enforce", help="Fail if critical hub checks failed")  # noqa: F841

    _hub_ci_verify_matrix = hub_ci_sub.add_parser(  # noqa: F841
        "verify-matrix-keys",
        help="Verify hub-run-all.yml matrix keys match discover.py output",
    )

    hub_ci_quarantine = hub_ci_sub.add_parser(
        "quarantine-check",
        help="Fail if any file imports from _quarantine",
    )
    hub_ci_quarantine.add_argument(
        "--path",
        help="Root directory to scan (default: hub root)",
    )
