#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml

PROJECTS_PATH = Path(__file__).resolve().parent.parent / "config" / "projects.yaml"


def main() -> int:
    try:
        text = PROJECTS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {PROJECTS_PATH} not found", file=sys.stderr)
        return 1
    try:
        projects = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML: {exc}", file=sys.stderr)
        return 1
    print(projects)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
