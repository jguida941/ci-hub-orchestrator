"""Secrets command handlers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

from cihub.cli import (
    CommandResult,
    get_connected_repos,
    resolve_executable,
    safe_urlopen,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


def cmd_setup_secrets(args: argparse.Namespace) -> int | CommandResult:
    """Set HUB_DISPATCH_TOKEN on hub and optionally all connected repos."""
    import getpass

    hub_repo = args.hub_repo
    token = args.token
    json_mode = getattr(args, "json", False)

    if not token:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary="Token required; re-run with --token",
            )
        token = getpass.getpass("Enter GitHub PAT: ")

    token = token.strip()

    if not token:
        message = "Error: No token provided"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    if any(ch.isspace() for ch in token):
        message = "Error: Token contains whitespace; paste the raw token value."
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    def verify_token(pat: str) -> tuple[bool, str]:
        req = urllib.request.Request(  # noqa: S310
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                scopes = resp.headers.get("X-OAuth-Scopes", "")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return False, "unauthorized (token invalid or expired)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)

        login = data.get("login", "unknown")
        scope_msg = f"scopes: {scopes}" if scopes else "scopes: (not reported)"
        return True, f"user {login} ({scope_msg})"

    def verify_cross_repo_access(pat: str, target_repo: str) -> tuple[bool, str]:
        """Verify token can access another repo's artifacts."""
        req = urllib.request.Request(  # noqa: S310
            f"https://api.github.com/repos/{target_repo}/actions/artifacts",
            headers={
                "Authorization": f"token {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                count = data.get("total_count", 0)
                return True, f"{count} artifacts accessible"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False, f"repo not found or no access: {target_repo}"
            if exc.code == 401:
                return False, "token cannot access this repo (needs 'repo' scope)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)

    if args.verify:
        ok, message = verify_token(token)
        if not ok:
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(f"Token verification failed: {message}", file=sys.stderr)
            return EXIT_FAILURE
        if not json_mode:
            print(f"Token verified: {message}")

        connected = get_connected_repos()
        if connected:
            test_repo = connected[0]
            ok, message = verify_cross_repo_access(token, test_repo)
            if not ok:
                if json_mode:
                    return CommandResult(exit_code=EXIT_FAILURE, summary=message)
                print(
                    f"Cross-repo access failed for {test_repo}: {message}",
                    file=sys.stderr,
                )
                print(
                    "The token needs 'repo' scope to access other repos' artifacts.",
                    file=sys.stderr,
                )
                return EXIT_FAILURE
            if not json_mode:
                print(f"Cross-repo access verified: {test_repo} ({message})")

    gh_bin = resolve_executable("gh")

    def set_secret(repo: str) -> tuple[bool, str]:
        result = subprocess.run(  # noqa: S603
            [gh_bin, "secret", "set", "HUB_DISPATCH_TOKEN", "-R", repo],
            input=token,
            capture_output=True,
            text=True,
        )  # noqa: S603
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""

    if not json_mode:
        print(f"Setting HUB_DISPATCH_TOKEN on {hub_repo}...")
    ok, error = set_secret(hub_repo)
    if not ok:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE, summary=error or "Failed to set secret"
            )
        print(f"Failed: {error}", file=sys.stderr)
        return EXIT_FAILURE
    if not json_mode:
        print(f"  [OK] {hub_repo}")

    repo_results: list[dict[str, str]] = []
    failures = 0
    if args.all:
        if not json_mode:
            print("\nSetting on connected repos...")
        repos = get_connected_repos()
        for repo in repos:
            if repo == hub_repo:
                continue
            ok, error = set_secret(repo)
            if ok:
                if not json_mode:
                    print(f"  [OK] {repo}")
                repo_results.append({"repo": repo, "status": "updated"})
            else:
                suffix = " (no admin access)"
                if error:
                    suffix = f" ({error})"
                if not json_mode:
                    print(f"  [FAIL] {repo}{suffix}")
                repo_results.append(
                    {"repo": repo, "status": "failed", "message": error or ""}
                )
                failures += 1

    if json_mode:
        summary = (
            "Secrets updated" if failures == 0 else "Secrets updated with failures"
        )
        data: dict[str, object] = {"hub_repo": hub_repo}
        if repo_results:
            data["repos"] = repo_results
        return CommandResult(
            exit_code=EXIT_FAILURE if failures else EXIT_SUCCESS,
            summary=summary,
            data=data,
        )

    print("\nConnected dispatch-enabled repos:")
    for repo in get_connected_repos():
        print(f"  - {repo}")
    print(
        "\nEnsure PAT has 'repo' scope (classic) or Actions R/W (fine-grained) "
        "on all repos."
    )
    return EXIT_SUCCESS


def cmd_setup_nvd(args: argparse.Namespace) -> int | CommandResult:
    """Set NVD_API_KEY on Java repos for OWASP Dependency Check."""
    import getpass

    nvd_key = args.nvd_key
    json_mode = getattr(args, "json", False)

    if not nvd_key:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary="NVD API key required; re-run with --nvd-key",
            )
        print("NVD API Key is required for fast OWASP Dependency Check scans.")
        print("Get a free key at: https://nvd.nist.gov/developers/request-an-api-key")
        print()
        nvd_key = getpass.getpass("Enter NVD API Key: ")

    nvd_key = nvd_key.strip()

    if not nvd_key:
        message = "Error: No NVD API key provided"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    if any(ch.isspace() for ch in nvd_key):
        message = "Error: Key contains whitespace; paste the raw key value."
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    def verify_nvd_key(key: str) -> tuple[bool, str]:
        """Verify NVD API key by making a test request."""
        test_url = (
            "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228"
        )
        req = urllib.request.Request(  # noqa: S310
            test_url,
            headers={
                "apiKey": key,
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return True, "NVD API key is valid"
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "invalid or expired API key"
            if exc.code == 404:
                return True, "API key accepted (test CVE not found)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)
        return True, "API key accepted"

    if args.verify:
        if not json_mode:
            print("Verifying NVD API key...")
        ok, message = verify_nvd_key(nvd_key)
        if not ok:
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(f"NVD API key verification failed: {message}", file=sys.stderr)
            return EXIT_FAILURE
        if not json_mode:
            print(f"NVD API key verified: {message}")

    gh_bin = resolve_executable("gh")

    def set_secret(repo: str, secret_name: str, secret_value: str) -> tuple[bool, str]:
        result = subprocess.run(  # noqa: S603
            [gh_bin, "secret", "set", secret_name, "-R", repo],
            input=secret_value,
            capture_output=True,
            text=True,
        )  # noqa: S603
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""

    java_repos = get_connected_repos(
        only_dispatch_enabled=False,
        language_filter="java",
    )

    if not java_repos:
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="No Java repos found",
                data={"repos": []},
            )
        print("No Java repos found in config/repos/*.yaml")
        print("NVD_API_KEY is only needed for Java repos (OWASP Dependency Check).")
        return EXIT_SUCCESS

    if not json_mode:
        print(f"\nSetting NVD_API_KEY on {len(java_repos)} Java repo(s)...")
    success_count = 0
    repo_results: list[dict[str, str]] = []
    for repo in java_repos:
        ok, error = set_secret(repo, "NVD_API_KEY", nvd_key)
        if ok:
            if not json_mode:
                print(f"  [OK] {repo}")
            success_count += 1
            repo_results.append({"repo": repo, "status": "updated"})
        else:
            suffix = " (no admin access)" if not error else f" ({error})"
            if not json_mode:
                print(f"  [FAIL] {repo}{suffix}")
            repo_results.append(
                {"repo": repo, "status": "failed", "message": error or ""}
            )

    if json_mode:
        failures = len(java_repos) - success_count
        summary = (
            "NVD key set on all repos" if failures == 0 else "NVD key set with failures"
        )
        return CommandResult(
            exit_code=EXIT_FAILURE if failures else EXIT_SUCCESS,
            summary=summary,
            data={"repos": repo_results},
        )
    print(f"\nSet NVD_API_KEY on {success_count}/{len(java_repos)} Java repos.")
    if success_count < len(java_repos):
        print("For repos you don't have admin access to, set the secret manually:")
        print("  gh secret set NVD_API_KEY -R owner/repo")
    return EXIT_SUCCESS
