"""Tests for correlation.py - Deterministic run matching."""

import json
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.correlation import (
    extract_correlation_id_from_artifact,
    find_run_by_correlation_id,
    generate_correlation_id,
    validate_correlation_id,
)


class TestGenerateCorrelationId:
    """Tests for generate_correlation_id function."""

    def test_basic_format(self):
        """Correlation ID follows expected format."""
        result = generate_correlation_id("12345678", "1", "smoke-test-python")
        assert result == "12345678-1-smoke-test-python"

    def test_integer_inputs(self):
        """Integer inputs are converted to strings."""
        result = generate_correlation_id(12345678, 1, "config-name")
        assert result == "12345678-1-config-name"

    def test_retry_attempt(self):
        """Run attempt is included for retry scenarios."""
        result = generate_correlation_id("12345678", "2", "my-config")
        assert result == "12345678-2-my-config"


class TestValidateCorrelationId:
    """Tests for validate_correlation_id function."""

    def test_matching_ids(self):
        """Matching IDs return True."""
        assert validate_correlation_id("abc-123", "abc-123") is True

    def test_mismatched_ids(self):
        """Mismatched IDs return False."""
        assert validate_correlation_id("abc-123", "xyz-456") is False

    def test_empty_expected_skips_validation(self):
        """Empty expected ID skips validation (returns True)."""
        assert validate_correlation_id("", "any-value") is True
        assert validate_correlation_id("", None) is True

    def test_expected_but_no_actual(self):
        """Expected ID but no actual returns False."""
        assert validate_correlation_id("expected-id", None) is False
        assert validate_correlation_id("expected-id", "") is False


class TestExtractCorrelationIdFromArtifact:
    """Tests for extract_correlation_id_from_artifact function."""

    def test_valid_artifact_with_correlation_id(self, tmp_path: Path):
        """Extracts correlation ID from valid artifact."""
        # Create a mock artifact ZIP
        report_data = {
            "hub_correlation_id": "12345-1-test-config",
            "results": {"coverage": 80},
        }
        artifact_dir = tmp_path / "artifact"
        artifact_dir.mkdir()
        (artifact_dir / "report.json").write_text(json.dumps(report_data))

        zip_path = tmp_path / "artifact.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(artifact_dir / "report.json", "report.json")

        # Mock the download to return our test ZIP
        with patch("scripts.correlation.download_artifact") as mock_download:
            mock_download.return_value = artifact_dir

            result = extract_correlation_id_from_artifact(
                "https://fake-url/artifact.zip",
                "fake-token"
            )
            assert result == "12345-1-test-config"

    def test_artifact_without_correlation_id(self, tmp_path: Path):
        """Returns None if report.json has no correlation ID."""
        report_data = {"results": {"coverage": 80}}
        artifact_dir = tmp_path / "artifact"
        artifact_dir.mkdir()
        (artifact_dir / "report.json").write_text(json.dumps(report_data))

        with patch("scripts.correlation.download_artifact") as mock_download:
            mock_download.return_value = artifact_dir

            result = extract_correlation_id_from_artifact(
                "https://fake-url/artifact.zip",
                "fake-token"
            )
            assert result is None

    def test_download_failure(self):
        """Returns None if download fails."""
        with patch("scripts.correlation.download_artifact") as mock_download:
            mock_download.return_value = None

            result = extract_correlation_id_from_artifact(
                "https://fake-url/artifact.zip",
                "fake-token"
            )
            assert result is None

    def test_invalid_json(self, tmp_path: Path):
        """Returns None if report.json is invalid JSON."""
        artifact_dir = tmp_path / "artifact"
        artifact_dir.mkdir()
        (artifact_dir / "report.json").write_text("not valid json {{{")

        with patch("scripts.correlation.download_artifact") as mock_download:
            mock_download.return_value = artifact_dir

            result = extract_correlation_id_from_artifact(
                "https://fake-url/artifact.zip",
                "fake-token"
            )
            assert result is None


class TestFindRunByCorrelationId:
    """Tests for find_run_by_correlation_id function."""

    def test_empty_correlation_id(self):
        """Returns None for empty correlation ID."""
        result = find_run_by_correlation_id(
            "owner", "repo", "workflow.yml", "", "token"
        )
        assert result is None

    def test_finds_matching_run(self, tmp_path: Path):
        """Finds run with matching correlation ID in artifact."""
        # Mock API responses
        runs_response = {
            "workflow_runs": [
                {"id": 111, "status": "completed"},
                {"id": 222, "status": "completed"},
            ]
        }

        artifacts_111 = {
            "artifacts": [
                {"name": "other-artifact", "archive_download_url": "url1"},
            ]
        }

        artifacts_222 = {
            "artifacts": [
                {"name": "smoke-test-ci-report", "archive_download_url": "url2"},
            ]
        }

        def mock_gh_get(url: str) -> dict:
            if "workflows" in url and "runs" in url:
                return runs_response
            elif "runs/111/artifacts" in url:
                return artifacts_111
            elif "runs/222/artifacts" in url:
                return artifacts_222
            return {}

        # Mock artifact extraction to return matching ID for run 222
        with patch("scripts.correlation.extract_correlation_id_from_artifact") as mock_extract:
            mock_extract.return_value = "target-correlation-id"

            result = find_run_by_correlation_id(
                "owner",
                "repo",
                "workflow.yml",
                "target-correlation-id",
                "token",
                gh_get=mock_gh_get
            )

            assert result == "222"

    def test_no_matching_run(self, tmp_path: Path):
        """Returns None when no run has matching correlation ID."""
        runs_response = {
            "workflow_runs": [
                {"id": 111, "status": "completed"},
            ]
        }

        artifacts_111 = {
            "artifacts": [
                {"name": "test-ci-report", "archive_download_url": "url1"},
            ]
        }

        def mock_gh_get(url: str) -> dict:
            if "workflows" in url and "runs" in url:
                return runs_response
            elif "artifacts" in url:
                return artifacts_111
            return {}

        with patch("scripts.correlation.extract_correlation_id_from_artifact") as mock_extract:
            mock_extract.return_value = "different-correlation-id"

            result = find_run_by_correlation_id(
                "owner",
                "repo",
                "workflow.yml",
                "target-correlation-id",
                "token",
                gh_get=mock_gh_get
            )

            assert result is None

    def test_no_ci_report_artifact(self):
        """Skips runs without ci-report artifact."""
        runs_response = {
            "workflow_runs": [
                {"id": 111, "status": "completed"},
            ]
        }

        artifacts_111 = {
            "artifacts": [
                {"name": "logs", "archive_download_url": "url1"},
                {"name": "coverage-data", "archive_download_url": "url2"},
            ]
        }

        def mock_gh_get(url: str) -> dict:
            if "workflows" in url and "runs" in url:
                return runs_response
            elif "artifacts" in url:
                return artifacts_111
            return {}

        result = find_run_by_correlation_id(
            "owner",
            "repo",
            "workflow.yml",
            "target-id",
            "token",
            gh_get=mock_gh_get
        )

        assert result is None

    def test_api_error_handling(self):
        """Handles API errors gracefully."""
        def mock_gh_get(url: str) -> dict:
            raise Exception("API rate limit exceeded")

        result = find_run_by_correlation_id(
            "owner",
            "repo",
            "workflow.yml",
            "target-id",
            "token",
            gh_get=mock_gh_get
        )

        assert result is None

    def test_artifact_check_error_continues(self):
        """Continues checking other runs if one artifact check fails."""
        runs_response = {
            "workflow_runs": [
                {"id": 111, "status": "completed"},
                {"id": 222, "status": "completed"},
            ]
        }

        call_count = [0]

        def mock_gh_get(url: str) -> dict:
            if "workflows" in url and "runs" in url:
                return runs_response
            elif "runs/111/artifacts" in url:
                raise Exception("Network error")
            elif "runs/222/artifacts" in url:
                return {
                    "artifacts": [
                        {"name": "ci-report", "archive_download_url": "url2"},
                    ]
                }
            return {}

        with patch("scripts.correlation.extract_correlation_id_from_artifact") as mock_extract:
            mock_extract.return_value = "target-id"

            result = find_run_by_correlation_id(
                "owner",
                "repo",
                "workflow.yml",
                "target-id",
                "token",
                gh_get=mock_gh_get
            )

            # Should find run 222 even though 111 failed
            assert result == "222"
