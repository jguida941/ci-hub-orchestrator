#!/usr/bin/env python3
"""
Emit a `pipeline_run.v1.2` NDJSON record for ingestion.

The GitHub release workflow uses this to serialize key metadata about the
pipeline so downstream analytics and dbt models have a canonical source
of truth even before the full warehouse stack exists.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_run_id(repo: str, commit: str) -> str:
    gha_run = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    base = f"{repo}:{commit}:{gha_run}:{attempt}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, base))


def _parse_job_json(raw: str) -> dict[str, Any]:
    try:
        candidate = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI logs
        raise SystemExit(f"[emit_pipeline_run] invalid job JSON: {exc}") from exc
    if not isinstance(candidate, dict):
        raise SystemExit("[emit_pipeline_run] job definitions must be JSON objects")
    for key in ("id", "name", "status", "duration_ms"):
        if key not in candidate:
            raise SystemExit(f"[emit_pipeline_run] job missing required field '{key}'")
    return candidate


def _load_jobs(job_args: list[str] | None, jobs_file: Path | None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if jobs_file:
        raw = json.loads(jobs_file.read_text())
        if not isinstance(raw, list):
            raise SystemExit("[emit_pipeline_run] jobs file must be a JSON array")
        for entry in raw:
            if not isinstance(entry, dict):
                raise SystemExit("[emit_pipeline_run] jobs file entries must be objects")
            jobs.append(entry)
    if job_args:
        for job_json in job_args:
            jobs.append(_parse_job_json(job_json))
    return jobs


def _build_default_job(status: str, duration_ms: int) -> dict[str, Any]:
    attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    return {
        "id": "gha-release",
        "name": "gha-release",
        "status": status,
        "attempt": attempt,
        "duration_ms": duration_ms,
        "queue_ms": 0,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit pipeline_run.v1.2 NDJSON")
    parser.add_argument("--output", required=True, type=Path, help="Destination NDJSON path")
    parser.add_argument("--run-id", help="Override generated run_id")
    parser.add_argument("--repo", help="Defaults to $GITHUB_REPOSITORY")
    parser.add_argument("--commit-sha", help="Defaults to $GITHUB_SHA")
    parser.add_argument("--branch", help="Defaults to $GITHUB_REF_NAME")
    parser.add_argument("--pr-number", type=int, help="Associated pull request number")
    parser.add_argument("--status", default="success", choices=["success", "failed", "canceled", "skipped"])
    parser.add_argument("--environment", default="staging", help="preview/dev/staging/prod/test")
    parser.add_argument("--queue-ms", type=int, default=0)
    parser.add_argument("--artifact-bytes", type=int, default=0)
    parser.add_argument("--started-at", help="ISO8601 timestamp; defaults to now")
    parser.add_argument("--ended-at", help="ISO8601 timestamp; defaults to now")
    parser.add_argument("--image-digest", help="sha256:... digest of deployed image")
    parser.add_argument("--sbom-uri", help="URI to CycloneDX/SPDX SBOM bundle")
    parser.add_argument("--provenance-uri", help="URI to SLSA provenance artifact")
    parser.add_argument("--signature-uri", help="URI to Cosign signature artifact")
    parser.add_argument("--release-evidence-uri", help="URI to Evidence Bundle (HTML/JSON)")
    parser.add_argument("--runner-os", default="linux")
    parser.add_argument("--runner-type", default="hosted")
    parser.add_argument("--region", default="global")
    parser.add_argument("--cache-key", action="append", help="Cache keys restored during run")
    parser.add_argument("--spot", action="store_true", help="Mark run as spot/preemptible runner")
    parser.add_argument("--carbon-g-co2e", type=float, default=0.0)
    parser.add_argument("--energy-kwh", type=float, default=0.0)
    parser.add_argument("--tests-total", type=int, default=0)
    parser.add_argument("--tests-failed", type=int, default=0)
    parser.add_argument("--tests-skipped", type=int, default=0)
    parser.add_argument("--tests-duration-ms", type=int, default=0)
    parser.add_argument("--resilience-mutants", type=int, default=0)
    parser.add_argument("--resilience-killed", type=int, default=0)
    parser.add_argument("--resilience-equiv", type=int, default=0)
    parser.add_argument("--resilience-timeout", type=int, default=0)
    parser.add_argument("--resilience-score", type=float, default=0.0)
    parser.add_argument("--resilience-delta", type=float, default=0.0)
    parser.add_argument("--cost-usd", type=float, default=0.0)
    parser.add_argument("--cpu-seconds", type=float, default=0.0)
    parser.add_argument("--gpu-seconds", type=float, default=0.0)
    parser.add_argument("--primary-job-duration-ms", type=int, default=0)
    parser.add_argument("--jobs-file", type=Path, help="Path to JSON array describing jobs")
    parser.add_argument("--job", action="append", help="Inline JSON job definition")
    parser.add_argument("--output-dir", type=Path, help=argparse.SUPPRESS)  # legacy compatibility
    parser.add_argument("--autopsy-report", type=Path, help="Path to autopsy JSON report")
    parser.add_argument("--scheduler-report", type=Path, help="Path to predictive scheduler JSON report")
    return parser.parse_args()


def build_record(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY", "unknown/unknown")
    commit = args.commit_sha or os.environ.get("GITHUB_SHA", "0" * 40)
    branch = args.branch or os.environ.get("GITHUB_REF_NAME", "main")
    started_at = args.started_at or _iso_now()
    ended_at = args.ended_at or _iso_now()
    run_id = args.run_id or _default_run_id(repo, commit)

    jobs = _load_jobs(args.job, args.jobs_file)
    if not jobs:
        jobs = [_build_default_job(args.status, args.primary_job_duration_ms)]

    tests = {
        "total": args.tests_total,
        "failed": args.tests_failed,
        "skipped": args.tests_skipped,
        "duration_ms": args.tests_duration_ms,
        "resilience": {
            "mutants_total": args.resilience_mutants,
            "killed": args.resilience_killed,
            "equiv": args.resilience_equiv,
            "timeout": args.resilience_timeout,
            "score": args.resilience_score,
            "delta_vs_main": args.resilience_delta,
            "equivalent_mutants_dropped": False,
        },
    }

    record: dict[str, Any] = {
        "schema": "pipeline_run.v1.2",
        "run_id": run_id,
        "repo": repo,
        "commit_sha": commit,
        "branch": branch,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": args.status,
        "queue_ms": args.queue_ms,
        "artifact_bytes": args.artifact_bytes,
        "environment": args.environment,
        "jobs": jobs,
        "tests": tests,
        "cost": {
            "usd": args.cost_usd,
            "cpu_seconds": args.cpu_seconds,
            "gpu_seconds": args.gpu_seconds,
        },
    }

    if args.pr_number:
        record["pr"] = args.pr_number
    if args.image_digest:
        record["image_digest"] = args.image_digest
    if args.sbom_uri:
        record["sbom_uri"] = args.sbom_uri
    if args.provenance_uri:
        record["provenance_uri"] = args.provenance_uri
    if args.signature_uri:
        record["signature_uri"] = args.signature_uri
    if args.release_evidence_uri:
        record["release_evidence_uri"] = args.release_evidence_uri
    record["runner_os"] = args.runner_os
    record["runner_type"] = args.runner_type
    record["region"] = args.region
    record["spot"] = args.spot
    if args.carbon_g_co2e:
        record["carbon_g_co2e"] = args.carbon_g_co2e
    if args.energy_kwh:
        record["energy"] = {"kwh": args.energy_kwh}
    if args.cache_key:
        record["cache_keys"] = args.cache_key
    if args.autopsy_report:
        autopsy_findings = _load_autopsy_findings(args.autopsy_report)
        if autopsy_findings:
            record["autopsy"] = {"root_causes": autopsy_findings}
    if args.scheduler_report:
        scheduler_blob = _load_scheduler_report(args.scheduler_report)
        if scheduler_blob:
            record["scheduler"] = scheduler_blob
    return record


AUTOPSY_ALLOWED_FIELDS = {"tool", "pattern", "file", "line", "message", "suggestion", "severity", "docs_uri"}


def _load_autopsy_findings(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"[emit_pipeline_run] autopsy report not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[emit_pipeline_run] failed to parse autopsy report {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"[emit_pipeline_run] autopsy report must be an object: {path}")
    if "findings" not in payload:
        findings: list[Any] = []
    else:
        findings = payload["findings"]
    if not isinstance(findings, list):
        raise SystemExit("[emit_pipeline_run] autopsy report 'findings' must be a list")
    normalized: list[dict[str, Any]] = []
    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise SystemExit(f"[emit_pipeline_run] autopsy finding #{idx} must be an object")
        filtered = {k: finding[k] for k in AUTOPSY_ALLOWED_FIELDS if k in finding}
        required = {"tool", "pattern", "file", "line", "message", "severity"}
        missing = required - filtered.keys()
        if missing:
            raise SystemExit(
                f"[emit_pipeline_run] autopsy finding #{idx} missing required fields: {', '.join(sorted(missing))}"
            )
        line_value = filtered.get("line")
        if not isinstance(line_value, int):
            raise SystemExit(f"[emit_pipeline_run] autopsy finding #{idx} field 'line' must be an integer")
        for field in ("tool", "pattern", "file", "message", "severity"):
            value = filtered.get(field)
            if not isinstance(value, str) or not value.strip():
                raise SystemExit(f"[emit_pipeline_run] autopsy finding #{idx} field '{field}' must be a non-empty string")
        for field in ("suggestion", "docs_uri"):
            if field in filtered:
                value = filtered[field]
                if not isinstance(value, str) or not value.strip():
                    raise SystemExit(
                        f"[emit_pipeline_run] autopsy finding #{idx} field '{field}' must be a non-empty string when present"
                    )
        normalized.append(filtered)
    return normalized


def _load_scheduler_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[emit_pipeline_run] ignoring invalid scheduler report {path}: {exc}", file=sys.stderr)
        return {}
    if not isinstance(payload, dict):
        print(f"[emit_pipeline_run] ignoring invalid scheduler report {path}: must be an object", file=sys.stderr)
        return {}
    allowed = {
        "schema",
        "job",
        "jobs",
        "sample_size",
        "stats",
        "recommendation",
        "generated_at",
    }
    return {k: payload[k] for k in allowed if k in payload}


def main() -> int:
    args = _parse_args()
    record = build_record(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(record))
        handle.write("\n")
    print(f"[emit_pipeline_run] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
