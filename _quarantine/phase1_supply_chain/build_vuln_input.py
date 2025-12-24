#!/usr/bin/env python3
"""
Builds the JSON input expected by policies/sbom_vex.rego from a Grype report.

The script extracts the highest CVSS score per vulnerability ID, carries through
optional VEX statements, and emits the policy thresholds so the downstream OPA
policy can evaluate real scan data instead of placeholder fixtures.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_SEVERITY_FALLBACK_SCORES = {
    "critical": 10.0,
    "high": 8.0,
    "medium": 5.0,
    "moderate": 5.0,
    "low": 3.0,
}


def _pick_cvss_score(entries: Any) -> float | None:
    best: float | None = None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        metrics = entry.get("metrics") or {}
        candidate = metrics.get("baseScore", entry.get("baseScore"))
        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue
        if best is None or value > best:
            best = value
    return best


def _severity_fallback_score(vuln: Dict[str, Any]) -> float | None:
    label = vuln.get("severity")
    if not isinstance(label, str):
        return None
    return _SEVERITY_FALLBACK_SCORES.get(label.strip().lower())


def _extract_epss_percentile(entry: Any) -> float | None:
    best: float | None = None

    def _consider(raw: Any) -> None:
        nonlocal best
        if raw is None:
            return
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return
        if value > 1 and value <= 100:
            value /= 100.0
        if 0 <= value <= 1 and (best is None or value > best):
            best = value

    def _from_mapping(mapping: Dict[str, Any]) -> None:
        epss_meta = None
        metadata = mapping.get("metadata")
        if isinstance(metadata, dict):
            epss_meta = metadata.get("epss")
        if epss_meta is None:
            epss_meta = mapping.get("epss")
        if isinstance(epss_meta, dict):
            for key in ("percentile", "percentileScore", "percentile_score"):
                _consider(epss_meta.get(key))
        elif isinstance(epss_meta, list):
            for item in epss_meta:
                if isinstance(item, dict):
                    for key in ("percentile", "percentileScore", "percentile_score"):
                        _consider(item.get(key))

    if isinstance(entry, dict):
        _from_mapping(entry)
    elif isinstance(entry, list):
        for item in entry:
            if isinstance(item, dict):
                _from_mapping(item)
    return best


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized == "notaffected":
        normalized = "not_affected"
    return normalized or None


def _build_vulnerability_list(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for match in report.get("matches", []):
        if not isinstance(match, dict):
            continue
        vuln = match.get("vulnerability")
        if not isinstance(vuln, dict):
            continue
        vuln_id = vuln.get("id")
        if not vuln_id:
            continue
        score = _pick_cvss_score(vuln.get("cvss"))
        entry = aggregated.setdefault(
            vuln_id,
            {
                "id": vuln_id,
                "cvss": 0.0,
                "epss_percentile": 0.0,
                "_has_real_cvss": False,
            },
        )
        severity_fallback = _severity_fallback_score(vuln)
        related_vulns = match.get("relatedVulnerabilities")
        related_vulns = (
            related_vulns if isinstance(related_vulns, list) else []
        )
        related_scores = [
            _pick_cvss_score(rel.get("cvss"))
            for rel in related_vulns
            if isinstance(rel, dict)
        ]
        for candidate in [score, *related_scores]:
            if candidate is None:
                continue
            if (not entry["_has_real_cvss"]) or candidate > entry["cvss"]:
                entry["cvss"] = candidate
                entry["_has_real_cvss"] = True
        if (
            not entry["_has_real_cvss"]
            and severity_fallback is not None
            and severity_fallback > entry["cvss"]
        ):
            entry["cvss"] = severity_fallback
        epss_candidates = [
            _extract_epss_percentile(source)
            for source in (vuln, match, related_vulns)
        ]
        epss_value = max(
            (value for value in epss_candidates if value is not None),
            default=None,
        )
        if epss_value is not None and epss_value > entry["epss_percentile"]:
            entry["epss_percentile"] = epss_value
    normalized: List[Dict[str, Any]] = []
    for entry in aggregated.values():
        normalized.append(
            {
                "id": entry["id"],
                "cvss": entry["cvss"],
                "epss_percentile": entry["epss_percentile"],
            }
        )
    return sorted(normalized, key=lambda item: item["id"])


def _normalize_vex_entries(raw: Any) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []

    def _append(v_id: Any, status: Any) -> None:
        normalized_status = _normalize_status(status)
        if isinstance(v_id, str) and normalized_status:
            entries.append({"id": v_id, "status": normalized_status})

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            status = item.get("status") or (item.get("analysis") or {}).get("state")
            _append(item.get("id"), status)
        return entries

    if isinstance(raw, dict):
        if "vulnerabilities" in raw and isinstance(raw["vulnerabilities"], list):
            for vuln in raw["vulnerabilities"]:
                if not isinstance(vuln, dict):
                    continue
                status = vuln.get("status") or (vuln.get("analysis") or {}).get("state")
                _append(vuln.get("id"), status)
            return entries
        if "statements" in raw and isinstance(raw["statements"], list):
            for statement in raw["statements"]:
                if not isinstance(statement, dict):
                    continue
                vuln_id = (
                    statement.get("id")
                    or (statement.get("vulnerability") or {}).get("id")
                )
                status = statement.get("status") or (
                    statement.get("analysis") or {}
                ).get("state")
                _append(vuln_id, status)
            return entries
        _append(raw.get("id"), raw.get("status"))
    return entries


def build_input(
    grype_report: Path,
    output_path: Path,
    cvss_threshold: float,
    epss_threshold: float,
    vex_json: Path | None,
) -> None:
    try:
        report_data = json.loads(grype_report.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI logs
        raise SystemExit(f"[build_vuln_input] invalid Grype report JSON: {exc}") from exc

    vulnerabilities = _build_vulnerability_list(report_data)

    vex_entries: List[Dict[str, Any]] = []
    if vex_json:
        try:
            vex_entries = _normalize_vex_entries(json.loads(vex_json.read_text()))
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise SystemExit(f"[build_vuln_input] invalid VEX JSON: {exc}") from exc

    payload = {
        "policy": {
            "cvss_threshold": cvss_threshold,
            "epss_threshold": epss_threshold,
        },
        "vulnerabilities": vulnerabilities,
        "vex": vex_entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Grype JSON report into sbom_vex policy input"
    )
    parser.add_argument(
        "--grype-report",
        required=True,
        type=Path,
        help="Path to the Grype JSON report generated from an SBOM",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination file for the normalized policy input JSON",
    )
    parser.add_argument(
        "--cvss-threshold",
        type=float,
        default=7.0,
        help="CVSS score that requires a VEX justification",
    )
    parser.add_argument(
        "--epss-threshold",
        type=float,
        default=0.7,
        help="EPSS percentile that requires a VEX justification",
    )
    parser.add_argument(
        "--vex",
        type=Path,
        help="Optional path to a VEX JSON document to include in the input",
    )
    args = parser.parse_args()

    if not args.grype_report.is_file():
        raise SystemExit(
            f"[build_vuln_input] Grype report not found: {args.grype_report}"
        )

    vex_path = args.vex if args.vex and args.vex.is_file() else None
    build_input(
        grype_report=args.grype_report,
        output_path=args.output,
        cvss_threshold=args.cvss_threshold,
        epss_threshold=args.epss_threshold,
        vex_json=vex_path,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - developer convenience
        sys.exit(130)
