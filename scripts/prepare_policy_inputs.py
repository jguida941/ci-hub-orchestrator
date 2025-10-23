#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


def run(cmd):
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    refs_json = run([
        "oras", "discover", f"{args.image_ref}@{args.image_digest}", "--output", "json"
    ])
    (output_dir / "referrers.json").write_text(refs_json)

    iss = run([
        "cosign", "verify", "--certificate-identity-regexp", ".*",
        "--certificate-oidc-issuer-regexp", ".*",
        f"{args.image_ref}@{args.image_digest}"
    ])
    (output_dir / "issuer_subject.log").write_text(iss)


if __name__ == "__main__":
    main()
