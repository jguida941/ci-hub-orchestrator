import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import (
    apply_dependency_fixes,
    apply_pom_fixes,
    build_parser,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    get_java_tool_flags,
)


def write_pom(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def base_config(jqwik_enabled: bool = True) -> dict:
    return {
        "repo": {"subdir": ""},
        "java": {
            "build_tool": "maven",
            "tools": {"jqwik": {"enabled": jqwik_enabled}},
        },
    }


def base_plugin_config(tool: str) -> dict:
    return {
        "repo": {"subdir": ""},
        "java": {
            "build_tool": "maven",
            "tools": {tool: {"enabled": True}},
        },
    }


def test_collect_java_pom_warnings_missing_plugin(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    warnings, missing = collect_java_pom_warnings(
        tmp_path, base_plugin_config("jacoco")
    )

    assert warnings
    assert missing
    assert missing[0][1] == "jacoco-maven-plugin"


def test_apply_pom_fixes_inserts_plugin(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    result = apply_pom_fixes(tmp_path, base_plugin_config("jacoco"), apply=True)
    assert result == 0
    updated = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jacoco-maven-plugin</artifactId>" in updated


def test_collect_java_dependency_warnings_single_module(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    warnings, missing = collect_java_dependency_warnings(
        tmp_path, base_config(jqwik_enabled=True)
    )

    assert warnings
    assert missing
    target, dep_id = missing[0]
    assert target == pom_path
    assert dep_id[1] == "jqwik"


def test_apply_dependency_fixes_inserts_dependency(tmp_path: Path) -> None:
    pom_path = tmp_path / "pom.xml"
    write_pom(
        pom_path,
        """<project>
  <modelVersion>4.0.0</modelVersion>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""",
    )

    result = apply_dependency_fixes(tmp_path, base_config(jqwik_enabled=True), apply=True)
    assert result == 0
    updated = pom_path.read_text(encoding="utf-8")
    assert "<artifactId>jqwik</artifactId>" in updated


def test_apply_dependency_fixes_multi_module(tmp_path: Path) -> None:
    parent_pom = tmp_path / "pom.xml"
    module_dir = tmp_path / "module-a"
    module_dir.mkdir()
    module_pom = module_dir / "pom.xml"

    write_pom(
        parent_pom,
        """<project>
  <modelVersion>4.0.0</modelVersion>
  <packaging>pom</packaging>
  <modules>
    <module>module-a</module>
  </modules>
</project>
""",
    )
    write_pom(
        module_pom,
        """<project>
  <modelVersion>4.0.0</modelVersion>
</project>
""",
    )

    result = apply_dependency_fixes(tmp_path, base_config(jqwik_enabled=True), apply=True)
    assert result == 0
    updated = module_pom.read_text(encoding="utf-8")
    assert "<artifactId>jqwik</artifactId>" in updated


def test_get_java_tool_flags_defaults() -> None:
    flags = get_java_tool_flags({})
    assert flags["jacoco"] is True
    assert flags["checkstyle"] is True
    assert flags["spotbugs"] is True
    assert flags["pmd"] is True
    assert flags["owasp"] is True
    assert flags["pitest"] is True
    assert flags["jqwik"] is False
    assert flags["semgrep"] is False
    assert flags["trivy"] is False
    assert flags["codeql"] is False
    assert flags["docker"] is False


def test_update_parser_accepts_fix_pom() -> None:
    parser = build_parser()
    args = parser.parse_args(["update", "--repo", ".", "--fix-pom"])
    assert args.fix_pom is True
