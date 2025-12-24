#!/usr/bin/env python3
"""Generate issuer/subject policy input from cosign verification output."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.safe_subprocess import run_checked

ANSI_ESCAPE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
JSON_START_RE = re.compile(r"[\{\[]")
IDENTITY_RE = re.compile(
    r"(?:certificate\s+)?(?:identity|subject(?!\s+url))\b[:\s]+(.+)",
    re.IGNORECASE,
)
ISSUER_RE = re.compile(
    r"(?:certificate\s+)?(?:(?:oidc\s+)?issuer(?:\s+url)?|issuer\s+url)\b[:\s]+(.+)",
    re.IGNORECASE,
)


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def _parse_json_identity(raw: str) -> Tuple[str, str] | None:
    if not raw:
        return None

    decoder = json.JSONDecoder()
    entries: list[dict[str, object]] = []
    idx = 0
    length = len(raw)

    while idx < length:
        match = JSON_START_RE.search(raw, idx)
        if not match:
            break
        start = match.start()
        try:
            parsed, end = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
        elif isinstance(parsed, list):
            entries.extend(item for item in parsed if isinstance(item, dict))
        idx = start + end

    for entry in entries:
        identity = entry.get("critical", {}).get("identity", {})  # type: ignore[arg-type]
        issuer = identity.get("issuer") if isinstance(identity, dict) else None
        subject = identity.get("subject") if isinstance(identity, dict) else None
        if issuer and subject:
            return str(issuer), str(subject)
    return None


def _parse_identity(stdout: str) -> Tuple[str, str]:
    issuer: str | None = None
    subject: str | None = None
    for raw_line in stdout.splitlines():
        line = _strip_ansi(raw_line).strip()
        if not line:
            continue
        identity_match = IDENTITY_RE.search(line)
        if identity_match:
            subject = identity_match.group(1).strip()
            continue
        issuer_match = ISSUER_RE.search(line)
        if issuer_match:
            issuer = issuer_match.group(1).strip()
    if not issuer or not subject:
        raise ValueError("unable to parse issuer/subject from cosign output")
    return issuer, subject


def _run_cosign(
    image: str,
    expected_subject: str | None,
    expected_issuer: str | None,
    env: dict[str, str],
    request_json: bool,
):
    cmd = ["cosign", "verify", "--verbose", image]
    if request_json:
        cmd.extend(["--output", "json"])
    if expected_subject:
        cmd.extend(["--certificate-identity", expected_subject])
    else:
        cmd.extend(["--certificate-identity-regexp", ".*"])
    if expected_issuer:
        cmd.extend(["--certificate-oidc-issuer", expected_issuer])
    else:
        cmd.extend(["--certificate-oidc-issuer-regexp", ".*"])
    try:
        return run_checked(
            cmd,
            allowed_programs={"cosign"},
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except CalledProcessError as exc:  # pragma: no cover
        output = "\n".join(filter(None, [exc.stdout, exc.stderr]))
        if request_json and "unknown flag" in (output or "").lower():
            return None
        raise SystemExit(
            f"[build_issuer_subject_input] cosign verify failed: {output}"
        ) from exc


def _verify_signature(
    image: str,
    expected_subject: str | None,
    expected_issuer: str | None,
) -> Tuple[str, str]:
    env = dict(os.environ)
    env.setdefault("COSIGN_EXPERIMENTAL", "1")

    result = _run_cosign(
        image=image,
        expected_subject=expected_subject,
        expected_issuer=expected_issuer,
        env=env,
        request_json=True,
    )
    if result is not None:
        if parsed := _parse_json_identity(result.stdout):
            return parsed
        combined_output = "\n".join(filter(None, [result.stdout, result.stderr]))
        if parsed := _parse_json_identity(combined_output):
            return parsed

    text_result = _run_cosign(
        image=image,
        expected_subject=expected_subject,
        expected_issuer=expected_issuer,
        env=env,
        request_json=False,
    )
    combined_output = "\n".join(filter(None, [text_result.stdout, text_result.stderr]))
    try:
        return _parse_identity(combined_output)
    except ValueError:
        if expected_subject and expected_issuer:
            print(
                "[build_issuer_subject_input] falling back to expected issuer/subject; cosign output lacked explicit lines",
                file=sys.stderr,
            )
            return expected_issuer, expected_subject
        raise


def build_input(
    image: str,
    output_path: Path,
    allowed_issuer_regex: str,
    allowed_subject_regex: str,
    expected_subject: str | None,
    expected_issuer: str | None,
) -> Tuple[str, str]:
    issuer, subject = _verify_signature(
        image=image,
        expected_subject=expected_subject,
        expected_issuer=expected_issuer,
    )
    payload = {
        "issuer": issuer,
        "subject": subject,
        "policy": {
            "allowed_issuer_regex": allowed_issuer_regex,
            "allowed_subject_regex": allowed_subject_regex,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return issuer, subject


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate issuer/subject policy input by verifying a cosigned image"
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Full registry reference to the signed image (including digest)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination path for the issuer/subject JSON payload",
    )
    parser.add_argument(
        "--allowed-issuer-regex",
        required=True,
        help="Regex enforced by the issuer/subject policy for issuer values",
    )
    parser.add_argument(
        "--allowed-subject-regex",
        required=True,
        help="Regex enforced by the issuer/subject policy for subject values",
    )
    parser.add_argument(
        "--expected-subject",
        help="Optional subject to enforce via cosign --certificate-identity",
    )
    parser.add_argument(
        "--expected-issuer",
        help="Optional issuer to enforce via cosign --certificate-oidc-issuer",
    )
    args = parser.parse_args()
    build_input(
        image=args.image,
        output_path=args.output,
        allowed_issuer_regex=args.allowed_issuer_regex,
        allowed_subject_regex=args.allowed_subject_regex,
        expected_subject=args.expected_subject,
        expected_issuer=args.expected_issuer,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(130)
