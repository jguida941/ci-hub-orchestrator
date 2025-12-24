#!/usr/bin/env python3
"""Cache Sentinel: record and verify cache manifests using BLAKE3 digests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable

try:
    from blake3 import blake3 as _blake3

    BLAKE3_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _blake3 = None
    BLAKE3_AVAILABLE = False

HASH_ALGO = "blake3" if BLAKE3_AVAILABLE else "sha256"
_CACHE_SENTINEL_WARNED = False


def new_hasher_for(algorithm: str):
    if algorithm == "blake3":
        if not BLAKE3_AVAILABLE:
            raise RuntimeError("blake3 module not installed; cannot verify manifest that requires it")
        return _blake3()
    if algorithm == "sha256":
        return hashlib.sha256()
    raise ValueError(f"unsupported hash algorithm '{algorithm}'")


def new_hasher():
    global _CACHE_SENTINEL_WARNED
    if HASH_ALGO == "sha256" and not BLAKE3_AVAILABLE and not _CACHE_SENTINEL_WARNED:
        print("[cache_sentinel] blake3 module not installed; falling back to sha256", file=sys.stderr)
        _CACHE_SENTINEL_WARNED = True
    return new_hasher_for(HASH_ALGO)

CHUNK_SIZE = 512 * 1024


def iter_files(cache_dir: Path, max_files: int | None = None) -> Iterable[Path]:
    count = 0
    for root, _, files in os.walk(cache_dir):
        for file_name in files:
            yield Path(root) / file_name
            count += 1
            if max_files is not None and count >= max_files:
                return


def compute_digest(path: Path, *, algorithm: str | None = None) -> str:
    algo = algorithm or HASH_ALGO
    hasher = new_hasher_for(algo)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def command_record(args: argparse.Namespace) -> int:
    cache_dir = Path(args.cache_dir).resolve()
    if not cache_dir.is_dir():
        print(f"[cache_sentinel] cache directory '{cache_dir}' does not exist", file=sys.stderr)
        return 1

    entries = []
    for file_path in iter_files(cache_dir, args.max_files):
        rel_path = file_path.relative_to(cache_dir).as_posix()
        try:
            size = file_path.stat().st_size
            digest = compute_digest(file_path)
        except (OSError, IOError) as exc:
            print(f"[cache_sentinel] warning: skipping {rel_path}: {exc}", file=sys.stderr)
            continue
        entries.append(
            {
                "path": rel_path,
                "size": size,
                HASH_ALGO: digest,
            }
        )

    manifest = {
        "version": 1,
        "cache_dir": str(cache_dir),
        "entry_count": len(entries),
        "algorithm": HASH_ALGO,
        "entries": entries,
    }

    output = Path(args.output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2) + "\n")
    except OSError as exc:
        print(f"[cache_sentinel] failed to write manifest '{output}': {exc}", file=sys.stderr)
        return 1
    print(f"[cache_sentinel] Recorded {len(entries)} cache entries to {output}")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    cache_dir = Path(args.cache_dir).resolve()
    manifest_path = Path(args.manifest)
    quarantine_dir = Path(args.quarantine_dir).resolve()
    if not cache_dir.is_dir():
        print(f"[cache_sentinel] cache directory '{cache_dir}' does not exist", file=sys.stderr)
        return 1
    if not manifest_path.is_file():
        print(f"[cache_sentinel] manifest '{manifest_path}' not found", file=sys.stderr)
        return 1

    try:
        manifest_raw = manifest_path.read_text()
    except OSError as exc:
        print(f"[cache_sentinel] unable to read manifest '{manifest_path}': {exc}", file=sys.stderr)
        return 1
    try:
        manifest = json.loads(manifest_raw)
    except json.JSONDecodeError as exc:
        print(f"[cache_sentinel] failed to parse manifest '{manifest_path}': {exc}", file=sys.stderr)
        return 1

    if manifest.get("version") != 1:
        print(f"[cache_sentinel] unsupported manifest version: {manifest.get('version')}", file=sys.stderr)
        return 1
    manifest_algo = manifest.get("algorithm")
    if manifest_algo not in {"blake3", "sha256"}:
        print(f"[cache_sentinel] unsupported manifest algorithm '{manifest_algo}'", file=sys.stderr)
        return 1
    if manifest_algo == "blake3" and not BLAKE3_AVAILABLE:
        print(
            "[cache_sentinel] manifest requires blake3 but module is not installed; install 'blake3' package",
            file=sys.stderr,
        )
        return 1

    entries = manifest.get("entries")
    if not isinstance(entries, list):
        print("[cache_sentinel] manifest missing 'entries' list", file=sys.stderr)
        return 1
    mismatches = []
    missing = []
    moved = []

    for entry in entries:
        rel_path = entry.get("path")
        if not isinstance(rel_path, str):
            print(f"[cache_sentinel] manifest entry missing path: {entry}", file=sys.stderr)
            continue
        expected = entry.get(manifest_algo)
        if expected is None:
            print(
                f"[cache_sentinel] manifest entry for {rel_path} missing {manifest_algo} digest; treating as missing",
                file=sys.stderr,
            )
            missing.append(rel_path)
            continue
        target = cache_dir / rel_path
        if not target.exists():
            missing.append(rel_path)
            continue
        try:
            actual = compute_digest(target, algorithm=manifest_algo)
        except (OSError, IOError) as exc:
            print(f"[cache_sentinel] error reading {target}: {exc}", file=sys.stderr)
            missing.append(rel_path)
            continue
        except RuntimeError as exc:
            print(f"[cache_sentinel] {exc}", file=sys.stderr)
            return 1
        if actual != expected:
            print(
                f"[cache_sentinel] mismatch for {target} (expected {expected}, got {actual}); quarantining",
                file=sys.stderr,
            )
            destination = quarantine_dir / rel_path
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(destination))
            except (OSError, IOError) as exc:
                print(f"[cache_sentinel] failed to quarantine {target}: {exc}", file=sys.stderr)
                continue
            mismatches.append(rel_path)
            moved.append(str(destination))

    status = 0
    if missing or mismatches:
        status = 1
    if moved:
        print(f"[cache_sentinel] quarantined files written to {quarantine_dir}", file=sys.stderr)

    details = {
        "manifest": str(manifest_path),
        "checked": len(entries),
        "missing": missing,
        "mismatches": mismatches,
        "quarantined": moved,
    }
    if args.report:
        report_path = Path(args.report)
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(details, indent=2) + "\n")
        except OSError as exc:
            print(f"[cache_sentinel] failed to write report '{report_path}': {exc}", file=sys.stderr)
            status = 1
    print(json.dumps(details, indent=2))
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cache sentinel manifest recorder/verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="Record cache manifest entries")
    record.add_argument("--cache-dir", required=True, help="Cache directory to scan")
    record.add_argument("--output", required=True, help="Manifest JSON output path")
    record.add_argument(
        "--max-files",
        type=int,
        default=1000,
        help="Maximum number of files to record (default: 1000)",
    )
    record.set_defaults(func=command_record)

    verify = subparsers.add_parser("verify", help="Verify cache manifest and quarantine mismatches")
    verify.add_argument("--cache-dir", required=True, help="Cache directory to check")
    verify.add_argument("--manifest", required=True, help="Manifest JSON path to validate against")
    verify.add_argument(
        "--quarantine-dir",
        required=True,
        help="Directory to move mismatched files into",
    )
    verify.add_argument(
        "--report",
        help="Optional JSON report output path",
    )
    verify.set_defaults(func=command_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
