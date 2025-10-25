"""Helpers for reading and writing DSSE provenance envelopes."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Iterable, List, Sequence


class ProvenanceParseError(RuntimeError):
    """Raised when the provenance artifact cannot be decoded."""


def normalize_digest(digest: str | None) -> str:
    if not digest:
        return ""
    digest = digest.lower()
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


def _parse_standard_json(text: str) -> List[dict] | None:
    """Try to parse canonical JSON (object or array)."""
    if not text.strip():
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ProvenanceParseError("provenance JSON must be an object or array")


def _parse_json_lines(text: str) -> List[dict]:
    """Parse newline-delimited JSON envelopes."""
    decoder = json.JSONDecoder()
    records = []
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, offset = decoder.raw_decode(text, idx)
        except json.JSONDecodeError as exc:
            raise ProvenanceParseError(f"provenance not valid JSON: {exc}") from exc
        records.append(obj)
        idx = offset
    return records


def load_records(path: Path) -> List[dict]:
    """Load DSSE envelopes from a file."""
    text = path.read_text(encoding="utf-8")
    parsed = _parse_standard_json(text)
    if parsed is not None:
        return parsed
    return _parse_json_lines(text)


def dump_records(records: Iterable[dict], path: Path, indent: int = 2) -> None:
    """Write DSSE envelopes as a canonical JSON array."""
    payload = json.dumps(list(records), indent=indent) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def decode_statement(envelope: dict) -> dict:
    """Decode the DSSE payload of an envelope into an in-toto statement."""
    payload = envelope.get("payload")
    if not isinstance(payload, str):
        raise ProvenanceParseError("provenance payload missing or not a string")
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.b64decode(payload + padding).decode("utf-8")
    except Exception as exc:  # pragma: no cover - decoding issues bubble up
        raise ProvenanceParseError(f"failed to decode DSSE payload: {exc}") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced in CI
        raise ProvenanceParseError(f"decoded payload not valid JSON: {exc}") from exc


def subjects_from_statement(statement: dict) -> Sequence[dict]:
    subjects = statement.get("subject")
    if isinstance(subjects, list):
        return [subj for subj in subjects if isinstance(subj, dict)]
    return []


def select_envelope(records: Sequence[dict], expected_digest: str | None, index: int) -> dict:
    """Pick an envelope either by digest match or positional index."""
    if expected_digest:
        target = normalize_digest(expected_digest)
        for envelope in records:
            statement = envelope
            if "payload" in envelope:
                statement = decode_statement(envelope)
            if not isinstance(statement, dict):
                continue
            for subj in subjects_from_statement(statement):
                digest = normalize_digest((subj.get("digest") or {}).get("sha256"))
                if digest and digest == target:
                    return envelope
        raise ProvenanceParseError(f"no provenance envelope matched digest {target}")

    if not records:
        raise ProvenanceParseError("provenance file contains no envelopes")
    if index < 0 or index >= len(records):
        raise ProvenanceParseError(
            f"provenance index {index} out of range (records={len(records)})"
        )
    return records[index]
