from __future__ import annotations

from pathlib import Path

from tools import ephemeral_data_lab as lab


def _config(tmp_path: Path, seed_text: str = "insert into demo values (1);") -> Path:
    seed = tmp_path / "seed.sql"
    seed.write_text(seed_text, encoding="utf-8")
    cfg = tmp_path / "lab.yaml"
    cfg.write_text(
        f"""
name: demo-lab
ttl_hours: 2
seed_file: {seed}
services:
  - name: postgres
    image: postgres:15
    ports: [5432]
    env:
      POSTGRES_PASSWORD: example
""",
        encoding="utf-8",
    )
    return cfg


def test_plan_and_snapshot(tmp_path):
    cfg_path = _config(tmp_path)
    config = lab.load_config(cfg_path)
    plan = lab.plan_lab(config)
    assert plan["name"] == "demo-lab"
    snapshot_dir = tmp_path / "snapshot"
    manifest = lab.snapshot_lab(config, snapshot_dir)
    assert manifest["seed"] == "seed.sql"
    assert (snapshot_dir / "seed.sql").exists()

