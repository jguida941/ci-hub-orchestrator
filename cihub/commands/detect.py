"""Detect command handler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult, resolve_language


def cmd_detect(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    try:
        language, reasons = resolve_language(repo_path, args.language)
    except ValueError as exc:
        if json_mode:
            return CommandResult(
                exit_code=1,
                summary=str(exc),
                problems=[
                    {
                        "severity": "error",
                        "message": str(exc),
                        "code": "CIHUB-DETECT-001",
                    }
                ],
            )
        raise
    payload: dict[str, Any] = {"language": language}
    if args.explain:
        payload["reasons"] = reasons
    if json_mode:
        return CommandResult(
            exit_code=0,
            summary=f"Detected language: {language}",
            data=payload,
        )
    print(json.dumps(payload, indent=2))
    return 0
