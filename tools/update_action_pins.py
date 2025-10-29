#!/usr/bin/env python3
from __future__ import annotations

"""
Resolve floating action tags (for example `v4`) to their current commit SHAs and
rewrite pinned workflow references when a new digest becomes available.

This keeps workflows aligned with upstream security rotations while ensuring we
continue to pin to exact commits.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


GITHUB_API_ROOT = "https://api.github.com"


@dataclass(frozen=True)
class ActionSpec:
    slug: str  # e.g. actions/upload-artifact
    tag: str  # e.g. v4


TRACKED_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec(slug="actions/upload-artifact", tag="v4"),
)


def _ensure_github_api_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise SystemExit(f"Insecure URL scheme for GitHub API request: {url}")
    if parsed.netloc.lower() != "api.github.com":
        raise SystemExit(f"Unexpected host for GitHub API request: {url}")


def _open_https(request: urllib.request.Request, *, timeout: int = 30):
    _ensure_github_api_url(request.full_url)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler())
    return opener.open(request, timeout=timeout)


def github_api(path: str) -> dict[str, object]:
    url = f"{GITHUB_API_ROOT}{path}"
    _ensure_github_api_url(url)
    req = urllib.request.Request(url)  # noqa: S310 - URL validated by _ensure_github_api_url
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ci-cd-hub/action-pin-updater")
    try:
        with _open_https(req, timeout=30) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"GitHub API error {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GitHub API request failed for {url}: {exc}") from exc
    return json.loads(payload.decode("utf-8"))


def resolve_tag_commit(action: ActionSpec) -> str:
    ref = github_api(f"/repos/{action.slug}/git/ref/tags/{action.tag}")
    obj = ref.get("object", {})
    sha = obj.get("sha")
    obj_type = obj.get("type")
    if not isinstance(sha, str) or not isinstance(obj_type, str):
        raise SystemExit(f"Unexpected tag reference payload for {action.slug}@{action.tag}: {ref}")
    if obj_type == "commit":
        return sha
    if obj_type != "tag":
        raise SystemExit(f"Unsupported tag object type '{obj_type}' for {action.slug}@{action.tag}")
    tag_obj = github_api(f"/repos/{action.slug}/git/tags/{sha}")
    inner = tag_obj.get("object", {})
    commit_sha = inner.get("sha")
    inner_type = inner.get("type")
    if inner_type != "commit" or not isinstance(commit_sha, str):
        raise SystemExit(f"Unexpected nested tag payload for {action.slug}@{action.tag}: {tag_obj}")
    return commit_sha


def iter_workflow_files(workflows_dir: Path) -> Iterable[Path]:
    for path in sorted(workflows_dir.rglob("*.y*ml")):
        if path.is_file():
            yield path


def update_action_pin(workflows_dir: Path, spec: ActionSpec, new_sha: str, dry_run: bool) -> list[str]:
    import re

    pattern = re.compile(rf"({re.escape(spec.slug)}@)([0-9a-f]{{40}})")
    touched: list[str] = []

    for path in iter_workflow_files(workflows_dir):
        original = path.read_text(encoding="utf-8")
        changed = False
        previous_shas: set[str] = set()

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            current_sha = match.group(2)
            if current_sha == new_sha:
                return match.group(0)
            previous_shas.add(current_sha)
            changed = True
            return f"{match.group(1)}{new_sha}"

        updated, _count = pattern.subn(repl, original)
        if changed:
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
            touched.append(f"{path}: {', '.join(sorted(previous_shas))} -> {new_sha}")
    return touched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update pinned GitHub Actions references to the latest floating tag commits."
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="Directory containing workflow definitions (default: .github/workflows).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned updates without modifying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workflows_dir: Path = args.workflows_dir
    if not workflows_dir.is_dir():
        raise SystemExit(f"Workflows directory not found: {workflows_dir}")

    overall_changes: list[str] = []

    for spec in TRACKED_ACTIONS:
        latest_sha = resolve_tag_commit(spec)
        updates = update_action_pin(workflows_dir, spec, latest_sha, args.dry_run)
        if updates:
            overall_changes.extend(updates)
            print(f"[update-action-pins] {spec.slug}@{spec.tag} -> {latest_sha}")
            for entry in updates:
                print(f"  updated {entry}")
        else:
            print(f"[update-action-pins] {spec.slug}@{spec.tag} already pinned to {latest_sha}")

    if not overall_changes:
        print("[update-action-pins] No action references required updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
