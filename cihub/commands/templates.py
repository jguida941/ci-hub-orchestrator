"""Template sync command handler."""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from cihub.cli import (
    CommandResult,
    delete_remote_file,
    fetch_remote_file,
    get_repo_entries,
    render_dispatch_workflow,
    resolve_executable,
    update_remote_file,
)


def cmd_sync_templates(args: argparse.Namespace) -> int | CommandResult:
    """Sync caller workflow templates to target repos."""
    json_mode = getattr(args, "json", False)
    results: list[dict[str, Any]] = []
    entries = get_repo_entries(only_dispatch_enabled=not args.include_disabled)
    if args.repo:
        repo_map = {entry["full"]: entry for entry in entries}
        missing = [repo for repo in args.repo if repo not in repo_map]
        if missing:
            message = "Error: repos not found in config/repos/*.yaml: " + ", ".join(
                missing
            )
            if json_mode:
                return CommandResult(exit_code=2, summary=message)
            print(message, file=sys.stderr)
            return 2
        entries = [repo_map[repo] for repo in args.repo]

    if not entries:
        if json_mode:
            return CommandResult(exit_code=0, summary="No repos found to sync.")
        print("No repos found to sync.")
        return 0

    failures = 0
    for entry in entries:
        repo = entry["full"]
        language = entry.get("language", "")
        dispatch_workflow = entry.get("dispatch_workflow", "hub-ci.yml")
        branch = entry.get("default_branch", "main") or "main"
        path = f".github/workflows/{dispatch_workflow}"
        repo_result: dict[str, Any] = {
            "repo": repo,
            "path": path,
            "status": "unknown",
            "stale": [],
        }

        try:
            desired = render_dispatch_workflow(language, dispatch_workflow)
        except ValueError as exc:
            if not json_mode:
                print(f"Error: {repo} {path}: {exc}", file=sys.stderr)
            repo_result["status"] = "error"
            repo_result["message"] = str(exc)
            failures += 1
            results.append(repo_result)
            continue

        remote = fetch_remote_file(repo, path, branch)
        workflow_synced = False

        if remote and remote.get("content") == desired:
            if not json_mode:
                print(f"[OK] {repo} {path} up to date")
            workflow_synced = True
            repo_result["status"] = "up_to_date"
        elif args.check:
            if not json_mode:
                print(f"[FAIL] {repo} {path} out of date")
            failures += 1
            repo_result["status"] = "out_of_date"
        elif args.dry_run:
            if not json_mode:
                print(f"# Would update {repo} {path}")
            repo_result["status"] = "would_update"
        else:
            try:
                update_remote_file(
                    repo,
                    path,
                    branch,
                    desired,
                    args.commit_message,
                    remote.get("sha") if remote else None,
                )
                if not json_mode:
                    print(f"[OK] {repo} {path} updated")
                workflow_synced = True
                repo_result["status"] = "updated"
            except RuntimeError as exc:
                if not json_mode:
                    print(
                        f"[FAIL] {repo} {path} update failed: {exc}",
                        file=sys.stderr,
                    )
                failures += 1
                repo_result["status"] = "failed"
                repo_result["message"] = str(exc)

        if dispatch_workflow == "hub-ci.yml":
            stale_workflow_names = ["hub-java-ci.yml", "hub-python-ci.yml"]
            for stale_name in stale_workflow_names:
                stale_path = f".github/workflows/{stale_name}"
                stale_file = fetch_remote_file(repo, stale_path, branch)
                if stale_file and stale_file.get("sha"):
                    if args.check:
                        if not json_mode:
                            print(
                                f"[FAIL] {repo} {stale_path} stale (should be deleted)"
                            )
                        failures += 1
                        repo_result["stale"].append(
                            {"path": stale_path, "status": "stale"}
                        )
                    elif args.dry_run:
                        if not json_mode:
                            print(f"# Would delete {repo} {stale_path} (stale)")
                        repo_result["stale"].append(
                            {"path": stale_path, "status": "would_delete"}
                        )
                    elif workflow_synced:
                        try:
                            delete_remote_file(
                                repo,
                                stale_path,
                                branch,
                                stale_file["sha"],
                                "Remove stale workflow (migrated to hub-ci.yml)",
                            )
                            if not json_mode:
                                print(f"[OK] {repo} {stale_path} deleted (stale)")
                            repo_result["stale"].append(
                                {"path": stale_path, "status": "deleted"}
                            )
                        except RuntimeError as exc:
                            if not json_mode:
                                print(
                                    f"[WARN] {repo} {stale_path} delete failed: {exc}",
                                    file=sys.stderr,
                                )
                            repo_result["stale"].append(
                                {
                                    "path": stale_path,
                                    "status": "delete_failed",
                                    "message": str(exc),
                                }
                            )
        results.append(repo_result)

    exit_code = 0
    if args.check and failures:
        if not json_mode:
            print(f"Template drift detected in {failures} repo(s).", file=sys.stderr)
        exit_code = 1
    elif failures:
        exit_code = 1

    tag_status = None
    if args.update_tag and not args.check and not args.dry_run:
        try:
            git_bin = resolve_executable("git")
            result = subprocess.run(  # noqa: S603
                [git_bin, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            head_sha = result.stdout.strip()

            result = subprocess.run(  # noqa: S603
                [git_bin, "rev-parse", "v1"],
                capture_output=True,
                text=True,
            )
            current_v1 = result.stdout.strip() if result.returncode == 0 else None

            if current_v1 == head_sha:
                if not json_mode:
                    print("[OK] v1 tag already at HEAD")
                tag_status = "up_to_date"
            else:
                # Security: Require confirmation for force-push operations
                if not getattr(args, "yes", False):
                    if json_mode:
                        return CommandResult(
                            exit_code=2,
                            summary="Confirmation required; re-run with --yes",
                        )
                    print(
                        f"Warning: This will force-push v1 tag from "
                        f"{current_v1[:7] if current_v1 else 'none'} to {head_sha[:7]}"
                    )
                    print(
                        "This affects all repositories referencing "
                        "jguida941/hub-release/.github/workflows/*@v1"
                    )
                    confirm = input("Continue? [y/N] ").strip().lower()
                    if confirm not in ("y", "yes"):
                        if json_mode:
                            return CommandResult(exit_code=0, summary="Aborted")
                        print("Aborted.")
                        return 0

                subprocess.run(  # noqa: S603
                    [git_bin, "tag", "-f", "v1", "HEAD"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(  # noqa: S603
                    [git_bin, "push", "origin", "v1", "--force"],
                    check=True,
                    capture_output=True,
                )
                if not json_mode:
                    print(
                        "[OK] v1 tag updated: "
                        f"{current_v1[:7] if current_v1 else 'none'} -> {head_sha[:7]}"
                    )
                tag_status = "updated"
        except subprocess.CalledProcessError as exc:
            if not json_mode:
                print(f"[WARN] Failed to update v1 tag: {exc}", file=sys.stderr)
            tag_status = "failed"
    elif args.dry_run and args.update_tag:
        if not json_mode:
            print("# Would update v1 tag to HEAD")
        tag_status = "would_update"

    if json_mode:
        summary = "Template sync complete" if exit_code == 0 else "Template sync failed"
        data: dict[str, object] = {"repos": results, "failures": failures}
        if tag_status:
            data["tag"] = tag_status
        return CommandResult(exit_code=exit_code, summary=summary, data=data)
    return exit_code
