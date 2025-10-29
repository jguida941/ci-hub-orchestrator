#!/usr/bin/env python3
"""Resolve an OCI image digest from GitHub Container Registry using the GitHub API."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional


API_ROOT = "https://api.github.com"
USER_AGENT = "resolve-container-digest/1.0"


class ResolutionError(RuntimeError):
    """Raised when the digest cannot be resolved."""


def _ensure_https(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ResolutionError(f"Insecure URL scheme for GitHub API request: '{url}'.")
    if parsed.netloc.lower() != "api.github.com":
        raise ResolutionError(f"Unexpected host for GitHub API request: '{url}'.")


def _open_request(request: urllib.request.Request, *, timeout: int = 20):
    _ensure_https(request.full_url)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler())
    return opener.open(request, timeout=timeout)


@dataclass
class Subject:
    registry: str
    owner: str
    package: str

    @classmethod
    def parse(cls, subject: str) -> "Subject":
        if not subject:
            raise ResolutionError("Subject is empty.")
        normalized = subject.strip()
        if not normalized.startswith("ghcr.io/"):
            raise ResolutionError(
                f"Subject must start with 'ghcr.io/': received '{subject}'."
            )
        remainder = normalized.split("/", 1)[1]
        parts = remainder.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ResolutionError(
                f"Subject should be ghcr.io/<owner>/<image>: received '{subject}'."
            )
        owner = parts[0]
        package = parts[1]
        return cls(registry="ghcr.io", owner=owner, package=package)


def _build_request(path: str, token: Optional[str], *, params: Optional[dict] = None) -> urllib.request.Request:
    url = urllib.parse.urljoin(API_ROOT, path)
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    _ensure_https(url)
    request = urllib.request.Request(url)  # noqa: S310 - URL validated by _ensure_https
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", USER_AGENT)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    return request


def _load_json(path: str, token: Optional[str], *, params: Optional[dict] = None, allow_404: bool = False):
    request = _build_request(path, token, params=params)
    try:
        with contextlib.closing(_open_request(request, timeout=20)) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover - network error branch
        if allow_404 and exc.code == 404:
            return None
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:  # pragma: no cover - very rare
            detail = ""
        raise ResolutionError(
            f"GitHub API request to '{path}' failed with status {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network error branch
        raise ResolutionError(f"Failed to reach GitHub API for '{path}': {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResolutionError(f"Invalid JSON response from '{path}': {exc}") from exc


def _detect_owner_kind(owner: str, token: Optional[str]) -> str:
    for endpoint, label in ((f"/orgs/{owner}", "orgs"), (f"/users/{owner}", "users")):
        data = _load_json(endpoint, token, allow_404=True)
        if data is not None:
            return label
    raise ResolutionError(
        f"Unable to determine if '{owner}' is a user or organization in GitHub API."
    )


_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


def _candidate_digests(version: dict) -> Iterable[str]:
    name = version.get("name")
    if isinstance(name, str) and _DIGEST_PATTERN.match(name):
        yield name

    metadata = version.get("metadata", {})
    container_meta = metadata.get("container")
    if isinstance(container_meta, dict):
        digest = container_meta.get("digest")
        if isinstance(digest, str) and _DIGEST_PATTERN.match(digest):
            yield digest
        images = container_meta.get("images")
        if isinstance(images, list):
            for image in images:
                if not isinstance(image, dict):
                    continue
                digest_val = image.get("digest")
                if isinstance(digest_val, str) and _DIGEST_PATTERN.match(digest_val):
                    yield digest_val


def resolve_digest(subject: Subject, tag: str, token: Optional[str]) -> str:
    owner_kind = _detect_owner_kind(subject.owner, token)
    package_name = urllib.parse.quote(subject.package, safe="")
    page = 1
    while True:
        versions = _load_json(
            f"/{owner_kind}/{subject.owner}/packages/container/{package_name}/versions",
            token,
            params={"per_page": 100, "page": page},
        )
        if not versions:
            break
        if not isinstance(versions, list):
            raise ResolutionError("Unexpected response format when listing package versions.")
        for version in versions:
            if not isinstance(version, dict):
                continue
            metadata = version.get("metadata", {})
            container_meta = metadata.get("container", {})
            tags = container_meta.get("tags") or []
            if not isinstance(tags, list):
                tags = []
            if tag not in tags:
                continue
            for candidate in _candidate_digests(version):
                return candidate
            raise ResolutionError(
                f"Found tag '{tag}' for subject '{subject.registry}/{subject.owner}/{subject.package}' "
                "but no digest field was present in the API response."
            )
        page += 1
    raise ResolutionError(
        f"Tag '{tag}' not found for subject '{subject.registry}/{subject.owner}/{subject.package}'."
    )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, help="Image subject, e.g. ghcr.io/org/image")
    parser.add_argument("--tag", default="latest", help="Tag to resolve (default: latest)")
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("TOKEN"),
        help="GitHub API token with read:packages (default: env GITHUB_TOKEN/GH_TOKEN/TOKEN)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    try:
        subject = Subject.parse(args.subject)
        digest = resolve_digest(subject, args.tag, args.token)
    except ResolutionError as exc:
        print(f"[resolve_container_digest] {exc}", file=sys.stderr)
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
