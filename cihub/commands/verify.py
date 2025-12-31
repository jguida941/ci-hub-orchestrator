"""Verify workflow/template contracts for drift."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from cihub.cli import CommandResult, get_repo_entries, hub_root, resolve_executable
from cihub.config.io import load_yaml_file
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

REQUIRED_TEMPLATE_INPUTS = {"hub_repo", "hub_ref"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_yaml(path: Path) -> dict[str, Any]:
    data_any = cast(dict[object, Any], load_yaml_file(path))
    if "on" not in data_any and True in data_any:
        data_any["on"] = data_any.pop(True)
    return cast(dict[str, Any], data_any)


def _workflow_inputs(data: dict[str, Any]) -> dict[str, Any]:
    on_block = _as_dict(data.get("on", {}))
    workflow_call = _as_dict(on_block.get("workflow_call", {}))
    return _as_dict(workflow_call.get("inputs", {}))


def _required_inputs(inputs: dict[str, Any]) -> set[str]:
    required: set[str] = set()
    for name, spec in inputs.items():
        spec_dict = _as_dict(spec)
        if spec_dict.get("required") is True or "default" not in spec_dict:
            required.add(name)
    return required


def _job_block(data: dict[str, Any], job_name: str) -> dict[str, Any]:
    jobs = _as_dict(data.get("jobs", {}))
    return _as_dict(jobs.get(job_name, {}))


def _job_with_inputs(data: dict[str, Any], job_name: str) -> dict[str, Any]:
    return _as_dict(_job_block(data, job_name).get("with", {}))


def _job_uses(data: dict[str, Any], job_name: str) -> str | None:
    uses = _job_block(data, job_name).get("uses")
    return uses if isinstance(uses, str) else None


def _parse_uses(uses: str | None) -> tuple[str | None, str | None]:
    if not uses or "@" not in uses:
        return None, None
    path, ref = uses.rsplit("@", 1)
    repo = path.split("/.github/")[0]
    if repo.startswith("./"):
        return None, None
    return repo, ref


def validate_template_contracts(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    data: dict[str, Any] = {"templates_checked": 0, "templates": []}

    hub_ci_path = root / ".github" / "workflows" / "hub-ci.yml"
    hub_ci = _load_yaml(hub_ci_path)
    hub_inputs = _workflow_inputs(hub_ci)
    hub_input_keys = set(hub_inputs.keys())
    required_inputs = _required_inputs(hub_inputs) | REQUIRED_TEMPLATE_INPUTS

    templates_dir = root / "templates" / "repo"
    templates = sorted(templates_dir.glob("hub-*-ci.yml")) + sorted(templates_dir.glob("hub-*-ci.yaml"))
    data["templates_checked"] = len(templates)

    for template in templates:
        payload = _load_yaml(template)
        with_inputs = _job_with_inputs(payload, "ci")
        uses = _job_uses(payload, "ci")

        entry: dict[str, Any] = {"template": str(template), "issues": []}

        if uses is None:
            entry["issues"].append("missing jobs.ci.uses")
            problems.append(
                {
                    "severity": "error",
                    "message": "Template missing jobs.ci.uses",
                    "file": str(template),
                }
            )
        else:
            repo, ref = _parse_uses(uses)
            if repo and with_inputs.get("hub_repo") != repo:
                entry["issues"].append("hub_repo does not match workflow repo")
                problems.append(
                    {
                        "severity": "error",
                        "message": f"hub_repo '{with_inputs.get('hub_repo')}' does not match uses repo '{repo}'",
                        "file": str(template),
                    }
                )
            if ref and with_inputs.get("hub_ref") != ref:
                entry["issues"].append("hub_ref does not match workflow ref")
                problems.append(
                    {
                        "severity": "error",
                        "message": f"hub_ref '{with_inputs.get('hub_ref')}' does not match uses ref '{ref}'",
                        "file": str(template),
                    }
                )

        missing = sorted(required_inputs - set(with_inputs.keys()))
        if missing:
            entry["issues"].append(f"missing inputs: {', '.join(missing)}")
            problems.append(
                {
                    "severity": "error",
                    "message": f"Template missing required inputs: {', '.join(missing)}",
                    "file": str(template),
                }
            )

        unknown = sorted(set(with_inputs.keys()) - hub_input_keys)
        if unknown:
            entry["issues"].append(f"unknown inputs: {', '.join(unknown)}")
            problems.append(
                {
                    "severity": "error",
                    "message": f"Template passes unknown inputs: {', '.join(unknown)}",
                    "file": str(template),
                }
            )

        data["templates"].append(entry)

    return problems, data


def validate_reusable_contracts(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    data: dict[str, Any] = {"workflows": []}

    hub_ci_path = root / ".github" / "workflows" / "hub-ci.yml"
    hub_ci = _load_yaml(hub_ci_path)

    checks = [
        ("python", root / ".github" / "workflows" / "python-ci.yml"),
        ("java", root / ".github" / "workflows" / "java-ci.yml"),
    ]

    for job_name, workflow_path in checks:
        workflow = _load_yaml(workflow_path)
        inputs = _workflow_inputs(workflow)
        input_keys = set(inputs.keys())
        required = _required_inputs(inputs)
        with_inputs = _job_with_inputs(hub_ci, job_name)

        entry = {
            "job": job_name,
            "workflow": str(workflow_path),
            "missing_required": sorted(required - set(with_inputs.keys())),
            "unknown_inputs": sorted(set(with_inputs.keys()) - input_keys),
        }
        data["workflows"].append(entry)

        if entry["missing_required"]:
            problems.append(
                {
                    "severity": "error",
                    "message": f"{job_name} job missing required inputs: {', '.join(entry['missing_required'])}",
                    "file": str(hub_ci_path),
                }
            )
        if entry["unknown_inputs"]:
            problems.append(
                {
                    "severity": "error",
                    "message": f"{job_name} job passes unknown inputs: {', '.join(entry['unknown_inputs'])}",
                    "file": str(hub_ci_path),
                }
            )

    return problems, data


def _check_gh_auth() -> tuple[bool, str]:
    try:
        gh_bin = resolve_executable("gh")
    except FileNotFoundError:
        return False, "gh not found"
    proc = subprocess.run(  # noqa: S603
        [gh_bin, "auth", "status", "--hostname", "github.com"],
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def _run_sync_check(
    *,
    repo: list[str] | None,
    include_disabled: bool,
) -> CommandResult:
    from cihub.commands.templates import cmd_sync_templates

    args = argparse.Namespace(
        repo=repo,
        check=True,
        dry_run=False,
        include_disabled=include_disabled,
        update_tag=False,
        commit_message="",
        yes=False,
        json=True,
    )
    result = cmd_sync_templates(args)
    return result if isinstance(result, CommandResult) else CommandResult(exit_code=int(result))


def _run_integration(
    *,
    entries: list[dict[str, str]],
    workdir: Path,
    install_deps: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    problems: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for entry in entries:
        repo = entry["full"]
        repo_dir = workdir / repo.replace("/", "__")
        result_entry: dict[str, Any] = {"repo": repo, "path": str(repo_dir), "status": "unknown"}

        try:
            gh_bin = resolve_executable("gh")
        except FileNotFoundError:
            problems.append(
                {
                    "severity": "error",
                    "message": "gh not found (required for integration)",
                }
            )
            break

        clone_cmd = [gh_bin, "repo", "clone", repo, str(repo_dir), "--", "--depth", "1"]
        clone = subprocess.run(  # noqa: S603
            clone_cmd,
            capture_output=True,
            text=True,
        )
        if clone.returncode != 0:
            detail = (clone.stderr or clone.stdout or "").strip()
            result_entry["status"] = "clone_failed"
            result_entry["detail"] = detail
            problems.append(
                {
                    "severity": "error",
                    "message": f"Clone failed for {repo}",
                    "detail": detail,
                }
            )
            results.append(result_entry)
            continue

        branch = entry.get("default_branch") or ""
        if branch:
            try:
                git_bin = resolve_executable("git")
            except FileNotFoundError:
                problems.append(
                    {
                        "severity": "error",
                        "message": "git not found (required for integration)",
                    }
                )
                break
            checkout = subprocess.run(  # noqa: S603
                [git_bin, "-C", str(repo_dir), "checkout", branch],
                capture_output=True,
                text=True,
            )
            if checkout.returncode != 0:
                detail = (checkout.stderr or checkout.stdout or "").strip()
                problems.append(
                    {
                        "severity": "error",
                        "message": f"Checkout failed for {repo} ({branch})",
                        "detail": detail,
                    }
                )
                result_entry["status"] = "checkout_failed"
                result_entry["detail"] = detail
                results.append(result_entry)
                continue

        cmd = [sys.executable, "-m", "cihub", "ci", "--repo", str(repo_dir)]
        if install_deps:
            cmd.append("--install-deps")

        run = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
        )
        detail = (run.stdout or "") + (run.stderr or "")
        result_entry["status"] = "ok" if run.returncode == 0 else "failed"
        result_entry["detail"] = detail.strip()
        results.append(result_entry)
        if run.returncode != 0:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Integration run failed for {repo}",
                    "detail": detail.strip(),
                }
            )

    return problems, results


def cmd_verify(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    root = hub_root()
    run_remote = bool(getattr(args, "remote", False))
    run_integration = bool(getattr(args, "integration", False))
    install_deps = bool(getattr(args, "install_deps", False))
    include_disabled = bool(getattr(args, "include_disabled", False))
    repo_filter = getattr(args, "repo", None)
    keep = bool(getattr(args, "keep", False))
    workdir_arg = getattr(args, "workdir", None)

    problems: list[dict[str, Any]] = []
    template_problems, template_data = validate_template_contracts(root)
    workflow_problems, workflow_data = validate_reusable_contracts(root)
    problems.extend(template_problems)
    problems.extend(workflow_problems)

    remote_data: dict[str, Any] | None = None
    integration_data: dict[str, Any] | None = None

    if run_remote or run_integration:
        ok, detail = _check_gh_auth()
        if not ok:
            problems.append(
                {
                    "severity": "error",
                    "message": "GitHub auth required for remote verification",
                    "detail": detail,
                }
            )
            run_remote = False
            run_integration = False

    if run_remote:
        try:
            result = _run_sync_check(repo=repo_filter, include_disabled=include_disabled)
            remote_data = result.data or {}
            if result.exit_code != 0:
                problems.extend(result.problems)
        except RuntimeError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Remote sync check failed: {exc}",
                }
            )

    if run_integration:
        entries = [
            entry
            for entry in get_repo_entries(only_dispatch_enabled=not include_disabled)
            if not repo_filter or entry["full"] in set(repo_filter)
        ]
        delete_workdir = False
        if workdir_arg:
            workdir = Path(workdir_arg).expanduser().resolve()
            workdir.mkdir(parents=True, exist_ok=True)
        else:
            workdir = Path(tempfile.mkdtemp(prefix="cihub-verify-"))
            delete_workdir = True
        integration_problems, integration_results = _run_integration(
            entries=entries,
            workdir=workdir,
            install_deps=install_deps,
        )
        problems.extend(integration_problems)
        integration_data = {"workdir": str(workdir), "results": integration_results}
        if delete_workdir and not keep:
            shutil.rmtree(workdir, ignore_errors=True)

    summary = "Verify OK" if not problems else f"Verify failed ({len(problems)} issues)"
    exit_code = EXIT_SUCCESS if not problems else EXIT_FAILURE

    if json_mode:
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            problems=problems,
            data={
                "templates": template_data,
                "workflows": workflow_data,
                "remote": remote_data,
                "integration": integration_data,
            },
        )

    print(summary)
    for problem in problems:
        message = problem.get("message")
        file_path = problem.get("file")
        if file_path:
            print(f"- {message} ({file_path})")
        else:
            print(f"- {message}")
    return exit_code
