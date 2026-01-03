"""Shared types for CLI parser builders."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable

from cihub.types import CommandResult

CommandHandler = Callable[[argparse.Namespace], int | CommandResult]


@dataclass(frozen=True)
class CommandHandlers:
    cmd_detect: CommandHandler
    cmd_preflight: CommandHandler
    cmd_scaffold: CommandHandler
    cmd_smoke: CommandHandler
    cmd_smoke_validate: CommandHandler
    cmd_check: CommandHandler
    cmd_verify: CommandHandler
    cmd_ci: CommandHandler
    cmd_run: CommandHandler
    cmd_report: CommandHandler
    cmd_triage: CommandHandler
    cmd_docs: CommandHandler
    cmd_docs_links: CommandHandler
    cmd_adr: CommandHandler
    cmd_config_outputs: CommandHandler
    cmd_discover: CommandHandler
    cmd_dispatch: CommandHandler
    cmd_hub_ci: CommandHandler
    cmd_new: CommandHandler
    cmd_init: CommandHandler
    cmd_update: CommandHandler
    cmd_validate: CommandHandler
    cmd_setup_secrets: CommandHandler
    cmd_setup_nvd: CommandHandler
    cmd_fix_pom: CommandHandler
    cmd_fix_deps: CommandHandler
    cmd_sync_templates: CommandHandler
    cmd_config: CommandHandler
