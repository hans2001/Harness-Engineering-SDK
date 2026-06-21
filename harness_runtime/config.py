from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


HARNESS_DIR = ".harness"


class HarnessConfig(BaseModel):
    version: int = 1
    default_agent: str | None = None
    verification_commands: list[str] = Field(default_factory=lambda: ["pytest"])
    artifact_retention_days: int = 30
    privacy: dict[str, Any] = Field(
        default_factory=lambda: {
            "mode": "local_only",
            "upload_artifacts": False,
            "redact_secrets": True,
        }
    )
    env_allowlist: list[str] = Field(default_factory=lambda: ["PATH", "HOME", "SHELL", "PYTHONPATH"])
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            ".git",
            ".harness",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "node_modules",
        ]
    )


def harness_dir(repo: Path) -> Path:
    return repo / HARNESS_DIR


def config_path(repo: Path) -> Path:
    return harness_dir(repo) / "config.yaml"


def load_config(repo: Path) -> HarnessConfig:
    path = config_path(repo)
    if not path.exists():
        return HarnessConfig()
    return HarnessConfig.model_validate(yaml.safe_load(path.read_text()) or {})


def write_config(repo: Path, config: HarnessConfig | None = None) -> Path:
    config = config or HarnessConfig()
    path = config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False))
    return path


def init_layout(repo: Path) -> None:
    root = harness_dir(repo)
    for name in [
        "tasks",
        "runs",
        "datasets",
        "skills",
        "reports",
        "traces",
        "policies",
        "worktrees",
    ]:
        (root / name).mkdir(parents=True, exist_ok=True)
    write_config(repo)

