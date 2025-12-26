"""Template sync command handler."""

from __future__ import annotations

import argparse
import subprocess
import sys

from cihub.cli import (
    delete_remote_file,
    fetch_remote_file,
    get_repo_entries,
    render_dispatch_workflow,
    resolve_executable,
    update_remote_file,
)


def cmd_sync_templates(args: argparse.Namespace) -> int:
    """Sync caller workflow templates to target repos."""
    entries = get_repo_entries(only_dispatch_enabled=not args.include_disabled)
    if args.repo:
        repo_map = {entry["full"]: entry for entry in entries}
        missing = [repo for repo in args.repo if repo not in repo_map]
        if missing:
            print(
                "Error: repos not found in config/repos/*.yaml: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        entries = [repo_map[repo] for repo in args.repo]

    if not entries:
        print("No repos found to sync.")
        return 0

    failures = 0
    for entry in entries:
        repo = entry["full"]
        language = entry.get("language", "")
        dispatch_workflow = entry.get("dispatch_workflow", "hub-ci.yml")
        branch = entry.get("default_branch", "main") or "main"
        path = f".github/workflows/{dispatch_workflow}"

        try:
            desired = render_dispatch_workflow(language, dispatch_workflow)
        except ValueError as exc:
            print(f"Error: {repo} {path}: {exc}", file=sys.stderr)
            failures += 1
            continue

        remote = fetch_remote_file(repo, path, branch)
        workflow_synced = False

        if remote and remote.get("content") == desired:
            print(f"[OK] {repo} {path} up to date")
            workflow_synced = True
        elif args.check:
            print(f"[FAIL] {repo} {path} out of date")
            failures += 1
        elif args.dry_run:
            print(f"# Would update {repo} {path}")
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
                print(f"[OK] {repo} {path} updated")
                workflow_synced = True
            except RuntimeError as exc:
                print(f"[FAIL] {repo} {path} update failed: {exc}", file=sys.stderr)
                failures += 1

        if dispatch_workflow == "hub-ci.yml":
            stale_workflow_names = ["hub-java-ci.yml", "hub-python-ci.yml"]
            for stale_name in stale_workflow_names:
                stale_path = f".github/workflows/{stale_name}"
                stale_file = fetch_remote_file(repo, stale_path, branch)
                if stale_file and stale_file.get("sha"):
                    if args.check:
                        print(f"[FAIL] {repo} {stale_path} stale (should be deleted)")
                        failures += 1
                    elif args.dry_run:
                        print(f"# Would delete {repo} {stale_path} (stale)")
                    elif workflow_synced:
                        try:
                            delete_remote_file(
                                repo,
                                stale_path,
                                branch,
                                stale_file["sha"],
                                "Remove stale workflow (migrated to hub-ci.yml)",
                            )
                            print(f"[OK] {repo} {stale_path} deleted (stale)")
                        except RuntimeError as exc:
                            print(
                                f"[WARN] {repo} {stale_path} delete failed: {exc}",
                                file=sys.stderr,
                            )

    if args.check and failures:
        print(f"Template drift detected in {failures} repo(s).", file=sys.stderr)
        return 1
    if failures:
        return 1

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
                print("[OK] v1 tag already at HEAD")
            else:
                # Security: Require confirmation for force-push operations
                if not getattr(args, "yes", False):
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
                print(
                    "[OK] v1 tag updated: "
                    f"{current_v1[:7] if current_v1 else 'none'} -> {head_sha[:7]}"
                )
        except subprocess.CalledProcessError as exc:
            print(f"[WARN] Failed to update v1 tag: {exc}", file=sys.stderr)
    elif args.dry_run and args.update_tag:
        print("# Would update v1 tag to HEAD")

    return 0
