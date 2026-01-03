"""Detect command handler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult, resolve_language
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def cmd_detect(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    try:
        language, reasons = resolve_language(repo_path, args.language)
    except ValueError as exc:
        error_result = CommandResult(
            exit_code=EXIT_FAILURE,
            summary=str(exc),
            problems=[
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-DETECT-001",
                }
            ],
        )
        if json_mode:
            return error_result
        # Print user-friendly error to stderr and return exit code
        import sys
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    payload: dict[str, Any] = {"language": language}
    if args.explain:
        payload["reasons"] = reasons
    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Detected language: {language}",
            data=payload,
        )
    print(json.dumps(payload, indent=2))
    return EXIT_SUCCESS
