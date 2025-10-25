import base64
import json
import os
import pathlib
import sys


def normalize(digest: str | None) -> str:
    if not digest:
        return ""
    digest = digest.lower()
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


def load_records(path: pathlib.Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    records: list[dict] = []
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        obj, offset = decoder.raw_decode(text, idx)
        records.append(obj)
        idx = offset
    return records


def collect_subjects(records: list[dict]) -> list[dict]:
    subjects: list[dict] = []
    for envelope in records:
        current = envelope.get("subject")
        if not current:
            payload = envelope.get("payload")
            if not isinstance(payload, str):
                raise SystemExit("provenance payload missing")
            try:
                decoded = json.loads(base64.b64decode(payload + "==").decode("utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                raise SystemExit(f"failed to decode DSSE payload: {exc}")
            current = decoded.get("subject")
        if current:
            subjects.extend(current)
    return subjects


def main() -> None:
    expected = normalize(os.environ.get("EXPECTED_DIGEST"))
    if not expected:
        raise SystemExit("expected digest missing")

    path = pathlib.Path("artifacts/slsa-provenance.json")
    if not path.exists():
        raise SystemExit("provenance file missing")

    records = load_records(path)
    if not records:
        raise SystemExit("provenance file empty")

    subjects = collect_subjects(records)
    if not subjects:
        raise SystemExit("provenance subject missing")

    for subj in subjects:
        digest = normalize((subj.get("digest") or {}).get("sha256"))
        if digest == expected:
            return

    existing = [normalize((subj.get("digest") or {}).get("sha256")) for subj in subjects]
    raise SystemExit(f"provenance digest mismatch: expected {expected}, subjects {existing}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
