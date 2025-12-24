import os
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import main as cli_main


def resolve_fixtures_root() -> Path | None:
    candidates: list[Path] = []
    env_path = os.environ.get("CIHUB_FIXTURES_PATH")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(ROOT.parent / "ci-cd-hub-fixtures")
    candidates.append(ROOT.parent / "hub-fixtures")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def require_fixtures_root() -> Path:
    root = resolve_fixtures_root()
    if not root:
        import pytest

        pytest.skip("Fixtures repo not available; set CIHUB_FIXTURES_PATH")
    return root


def write_minimal_pom(path: Path) -> None:
    path.write_text(
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
</project>
""",
        encoding="utf-8",
    )


def prep_fixture_repo(tmp_path: Path, subdir: str) -> Path:
    fixtures_root = require_fixtures_root()
    source = fixtures_root / subdir
    if not source.exists():
        import pytest

        pytest.skip(f"Fixture subdir not found: {source}")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    shutil.copytree(source, repo_root / subdir)
    return repo_root


def test_cli_init_fix_pom_inserts_plugins(tmp_path: Path) -> None:
    repo_root = prep_fixture_repo(tmp_path, "java-passing")
    pom_path = repo_root / "java-passing" / "pom.xml"
    write_minimal_pom(pom_path)

    status = cli_main(
        [
            "init",
            "--repo",
            str(repo_root),
            "--language",
            "java",
            "--owner",
            "acme",
            "--name",
            "fixtures",
            "--branch",
            "main",
            "--subdir",
            "java-passing",
            "--fix-pom",
        ]
    )

    assert status == 0
    assert (repo_root / ".ci-hub.yml").exists()
    assert (repo_root / ".github" / "workflows" / "hub-ci.yml").exists()
    pom_text = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jacoco-maven-plugin</artifactId>" in pom_text


def test_cli_update_fix_pom_inserts_plugins(tmp_path: Path) -> None:
    repo_root = prep_fixture_repo(tmp_path, "java-passing")
    pom_path = repo_root / "java-passing" / "pom.xml"
    write_minimal_pom(pom_path)

    status = cli_main(
        [
            "update",
            "--repo",
            str(repo_root),
            "--language",
            "java",
            "--owner",
            "acme",
            "--name",
            "fixtures",
            "--branch",
            "main",
            "--subdir",
            "java-passing",
            "--fix-pom",
        ]
    )

    assert status == 0
    pom_text = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>maven-checkstyle-plugin</artifactId>" in pom_text


def test_cli_fix_pom_adds_dependencies(tmp_path: Path) -> None:
    repo_root = prep_fixture_repo(tmp_path, "java-passing")
    pom_path = repo_root / "java-passing" / "pom.xml"
    write_minimal_pom(pom_path)

    config = {
        "language": "java",
        "repo": {"subdir": "java-passing"},
        "java": {"tools": {"jqwik": {"enabled": True}}},
    }
    (repo_root / ".ci-hub.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    status = cli_main(["fix-pom", "--repo", str(repo_root), "--apply"])
    assert status == 0
    pom_text = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jqwik</artifactId>" in pom_text
