import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import build_issuer_subject_input as issuer_subject


class BuildIssuerSubjectInputTests(unittest.TestCase):
    def test_parse_identity_extracts_subject_and_issuer(self) -> None:
        sample = """
Verification for ghcr.io/example/app@sha256:abc
The following checks were performed on each of these signatures:
  - The cosign claims were validated
Certificate subject: repo:example/app:ref:refs/tags/v1.2.3
Certificate issuer URL: https://token.actions.githubusercontent.com
"""
        issuer, subject = issuer_subject._parse_identity(sample)
        self.assertEqual(subject, "repo:example/app:ref:refs/tags/v1.2.3")
        self.assertEqual(
            issuer,
            "https://token.actions.githubusercontent.com",
        )

    def test_parse_identity_handles_colonless_lines(self) -> None:
        sample = """
Verification for ghcr.io/example/app@sha256:def
Certificate identity repo:example/app:ref:refs/heads/main
Certificate issuer https://token.actions.githubusercontent.com
"""
        issuer, subject = issuer_subject._parse_identity(sample)
        self.assertEqual(subject, "repo:example/app:ref:refs/heads/main")
        self.assertEqual(issuer, "https://token.actions.githubusercontent.com")

    def test_parse_identity_from_ansi_colored_fixture(self) -> None:
        fixture = (
            Path(__file__).with_name("fixtures") / "cosign_verify_ansi_output.txt"
        )
        sample = fixture.read_text()
        issuer, subject = issuer_subject._parse_identity(sample)
        self.assertEqual(
            subject, "repo:example/app:ref:refs/tags/v1.2.3"
        )
        self.assertEqual(
            issuer,
            "https://token.actions.githubusercontent.com",
        )

    def test_parse_identity_from_verbose_cosign_fixture(self) -> None:
        fixture = (
            Path(__file__).with_name("fixtures")
            / "cosign_verify_verbose_output.txt"
        )
        sample = fixture.read_text()
        issuer, subject = issuer_subject._parse_identity(sample)
        self.assertEqual(
            subject, "repo:example/app:ref:refs/heads/main"
        )
        self.assertEqual(
            issuer,
            "https://token.actions.githubusercontent.com",
        )

    def test_parse_identity_from_multi_signature_fixture(self) -> None:
        fixture = (
            Path(__file__).with_name("fixtures")
            / "cosign_verify_multi_signature_output.txt"
        )
        sample = fixture.read_text()
        issuer, subject = issuer_subject._parse_identity(sample)
        self.assertEqual(
            subject, "repo:example/app:ref:refs/tags/v2.0.0"
        )
        self.assertEqual(
            issuer,
            "https://token.actions.githubusercontent.com",
        )

    def test_parse_identity_raises_on_missing_fields(self) -> None:
        with self.assertRaises(ValueError):
            issuer_subject._parse_identity("Certificate identity: missing issuer")

    @mock.patch("tools.build_issuer_subject_input._verify_signature")
    def test_build_input_materializes_payload(self, mock_verify: mock.Mock) -> None:
        mock_verify.return_value = (
            "https://token.actions.githubusercontent.com",
            "repo:example/app:ref:refs/tags/v1.2.3",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "issuer_subject.json"
            issuer, subject = issuer_subject.build_input(
                image="ghcr.io/example/app@sha256:abc",
                output_path=output,
                allowed_issuer_regex="^issuer$",
                allowed_subject_regex="^subject$",
                expected_subject="repo:example/app:ref:refs/tags/v1.2.3",
                expected_issuer="https://token.actions.githubusercontent.com",
            )
            self.assertTrue(output.is_file())
            payload = json.loads(output.read_text())
            self.assertEqual(payload["issuer"], issuer)
            self.assertEqual(payload["subject"], subject)
            self.assertEqual(payload["policy"]["allowed_issuer_regex"], "^issuer$")
            mock_verify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
