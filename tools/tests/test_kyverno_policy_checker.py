from __future__ import annotations

from pathlib import Path

import pytest

from tools.kyverno_policy_checker import (
    evaluate_require_referrers,
    evaluate_resource,
    evaluate_secretless,
    evaluate_verify_images,
)


POLICY_DIR = Path("policies/kyverno")
FIXTURES_DIR = Path("fixtures/kyverno")


@pytest.mark.parametrize(
    "resource_fixture,expect_pass",
    [
        ("deployment_secure.yaml", True),
        ("deployment_tagged.yaml", False),
    ],
)
def test_verify_images(resource_fixture: str, expect_pass: bool):
    result = evaluate_verify_images(
        POLICY_DIR / "verify-images.yaml",
        FIXTURES_DIR / resource_fixture,
    )
    assert result.passed is expect_pass
    if expect_pass:
        assert not result.failures
    else:
        assert any("missing a pinned digest" in msg for msg in result.failures)


@pytest.mark.parametrize(
    "resource_fixture,expect_pass",
    [
        ("deployment_secure.yaml", True),
        ("deployment_missing_referrers.yaml", False),
    ],
)
def test_require_referrers(resource_fixture: str, expect_pass: bool):
    result = evaluate_require_referrers(FIXTURES_DIR / resource_fixture)
    assert result.passed is expect_pass
    if expect_pass:
        assert not result.failures
    else:
        assert any("referrer" in msg for msg in result.failures)


@pytest.mark.parametrize(
    "resource_fixture,expect_pass",
    [
        ("deployment_secure.yaml", True),
        ("deployment_secret_env.yaml", False),
    ],
)
def test_secretless_policy(resource_fixture: str, expect_pass: bool):
    result = evaluate_secretless(FIXTURES_DIR / resource_fixture)
    assert result.passed is expect_pass
    if expect_pass:
        assert not result.failures
    else:
        assert any("secret" in msg for msg in result.failures)


def test_suite_helpers_return_combined_results():
    secure_results = evaluate_resource(POLICY_DIR, FIXTURES_DIR / "deployment_secure.yaml")
    assert all(result.passed for result in secure_results)

    failure_results = evaluate_resource(POLICY_DIR, FIXTURES_DIR / "deployment_tagged.yaml")
    assert not all(result.passed for result in failure_results)
    assert any("missing a pinned digest" in msg for result in failure_results for msg in result.failures)
