#!/usr/bin/env python3
"""Ephemeral Data Lab helper for spinning up temporary databases in CI."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class ServiceConfig:
    name: str
    image: str
    ports: list[int]
    env: dict[str, str]


@dataclass
class LabConfig:
    name: str
    ttl_hours: int
    services: list[ServiceConfig]
    seed_path: Path | None


def load_config(path: Path) -> LabConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"[ephemeral] config {path} must be a mapping")
    services_raw = data.get("services")
    if not services_raw:
        raise SystemExit(f"[ephemeral] config {path} missing 'services'")
    services: list[ServiceConfig] = []
    for idx, entry in enumerate(services_raw):
        if not isinstance(entry, dict):
            raise SystemExit(f"[ephemeral] service #{idx} must be a mapping")
        for field in ("name", "image"):
            if field not in entry:
                raise SystemExit(f"[ephemeral] service #{idx} missing required field '{field}'")
        ports_raw = entry.get("ports", [])
        if ports_raw is None:
            ports_raw = []
        if not isinstance(ports_raw, (list, tuple)):
            raise SystemExit(f"[ephemeral] service #{idx} ports must be a list, got {type(ports_raw).__name__}")
        ports: list[int] = []
        for port_idx, raw_port in enumerate(ports_raw):
            try:
                port = int(raw_port)
            except (TypeError, ValueError) as exc:
                raise SystemExit(
                    f"[ephemeral] service #{idx} port #{port_idx} invalid integer value: {raw_port!r}"
                ) from exc
            if not (1 <= port <= 65535):
                raise SystemExit(
                    f"[ephemeral] service #{idx} port #{port_idx} invalid port {port} (must be 1-65535)"
                )
            ports.append(port)
        env_raw = entry.get("env")
        if env_raw is not None and not isinstance(env_raw, dict):
            raise SystemExit(f"[ephemeral] service #{idx} env must be a mapping, got {type(env_raw).__name__}")
        services.append(
            ServiceConfig(
                name=str(entry["name"]),
                image=str(entry["image"]),
                ports=ports,
                env={str(k): str(v) for k, v in (env_raw or {}).items()},
            )
        )
    seed_file = data.get("seed_file")
    seed_path = None
    if seed_file:
        seed_candidate = Path(seed_file)
        if not seed_candidate.is_absolute():
            if seed_candidate.exists():
                seed_candidate = seed_candidate.resolve()
            else:
                seed_candidate = (path.parent / seed_candidate).resolve()
        if not seed_candidate.exists():
            raise SystemExit(f"[ephemeral] seed file not found: {seed_candidate}")
        seed_path = seed_candidate
    ttl_raw = data.get("ttl_hours", 4)
    try:
        ttl = int(ttl_raw)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"[ephemeral] ttl_hours must be an integer, got {ttl_raw!r}") from exc
    if ttl <= 0:
        raise SystemExit(f"[ephemeral] ttl_hours must be positive, got {ttl}")
    return LabConfig(
        name=str(data.get("name", path.stem)),
        ttl_hours=ttl,
        services=services,
        seed_path=seed_path,
    )


def plan_lab(config: LabConfig) -> dict[str, Any]:
    return {
        "schema": "ephemeral_lab.plan.v1",
        "name": config.name,
        "ttl_hours": config.ttl_hours,
        "services": [
            {
                "name": svc.name,
                "image": svc.image,
                "ports": svc.ports,
                "env": svc.env,
            }
            for svc in config.services
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_attached": bool(config.seed_path),
    }


def snapshot_lab(config: LabConfig, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "ephemeral_lab.snapshot.v1",
        "name": config.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": None,
    }
    if config.seed_path:
        destination = output_dir / config.seed_path.name
        shutil.copyfile(config.seed_path, destination)
        manifest["seed"] = destination.name
    manifest_path = output_dir / "snapshot.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ephemeral Data Lab helper")
    parser.add_argument("--config", required=True, type=Path, help="Lab config YAML")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Emit lab plan JSON")
    plan_parser.add_argument("--output", required=True, type=Path, help="Plan JSON output")

    snapshot_parser = subparsers.add_parser("snapshot", help="Create seed snapshot artifact")
    snapshot_parser.add_argument("--output-dir", required=True, type=Path, help="Directory for artifacts")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.command == "plan":
        plan = plan_lab(config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(f"[ephemeral] wrote plan for lab '{config.name}' to {args.output}")
        return 0
    if args.command == "snapshot":
        manifest = snapshot_lab(config, args.output_dir)
        print(f"[ephemeral] snapshot ready at {args.output_dir} (seed={manifest['seed']})")
        return 0
    raise ValueError(f"[ephemeral] unexpected command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
