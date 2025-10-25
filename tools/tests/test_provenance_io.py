import base64
import json
from pathlib import Path
import tempfile
import unittest

from tools import provenance_io


class TestProvenanceIO(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)

    def test_load_records_from_array(self):
        data = [{"payloadType": "in-toto", "payload": "aaa"}]
        path = self.tmpdir / "prov.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        records = provenance_io.load_records(path)
        self.assertEqual(records, data)

    def test_load_records_from_single_object(self):
        data = {"payloadType": "in-toto", "payload": "bbb"}
        path = self.tmpdir / "single.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        records = provenance_io.load_records(path)
        self.assertEqual(records, [data])

    def test_load_records_from_jsonl(self):
        entries = [
            {"payloadType": "in-toto", "payload": "aaa"},
            {"payloadType": "in-toto", "payload": "bbb"},
        ]
        path = self.tmpdir / "multi.jsonl"
        path.write_text(
            "\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8"
        )
        records = provenance_io.load_records(path)
        self.assertEqual(records, entries)

    def test_dump_records_creates_pretty_json(self):
        path = self.tmpdir / "out.json"
        provenance_io.dump_records(
            [{"payloadType": "in-toto", "payload": "ccc"}], path, indent=4
        )
        content = path.read_text(encoding="utf-8")
        self.assertIn("\n", content)
        parsed = json.loads(content)
        self.assertEqual(len(parsed), 1)

    def test_decode_statement_round_trip(self):
        statement = {"subject": [{"name": "img", "digest": {"sha256": "aaa"}}]}
        payload = base64.b64encode(json.dumps(statement).encode("utf-8")).decode("utf-8")
        envelope = {"payloadType": "in-toto", "payload": payload}
        decoded = provenance_io.decode_statement(envelope)
        self.assertEqual(decoded["subject"][0]["digest"]["sha256"], "aaa")

    def test_select_envelope_by_digest(self):
        def make_envelope(hex_digest):
            stmt = {"subject": [{"name": "img", "digest": {"sha256": hex_digest}}]}
            payload = base64.b64encode(json.dumps(stmt).encode("utf-8")).decode("utf-8")
            return {"payloadType": "in-toto", "payload": payload}

        records = [make_envelope("aaa"), make_envelope("bbb")]
        selected = provenance_io.select_envelope(records, "sha256:bbb", 0)
        decoded = provenance_io.decode_statement(selected)
        self.assertEqual(
            provenance_io.normalize_digest(decoded["subject"][0]["digest"]["sha256"]),
            "sha256:bbb",
        )

    def test_select_envelope_out_of_range(self):
        records = [{"payloadType": "in-toto", "payload": "aaa"}]
        with self.assertRaises(provenance_io.ProvenanceParseError):
            provenance_io.select_envelope(records, None, 10)
