"""GitHub API utilities."""

from __future__ import annotations

import base64
import json
import subprocess
from typing import Any

from cihub.utils.exec_utils import resolve_executable


def gh_api_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call the GitHub API via the gh CLI.

    Args:
        path: API path (e.g., '/repos/owner/repo/contents/file').
        method: HTTP method (GET, POST, PUT, etc.).
        payload: Optional JSON payload for the request body.

    Returns:
        The parsed JSON response as a dict.

    Raises:
        RuntimeError: If the API call fails.
    """
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "api"]
    if method != "GET":
        cmd += ["-X", method]
    cmd.append(path)
    input_data = None
    if payload is not None:
        cmd += ["--input", "-"]
        input_data = json.dumps(payload)
    result = subprocess.run(  # noqa: S603
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
    )  # noqa: S603
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg or "gh api failed")
    if not result.stdout.strip():
        return {}
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("gh api returned non-object JSON")
    return data


def fetch_remote_file(repo: str, path: str, branch: str) -> dict[str, str] | None:
    """Fetch a file from a GitHub repository.

    Args:
        repo: Repository in 'owner/repo' format.
        path: Path to the file in the repository.
        branch: Branch or ref to fetch from.

    Returns:
        A dict with 'sha' and 'content' keys, or None if not found.
    """
    api_path = f"/repos/{repo}/contents/{path}?ref={branch}"
    try:
        data = gh_api_json(api_path)
    except RuntimeError as exc:
        msg = str(exc)
        if "Not Found" in msg or "404" in msg:
            return None
        raise
    if "content" not in data or "sha" not in data:
        return None
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"sha": data["sha"], "content": content}


def update_remote_file(
    repo: str,
    path: str,
    branch: str,
    content: str,
    message: str,
    sha: str | None = None,
) -> None:
    """Update a file in a GitHub repository.

    Args:
        repo: Repository in 'owner/repo' format.
        path: Path to the file in the repository.
        branch: Branch to update.
        content: New file content.
        message: Commit message.
        sha: SHA of the file being replaced (required for updates).
    """
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    gh_api_json(f"/repos/{repo}/contents/{path}", method="PUT", payload=payload)
