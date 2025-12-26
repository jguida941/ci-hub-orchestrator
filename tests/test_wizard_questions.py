"""Tests for wizard/questions modules."""

from __future__ import annotations

# isort: skip_file

import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.wizard import WizardCancelled  # isort: skip # noqa: E402
from cihub.wizard.core import _check_cancelled  # noqa: E402
from cihub.wizard.questions.java_tools import (  # noqa: E402
    JAVA_TOOL_ORDER,
    configure_java_tools,
)
from cihub.wizard.questions.language import (  # noqa: E402
    select_build_tool,
    select_java_version,
    select_language,
    select_python_version,
)
from cihub.wizard.questions.python_tools import (  # noqa: E402
    PYTHON_TOOL_ORDER,
    configure_python_tools,
)
from cihub.wizard.questions.security import (  # noqa: E402
    _prompt_security_tools,
    configure_security_tools,
)
from cihub.wizard.questions.thresholds import configure_thresholds  # noqa: E402


# =============================================================================
# _check_cancelled Tests
# =============================================================================


class TestCheckCancelled:
    """Tests for _check_cancelled helper function."""

    def test_returns_value_when_not_none(self) -> None:
        """Returns value when value is not None."""
        result = _check_cancelled("test", "context")
        assert result == "test"

    def test_returns_integer_value(self) -> None:
        """Returns integer values correctly."""
        result = _check_cancelled(42, "context")
        assert result == 42

    def test_returns_bool_value(self) -> None:
        """Returns boolean values correctly."""
        result = _check_cancelled(True, "context")
        assert result is True
        result = _check_cancelled(False, "context")
        assert result is False

    def test_raises_wizard_cancelled_when_none(self) -> None:
        """Raises WizardCancelled when value is None."""
        with pytest.raises(WizardCancelled, match="Test context cancelled"):
            _check_cancelled(None, "Test context")


# =============================================================================
# Language Selection Tests
# =============================================================================


class TestSelectLanguage:
    """Tests for select_language function."""

    def test_returns_java(self) -> None:
        """Returns 'java' when user selects java."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = "java"
            result = select_language()
            assert result == "java"

    def test_returns_python(self) -> None:
        """Returns 'python' when user selects python."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = "python"
            result = select_language()
            assert result == "python"

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                select_language()


class TestSelectJavaVersion:
    """Tests for select_java_version function."""

    def test_returns_version(self) -> None:
        """Returns version string."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = "21"
            result = select_java_version()
            assert result == "21"

    def test_returns_custom_version(self) -> None:
        """Returns custom version string."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = "17"
            result = select_java_version(default="17")
            assert result == "17"

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                select_java_version()


class TestSelectPythonVersion:
    """Tests for select_python_version function."""

    def test_returns_version(self) -> None:
        """Returns version string."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = "3.12"
            result = select_python_version()
            assert result == "3.12"

    def test_returns_custom_version(self) -> None:
        """Returns custom version string."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = "3.11"
            result = select_python_version(default="3.11")
            assert result == "3.11"

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                select_python_version()


class TestSelectBuildTool:
    """Tests for select_build_tool function."""

    def test_returns_maven(self) -> None:
        """Returns 'maven' when user selects maven."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = "maven"
            result = select_build_tool()
            assert result == "maven"

    def test_returns_gradle(self) -> None:
        """Returns 'gradle' when user selects gradle."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = "gradle"
            result = select_build_tool()
            assert result == "gradle"

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.language.questionary.select"
        ) as mock_select:
            mock_select.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                select_build_tool()


# =============================================================================
# Thresholds Tests
# =============================================================================


class TestConfigureThresholds:
    """Tests for configure_thresholds function."""

    def test_returns_thresholds(self) -> None:
        """Returns threshold values."""
        with mock.patch(
            "cihub.wizard.questions.thresholds.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.side_effect = ["80", "75"]
            defaults = {"thresholds": {"coverage_min": 70, "mutation_score_min": 70}}
            result = configure_thresholds(defaults)
            assert result["coverage_min"] == 80
            assert result["mutation_score_min"] == 75

    def test_uses_defaults_when_no_thresholds(self) -> None:
        """Uses default values when no thresholds in config."""
        with mock.patch(
            "cihub.wizard.questions.thresholds.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.side_effect = ["70", "70"]
            result = configure_thresholds({})
            assert result["coverage_min"] == 70
            assert result["mutation_score_min"] == 70

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.thresholds.questionary.text"
        ) as mock_text:
            mock_text.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                configure_thresholds({})


# =============================================================================
# Java Tools Tests
# =============================================================================


class TestJavaToolOrder:
    """Tests for JAVA_TOOL_ORDER constant."""

    def test_contains_expected_tools(self) -> None:
        """Contains expected Java tools."""
        expected = ["jacoco", "checkstyle", "spotbugs", "pmd", "owasp", "pitest"]
        for tool in expected:
            assert tool in JAVA_TOOL_ORDER

    def test_jacoco_first(self) -> None:
        """jacoco is first in order."""
        assert JAVA_TOOL_ORDER[0] == "jacoco"


class TestConfigureJavaTools:
    """Tests for configure_java_tools function."""

    def test_enables_tools(self) -> None:
        """Enables tools when user confirms."""
        with mock.patch(
            "cihub.wizard.questions.java_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            defaults = {"java": {"tools": {"jacoco": {"enabled": False}}}}
            result = configure_java_tools(defaults)
            assert result["jacoco"]["enabled"] is True

    def test_disables_tools(self) -> None:
        """Disables tools when user declines."""
        with mock.patch(
            "cihub.wizard.questions.java_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            defaults = {"java": {"tools": {"jacoco": {"enabled": True}}}}
            result = configure_java_tools(defaults)
            assert result["jacoco"]["enabled"] is False

    def test_skips_tools_not_in_defaults(self) -> None:
        """Skips tools not present in defaults."""
        with mock.patch(
            "cihub.wizard.questions.java_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            defaults = {"java": {"tools": {"jacoco": {"enabled": False}}}}
            result = configure_java_tools(defaults)
            # Only jacoco should be present, not checkstyle
            assert "jacoco" in result
            assert "checkstyle" not in result

    def test_empty_defaults_returns_empty(self) -> None:
        """Returns empty dict when defaults are empty."""
        result = configure_java_tools({})
        assert result == {}

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.java_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = None
            defaults = {"java": {"tools": {"jacoco": {"enabled": False}}}}
            with pytest.raises(WizardCancelled):
                configure_java_tools(defaults)


# =============================================================================
# Python Tools Tests
# =============================================================================


class TestPythonToolOrder:
    """Tests for PYTHON_TOOL_ORDER constant."""

    def test_contains_expected_tools(self) -> None:
        """Contains expected Python tools."""
        expected = ["pytest", "ruff", "black", "isort", "mypy", "bandit", "mutmut"]
        for tool in expected:
            assert tool in PYTHON_TOOL_ORDER

    def test_pytest_first(self) -> None:
        """pytest is first in order."""
        assert PYTHON_TOOL_ORDER[0] == "pytest"


class TestConfigurePythonTools:
    """Tests for configure_python_tools function."""

    def test_enables_tools(self) -> None:
        """Enables tools when user confirms."""
        with mock.patch(
            "cihub.wizard.questions.python_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            defaults = {"python": {"tools": {"pytest": {"enabled": False}}}}
            result = configure_python_tools(defaults)
            assert result["pytest"]["enabled"] is True

    def test_disables_tools(self) -> None:
        """Disables tools when user declines."""
        with mock.patch(
            "cihub.wizard.questions.python_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            defaults = {"python": {"tools": {"pytest": {"enabled": True}}}}
            result = configure_python_tools(defaults)
            assert result["pytest"]["enabled"] is False

    def test_skips_tools_not_in_defaults(self) -> None:
        """Skips tools not present in defaults."""
        with mock.patch(
            "cihub.wizard.questions.python_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            defaults = {"python": {"tools": {"pytest": {"enabled": False}}}}
            result = configure_python_tools(defaults)
            # Only pytest should be present
            assert "pytest" in result
            assert "ruff" not in result

    def test_empty_defaults_returns_empty(self) -> None:
        """Returns empty dict when defaults are empty."""
        result = configure_python_tools({})
        assert result == {}

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.python_tools.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = None
            defaults = {"python": {"tools": {"pytest": {"enabled": False}}}}
            with pytest.raises(WizardCancelled):
                configure_python_tools(defaults)


# =============================================================================
# Security Tools Tests
# =============================================================================


class TestPromptSecurityTools:
    """Tests for _prompt_security_tools function."""

    def test_returns_enabled_tools(self) -> None:
        """Returns enabled security tools."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.side_effect = [True, True, True]
            result = _prompt_security_tools({})
            assert result["semgrep"]["enabled"] is True
            assert result["trivy"]["enabled"] is True
            assert result["codeql"]["enabled"] is True

    def test_returns_disabled_tools(self) -> None:
        """Returns disabled security tools."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.side_effect = [False, False, False]
            result = _prompt_security_tools({})
            assert result["semgrep"]["enabled"] is False
            assert result["trivy"]["enabled"] is False
            assert result["codeql"]["enabled"] is False

    def test_mixed_enabled_disabled(self) -> None:
        """Returns mixed enabled/disabled tools."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.side_effect = [True, False, True]
            result = _prompt_security_tools({})
            assert result["semgrep"]["enabled"] is True
            assert result["trivy"]["enabled"] is False
            assert result["codeql"]["enabled"] is True

    def test_raises_when_cancelled(self) -> None:
        """Raises WizardCancelled when user cancels."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.return_value = None
            with pytest.raises(WizardCancelled):
                _prompt_security_tools({})


class TestConfigureSecurityTools:
    """Tests for configure_security_tools function."""

    def test_java_security_tools(self) -> None:
        """Returns Java security tool overrides."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.side_effect = [True, True, False]
            defaults = {"java": {"tools": {}}}
            result = configure_security_tools("java", defaults)
            assert "java" in result
            assert result["java"]["tools"]["semgrep"]["enabled"] is True
            assert result["java"]["tools"]["trivy"]["enabled"] is True
            assert result["java"]["tools"]["codeql"]["enabled"] is False

    def test_python_security_tools(self) -> None:
        """Returns Python security tool overrides."""
        with mock.patch(
            "cihub.wizard.questions.security.questionary.confirm"
        ) as mock_confirm:
            mock_confirm.return_value.ask.side_effect = [True, False, True]
            defaults = {"python": {"tools": {}}}
            result = configure_security_tools("python", defaults)
            assert "python" in result
            assert result["python"]["tools"]["semgrep"]["enabled"] is True
            assert result["python"]["tools"]["trivy"]["enabled"] is False
            assert result["python"]["tools"]["codeql"]["enabled"] is True

    def test_unknown_language_returns_empty(self) -> None:
        """Returns empty dict for unknown language."""
        result = configure_security_tools("ruby", {})
        assert result == {}
