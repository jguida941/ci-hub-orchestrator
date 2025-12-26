"""Wizard runner orchestration."""

from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

import questionary  # type: ignore[import-untyped]
from rich.console import Console

from cihub.config.io import load_defaults, load_profile_strict
from cihub.config.merge import deep_merge
from cihub.config.paths import PathConfig
from cihub.wizard import WizardCancelled
from cihub.wizard.styles import get_style
from cihub.wizard.validators import validate_repo_name

T = TypeVar("T")


def _check_cancelled(value: T | None, ctx: str) -> T:
    if value is None:
        raise WizardCancelled(f"{ctx} cancelled")
    return value


class WizardRunner:
    """Interactive wizard orchestration for config creation/editing."""

    def __init__(self, console: Console, paths: PathConfig) -> None:
        self.console = console
        self.paths = paths

    def _load_base(self, profile: str | None) -> dict:
        defaults = load_defaults(self.paths)
        if profile:
            profile_cfg = load_profile_strict(self.paths, profile)
            return deep_merge(defaults, profile_cfg)
        return defaults

    def _prompt_repo(self, name: str | None, base: dict) -> dict:
        repo_defaults = base.get("repo", {})
        owner = _check_cancelled(
            questionary.text(
                "Repo owner (org/user):",
                default=repo_defaults.get("owner", ""),
                style=get_style(),
            ).ask(),
            "Repo owner",
        )
        repo_name = _check_cancelled(
            questionary.text(
                "Repo name:",
                default=name or repo_defaults.get("name", ""),
                validate=validate_repo_name,
                style=get_style(),
            ).ask(),
            "Repo name",
        )
        use_central_runner = _check_cancelled(
            questionary.confirm(
                "Use central runner?",
                default=bool(repo_defaults.get("use_central_runner", True)),
                style=get_style(),
            ).ask(),
            "Central runner prompt",
        )
        repo_side_execution = _check_cancelled(
            questionary.confirm(
                "Enable repo-side execution (writes workflows)?",
                default=bool(repo_defaults.get("repo_side_execution", False)),
                style=get_style(),
            ).ask(),
            "Repo-side execution prompt",
        )
        return {
            "owner": str(owner),
            "name": str(repo_name),
            "use_central_runner": bool(use_central_runner),
            "repo_side_execution": bool(repo_side_execution),
        }

    def _apply_language_prompts(self, config: dict) -> dict:
        from cihub.wizard.questions.java_tools import configure_java_tools
        from cihub.wizard.questions.language import (
            select_build_tool,
            select_java_version,
            select_language,
            select_python_version,
        )
        from cihub.wizard.questions.python_tools import configure_python_tools
        from cihub.wizard.questions.security import configure_security_tools
        from cihub.wizard.questions.thresholds import configure_thresholds

        defaults = config
        language = select_language(default=defaults.get("language", "java"))
        config["language"] = language

        if language == "java":
            java_cfg = deepcopy(defaults.get("java", {}))
            java_cfg["version"] = select_java_version(
                default=str(java_cfg.get("version", "21"))
            )
            java_cfg["build_tool"] = select_build_tool(
                default=str(java_cfg.get("build_tool", "maven"))
            )
            java_cfg["tools"] = configure_java_tools(defaults)
            config["java"] = java_cfg
        elif language == "python":
            py_cfg = deepcopy(defaults.get("python", {}))
            py_cfg["version"] = select_python_version(
                default=str(py_cfg.get("version", "3.12"))
            )
            py_cfg["tools"] = configure_python_tools(defaults)
            config["python"] = py_cfg

        security_overrides = configure_security_tools(language, defaults)
        config = deep_merge(config, security_overrides)
        config["thresholds"] = configure_thresholds(defaults)
        return config

    def run_new_wizard(self, name: str, profile: str | None = None) -> dict:
        base = self._load_base(profile)
        config = deepcopy(base)
        config["repo"] = self._prompt_repo(name, base)
        return self._apply_language_prompts(config)

    def run_init_wizard(self, detected: dict) -> dict:
        base = self._load_base(profile=None)
        config = deep_merge(base, detected)
        repo_name = detected.get("repo", {}).get("name", "")
        config["repo"] = self._prompt_repo(repo_name, config)
        return self._apply_language_prompts(config)

    def run_config_wizard(self, existing: dict) -> dict:
        config = deepcopy(existing)
        repo_name = existing.get("repo", {}).get("name", "")
        config["repo"] = self._prompt_repo(repo_name, existing)
        return self._apply_language_prompts(config)
