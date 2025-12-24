#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import build_issuer_subject_input
from tools.safe_subprocess import run_checked


def run(cmd: list[str], *, allowed_programs: set[str]) -> str:
    """Execute a trusted CLI command and return stdout."""
    result = run_checked(
        cmd,
        allowed_programs=allowed_programs,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--allowed-issuer-regex",
        required=True,
        help="Regex enforced by policies/issuer_subject.rego for issuer values",
    )
    parser.add_argument(
        "--allowed-subject-regex",
        required=True,
        help="Regex enforced by policies/issuer_subject.rego for subject values",
    )
    parser.add_argument(
        "--expected-issuer",
        help="Optional issuer passed to cosign --certificate-oidc-issuer",
    )
    parser.add_argument(
        "--expected-subject",
        help="Optional subject passed to cosign --certificate-identity",
    )
    args = parser.parse_args()

    image_ref = f"{args.image_ref}@{args.image_digest}"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    refs_json = run(
        ["oras", "discover", image_ref, "--output", "json"],
        allowed_programs={"oras"},
    )
    (output_dir / "referrers.json").write_text(refs_json)

    issuer, subject = build_issuer_subject_input.build_input(
        image=image_ref,
        output_path=output_dir / "issuer_subject.json",
        allowed_issuer_regex=args.allowed_issuer_regex,
        allowed_subject_regex=args.allowed_subject_regex,
        expected_subject=args.expected_subject,
        expected_issuer=args.expected_issuer,
    )
    (output_dir / "issuer_subject.log").write_text(
        json.dumps({"issuer": issuer, "subject": subject}, indent=2)
    )


if __name__ == "__main__":
    main()
