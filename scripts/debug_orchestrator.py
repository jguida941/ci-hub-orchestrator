#!/usr/bin/env python3
"""
Debug script to check orchestrator artifact downloads and report parsing.

Usage:
  # Check specific repo's recent dispatch runs
  python scripts/debug_orchestrator.py --repo jguida941/ci-cd-hub-fixtures \
    --token YOUR_PAT

  # Check all recent hub orchestrator runs
  python scripts/debug_orchestrator.py --hub-runs --token YOUR_PAT

Requires: A GitHub PAT with 'repo' and 'actions' scopes.
"""

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlparse


def gh_get(url: str, token: str) -> dict:
    """Make authenticated GET request to GitHub API."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    req = request.Request(  # noqa: S310
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"URL: {url}")
        if e.code == 403:
            print("⚠️  Token may lack permissions. Need 'repo' and 'actions' scopes.")
        return {}


def download_artifact(archive_url: str, token: str, target_dir: Path) -> Path | None:
    """Download and extract artifact ZIP."""
    parsed = urlparse(archive_url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    req = request.Request(  # noqa: S310
        archive_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = resp.read()
        target_dir.mkdir(parents=True, exist_ok=True)
        zip_path = target_dir / "artifact.zip"
        zip_path.write_bytes(data)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        return target_dir
    except HTTPError as e:
        print(f"  ❌ Failed to download artifact: HTTP {e.code}")
        if e.code == 410:
            print("     Artifact expired (past retention period)")
        return None


def check_repo_runs(owner: str, repo: str, token: str, limit: int = 5):
    """Check recent workflow runs for a repo."""
    print(f"\n{'='*60}")
    print(f"Checking {owner}/{repo}")
    print(f"{'='*60}")

    # List recent workflow runs
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page={limit}"
    runs = gh_get(url, token)

    if not runs.get("workflow_runs"):
        print("No workflow runs found")
        return

    for run in runs["workflow_runs"][:limit]:
        run_id = run["id"]
        workflow = run["name"]
        status = run["status"]
        conclusion = run.get("conclusion", "N/A")
        created = run["created_at"]

        print(f"\n📋 Run #{run_id}: {workflow}")
        print(f"   Status: {status} | Conclusion: {conclusion}")
        print(f"   Created: {created}")

        if status != "completed":
            print("   ⏳ Run not completed, skipping artifact check")
            continue

        # Check artifacts
        artifacts_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        artifacts = gh_get(artifacts_url, token)

        if not artifacts.get("artifacts"):
            print("   ⚠️  No artifacts found")
            continue

        print(f"   📦 Artifacts: {len(artifacts['artifacts'])}")
        for art in artifacts["artifacts"]:
            print(
                f"      - {art['name']} ({art['size_in_bytes']} bytes, "
                f"expired: {art['expired']})"
            )

            # Look for ci-report
            if art["name"] == "ci-report":
                print("      🔍 Checking ci-report contents...")
                with tempfile.TemporaryDirectory() as tmpdir:
                    extracted = download_artifact(
                        art["archive_download_url"],
                        token,
                        Path(tmpdir),
                    )
                    if extracted:
                        # List extracted files
                        files = list(Path(tmpdir).rglob("*"))
                        print(f"         Files extracted: {len(files)}")
                        for f in files:
                            if f.is_file():
                                rel = f.relative_to(tmpdir)
                                print(f"         - {rel}")

                        # Check for report.json
                        report_file = next(Path(tmpdir).rglob("report.json"), None)
                        if report_file:
                            print("         ✅ Found report.json")
                            try:
                                report_data = json.loads(report_file.read_text())
                                results = report_data.get("results", {})
                                print("         📊 Results:")
                                coverage = results.get("coverage")
                                mutation = results.get("mutation_score")
                                build_status = results.get("build_status")
                                print(f"            Coverage: {coverage}")
                                print(f"            Mutation: {mutation}")
                                print(f"            Build: {build_status}")

                                tools = report_data.get("tools_ran", {})
                                print("         🔧 Tools ran:")
                                for tool, ran in tools.items():
                                    status_icon = "✅" if ran else "⏭️"
                                    print(f"            {status_icon} {tool}: {ran}")
                            except json.JSONDecodeError as e:
                                print(f"         ❌ Invalid JSON: {e}")
                                # Print first 500 chars of the file
                                content = report_file.read_text()[:500]
                                print(f"         Content preview:\n{content}")
                        else:
                            print("         ❌ No report.json found in artifact")


def check_hub_runs(token: str, limit: int = 3):
    """Check recent hub orchestrator runs."""
    print("\n" + "=" * 60)
    print("Hub Orchestrator Recent Runs")
    print("=" * 60)

    # Assuming hub repo is jguida941/ci-cd-hub or similar
    # You may need to adjust this
    hub_repos = [
        ("jguida941", "ci-cd-hub"),
    ]

    for owner, repo in hub_repos:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
        workflows = gh_get(url, token)

        if not workflows.get("workflows"):
            continue

        for wf in workflows["workflows"]:
            if "orchestrator" in wf["name"].lower():
                print(f"\nFound orchestrator workflow: {wf['name']} in {owner}/{repo}")
                check_repo_runs(owner, repo, token, limit)
                return

    print("Could not find orchestrator workflow")


def main():
    parser = argparse.ArgumentParser(
        description="Debug orchestrator artifact downloads"
    )
    parser.add_argument("--repo", help="Check specific repo (format: owner/repo)")
    parser.add_argument(
        "--hub-runs",
        action="store_true",
        help="Check hub orchestrator runs",
    )
    parser.add_argument("--token", help="GitHub PAT (or set GITHUB_TOKEN env var)")
    parser.add_argument("--limit", type=int, default=5, help="Number of runs to check")
    args = parser.parse_args()

    token = (
        args.token
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("HUB_DISPATCH_TOKEN")
    )
    if not token:
        print("Error: No token provided. Use --token or set GITHUB_TOKEN env var")
        sys.exit(1)

    if args.repo:
        parts = args.repo.split("/")
        if len(parts) != 2:
            print("Error: --repo must be in format owner/repo")
            sys.exit(1)
        check_repo_runs(parts[0], parts[1], token, args.limit)
    elif args.hub_runs:
        check_hub_runs(token, args.limit)
    else:
        # Default: check fixtures repo
        check_repo_runs("jguida941", "ci-cd-hub-fixtures", token, args.limit)


if __name__ == "__main__":
    main()
