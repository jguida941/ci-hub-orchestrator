from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft7Validator

from cihub import __version__

GIT_REMOTE_RE = re.compile(
    r"(?:github\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$"
)

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


def hub_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping at top level")
    return data


def write_yaml(path: Path, data: dict[str, Any], dry_run: bool) -> None:
    payload = yaml.safe_dump(
        data, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    if dry_run:
        print(f"# Would write: {path}")
        print(payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"# Would write: {path}")
        print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in base:
        if key in override:
            b, o = base[key], override[key]
            if isinstance(b, dict) and isinstance(o, dict):
                result[key] = deep_merge(b, o)
            else:
                result[key] = o
        else:
            result[key] = base[key]
    for key in override:
        if key not in base:
            result[key] = override[key]
    return result


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
    defaults = read_yaml(defaults_path)
    local_path = repo_path / ".ci-hub.yml"
    local_config = read_yaml(local_path)
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
    if root.tag.startswith("{"):
        return root.tag.split("}")[0][1:]
    return ""


def ns_tag(namespace: str, tag: str) -> str:
    if not namespace:
        return tag
    return f"{{{namespace}}}{tag}"


def elem_text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def resolve_executable(name: str) -> str:
    return shutil.which(name) or name


def parse_xml_text(text: str) -> ET.Element:
    upper = text.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise ValueError("XML contains disallowed DTD/ENTITY declarations.")
    return ET.fromstring(text)  # noqa: S314


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


def plugin_matches(
    plugins: set[tuple[str, str]], group_id: str, artifact_id: str
) -> bool:
    for group, artifact in plugins:
        if artifact != artifact_id:
            continue
        if not group or group == group_id:
            return True
    return False


def collect_java_pom_warnings(
    repo_path: Path, config: dict[str, Any]
) -> tuple[list[str], list[tuple[str, str]]]:
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
    checkstyle_config = (
        config.get("java", {})
        .get("tools", {})
        .get("checkstyle", {})
        .get("config_file")
    )
    if checkstyle_config:
        config_path = repo_path / checkstyle_config
        if not config_path.exists():
            alt_path = root_path / checkstyle_config
            if not alt_path.exists():
                warnings.append(
                    f"checkstyle config file not found: {checkstyle_config}"
                )
    for tool, enabled in tool_flags.items():
        if tool not in JAVA_TOOL_PLUGINS or not enabled:
            continue
        group_id, artifact_id = JAVA_TOOL_PLUGINS[tool]
        if plugin_matches(plugins, group_id, artifact_id):
            continue
        if plugin_matches(plugins_mgmt, group_id, artifact_id):
            warnings.append(
                f"pom.xml: {tool} plugin is only in <pluginManagement>; "
                "move to <build><plugins>"
            )
        else:
            warnings.append(
                f"pom.xml: missing plugin for enabled tool '{tool}' "
                f"({group_id}:{artifact_id})"
            )
        missing_plugins.append((group_id, artifact_id))

    if has_modules and missing_plugins:
        warnings.append(
            "pom.xml: multi-module project detected; add plugins to parent "
            "<build><plugins>"
        )

    return warnings, missing_plugins


def dependency_matches(
    dependencies: set[tuple[str, str]], group_id: str, artifact_id: str
) -> bool:
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
                warnings.append(
                    f"{target}: {tool} dependency only in <dependencyManagement>; "
                    "add to <dependencies>"
                )
            else:
                warnings.append(
                    f"{target}: missing dependency for enabled tool '{tool}' "
                    f"({group_id}:{artifact_id})"
                )
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
        build_section = pom_text[build_match.end():build_close]
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
        plugins_block = (
            f"\n{plugins_indent}<plugins>\n{block}\n{plugins_indent}</plugins>\n{build_indent}"
        )
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


def insert_dependencies_into_pom(
    pom_text: str, dependency_block: str
) -> tuple[str, bool]:
    dep_mgmt_spans = find_tag_spans(pom_text, "dependencyManagement")
    build_spans = find_tag_spans(pom_text, "build")

    def in_spans(index: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= index < end for start, end in spans)

    for match in re.finditer(r"<dependencies[^>]*>", pom_text):
        if in_spans(match.start(), dep_mgmt_spans) or in_spans(
            match.start(), build_spans
        ):
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
    deps_block = (
        f"\n{deps_indent}<dependencies>\n{block}\n{deps_indent}</dependencies>\n"
        f"{project_indent}"
    )
    return pom_text[:project_close] + deps_block + pom_text[project_close:], True


def parse_repo_from_remote(url: str) -> tuple[str | None, str | None]:
    match = GIT_REMOTE_RE.search(url)
    if not match:
        return None, None
    return match.group("owner"), match.group("repo")


def get_git_remote(repo_path: Path) -> str | None:
    try:
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [
                git_bin,
                "-C",
                str(repo_path),
                "config",
                "--get",
                "remote.origin.url",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        )  # noqa: S603
        return output.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_branch(repo_path: Path) -> str | None:
    try:
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [git_bin, "-C", str(repo_path), "symbolic-ref", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )  # noqa: S603
        return output.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_repo_config(
    language: str,
    owner: str,
    name: str,
    branch: str,
    subdir: str | None = None,
) -> dict[str, Any]:
    template_path = hub_root() / "templates" / "repo" / ".ci-hub.yml"
    base = read_yaml(template_path)

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


def validate_config(config: dict[str, Any]) -> list[str]:
    schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = []
    for err in validator.iter_errors(config):
        path = ".".join([str(p) for p in err.path]) or "<root>"
        errors.append(f"{path}: {err.message}")
    return sorted(errors)


def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
    if override:
        return override, []
    detected, reasons = detect_language(repo_path)
    if not detected:
        reason_text = ", ".join(reasons) if reasons else "no language markers found"
        raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
    return detected, reasons


def cmd_detect(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    language, reasons = resolve_language(repo_path, args.language)
    payload: dict[str, Any] = {"language": language}
    if args.explain:
        payload["reasons"] = reasons
    print(json.dumps(payload, indent=2))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    language, _ = resolve_language(repo_path, args.language)

    owner = args.owner or ""
    name = args.name or ""
    if not owner or not name:
        remote = get_git_remote(repo_path)
        if remote:
            git_owner, git_name = parse_repo_from_remote(remote)
            owner = owner or (git_owner or "")
            name = name or (git_name or "")

    if not name:
        name = repo_path.name
    if not owner:
        owner = "unknown"
        print(
            "Warning: could not detect repo owner; set repo.owner manually.",
            file=sys.stderr,
        )

    branch = args.branch or get_git_branch(repo_path) or "main"

    subdir = args.subdir or ""
    config = build_repo_config(language, owner, name, branch, subdir=subdir)
    config_path = repo_path / ".ci-hub.yml"
    write_yaml(config_path, config, args.dry_run)

    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, args.dry_run)

    if language == "java" and not args.dry_run:
        effective = load_effective_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            print("POM warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            if args.fix_pom:
                status = apply_pom_fixes(repo_path, effective, apply=True)
                status = max(
                    status, apply_dependency_fixes(repo_path, effective, apply=True)
                )
                return status
            print("Run: cihub fix-pom --repo . --apply")

    return 0


def cmd_update(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    existing = read_yaml(config_path) if config_path.exists() else {}

    language = args.language or existing.get("language")
    if not language:
        language, _ = resolve_language(repo_path, None)

    owner = args.owner or existing.get("repo", {}).get("owner", "")
    name = args.name or existing.get("repo", {}).get("name", "")
    repo_existing = (
        existing.get("repo", {}) if isinstance(existing.get("repo"), dict) else {}
    )
    branch = args.branch or repo_existing.get("default_branch", "main")
    subdir = args.subdir or repo_existing.get("subdir")

    if not name:
        name = repo_path.name
    if not owner:
        owner = "unknown"
        print(
            "Warning: could not detect repo owner; set repo.owner manually.",
            file=sys.stderr,
        )

    base = build_repo_config(language, owner, name, branch, subdir=subdir)
    merged = deep_merge(base, existing)
    write_yaml(config_path, merged, args.dry_run)

    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, args.dry_run)

    if language == "java" and not args.dry_run:
        effective = load_effective_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            print("POM warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            if args.fix_pom:
                apply_pom_fixes(repo_path, effective, apply=True)
                apply_dependency_fixes(repo_path, effective, apply=True)
            else:
                print("Run: cihub fix-pom --repo . --apply")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = read_yaml(config_path)
    errors = validate_config(config)
    if errors:
        print("Validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Config OK")
    effective = load_effective_config(repo_path)
    if effective.get("language") == "java":
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            print("POM warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            if args.strict:
                return 1
        else:
            print("POM OK")
    return 0


def apply_pom_fixes(
    repo_path: Path, config: dict[str, Any], apply: bool
) -> int:
    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        print("pom.xml not found", file=sys.stderr)
        return 1

    warnings, missing_plugins = collect_java_pom_warnings(repo_path, config)
    if warnings:
        print("POM warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if not missing_plugins:
        print("No pom.xml changes needed.")
        return 0

    snippets = load_plugin_snippets()
    blocks = []
    for plugin_id in missing_plugins:
        snippet = snippets.get(plugin_id)
        if snippet:
            blocks.append(snippet)
        else:
            group_id, artifact_id = plugin_id
            warnings.append(
                f"Missing snippet for plugin {group_id}:{artifact_id}"
            )
    if not blocks:
        for warning in warnings:
            print(f"  - {warning}")
        return 1

    pom_text = pom_path.read_text(encoding="utf-8")
    plugin_block = "\n\n".join(blocks)
    updated_text, inserted = insert_plugins_into_pom(pom_text, plugin_block)
    if not inserted:
        print(
            "Failed to update pom.xml - unable to find insertion point.",
            file=sys.stderr,
        )
        return 1

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
        return 0

    pom_path.write_text(updated_text, encoding="utf-8")
    print("pom.xml updated.")
    return 0


def apply_dependency_fixes(
    repo_path: Path, config: dict[str, Any], apply: bool
) -> int:
    warnings, missing = collect_java_dependency_warnings(repo_path, config)
    if warnings:
        print("Dependency warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not missing:
        print("No dependency changes needed.")
        return 0

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
        return 1

    for pom_path, blocks in per_pom.items():
        pom_text = pom_path.read_text(encoding="utf-8")
        dep_block = "\n\n".join(blocks)
        updated_text, inserted = insert_dependencies_into_pom(pom_text, dep_block)
        if not inserted:
            print(f"Failed to update {pom_path} - unable to find insertion point.")
            return 1
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
    return 0


def cmd_fix_pom(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        print("fix-pom is only supported for Java repos.")
        return 0
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        print("fix-pom only supports Maven repos.")
        return 0
    status = apply_pom_fixes(repo_path, config, apply=args.apply)
    status = max(status, apply_dependency_fixes(repo_path, config, apply=args.apply))
    return status


def cmd_fix_deps(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        print("fix-deps is only supported for Java repos.")
        return 0
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        print("fix-deps only supports Maven repos.")
        return 0
    return apply_dependency_fixes(repo_path, config, apply=args.apply)


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
            data = read_yaml(cfg_file)
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
            data = read_yaml(cfg_file)
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


def gh_api_json(
    path: str, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any]:
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
    return json.loads(result.stdout)


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


def cmd_setup_secrets(args: argparse.Namespace) -> int:
    """Set HUB_DISPATCH_TOKEN on hub and optionally all connected repos."""
    import getpass

    hub_repo = args.hub_repo
    token = args.token

    if not token:
        token = getpass.getpass("Enter GitHub PAT: ")

    token = token.strip()

    if not token:
        print("Error: No token provided", file=sys.stderr)
        return 1

    if any(ch.isspace() for ch in token):
        print(
            "Error: Token contains whitespace; paste the raw token value.",
            file=sys.stderr,
        )
        return 1

    def verify_token(pat: str) -> tuple[bool, str]:
        req = urllib.request.Request(  # noqa: S310
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                scopes = resp.headers.get("X-OAuth-Scopes", "")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return False, "unauthorized (token invalid or expired)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)

        login = data.get("login", "unknown")
        scope_msg = f"scopes: {scopes}" if scopes else "scopes: (not reported)"
        return True, f"user {login} ({scope_msg})"

    def verify_cross_repo_access(pat: str, target_repo: str) -> tuple[bool, str]:
        """Verify token can access another repo's artifacts.

        Required for orchestrator downloads.
        """
        req = urllib.request.Request(  # noqa: S310
            f"https://api.github.com/repos/{target_repo}/actions/artifacts",
            headers={
                "Authorization": f"token {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                count = data.get("total_count", 0)
                return True, f"{count} artifacts accessible"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False, f"repo not found or no access: {target_repo}"
            if exc.code == 401:
                return False, "token cannot access this repo (needs 'repo' scope)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)

    if args.verify:
        ok, message = verify_token(token)
        if not ok:
            print(f"Token verification failed: {message}", file=sys.stderr)
            return 1
        print(f"Token verified: {message}")

        # Also verify cross-repo access on connected repos
        connected = get_connected_repos()
        if connected:
            test_repo = connected[0]
            ok, message = verify_cross_repo_access(token, test_repo)
            if not ok:
                print(
                    f"Cross-repo access failed for {test_repo}: {message}",
                    file=sys.stderr,
                )
                print(
                    "The token needs 'repo' scope to access other repos' artifacts.",
                    file=sys.stderr,
                )
                return 1
            print(f"Cross-repo access verified: {test_repo} ({message})")

    gh_bin = resolve_executable("gh")

    def set_secret(repo: str) -> tuple[bool, str]:
        result = subprocess.run(  # noqa: S603
            [gh_bin, "secret", "set", "HUB_DISPATCH_TOKEN", "-R", repo],
            input=token,
            capture_output=True,
            text=True,
        )  # noqa: S603
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""

    # Set on hub repo
    print(f"Setting HUB_DISPATCH_TOKEN on {hub_repo}...")
    ok, error = set_secret(hub_repo)
    if not ok:
        print(f"Failed: {error}", file=sys.stderr)
        return 1
    print(f"  ✅ {hub_repo}")

    if args.all:
        print("\nSetting on connected repos...")
        repos = get_connected_repos()
        for repo in repos:
            if repo == hub_repo:
                continue
            ok, error = set_secret(repo)
            if ok:
                print(f"  ✅ {repo}")
            else:
                suffix = " (no admin access)"
                if error:
                    suffix = f" ({error})"
                print(f"  ❌ {repo}{suffix}")

    print("\nConnected dispatch-enabled repos:")
    for repo in get_connected_repos():
        print(f"  - {repo}")
    print(
        "\nEnsure PAT has 'repo' scope (classic) or Actions R/W (fine-grained) "
        "on all repos."
    )
    return 0


def cmd_setup_nvd(args: argparse.Namespace) -> int:
    """Set NVD_API_KEY on Java repos for OWASP Dependency Check."""
    import getpass

    nvd_key = args.nvd_key

    if not nvd_key:
        print("NVD API Key is required for fast OWASP Dependency Check scans.")
        print("Get a free key at: https://nvd.nist.gov/developers/request-an-api-key")
        print()
        nvd_key = getpass.getpass("Enter NVD API Key: ")

    nvd_key = nvd_key.strip()

    if not nvd_key:
        print("Error: No NVD API key provided", file=sys.stderr)
        return 1

    if any(ch.isspace() for ch in nvd_key):
        print(
            "Error: Key contains whitespace; paste the raw key value.",
            file=sys.stderr,
        )
        return 1

    def verify_nvd_key(key: str) -> tuple[bool, str]:
        """Verify NVD API key by making a test request."""
        # NVD API test - fetch a known CVE
        test_url = (
            "https://services.nvd.nist.gov/rest/json/cves/2.0"
            "?cveId=CVE-2021-44228"
        )
        req = urllib.request.Request(  # noqa: S310
            test_url,
            headers={
                "apiKey": key,
                "User-Agent": "cihub",
            },
        )
        try:
            with safe_urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return True, "NVD API key is valid"
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "invalid or expired API key"
            if exc.code == 404:
                return True, "API key accepted (test CVE not found)"
            return False, f"HTTP {exc.code} {exc.reason}"
        except Exception as exc:
            return False, str(exc)
        return True, "API key accepted"

    if args.verify:
        print("Verifying NVD API key...")
        ok, message = verify_nvd_key(nvd_key)
        if not ok:
            print(f"NVD API key verification failed: {message}", file=sys.stderr)
            return 1
        print(f"NVD API key verified: {message}")

    gh_bin = resolve_executable("gh")

    def set_secret(repo: str, secret_name: str, secret_value: str) -> tuple[bool, str]:
        result = subprocess.run(  # noqa: S603
            [gh_bin, "secret", "set", secret_name, "-R", repo],
            input=secret_value,
            capture_output=True,
            text=True,
        )  # noqa: S603
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""

    # Get Java repos
    java_repos = get_connected_repos(
        only_dispatch_enabled=False,
        language_filter="java",
    )

    if not java_repos:
        print("No Java repos found in config/repos/*.yaml")
        print("NVD_API_KEY is only needed for Java repos (OWASP Dependency Check).")
        return 0

    print(f"\nSetting NVD_API_KEY on {len(java_repos)} Java repo(s)...")
    success_count = 0
    for repo in java_repos:
        ok, error = set_secret(repo, "NVD_API_KEY", nvd_key)
        if ok:
            print(f"  ✅ {repo}")
            success_count += 1
        else:
            suffix = " (no admin access)" if not error else f" ({error})"
            print(f"  ❌ {repo}{suffix}")

    print(f"\nSet NVD_API_KEY on {success_count}/{len(java_repos)} Java repos.")
    if success_count < len(java_repos):
        print("For repos you don't have admin access to, set the secret manually:")
        print("  gh secret set NVD_API_KEY -R owner/repo")
    return 0


def cmd_sync_templates(args: argparse.Namespace) -> int:
    """Sync caller workflow templates to target repos."""
    entries = get_repo_entries(only_dispatch_enabled=not args.include_disabled)
    if args.repo:
        repo_map = {entry["full"]: entry for entry in entries}
        missing = [repo for repo in args.repo if repo not in repo_map]
        if missing:
            print(
                "Error: repos not found in config/repos/*.yaml: "
                + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        entries = [repo_map[repo] for repo in args.repo]

    if not entries:
        print("No repos found to sync.")
        return 0

    failures = 0
    for entry in entries:
        repo = entry["full"]
        language = entry.get("language", "")
        dispatch_workflow = entry.get("dispatch_workflow", "hub-ci.yml")
        branch = entry.get("default_branch", "main") or "main"
        path = f".github/workflows/{dispatch_workflow}"

        try:
            desired = render_dispatch_workflow(language, dispatch_workflow)
        except ValueError as exc:
            print(f"Error: {repo} {path}: {exc}", file=sys.stderr)
            failures += 1
            continue

        remote = fetch_remote_file(repo, path, branch)
        workflow_synced = False

        if remote and remote.get("content") == desired:
            print(f"✅ {repo} {path} up to date")
            workflow_synced = True
        elif args.check:
            print(f"❌ {repo} {path} out of date")
            failures += 1
        elif args.dry_run:
            print(f"# Would update {repo} {path}")
        else:
            try:
                update_remote_file(
                    repo,
                    path,
                    branch,
                    desired,
                    args.commit_message,
                    remote.get("sha") if remote else None,
                )
                print(f"✅ {repo} {path} updated")
                workflow_synced = True
            except RuntimeError as exc:
                print(f"❌ {repo} {path} update failed: {exc}", file=sys.stderr)
                failures += 1

        # Delete stale workflow files only when migrating to unified hub-ci.yml
        # For language-specific workflows (monorepos), don't touch other files
        if dispatch_workflow == "hub-ci.yml":
            stale_workflow_names = ["hub-java-ci.yml", "hub-python-ci.yml"]
            for stale_name in stale_workflow_names:
                stale_path = f".github/workflows/{stale_name}"
                stale_file = fetch_remote_file(repo, stale_path, branch)
                if stale_file and stale_file.get("sha"):
                    if args.check:
                        print(f"❌ {repo} {stale_path} stale (should be deleted)")
                        failures += 1
                    elif args.dry_run:
                        print(f"# Would delete {repo} {stale_path} (stale)")
                    elif workflow_synced:
                        try:
                            delete_remote_file(
                                repo,
                                stale_path,
                                branch,
                                stale_file["sha"],
                                "Remove stale workflow (migrated to hub-ci.yml)",
                            )
                            print(f"🗑️  {repo} {stale_path} deleted (stale)")
                        except RuntimeError as exc:
                            print(
                                f"⚠️  {repo} {stale_path} delete failed: {exc}",
                                file=sys.stderr,
                            )

    if args.check and failures:
        print(f"Template drift detected in {failures} repo(s).", file=sys.stderr)
        return 1
    if failures:
        return 1

    # Update v1 tag to current HEAD so caller workflows get latest reusable workflows
    if args.update_tag and not args.check and not args.dry_run:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            head_sha = result.stdout.strip()

            # Check current v1 tag
            result = subprocess.run(
                ["git", "rev-parse", "v1"],
                capture_output=True,
                text=True,
            )
            current_v1 = result.stdout.strip() if result.returncode == 0 else None

            if current_v1 == head_sha:
                print("✅ v1 tag already at HEAD")
            else:
                # Update v1 tag locally
                subprocess.run(
                    ["git", "tag", "-f", "v1", "HEAD"],
                    check=True,
                    capture_output=True,
                )
                # Push to origin
                subprocess.run(
                    ["git", "push", "origin", "v1", "--force"],
                    check=True,
                    capture_output=True,
                )
                print(f"✅ v1 tag updated: {current_v1[:7] if current_v1 else 'none'} → {head_sha[:7]}")
        except subprocess.CalledProcessError as exc:
            print(f"⚠️  Failed to update v1 tag: {exc}", file=sys.stderr)
    elif args.dry_run and args.update_tag:
        print("# Would update v1 tag to HEAD")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cihub", description="CI/CD Hub CLI")
    parser.add_argument("--version", action="version", version=f"cihub {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect", help="Detect repo language and tools")
    detect.add_argument("--repo", required=True, help="Path to repo")
    detect.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    detect.add_argument("--explain", action="store_true", help="Show detection reasons")
    detect.set_defaults(func=cmd_detect)

    init = subparsers.add_parser("init", help="Generate .ci-hub.yml and hub-ci.yml")
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
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    init.set_defaults(func=cmd_init)

    update = subparsers.add_parser("update", help="Refresh hub-ci.yml and .ci-hub.yml")
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
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    update.set_defaults(func=cmd_update)

    validate = subparsers.add_parser(
        "validate",
        help="Validate .ci-hub.yml against schema",
    )
    validate.add_argument("--repo", required=True, help="Path to repo")
    validate.add_argument(
        "--strict", action="store_true", help="Fail if pom.xml warnings are found"
    )
    validate.set_defaults(func=cmd_validate)

    setup_secrets = subparsers.add_parser(
        "setup-secrets", help="Set HUB_DISPATCH_TOKEN on hub and connected repos"
    )
    setup_secrets.add_argument(
        "--hub-repo",
        default="jguida941/ci-cd-hub",
        help="Hub repository (default: jguida941/ci-cd-hub)",
    )
    setup_secrets.add_argument("--token", help="GitHub PAT (prompts if not provided)")
    setup_secrets.add_argument(
        "--all", action="store_true", help="Also set on all connected repos"
    )
    setup_secrets.add_argument(
        "--verify",
        action="store_true",
        help="Verify token with GitHub API before setting secrets",
    )
    setup_secrets.set_defaults(func=cmd_setup_secrets)

    setup_nvd = subparsers.add_parser(
        "setup-nvd", help="Set NVD_API_KEY on Java repos for OWASP Dependency Check"
    )
    setup_nvd.add_argument(
        "--nvd-key", help="NVD API key (prompts if not provided)"
    )
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
    fix_pom.add_argument("--repo", required=True, help="Path to repo")
    fix_pom.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_pom.set_defaults(func=cmd_fix_pom)

    fix_deps = subparsers.add_parser(
        "fix-deps", help="Add missing Maven dependencies for Java repos"
    )
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
    sync_templates.set_defaults(func=cmd_sync_templates)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
