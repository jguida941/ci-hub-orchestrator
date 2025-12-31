#!/usr/bin/env python3
"""
Apply a profile onto a repo config.

Usage:
  python scripts/apply_profile.py templates/profiles/python-fast.yaml \
    config/repos/my-repo.yaml

Profile values are merged first; existing config overrides profile defaults so
you keep repo-specific tweaks.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping at top level")
    return data


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge overlay onto base recursively (overlay wins), returning a new dict.
    Deterministic order: preserve base key order, then append overlay-only keys
    in overlay order. Lists are replaced (not merged).
    """
    result: Dict[str, Any] = {}

    # Base keys (preserve order)
    for key in base:
        if key in overlay:
            b, o = base[key], overlay[key]
            if isinstance(b, dict) and isinstance(o, dict):
                result[key] = deep_merge(b, o)
            else:
                result[key] = overlay[key]
        else:
            result[key] = base[key]

    # Overlay-only keys (append in overlay order)
    for key in overlay:
        if key not in base:
            result[key] = overlay[key]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a CI/CD Hub profile to a repo config.")
    parser.add_argument("profile", type=Path, help="Path to profile YAML (source)")
    parser.add_argument(
        "target",
        type=Path,
        help="Path to repo config YAML to create/update",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output path (defaults to target path)",
    )
    args = parser.parse_args()

    profile_data = load_yaml(args.profile)
    target_data = load_yaml(args.target)

    # Profile provides defaults; existing config keeps overrides
    merged = deep_merge(profile_data, target_data)

    output_path = args.output or args.target
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            merged,
            handle,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
    tmp_path.replace(output_path)

    print(f"Profile applied: {args.profile} -> {output_path}")


if __name__ == "__main__":
    main()
