"""Tests for secrets command handlers in cihub/commands/secrets.py.

These tests target high-complexity functions with external dependencies:
- cmd_setup_secrets(): Token validation, API calls, subprocess execution
- cmd_setup_nvd(): NVD API key setup
- verify_token(): GitHub API verification
- verify_cross_repo_access(): Artifact access check

All external calls are mocked.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.error
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.secrets import cmd_setup_nvd, cmd_setup_secrets  # noqa: E402

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_getpass():
    """Mock getpass.getpass to return a test token."""
    with mock.patch("getpass.getpass") as m:
        m.return_value = "ghp_test_token_12345"
        yield m


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for gh secret set."""
    with mock.patch("subprocess.run") as m:
        m.return_value = mock.Mock(returncode=0, stderr="")
        yield m


@pytest.fixture
def mock_resolve_executable():
    """Mock resolve_executable to return 'gh'."""
    with mock.patch("cihub.commands.secrets.resolve_executable") as m:
        m.return_value = "gh"
        yield m


@pytest.fixture
def mock_get_connected_repos():
    """Mock get_connected_repos to return test repos."""
    with mock.patch("cihub.commands.secrets.get_connected_repos") as m:
        m.return_value = ["owner/repo1", "owner/repo2"]
        yield m


def make_urlopen_response(
    data: dict[str, Any], status: int = 200, scopes: str = "repo"
):
    """Create a mock urlopen response."""

    class MockResponse:
        def __init__(self):
            self.status = status
            self.headers = {"X-OAuth-Scopes": scopes}

        def read(self):
            return json.dumps(data).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockResponse()


# ==============================================================================
# Tests for token validation
# ==============================================================================


class TestTokenValidation:
    """Tests for token input validation."""

    def test_empty_token_rejected(self, capsys) -> None:
        """Reject empty token."""
        with mock.patch("getpass.getpass", return_value=""):
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token=None,
                all=False,
                verify=False,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "No token provided" in captured.err

    def test_token_with_embedded_whitespace_rejected(self, capsys) -> None:
        """Reject token containing whitespace."""
        with mock.patch("getpass.getpass", return_value="ghp_token with space"):
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token=None,
                all=False,
                verify=False,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "whitespace" in captured.err

    def test_token_with_leading_whitespace_stripped(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Strip leading/trailing whitespace from token."""
        with mock.patch("getpass.getpass", return_value="  ghp_valid_token  "):
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token=None,
                all=False,
                verify=False,
            )
            result = cmd_setup_secrets(args)
            # Should succeed (whitespace stripped)
            assert result == 0
            # Verify subprocess was called with stripped token
            mock_subprocess.assert_called()
            call_kwargs = mock_subprocess.call_args
            assert call_kwargs.kwargs.get("input") == "ghp_valid_token"

    def test_token_from_argument(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Use token from --token argument."""
        args = argparse.Namespace(
            hub_repo="owner/hub",
            token="ghp_from_arg",  # noqa: S106
            all=False,
            verify=False,
        )
        result = cmd_setup_secrets(args)
        assert result == 0
        call_kwargs = mock_subprocess.call_args
        assert call_kwargs.kwargs.get("input") == "ghp_from_arg"


# ==============================================================================
# Tests for token verification
# ==============================================================================


class TestTokenVerification:
    """Tests for GitHub API token verification."""

    def test_verify_token_success(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Verify valid token against GitHub API."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.return_value = make_urlopen_response(
                {"login": "testuser"}, scopes="repo, workflow"
            )
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_valid_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 0
            captured = capsys.readouterr()
            assert "Token verified" in captured.out
            assert "testuser" in captured.out

    def test_verify_token_401_unauthorized(self, capsys) -> None:
        """Fail verification for 401 response."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://api.github.com/user",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=io.BytesIO(b""),
            )
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_bad_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "verification failed" in captured.err
            assert "unauthorized" in captured.err

    def test_verify_token_other_http_error(self, capsys) -> None:
        """Handle non-401 HTTP errors."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://api.github.com/user",
                code=500,
                msg="Internal Server Error",
                hdrs={},
                fp=io.BytesIO(b""),
            )
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "verification failed" in captured.err
            assert "500" in captured.err


# ==============================================================================
# Tests for cross-repo access verification
# ==============================================================================


class TestCrossRepoAccessVerification:
    """Tests for cross-repo artifact access verification."""

    def test_cross_repo_access_success(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Verify cross-repo access works."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            # First call: token verification
            # Second call: cross-repo access
            mock_urlopen.side_effect = [
                make_urlopen_response({"login": "testuser"}),
                make_urlopen_response({"total_count": 5}),
            ]
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_valid_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 0
            captured = capsys.readouterr()
            assert "Cross-repo access verified" in captured.out

    def test_cross_repo_access_404(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Fail when repo not found (404)."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                make_urlopen_response({"login": "testuser"}),
                urllib.error.HTTPError(
                    url="https://api.github.com/repos/owner/repo1/actions/artifacts",
                    code=404,
                    msg="Not Found",
                    hdrs={},
                    fp=io.BytesIO(b""),
                ),
            ]
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_valid_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "Cross-repo access failed" in captured.err
            assert "not found" in captured.err

    def test_cross_repo_access_401(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Fail when token lacks repo scope (401)."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                make_urlopen_response({"login": "testuser"}),
                urllib.error.HTTPError(
                    url="https://api.github.com/repos/owner/repo1/actions/artifacts",
                    code=401,
                    msg="Unauthorized",
                    hdrs={},
                    fp=io.BytesIO(b""),
                ),
            ]
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_valid_token",  # noqa: S106
                all=False,
                verify=True,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "repo" in captured.err  # Mentions 'repo' scope


# ==============================================================================
# Tests for secret setting
# ==============================================================================


class TestSecretSetting:
    """Tests for gh secret set subprocess calls."""

    def test_set_secret_success(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Successfully set secret on hub repo."""
        args = argparse.Namespace(
            hub_repo="owner/hub",
            token="ghp_token",  # noqa: S106
            all=False,
            verify=False,
        )
        result = cmd_setup_secrets(args)
        assert result == 0
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args == [
            "gh",
            "secret",
            "set",
            "HUB_DISPATCH_TOKEN",
            "-R",
            "owner/hub",
        ]
        captured = capsys.readouterr()
        assert "[OK] owner/hub" in captured.out

    def test_set_secret_failure(
        self, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Handle gh secret set failure."""
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stderr="permission denied")
            args = argparse.Namespace(
                hub_repo="owner/hub",
                token="ghp_token",  # noqa: S106
                all=False,
                verify=False,
            )
            result = cmd_setup_secrets(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "Failed" in captured.err

    def test_set_secret_all_repos(
        self, mock_subprocess, mock_resolve_executable, mock_get_connected_repos, capsys
    ) -> None:
        """Set secret on hub and all connected repos."""
        args = argparse.Namespace(
            hub_repo="owner/hub",
            token="ghp_token",  # noqa: S106
            all=True,
            verify=False,
        )
        result = cmd_setup_secrets(args)
        assert result == 0
        # Should be called for hub + 2 connected repos (minus hub if in list)
        assert mock_subprocess.call_count >= 2
        captured = capsys.readouterr()
        assert "[OK] owner/hub" in captured.out


# ==============================================================================
# Tests for NVD key setup
# ==============================================================================


class TestNvdKeySetup:
    """Tests for NVD API key setup command."""

    def test_empty_nvd_key_rejected(self, capsys) -> None:
        """Reject empty NVD key."""
        with mock.patch("getpass.getpass", return_value=""):
            args = argparse.Namespace(nvd_key=None, verify=False)
            result = cmd_setup_nvd(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "No NVD API key provided" in captured.err

    def test_nvd_key_with_whitespace_rejected(self, capsys) -> None:
        """Reject NVD key containing whitespace."""
        with mock.patch("getpass.getpass", return_value="key with space"):
            args = argparse.Namespace(nvd_key=None, verify=False)
            result = cmd_setup_nvd(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "whitespace" in captured.err

    def test_nvd_verify_success(
        self, mock_subprocess, mock_resolve_executable, capsys
    ) -> None:
        """Verify valid NVD key."""
        with mock.patch("cihub.commands.secrets.get_connected_repos") as mock_repos:
            mock_repos.return_value = ["owner/java-repo"]
            with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
                mock_urlopen.return_value = make_urlopen_response(
                    {"resultsPerPage": 1}, status=200
                )
                args = argparse.Namespace(nvd_key="valid-nvd-key-12345", verify=True)
                result = cmd_setup_nvd(args)
                assert result == 0
                captured = capsys.readouterr()
                assert "NVD API key verified" in captured.out

    def test_nvd_verify_403_invalid_key(self, capsys) -> None:
        """Fail verification for invalid NVD key (403)."""
        with mock.patch("cihub.commands.secrets.safe_urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://services.nvd.nist.gov/rest/json/cves/2.0",
                code=403,
                msg="Forbidden",
                hdrs={},
                fp=io.BytesIO(b""),
            )
            args = argparse.Namespace(nvd_key="invalid-key", verify=True)
            result = cmd_setup_nvd(args)
            assert result == 1
            captured = capsys.readouterr()
            assert "verification failed" in captured.err
            assert "invalid or expired" in captured.err

    def test_nvd_no_java_repos(self, mock_resolve_executable, capsys) -> None:
        """Handle case when no Java repos found."""
        with mock.patch("cihub.commands.secrets.get_connected_repos") as mock_repos:
            mock_repos.return_value = []
            args = argparse.Namespace(nvd_key="valid-nvd-key", verify=False)
            result = cmd_setup_nvd(args)
            assert result == 0
            captured = capsys.readouterr()
            assert "No Java repos found" in captured.out

    def test_nvd_set_on_java_repos(
        self, mock_subprocess, mock_resolve_executable, capsys
    ) -> None:
        """Set NVD key on Java repos."""
        with mock.patch("cihub.commands.secrets.get_connected_repos") as mock_repos:
            mock_repos.return_value = ["owner/java-repo1", "owner/java-repo2"]
            args = argparse.Namespace(nvd_key="valid-nvd-key", verify=False)
            result = cmd_setup_nvd(args)
            assert result == 0
            assert mock_subprocess.call_count == 2
            captured = capsys.readouterr()
            assert "[OK] owner/java-repo1" in captured.out
            assert "[OK] owner/java-repo2" in captured.out
