"""Performance benchmarks for key CLI operations.

Uses pytest-benchmark to track execution time and catch performance regressions.
Run with: pytest tests/test_performance.py --benchmark-enable
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cihub.cli import main


@pytest.fixture
def python_repo(tmp_path: Path) -> Path:
    """Create a minimal Python repo fixture."""
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'test-project'\nversion = '1.0.0'\n"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("")
    return tmp_path


@pytest.fixture
def java_repo(tmp_path: Path) -> Path:
    """Create a minimal Java repo fixture."""
    pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
</project>
"""
    (tmp_path / "pom.xml").write_text(pom)
    (tmp_path / "src" / "main" / "java").mkdir(parents=True)
    (tmp_path / "src" / "test" / "java").mkdir(parents=True)
    return tmp_path


class TestDetectPerformance:
    """Benchmark detect command - should be fast."""

    def test_detect_python_speed(self, benchmark, python_repo: Path) -> None:
        """Detect Python repo should be fast (<100ms)."""
        def run():
            return main(["detect", "--repo", str(python_repo)])

        result = benchmark(run)
        assert result == 0

    def test_detect_java_speed(self, benchmark, java_repo: Path) -> None:
        """Detect Java repo should be fast (<100ms)."""
        def run():
            return main(["detect", "--repo", str(java_repo)])

        result = benchmark(run)
        assert result == 0


class TestInitPerformance:
    """Benchmark init command - should be reasonably fast."""

    def test_init_python_speed(self, benchmark, tmp_path: Path) -> None:
        """Init Python repo should complete quickly."""
        counter = [0]

        def run():
            # Use unique path for each run
            repo = tmp_path / f"repo_{counter[0]}"
            repo.mkdir()
            (repo / "pyproject.toml").write_text("[project]\n")
            counter[0] += 1
            return main([
                "init",
                "--repo", str(repo),
                "--language", "python",
                "--owner", "test",
                "--name", "repo",
                "--branch", "main",
                "--apply",
            ])

        result = benchmark(run)
        assert result == 0

    def test_init_java_speed(self, benchmark, tmp_path: Path) -> None:
        """Init Java repo should complete quickly."""
        counter = [0]

        def run():
            repo = tmp_path / f"repo_{counter[0]}"
            repo.mkdir()
            (repo / "pom.xml").write_text("<project></project>")
            counter[0] += 1
            return main([
                "init",
                "--repo", str(repo),
                "--language", "java",
                "--owner", "test",
                "--name", "repo",
                "--branch", "main",
                "--apply",
            ])

        result = benchmark(run)
        assert result == 0


class TestValidatePerformance:
    """Benchmark validate command."""

    def test_validate_speed(self, benchmark, python_repo: Path) -> None:
        """Validate should be fast for simple configs."""
        # Create config
        (python_repo / ".ci-hub.yml").write_text("language: python\n")

        def run():
            return main(["validate", "--repo", str(python_repo)])

        result = benchmark(run)
        # May succeed or fail, just checking performance
        assert result in (0, 1)


class TestScaffoldPerformance:
    """Benchmark scaffold command - file generation."""

    def test_scaffold_python_speed(self, benchmark, tmp_path: Path) -> None:
        """Scaffold Python project should be fast."""
        counter = [0]

        def run():
            path = tmp_path / f"scaffold_{counter[0]}"
            counter[0] += 1
            return main(["scaffold", "python-pyproject", str(path)])

        result = benchmark(run)
        assert result == 0


class TestDiscoverPerformance:
    """Benchmark discover command - matrix generation."""

    def test_discover_speed(self, benchmark) -> None:
        """Discover should complete in reasonable time."""
        def run():
            return main(["discover"])

        result = benchmark(run)
        assert result in (0, 1)


class TestConfigLoadPerformance:
    """Benchmark config loading operations."""

    def test_config_merge_speed(self, benchmark) -> None:
        """Config merging should be fast."""
        from cihub.config.merge import deep_merge

        base = {
            "language": "python",
            "python": {"version": "3.12", "tools": {"pytest": {"enabled": True}}},
            "thresholds": {"coverage_min": 70},
        }
        override = {
            "python": {"tools": {"ruff": {"enabled": True}}},
            "thresholds": {"coverage_min": 80},
        }

        def run():
            return deep_merge(base.copy(), override)

        result = benchmark(run)
        assert "python" in result

    def test_config_normalize_speed(self, benchmark) -> None:
        """Config normalization should be fast."""
        from cihub.config.normalize import normalize_config

        config = {
            "language": "python",
            "python": {"tools": {"pytest": True, "ruff": False}},
        }

        def run():
            return normalize_config(config.copy())

        result = benchmark(run)
        assert "python" in result


class TestReportBuildPerformance:
    """Benchmark report building operations."""

    def test_report_validation_speed(self, benchmark, tmp_path: Path) -> None:
        """Report validation should be fast."""
        import json

        report = tmp_path / "report.json"
        report.write_text(json.dumps({
            "schema_version": "2.0",
            "repository": "test/repo",
            "branch": "main",
            "python_version": "3.12",
            "results": {
                "coverage": 80,
                "tests_passed": 100,
                "tests_failed": 0,
            },
            "tool_metrics": {},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
        }))

        def run():
            return main(["report", "validate", "--report", str(report)])

        result = benchmark(run)
        assert result == 0


# Performance thresholds (optional - uncomment to enforce)
# @pytest.mark.benchmark(min_time=0.1, max_time=0.5, min_rounds=5)
# def test_detect_under_threshold(benchmark, python_repo: Path) -> None:
#     """Detect must complete under 500ms."""
#     result = benchmark(lambda: main(["detect", "--repo", str(python_repo)]))
#     assert result == 0
