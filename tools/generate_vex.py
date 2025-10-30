#!/usr/bin/env python3
"""
Emit a CycloneDX VEX document from a curated allowlist.

The script reads a JSON configuration that lists vulnerability IDs and their
analysis state (for example, "not_affected"), then produces a CycloneDX VEX
file tying those statements to the current image reference.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_config(path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI
        raise SystemExit(f"[generate_vex] invalid JSON config: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("statements") or data.get("vulnerabilities") or data.get("entries")

    if not isinstance(data, list):
        raise SystemExit("[generate_vex] configuration must be a list of statements")

    statements: List[Dict[str, Any]] = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue
        vuln_id = entry.get("id") or (entry.get("vulnerability") or {}).get("id")
        status = entry.get("status") or (entry.get("analysis") or {}).get("state")
        if not isinstance(vuln_id, str) or not isinstance(status, str):
            continue
        statements.append(
            {
                "id": vuln_id.strip(),
                "status": status.strip(),
                "justification": entry.get("justification"),
                "impact": entry.get("impact") or entry.get("impact_statement"),
                "details": entry.get("details") or entry.get("detail"),
                "timestamp": entry.get("timestamp"),
                "source": entry.get("source"),
            }
        )
    if not statements:
        raise SystemExit("[generate_vex] configuration produced zero statements")
    return statements


def _now_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def generate_vex(
    config_path: Path,
    output_path: Path,
    subject: str,
    manufacturer: str,
    product: str,
) -> None:
    statements = _load_config(config_path)
    metadata_timestamp = _now_iso8601()
    subject_digest = subject.split("@")[-1] if "@" in subject else ""

    vex = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": metadata_timestamp,
            "tools": [
                {
                    "vendor": "ci-cd-bst-demo-github-actions",
                    "name": "generate_vex.py",
                    "version": "1.0.0",
                }
            ],
            "component": {
                "type": "application",
                "name": product,
                "manufacturer": manufacturer,
                "bom-ref": subject,
            },
            "properties": [
                {"name": "subject.ref", "value": subject},
                {"name": "subject.digest", "value": subject_digest},
            ],
        },
        "vulnerabilities": [],
    }

    for entry in statements:
        analysis = {"state": entry["status"]}
        if entry.get("justification"):
            analysis["justification"] = entry["justification"]
        if entry.get("details"):
            analysis["detail"] = entry["details"]

        vuln = {
            "id": entry["id"],
            "analysis": analysis,
            "ratings": [],
        }
        if entry.get("impact"):
            vuln["detail"] = entry["impact"]
        if entry.get("timestamp"):
            vuln["timestamp"] = entry["timestamp"]
        if entry.get("source"):
            vuln["source"] = entry["source"]

        vex["vulnerabilities"].append(vuln)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(vex, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CycloneDX VEX from statements")
    parser.add_argument("--config", required=True, type=Path, help="JSON file with VEX statements")
    parser.add_argument("--output", required=True, type=Path, help="Destination VEX file path")
    parser.add_argument(
        "--subject",
        required=True,
        help="Subject reference (e.g., ghcr.io/org/app@sha256:...)",
    )
    parser.add_argument("--manufacturer", default="ci-intel-app", help="Manufacturer string")
    parser.add_argument("--product", default="ci-intel-app", help="Product/component name")
    args = parser.parse_args()

    if not args.config.is_file():
        raise SystemExit(f"[generate_vex] missing config file: {args.config}")

    generate_vex(
        config_path=args.config,
        output_path=args.output,
        subject=args.subject,
        manufacturer=args.manufacturer,
        product=args.product,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(130)
