from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import defusedxml.ElementTree as ET  # Secure XML parsing (prevents XXE)

from cihub import __version__
from cihub.config.io import load_yaml_file
from cihub.config.merge import deep_merge
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS

GIT_REMOTE_RE = re.compile(r"(?:github\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")

JAVA_TOOL_PLUGINS = {
    "jacoco": ("org.jacoco", "jacoco-maven-plugin"),
    "checkstyle": ("org.apache.maven.plugins", "maven-checkstyle-plugin"),
    "spotbugs": ("com.github.spotbugs", "spotbugs-maven-plugin"),
    "pmd": ("org.apache.maven.plugins", "maven-pmd-plugin"),
    "owasp": ("org.owasp", "dependency-check-maven"),
    "pitest": ("org.pitest", "pitest-maven"),
}

JAVA_TOOL_DEPENDENCIES = {
    "jqwik": ("net.jqwik", "jqwik"),
}


@dataclass
class CommandResult:
    """Structured command result for JSON output."""

    exit_code: int = 0
    summary: str = ""
    problems: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    files_generated: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_payload(self, command: str, status: str, duration_ms: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "command": command,
            "status": status,
            "exit_code": self.exit_code,
            "duration_ms": duration_ms,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "problems": self.problems,
            "suggestions": self.suggestions,
            "files_generated": self.files_generated,
            "files_modified": self.files_modified,
        }
        if self.data:
            payload["data"] = self.data
        return payload


def hub_root() -> Path:
    return Path(__file__).resolve().parents[1]


def write_text(path: Path, content: str, dry_run: bool, emit: bool = True) -> None:
    if dry_run:
        if emit:
            print(f"# Would write: {path}")
            print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def detect_language(repo_path: Path) -> tuple[str | None, list[str]]:
    checks = {
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "python": ["pyproject.toml", "requirements.txt", "setup.py"],
    }
    matches: dict[str, list[str]] = {"java": [], "python": []}
    for language, files in checks.items():
        for name in files:
            if (repo_path / name).exists():
                matches[language].append(name)

    java_found = bool(matches["java"])
    python_found = bool(matches["python"])

    if java_found and not python_found:
        return "java", matches["java"]
    if python_found and not java_found:
        return "python", matches["python"]
    if java_found and python_found:
        return None, matches["java"] + matches["python"]
    return None, []


def load_effective_config(repo_path: Path) -> dict[str, Any]:
    defaults_path = hub_root() / "config" / "defaults.yaml"
    defaults = load_yaml_file(defaults_path)
    local_path = repo_path / ".ci-hub.yml"
    local_config = load_yaml_file(local_path)
    merged = deep_merge(defaults, local_config)
    repo_info = merged.get("repo", {})
    if repo_info.get("language"):
        merged["language"] = repo_info["language"]
    return merged


def get_java_tool_flags(config: dict[str, Any]) -> dict[str, bool]:
    """Get enabled status for Java tools per ADR-0017 defaults."""
    tools = config.get("java", {}).get("tools", {})
    # Defaults per ADR-0017: Core tools enabled, expensive tools disabled
    defaults = {
        "jacoco": True,
        "checkstyle": True,
        "spotbugs": True,
        "pmd": True,
        "owasp": True,
        "pitest": True,
        "jqwik": False,  # opt-in
        "semgrep": False,  # expensive
        "trivy": False,  # expensive
        "codeql": False,  # expensive
        "docker": False,  # requires Dockerfile
    }
    enabled: dict[str, bool] = {}
    for tool, default in defaults.items():
        enabled[tool] = tools.get(tool, {}).get("enabled", default)
    return enabled


def get_xml_namespace(root: ET.Element) -> str:
    tag = root.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}")[0][1:]
    return ""


def ns_tag(namespace: str, tag: str) -> str:
    if not namespace:
        return tag
    return f"{{{namespace}}}{tag}"


def elem_text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    text = elem.text
    if not isinstance(text, str):
        return ""
    return text.strip()


def resolve_executable(name: str) -> str:
    return shutil.which(name) or name


def validate_repo_path(repo_path: Path) -> Path:
    """Validate and canonicalize a repository path.

    Prevents path traversal attacks and ensures the path is a valid directory.

    Args:
        repo_path: The path to validate.

    Returns:
        The canonicalized path.

    Raises:
        ValueError: If the path is invalid or not a directory.
    """
    # Resolve to absolute path (handles symlinks)
    resolved = repo_path.resolve()

    # Ensure it's a directory
    if not resolved.is_dir():
        raise ValueError(f"Repository path is not a valid directory: {repo_path}")

    return resolved


def validate_subdir(subdir: str) -> str:
    """Validate a subdirectory path to prevent path traversal.

    Args:
        subdir: The subdirectory path to validate.

    Returns:
        The validated subdirectory path.

    Raises:
        ValueError: If the path contains traversal sequences.
    """
    if not subdir:
        return subdir

    # Normalize the path
    normalized = Path(subdir).as_posix()

    # Check for path traversal attempts
    if ".." in normalized.split("/"):
        raise ValueError(f"Invalid subdirectory (path traversal detected): {subdir}")

    # Ensure it's a relative path
    if normalized.startswith("/"):
        raise ValueError(f"Subdirectory must be a relative path: {subdir}")

    return subdir


def parse_xml_text(text: str) -> ET.Element:
    """Parse XML text securely using defusedxml (prevents XXE attacks)."""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("disallowed DTD")
    return ET.fromstring(text)


def parse_xml_file(path: Path) -> ET.Element:
    return parse_xml_text(path.read_text(encoding="utf-8"))


def safe_urlopen(req: urllib.request.Request, timeout: int):
    parsed = urlparse(req.full_url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310


def parse_pom_plugins(
    pom_path: Path,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], bool, str | None]:
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return set(), set(), False, f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)

    def find_child(parent: ET.Element | None, tag: str) -> ET.Element | None:
        if parent is None:
            return None
        return parent.find(ns_tag(namespace, tag))

    def plugin_ids(parent: ET.Element | None) -> set[tuple[str, str]]:
        ids: set[tuple[str, str]] = set()
        if parent is None:
            return ids
        for plugin in parent.findall(ns_tag(namespace, "plugin")):
            group_id = elem_text(plugin.find(ns_tag(namespace, "groupId")))
            artifact_id = elem_text(plugin.find(ns_tag(namespace, "artifactId")))
            if artifact_id:
                ids.add((group_id, artifact_id))
        return ids

    build = find_child(root, "build")
    plugins = plugin_ids(find_child(build, "plugins"))

    plugin_mgmt = find_child(build, "pluginManagement")
    plugins_mgmt = plugin_ids(find_child(plugin_mgmt, "plugins"))

    has_modules = find_child(root, "modules") is not None
    return plugins, plugins_mgmt, has_modules, None


def parse_pom_modules(pom_path: Path) -> tuple[list[str], str | None]:
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return [], f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)
    modules_elem = root.find(ns_tag(namespace, "modules"))
    modules: list[str] = []
    if modules_elem is None:
        return modules, None
    for module in modules_elem.findall(ns_tag(namespace, "module")):
        if module.text:
            modules.append(module.text.strip())
    return modules, None


def parse_pom_dependencies(
    pom_path: Path,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], str | None]:
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return set(), set(), f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)

    def deps_from(parent: ET.Element | None) -> set[tuple[str, str]]:
        deps: set[tuple[str, str]] = set()
        if parent is None:
            return deps
        for dep in parent.findall(ns_tag(namespace, "dependency")):
            group_id = elem_text(dep.find(ns_tag(namespace, "groupId")))
            artifact_id = elem_text(dep.find(ns_tag(namespace, "artifactId")))
            if artifact_id:
                deps.add((group_id, artifact_id))
        return deps

    deps = deps_from(root.find(ns_tag(namespace, "dependencies")))
    dep_mgmt = root.find(ns_tag(namespace, "dependencyManagement"))
    deps_mgmt = set()
    if dep_mgmt is not None:
        deps_mgmt = deps_from(dep_mgmt.find(ns_tag(namespace, "dependencies")))
    return deps, deps_mgmt, None


def plugin_matches(plugins: set[tuple[str, str]], group_id: str, artifact_id: str) -> bool:
    for group, artifact in plugins:
        if artifact != artifact_id:
            continue
        if not group or group == group_id:
            return True
    return False


def collect_java_pom_warnings(repo_path: Path, config: dict[str, Any]) -> tuple[list[str], list[tuple[str, str]]]:
    warnings: list[str] = []
    missing_plugins: list[tuple[str, str]] = []

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        warnings.append("pom.xml not found")
        return warnings, missing_plugins

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
        return warnings, missing_plugins

    plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom_path)
    if error:
        warnings.append(error)
        return warnings, missing_plugins

    tool_flags = get_java_tool_flags(config)
    checkstyle_config = config.get("java", {}).get("tools", {}).get("checkstyle", {}).get("config_file")
    if checkstyle_config:
        config_path = repo_path / checkstyle_config
        if not config_path.exists():
            alt_path = root_path / checkstyle_config
            if not alt_path.exists():
                warnings.append(f"checkstyle config file not found: {checkstyle_config}")
    for tool, enabled in tool_flags.items():
        if tool not in JAVA_TOOL_PLUGINS or not enabled:
            continue
        group_id, artifact_id = JAVA_TOOL_PLUGINS[tool]
        if plugin_matches(plugins, group_id, artifact_id):
            continue
        if plugin_matches(plugins_mgmt, group_id, artifact_id):
            warnings.append(f"pom.xml: {tool} plugin is only in <pluginManagement>; move to <build><plugins>")
        else:
            warnings.append(f"pom.xml: missing plugin for enabled tool '{tool}' ({group_id}:{artifact_id})")
        missing_plugins.append((group_id, artifact_id))

    if has_modules and missing_plugins:
        warnings.append("pom.xml: multi-module project detected; add plugins to parent <build><plugins>")

    return warnings, missing_plugins


def dependency_matches(dependencies: set[tuple[str, str]], group_id: str, artifact_id: str) -> bool:
    for group, artifact in dependencies:
        if artifact != artifact_id:
            continue
        if not group or group == group_id:
            return True
    return False


def collect_java_dependency_warnings(
    repo_path: Path, config: dict[str, Any]
) -> tuple[list[str], list[tuple[Path, tuple[str, str]]]]:
    warnings: list[str] = []
    missing: list[tuple[Path, tuple[str, str]]] = []

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        return warnings, missing

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
        return warnings, missing

    modules, error = parse_pom_modules(pom_path)
    if error:
        warnings.append(error)
        return warnings, missing

    targets: list[Path] = []
    if modules:
        for module in modules:
            module_pom = root_path / module / "pom.xml"
            if module_pom.exists():
                targets.append(module_pom)
            else:
                warnings.append(f"pom.xml not found for module: {module}")
    else:
        targets.append(pom_path)

    tool_flags = get_java_tool_flags(config)
    for tool, dep in JAVA_TOOL_DEPENDENCIES.items():
        if not tool_flags.get(tool, False):
            continue
        group_id, artifact_id = dep
        for target in targets:
            deps, deps_mgmt, error = parse_pom_dependencies(target)
            if error:
                warnings.append(f"{target}: {error}")
                continue
            if dependency_matches(deps, group_id, artifact_id):
                continue
            if dependency_matches(deps_mgmt, group_id, artifact_id):
                warnings.append(f"{target}: {tool} dependency only in <dependencyManagement>; add to <dependencies>")
            else:
                warnings.append(f"{target}: missing dependency for enabled tool '{tool}' ({group_id}:{artifact_id})")
            missing.append((target, (group_id, artifact_id)))

    return warnings, missing


def load_plugin_snippets() -> dict[tuple[str, str], str]:
    snippets_path = hub_root() / "templates" / "java" / "pom-plugins.xml"
    content = snippets_path.read_text(encoding="utf-8")
    blocks = re.findall(r"<plugin>.*?</plugin>", content, flags=re.DOTALL)
    snippets: dict[tuple[str, str], str] = {}
    for block in blocks:
        try:
            elem = parse_xml_text(block)
        except (ET.ParseError, ValueError):
            continue
        group_id = elem_text(elem.find("groupId"))
        artifact_id = elem_text(elem.find("artifactId"))
        if artifact_id:
            snippets[(group_id, artifact_id)] = block.strip()
    return snippets


def load_dependency_snippets() -> dict[tuple[str, str], str]:
    snippets_path = hub_root() / "templates" / "java" / "pom-dependencies.xml"
    content = snippets_path.read_text(encoding="utf-8")
    blocks = re.findall(r"<dependency>.*?</dependency>", content, flags=re.DOTALL)
    snippets: dict[tuple[str, str], str] = {}
    for block in blocks:
        try:
            elem = parse_xml_text(block)
        except (ET.ParseError, ValueError):
            continue
        group_id = elem_text(elem.find("groupId"))
        artifact_id = elem_text(elem.find("artifactId"))
        if artifact_id:
            snippets[(group_id, artifact_id)] = block.strip()
    return snippets


def line_indent(text: str, index: int) -> str:
    line_start = text.rfind("\n", 0, index) + 1
    match = re.match(r"[ \t]*", text[line_start:])
    return match.group(0) if match else ""


def indent_block(block: str, indent: str) -> str:
    block = textwrap.dedent(block).strip("\n")
    lines = block.splitlines()
    return "\n".join((indent + line) if line.strip() else line for line in lines)


def insert_plugins_into_pom(pom_text: str, plugin_block: str) -> tuple[str, bool]:
    build_match = re.search(r"<build[^>]*>", pom_text)
    if build_match:
        build_close = pom_text.find("</build>", build_match.end())
        if build_close == -1:
            return pom_text, False
        build_section = pom_text[build_match.end() : build_close]
        plugins_match = re.search(r"<plugins[^>]*>", build_section)
        if plugins_match:
            plugins_close = build_section.find("</plugins>", plugins_match.end())
            if plugins_close == -1:
                return pom_text, False
            plugins_index = build_match.end() + plugins_match.start()
            plugins_indent = line_indent(pom_text, plugins_index)
            plugin_indent = plugins_indent + "  "
            block = indent_block(plugin_block, plugin_indent)
            insert_at = build_match.end() + plugins_close
            insert_text = f"\n{block}\n{plugins_indent}"
            return pom_text[:insert_at] + insert_text + pom_text[insert_at:], True

        build_indent = line_indent(pom_text, build_match.start())
        plugins_indent = build_indent + "  "
        plugin_indent = plugins_indent + "  "
        block = indent_block(plugin_block, plugin_indent)
        insert_at = build_close
        plugins_block = f"\n{plugins_indent}<plugins>\n{block}\n{plugins_indent}</plugins>\n{build_indent}"
        return pom_text[:insert_at] + plugins_block + pom_text[insert_at:], True

    project_close = pom_text.find("</project>")
    if project_close == -1:
        return pom_text, False
    project_indent = line_indent(pom_text, project_close)
    build_indent = project_indent + "  "
    plugins_indent = build_indent + "  "
    plugin_indent = plugins_indent + "  "
    block = indent_block(plugin_block, plugin_indent)
    build_block = (
        f"\n{build_indent}<build>\n{plugins_indent}<plugins>\n{block}\n"
        f"{plugins_indent}</plugins>\n{build_indent}</build>\n{project_indent}"
    )
    return pom_text[:project_close] + build_block + pom_text[project_close:], True


def find_tag_spans(text: str, tag: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in re.finditer(rf"<{tag}[^>]*>", text):
        close = text.find(f"</{tag}>", match.end())
        if close == -1:
            continue
        spans.append((match.start(), close + len(f"</{tag}>")))
    return spans


def insert_dependencies_into_pom(pom_text: str, dependency_block: str) -> tuple[str, bool]:
    dep_mgmt_spans = find_tag_spans(pom_text, "dependencyManagement")
    build_spans = find_tag_spans(pom_text, "build")

    def in_spans(index: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= index < end for start, end in spans)

    for match in re.finditer(r"<dependencies[^>]*>", pom_text):
        if in_spans(match.start(), dep_mgmt_spans) or in_spans(match.start(), build_spans):
            continue
        deps_close = pom_text.find("</dependencies>", match.end())
        if deps_close == -1:
            return pom_text, False
        deps_indent = line_indent(pom_text, match.start())
        dep_indent = deps_indent + "  "
        block = indent_block(dependency_block, dep_indent)
        insert_at = deps_close
        insert_text = f"\n{block}\n{deps_indent}"
        return pom_text[:insert_at] + insert_text + pom_text[insert_at:], True

    project_close = pom_text.find("</project>")
    if project_close == -1:
        return pom_text, False
    project_indent = line_indent(pom_text, project_close)
    deps_indent = project_indent + "  "
    dep_indent = deps_indent + "  "
    block = indent_block(dependency_block, dep_indent)
    deps_block = f"\n{deps_indent}<dependencies>\n{block}\n{deps_indent}</dependencies>\n{project_indent}"
    return pom_text[:project_close] + deps_block + pom_text[project_close:], True


def parse_repo_from_remote(url: str) -> tuple[str | None, str | None]:
    match = GIT_REMOTE_RE.search(url)
    if not match:
        return None, None
    return match.group("owner"), match.group("repo")


def get_git_remote(repo_path: Path) -> str | None:
    try:
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [
                git_bin,
                "-C",
                str(validated_path),
                "config",
                "--get",
                "remote.origin.url",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        )  # noqa: S603
        return output.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def get_git_branch(repo_path: Path) -> str | None:
    try:
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [git_bin, "-C", str(validated_path), "symbolic-ref", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )  # noqa: S603
        return output.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def build_repo_config(
    language: str,
    owner: str,
    name: str,
    branch: str,
    subdir: str | None = None,
) -> dict[str, Any]:
    template_path = hub_root() / "templates" / "repo" / ".ci-hub.yml"
    base = load_yaml_file(template_path)

    repo_block = base.get("repo", {}) if isinstance(base.get("repo"), dict) else {}
    repo_block["owner"] = owner
    repo_block["name"] = name
    repo_block["language"] = language
    repo_block["default_branch"] = branch
    repo_block.setdefault("dispatch_workflow", "hub-ci.yml")
    if subdir:
        repo_block["subdir"] = subdir
    base["repo"] = repo_block

    base["language"] = language

    if language == "java":
        base.pop("python", None)
    elif language == "python":
        base.pop("java", None)

    base.setdefault("version", "1.0")
    return base


def render_caller_workflow(language: str) -> str:
    templates_dir = hub_root() / "templates" / "repo"
    if language == "java":
        template_path = templates_dir / "hub-java-ci.yml"
        replacement = "hub-java-ci.yml"
    else:
        template_path = templates_dir / "hub-python-ci.yml"
        replacement = "hub-python-ci.yml"

    content = template_path.read_text(encoding="utf-8")
    content = content.replace(replacement, "hub-ci.yml")
    header = "# Generated by cihub init - DO NOT EDIT\n"
    return header + content


def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    detected, reasons = detect_language(repo_path)
    if not detected:
        reason_text = ", ".join(reasons) if reasons else "no language markers found"
        raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
    return detected, reasons


def cmd_detect(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.detect import cmd_detect as handler

    return handler(args)


def cmd_preflight(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.preflight import cmd_preflight as handler

    return handler(args)


def cmd_scaffold(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.scaffold import cmd_scaffold as handler

    return handler(args)


def cmd_smoke(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.smoke import cmd_smoke as handler

    return handler(args)


def cmd_check(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.check import cmd_check as handler

    return handler(args)


def cmd_ci(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.ci import cmd_ci as handler

    return handler(args)


def cmd_run(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.run import cmd_run as handler

    return handler(args)


def cmd_report(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.report import cmd_report as handler

    return handler(args)


def cmd_docs(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs as handler

    return handler(args)


def cmd_docs_links(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.docs import cmd_docs_links as handler

    return handler(args)


def cmd_adr(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.adr import cmd_adr as handler

    return handler(args)


def cmd_init(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.init import cmd_init as handler

    return handler(args)


def cmd_update(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.update import cmd_update as handler

    return handler(args)


def cmd_validate(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.validate import cmd_validate as handler

    return handler(args)


def apply_pom_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> int:
    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        print("pom.xml not found", file=sys.stderr)
        return EXIT_FAILURE

    warnings, missing_plugins = collect_java_pom_warnings(repo_path, config)
    if warnings:
        print("POM warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if not missing_plugins:
        print("No pom.xml changes needed.")
        return EXIT_SUCCESS

    snippets = load_plugin_snippets()
    blocks = []
    for plugin_id in missing_plugins:
        snippet = snippets.get(plugin_id)
        if snippet:
            blocks.append(snippet)
        else:
            group_id, artifact_id = plugin_id
            warnings.append(f"Missing snippet for plugin {group_id}:{artifact_id}")
    if not blocks:
        for warning in warnings:
            print(f"  - {warning}")
        return EXIT_FAILURE

    pom_text = pom_path.read_text(encoding="utf-8")
    plugin_block = "\n\n".join(blocks)
    updated_text, inserted = insert_plugins_into_pom(pom_text, plugin_block)
    if not inserted:
        print(
            "Failed to update pom.xml - unable to find insertion point.",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    if not apply:
        import difflib

        diff = difflib.unified_diff(
            pom_text.splitlines(),
            updated_text.splitlines(),
            fromfile=str(pom_path),
            tofile=str(pom_path),
            lineterm="",
        )
        print("\n".join(diff))
        return EXIT_SUCCESS

    pom_path.write_text(updated_text, encoding="utf-8")
    print("pom.xml updated.")
    return EXIT_SUCCESS


def apply_dependency_fixes(repo_path: Path, config: dict[str, Any], apply: bool) -> int:
    warnings, missing = collect_java_dependency_warnings(repo_path, config)
    if warnings:
        print("Dependency warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not missing:
        print("No dependency changes needed.")
        return EXIT_SUCCESS

    snippets = load_dependency_snippets()
    per_pom: dict[Path, list[str]] = {}
    for pom_path, dep_id in missing:
        snippet = snippets.get(dep_id)
        if not snippet:
            group_id, artifact_id = dep_id
            print(f"Missing snippet for dependency {group_id}:{artifact_id}")
            continue
        per_pom.setdefault(pom_path, []).append(snippet)

    if not per_pom:
        return EXIT_FAILURE

    for pom_path, blocks in per_pom.items():
        pom_text = pom_path.read_text(encoding="utf-8")
        dep_block = "\n\n".join(blocks)
        updated_text, inserted = insert_dependencies_into_pom(pom_text, dep_block)
        if not inserted:
            print(f"Failed to update {pom_path} - unable to find insertion point.")
            return EXIT_FAILURE
        if not apply:
            import difflib

            diff = difflib.unified_diff(
                pom_text.splitlines(),
                updated_text.splitlines(),
                fromfile=str(pom_path),
                tofile=str(pom_path),
                lineterm="",
            )
            print("\n".join(diff))
        else:
            pom_path.write_text(updated_text, encoding="utf-8")
            print(f"{pom_path} updated.")
    return EXIT_SUCCESS


def cmd_fix_pom(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_pom as handler

    return handler(args)


def cmd_fix_deps(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.pom import cmd_fix_deps as handler

    return handler(args)


def get_connected_repos(
    only_dispatch_enabled: bool = True,
    language_filter: str | None = None,
) -> list[str]:
    """Get unique repos from hub config/repos/*.yaml.

    Args:
        only_dispatch_enabled: If True, skip repos with dispatch_enabled=False
        language_filter: If set, only return repos with this language (java/python)
    """
    repos_dir = hub_root() / "config" / "repos"
    seen: set[str] = set()
    repos: list[str] = []
    for cfg_file in repos_dir.glob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            if language_filter:
                repo_lang = repo.get("language", "")
                if repo_lang != language_filter:
                    continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if owner and name:
                full = f"{owner}/{name}"
                if full not in seen:
                    seen.add(full)
                    repos.append(full)
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
    return repos


def get_repo_entries(
    only_dispatch_enabled: bool = True,
) -> list[dict[str, str]]:
    """Return repo metadata from config/repos/*.yaml."""
    repos_dir = hub_root() / "config" / "repos"
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for cfg_file in repos_dir.glob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if not owner or not name:
                continue
            full = f"{owner}/{name}"
            dispatch_workflow = repo.get("dispatch_workflow") or "hub-ci.yml"
            # Deduplicate by (repo, dispatch_workflow) to allow syncing
            # multiple workflow files for repos with both Java and Python configs
            key = f"{full}:{dispatch_workflow}"
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "full": full,
                    "language": repo.get("language", ""),
                    "dispatch_workflow": dispatch_workflow,
                    "default_branch": repo.get("default_branch", "main"),
                }
            )
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
            continue
    return entries


def render_dispatch_workflow(language: str, dispatch_workflow: str) -> str:
    templates_dir = hub_root() / "templates" / "repo"
    if dispatch_workflow == "hub-ci.yml":
        if not language:
            raise ValueError("language is required for hub-ci.yml rendering")
        return render_caller_workflow(language)
    if dispatch_workflow == "hub-java-ci.yml":
        return (templates_dir / "hub-java-ci.yml").read_text(encoding="utf-8")
    if dispatch_workflow == "hub-python-ci.yml":
        return (templates_dir / "hub-python-ci.yml").read_text(encoding="utf-8")
    raise ValueError(f"Unsupported dispatch_workflow: {dispatch_workflow}")


def gh_api_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "api"]
    if method != "GET":
        cmd += ["-X", method]
    cmd.append(path)
    input_data = None
    if payload is not None:
        cmd += ["--input", "-"]
        input_data = json.dumps(payload)
    result = subprocess.run(  # noqa: S603
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
    )  # noqa: S603
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg or "gh api failed")
    if not result.stdout.strip():
        return {}
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("gh api returned non-object JSON")
    return data


def fetch_remote_file(repo: str, path: str, branch: str) -> dict[str, str] | None:
    api_path = f"/repos/{repo}/contents/{path}?ref={branch}"
    try:
        data = gh_api_json(api_path)
    except RuntimeError as exc:
        msg = str(exc)
        if "Not Found" in msg or "404" in msg:
            return None
        raise
    if "content" not in data or "sha" not in data:
        return None
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"sha": data["sha"], "content": content}


def update_remote_file(
    repo: str,
    path: str,
    branch: str,
    content: str,
    message: str,
    sha: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    gh_api_json(f"/repos/{repo}/contents/{path}", method="PUT", payload=payload)


def delete_remote_file(
    repo: str,
    path: str,
    branch: str,
    sha: str,
    message: str,
) -> None:
    """Delete a file from a GitHub repo via the GitHub API."""
    payload: dict[str, Any] = {
        "message": message,
        "sha": sha,
        "branch": branch,
    }
    gh_api_json(f"/repos/{repo}/contents/{path}", method="DELETE", payload=payload)


def cmd_setup_secrets(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.secrets import cmd_setup_secrets as handler

    return handler(args)


def cmd_setup_nvd(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.secrets import cmd_setup_nvd as handler

    return handler(args)


def cmd_sync_templates(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.templates import cmd_sync_templates as handler

    return handler(args)


def cmd_new(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.new import cmd_new as handler

    return handler(args)


def cmd_config(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.config_cmd import cmd_config as handler

    return handler(args)


def cmd_config_outputs(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.config_outputs import cmd_config_outputs as handler

    return handler(args)


def cmd_hub_ci(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.hub_ci import cmd_hub_ci as handler

    return handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cihub", description="CI/CD Hub CLI")
    parser.add_argument("--version", action="version", version=f"cihub {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--json",
            action="store_true",
            help="Output machine-readable JSON",
        )

    detect = subparsers.add_parser("detect", help="Detect repo language and tools")
    add_json_flag(detect)
    detect.add_argument("--repo", required=True, help="Path to repo")
    detect.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    detect.add_argument("--explain", action="store_true", help="Show detection reasons")
    detect.set_defaults(func=cmd_detect)

    preflight = subparsers.add_parser("preflight", help="Check environment readiness")
    add_json_flag(preflight)
    preflight.add_argument(
        "--full",
        action="store_true",
        help="Check optional toolchains and CI runners",
    )
    preflight.set_defaults(func=cmd_preflight)

    doctor = subparsers.add_parser("doctor", help="Alias for preflight")
    add_json_flag(doctor)
    doctor.add_argument(
        "--full",
        action="store_true",
        help="Check optional toolchains and CI runners",
    )
    doctor.set_defaults(func=cmd_preflight)

    scaffold = subparsers.add_parser("scaffold", help="Generate a minimal fixture project")
    add_json_flag(scaffold)
    scaffold.add_argument(
        "type",
        nargs="?",
        help=("Fixture type (python-pyproject, python-setup, java-maven, java-gradle, monorepo)"),
    )
    scaffold.add_argument("path", nargs="?", help="Destination path")
    scaffold.add_argument("--list", action="store_true", help="List available fixture types")
    scaffold.add_argument("--force", action="store_true", help="Overwrite destination if not empty")
    scaffold.set_defaults(func=cmd_scaffold)

    smoke = subparsers.add_parser("smoke", help="Run a local smoke test")
    add_json_flag(smoke)
    smoke.add_argument(
        "repo",
        nargs="?",
        help="Path to repo (omit to scaffold fixtures)",
    )
    smoke.add_argument("--subdir", help="Subdirectory for monorepos")
    smoke.add_argument(
        "--type",
        action="append",
        help=(
            "Fixture type to generate (repeatable): python-pyproject, python-setup, java-maven, java-gradle, monorepo"
        ),
    )
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Generate and test all fixture types",
    )
    smoke.add_argument(
        "--full",
        action="store_true",
        help="Run cihub ci after init/validate",
    )
    smoke.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during cihub ci",
    )
    smoke.add_argument(
        "--force",
        action="store_true",
        help="Allow init to overwrite existing .ci-hub.yml",
    )
    smoke.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds when running full",
    )
    smoke.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    smoke.set_defaults(func=cmd_smoke)

    check = subparsers.add_parser("check", help="Run local validation checks")
    add_json_flag(check)
    check.add_argument(
        "--smoke-repo",
        help="Path to repo for smoke test (omit to scaffold fixtures)",
    )
    check.add_argument(
        "--smoke-subdir",
        help="Subdirectory for monorepo smoke test",
    )
    check.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during smoke test",
    )
    check.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds during smoke test",
    )
    check.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    # Tiered check modes
    check.add_argument(
        "--audit",
        action="store_true",
        help="Add drift detection checks (links, adr, configs)",
    )
    check.add_argument(
        "--security",
        action="store_true",
        help="Add security checks (bandit, pip-audit, trivy, gitleaks)",
    )
    check.add_argument(
        "--full",
        action="store_true",
        help="Add validation checks (templates, matrix, license, zizmor)",
    )
    check.add_argument(
        "--mutation",
        action="store_true",
        help="Add mutation testing with mutmut (~15min, very slow)",
    )
    check.add_argument(
        "--all",
        action="store_true",
        help="Run all checks (audit + security + full + mutation)",
    )
    check.set_defaults(func=cmd_check)

    ci = subparsers.add_parser("ci", help="Run CI based on .ci-hub.yml")
    add_json_flag(ci)
    ci.add_argument("--repo", default=".", help="Path to repo (default: .)")
    ci.add_argument("--workdir", help="Override workdir/subdir")
    ci.add_argument("--correlation-id", help="Hub correlation id")
    ci.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for reports (default: .cihub)",
    )
    ci.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies before running tools",
    )
    ci.add_argument("--report", help="Override report.json path")
    ci.add_argument("--summary", help="Override summary.md path")
    ci.set_defaults(func=cmd_ci)

    run = subparsers.add_parser("run", help="Run one tool and emit JSON output")
    add_json_flag(run)
    run.add_argument("tool", help="Tool name (pytest, ruff, bandit, etc.)")
    run.add_argument("--repo", default=".", help="Path to repo (default: .)")
    run.add_argument("--workdir", help="Override workdir/subdir")
    run.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for tool outputs (default: .cihub)",
    )
    run.add_argument("--output", help="Override tool output path")
    run.add_argument(
        "--force",
        action="store_true",
        help="Run even if tool is disabled in config",
    )
    run.set_defaults(func=cmd_run)

    report = subparsers.add_parser("report", help="Build reports and summaries")
    add_json_flag(report)
    report_sub = report.add_subparsers(dest="subcommand", required=True)

    report_build = report_sub.add_parser("build", help="Build report.json from tool outputs")
    add_json_flag(report_build)
    report_build.add_argument("--repo", default=".", help="Path to repo (default: .)")
    report_build.add_argument("--workdir", help="Override workdir/subdir")
    report_build.add_argument("--correlation-id", help="Hub correlation id")
    report_build.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for reports (default: .cihub)",
    )
    report_build.add_argument(
        "--tool-dir",
        help="Directory containing tool output JSON files",
    )
    report_build.add_argument("--report", help="Override report.json path")
    report_build.add_argument("--summary", help="Override summary.md path")
    report_build.set_defaults(func=cmd_report)

    report_summary = report_sub.add_parser("summary", help="Render summary from report.json")
    add_json_flag(report_summary)
    report_summary.add_argument("--report", required=True, help="Path to report.json")
    report_summary.add_argument("--output", help="Output summary.md path")
    report_summary.add_argument(
        "--write-github-summary",
        action="store_true",
        help="Write to GITHUB_STEP_SUMMARY if set",
    )
    report_summary.set_defaults(func=cmd_report)

    report_outputs = report_sub.add_parser("outputs", help="Write workflow outputs from report.json")
    add_json_flag(report_outputs)
    report_outputs.add_argument("--report", required=True, help="Path to report.json")
    report_outputs.add_argument("--output", help="Path to write outputs (defaults to GITHUB_OUTPUT)")
    report_outputs.set_defaults(func=cmd_report)

    docs = subparsers.add_parser("docs", help="Generate reference documentation")
    docs_sub = docs.add_subparsers(dest="subcommand", required=True)

    docs_generate = docs_sub.add_parser("generate", help="Generate CLI and config reference docs")
    add_json_flag(docs_generate)
    docs_generate.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_generate.add_argument(
        "--check",
        action="store_true",
        help="Fail if docs would change",
    )
    docs_generate.set_defaults(func=cmd_docs)

    docs_check = docs_sub.add_parser("check", help="Check reference docs are up to date")
    add_json_flag(docs_check)
    docs_check.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_check.set_defaults(func=cmd_docs)

    docs_links = docs_sub.add_parser("links", help="Check documentation for broken links")
    add_json_flag(docs_links)
    docs_links.add_argument(
        "--external",
        action="store_true",
        help="Also check external (http/https) links (requires lychee)",
    )
    docs_links.set_defaults(func=cmd_docs_links)

    # ADR (Architecture Decision Records) commands
    adr = subparsers.add_parser("adr", help="Manage Architecture Decision Records")
    adr_sub = adr.add_subparsers(dest="subcommand")
    adr.set_defaults(func=cmd_adr)

    adr_new = adr_sub.add_parser("new", help="Create a new ADR from template")
    add_json_flag(adr_new)
    adr_new.add_argument("title", help="Title for the new ADR")
    adr_new.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing",
    )
    adr_new.set_defaults(func=cmd_adr)

    adr_list = adr_sub.add_parser("list", help="List all ADRs with status")
    add_json_flag(adr_list)
    adr_list.add_argument(
        "--status",
        help="Filter by status (e.g., accepted, proposed, deprecated)",
    )
    adr_list.set_defaults(func=cmd_adr)

    adr_check = adr_sub.add_parser("check", help="Validate ADRs for broken links and missing fields")
    add_json_flag(adr_check)
    adr_check.set_defaults(func=cmd_adr)

    config_outputs = subparsers.add_parser(
        "config-outputs",
        help="Emit config outputs for GitHub Actions",
    )
    add_json_flag(config_outputs)
    config_outputs.add_argument("--repo", default=".", help="Path to repo (default: .)")
    config_outputs.add_argument("--workdir", help="Override workdir/subdir")
    config_outputs.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )
    config_outputs.set_defaults(func=cmd_config_outputs)

    hub_ci = subparsers.add_parser("hub-ci", help="Hub production CI helpers")
    hub_ci.set_defaults(func=cmd_hub_ci)
    hub_ci_sub = hub_ci.add_subparsers(dest="subcommand", required=True)

    hub_ci_ruff = hub_ci_sub.add_parser("ruff", help="Run ruff and emit issue count")
    hub_ci_ruff.add_argument("--path", default=".", help="Path to lint")
    hub_ci_ruff.add_argument("--force-exclude", action="store_true", help="Force ruff exclude rules")
    hub_ci_ruff.add_argument("--output", help="Write outputs to file")
    hub_ci_ruff.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")

    hub_ci_black = hub_ci_sub.add_parser("black", help="Run black and emit issue count")
    hub_ci_black.add_argument("--path", default=".", help="Path to check")
    hub_ci_black.add_argument("--output", help="Write outputs to file")
    hub_ci_black.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")

    hub_ci_mutmut = hub_ci_sub.add_parser("mutmut", help="Run mutmut and emit summary outputs")
    hub_ci_mutmut.add_argument("--workdir", default=".", help="Workdir to scan")
    hub_ci_mutmut.add_argument("--output-dir", default=".", help="Directory for mutmut logs")
    hub_ci_mutmut.add_argument("--min-score", type=int, default=70, help="Minimum mutation score")
    hub_ci_mutmut.add_argument("--output", help="Write outputs to file")
    hub_ci_mutmut.add_argument("--github-output", action="store_true", help="Write outputs to GITHUB_OUTPUT")
    hub_ci_mutmut.add_argument("--summary", help="Write summary to file")
    hub_ci_mutmut.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_bandit = hub_ci_sub.add_parser("bandit", help="Run bandit and enforce high severity gate")
    hub_ci_bandit.add_argument(
        "--paths",
        nargs="+",
        default=["cihub", "scripts"],
        help="Paths to scan",
    )
    hub_ci_bandit.add_argument("--output", default="bandit.json", help="Bandit JSON output path")
    hub_ci_bandit.add_argument("--severity", default="medium", help="Bandit severity level")
    hub_ci_bandit.add_argument("--confidence", default="medium", help="Bandit confidence level")
    hub_ci_bandit.add_argument("--summary", help="Write summary to file")
    hub_ci_bandit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_pip_audit = hub_ci_sub.add_parser("pip-audit", help="Run pip-audit and enforce vulnerability gate")
    hub_ci_pip_audit.add_argument(
        "--requirements",
        nargs="+",
        default=["requirements/requirements.txt", "requirements/requirements-dev.txt"],
        help="Requirements files",
    )
    hub_ci_pip_audit.add_argument("--output", default="pip-audit.json", help="pip-audit JSON output path")
    hub_ci_pip_audit.add_argument("--summary", help="Write summary to file")
    hub_ci_pip_audit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_zizmor = hub_ci_sub.add_parser("zizmor-check", help="Check zizmor SARIF for high findings")
    hub_ci_zizmor.add_argument("--sarif", default="zizmor.sarif", help="Path to SARIF file")
    hub_ci_zizmor.add_argument("--summary", help="Write summary to file")
    hub_ci_zizmor.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_validate_configs = hub_ci_sub.add_parser("validate-configs", help="Validate hub repo config files")
    hub_ci_validate_configs.add_argument("--configs-dir", help="Directory containing config repos")

    hub_ci_validate_profiles = hub_ci_sub.add_parser("validate-profiles", help="Validate profile YAML files")
    hub_ci_validate_profiles.add_argument("--profiles-dir", help="Directory containing profiles")

    hub_ci_license = hub_ci_sub.add_parser("license-check", help="Run license checks for dependencies")
    hub_ci_license.add_argument("--summary", help="Write summary to file")
    hub_ci_license.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_gitleaks = hub_ci_sub.add_parser("gitleaks-summary", help="Summarize gitleaks results")
    hub_ci_gitleaks.add_argument("--outcome", help="Gitleaks outcome")
    hub_ci_gitleaks.add_argument("--summary", help="Write summary to file")
    hub_ci_gitleaks.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    hub_ci_summary = hub_ci_sub.add_parser("summary", help="Generate hub CI summary")
    hub_ci_summary.add_argument("--summary", help="Write summary to file")
    hub_ci_summary.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )

    _hub_ci_enforce = hub_ci_sub.add_parser("enforce", help="Fail if critical hub checks failed")  # noqa: F841

    new = subparsers.add_parser("new", help="Create hub-side repo config")
    add_json_flag(new)
    new.add_argument("name", help="Repo config name (config/repos/<name>.yaml)")
    new.add_argument("--owner", help="Repo owner (GitHub user/org)")
    new.add_argument(
        "--language",
        choices=["java", "python"],
        help="Repo language",
    )
    new.add_argument("--branch", help="Default branch (e.g., main)")
    new.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    new.add_argument("--profile", help="Apply a profile from templates/profiles")
    new.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    new.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    new.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    new.set_defaults(func=cmd_new)

    init = subparsers.add_parser("init", help="Generate .ci-hub.yml and hub-ci.yml")
    add_json_flag(init)
    init.add_argument("--repo", required=True, help="Path to repo")
    init.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    init.add_argument("--owner", help="Repo owner (GitHub user/org)")
    init.add_argument("--name", help="Repo name")
    init.add_argument("--branch", help="Default branch (e.g., main)")
    init.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    init.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    init.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    init.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    init.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    init.set_defaults(func=cmd_init)

    update = subparsers.add_parser("update", help="Refresh hub-ci.yml and .ci-hub.yml")
    add_json_flag(update)
    update.add_argument("--repo", required=True, help="Path to repo")
    update.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    update.add_argument("--owner", help="Repo owner (GitHub user/org)")
    update.add_argument("--name", help="Repo name")
    update.add_argument("--branch", help="Default branch (e.g., main)")
    update.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    update.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    update.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    update.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    update.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    update.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    update.set_defaults(func=cmd_update)

    validate = subparsers.add_parser(
        "validate",
        help="Validate .ci-hub.yml against schema",
    )
    add_json_flag(validate)
    validate.add_argument("--repo", required=True, help="Path to repo")
    validate.add_argument("--strict", action="store_true", help="Fail if pom.xml warnings are found")
    validate.set_defaults(func=cmd_validate)

    setup_secrets = subparsers.add_parser("setup-secrets", help="Set HUB_DISPATCH_TOKEN on hub and connected repos")
    add_json_flag(setup_secrets)
    setup_secrets.add_argument(
        "--hub-repo",
        default="jguida941/ci-cd-hub",
        help="Hub repository (default: jguida941/ci-cd-hub)",
    )
    setup_secrets.add_argument("--token", help="GitHub PAT (prompts if not provided)")
    setup_secrets.add_argument("--all", action="store_true", help="Also set on all connected repos")
    setup_secrets.add_argument(
        "--verify",
        action="store_true",
        help="Verify token with GitHub API before setting secrets",
    )
    setup_secrets.set_defaults(func=cmd_setup_secrets)

    setup_nvd = subparsers.add_parser("setup-nvd", help="Set NVD_API_KEY on Java repos for OWASP Dependency Check")
    add_json_flag(setup_nvd)
    setup_nvd.add_argument("--nvd-key", help="NVD API key (prompts if not provided)")
    setup_nvd.add_argument(
        "--verify",
        action="store_true",
        help="Verify NVD API key before setting secrets",
    )
    setup_nvd.set_defaults(func=cmd_setup_nvd)

    fix_pom = subparsers.add_parser(
        "fix-pom",
        help="Add missing Maven plugins/dependencies to pom.xml for Java repos",
    )
    add_json_flag(fix_pom)
    fix_pom.add_argument("--repo", required=True, help="Path to repo")
    fix_pom.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_pom.set_defaults(func=cmd_fix_pom)

    fix_deps = subparsers.add_parser("fix-deps", help="Add missing Maven dependencies for Java repos")
    add_json_flag(fix_deps)
    fix_deps.add_argument("--repo", required=True, help="Path to repo")
    fix_deps.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_deps.set_defaults(func=cmd_fix_deps)

    sync_templates = subparsers.add_parser(
        "sync-templates",
        help="Sync caller workflow templates to dispatch-enabled repos",
    )
    add_json_flag(sync_templates)
    sync_templates.add_argument(
        "--repo",
        action="append",
        help="Target repo (owner/name). Repeatable.",
    )
    sync_templates.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include repos with dispatch_enabled=false",
    )
    sync_templates.add_argument(
        "--check",
        action="store_true",
        help="Check for template drift without updating",
    )
    sync_templates.add_argument(
        "--dry-run",
        action="store_true",
        help="Show updates without writing",
    )
    sync_templates.add_argument(
        "--commit-message",
        default="chore: sync hub templates",
        help="Commit message for synced templates",
    )
    sync_templates.add_argument(
        "--update-tag",
        action="store_true",
        default=True,
        help="Update v1 tag to current HEAD (default: true)",
    )
    sync_templates.add_argument(
        "--no-update-tag",
        action="store_false",
        dest="update_tag",
        help="Skip updating v1 tag",
    )
    sync_templates.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (for force-push operations)",
    )
    sync_templates.set_defaults(func=cmd_sync_templates)

    config = subparsers.add_parser(
        "config",
        help="Manage hub-side repo configs (config/repos/*.yaml)",
    )
    add_json_flag(config)
    config.add_argument("--repo", required=True, help="Repo config name")
    config.add_argument(
        "--dry-run",
        action="store_true",
        help="Show updates without writing",
    )
    config_sub = config.add_subparsers(dest="subcommand")
    config.set_defaults(func=cmd_config)

    config_edit = config_sub.add_parser("edit", help="Edit config via wizard")
    add_json_flag(config_edit)
    config_edit.set_defaults(func=cmd_config)

    config_show = config_sub.add_parser("show", help="Show config")
    add_json_flag(config_show)
    config_show.add_argument(
        "--effective",
        action="store_true",
        help="Show merged defaults + repo config",
    )
    config_show.set_defaults(func=cmd_config)

    config_set = config_sub.add_parser("set", help="Set a config value")
    add_json_flag(config_set)
    config_set.add_argument("path", help="Dot path (e.g., repo.use_central_runner)")
    config_set.add_argument("value", help="Value (YAML literal)")
    config_set.set_defaults(func=cmd_config)

    config_enable = config_sub.add_parser("enable", help="Enable a tool")
    add_json_flag(config_enable)
    config_enable.add_argument("tool", help="Tool name (e.g., jacoco)")
    config_enable.set_defaults(func=cmd_config)

    config_disable = config_sub.add_parser("disable", help="Disable a tool")
    add_json_flag(config_disable)
    config_disable.add_argument("tool", help="Tool name (e.g., jacoco)")
    config_disable.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    start = time.perf_counter()
    command = args.command
    subcommand = getattr(args, "subcommand", None)
    if subcommand:
        command = f"{command} {subcommand}"

    try:
        result = args.func(args)
    except Exception as exc:  # noqa: BLE001 - surface in JSON mode
        if getattr(args, "json", False):
            problems = [
                {
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-UNHANDLED",
                }
            ]
            payload = CommandResult(
                exit_code=EXIT_INTERNAL_ERROR,
                summary=str(exc),
                problems=problems,
            ).to_payload(
                command,
                "error",
                int((time.perf_counter() - start) * 1000),
            )
            print(json.dumps(payload, indent=2))
            return EXIT_INTERNAL_ERROR
        raise

    if isinstance(result, CommandResult):
        exit_code = result.exit_code
        command_result = result
    else:
        exit_code = int(result)
        command_result = CommandResult(exit_code=exit_code)

    if not command_result.summary:
        command_result.summary = "OK" if exit_code == EXIT_SUCCESS else "Command failed"

    if getattr(args, "json", False):
        status = "success" if exit_code == EXIT_SUCCESS else "failure"
        payload = command_result.to_payload(
            command,
            status,
            int((time.perf_counter() - start) * 1000),
        )
        print(json.dumps(payload, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
