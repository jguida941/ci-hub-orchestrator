import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import (
    build_repo_config,
    detect_language,
    parse_repo_from_remote,
    render_caller_workflow,
)


def test_parse_repo_from_remote_https():
    owner, name = parse_repo_from_remote("https://github.com/acme/example.git")
    assert owner == "acme"
    assert name == "example"


def test_parse_repo_from_remote_ssh():
    owner, name = parse_repo_from_remote("git@github.com:acme/example.git")
    assert owner == "acme"
    assert name == "example"


def test_detect_language_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    language, reasons = detect_language(tmp_path)
    assert language == "python"
    assert "pyproject.toml" in reasons


def test_detect_language_java(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    language, reasons = detect_language(tmp_path)
    assert language == "java"
    assert "pom.xml" in reasons


def test_build_repo_config_prunes_other_language():
    config = build_repo_config("python", "acme", "repo", "main")
    assert config["language"] == "python"
    assert "python" in config
    assert "java" not in config
    assert config["repo"]["dispatch_workflow"] == "hub-ci.yml"


def test_build_repo_config_sets_subdir():
    config = build_repo_config("java", "acme", "repo", "main", subdir="services/app")
    assert config["repo"]["subdir"] == "services/app"


def test_render_caller_workflow_renames_target():
    content = render_caller_workflow("python")
    assert "hub-ci.yml" in content
    assert "hub-python-ci.yml" not in content
