from __future__ import annotations

from pathlib import Path

import yaml

from harness_runtime.config import harness_dir
from harness_runtime.schemas import TaskSpec, VerificationSpec, dump_task
from harness_runtime.storage import Storage


def harvest_local(repo: Path, source: Path) -> list[TaskSpec]:
    source = source if source.is_absolute() else repo / source
    if not source.exists():
        raise FileNotFoundError(source)

    files = sorted(source.rglob("*")) if source.is_dir() else [source]
    tasks: list[TaskSpec] = []
    for path in files:
        if path.suffix.lower() in {".yaml", ".yml"}:
            tasks.append(TaskSpec.model_validate(yaml.safe_load(path.read_text()) or {}))
        elif path.suffix.lower() in {".md", ".txt", ".log"}:
            tasks.append(task_from_text(path, len(tasks) + 1))

    task_dir = harness_dir(repo) / "tasks"
    storage = Storage(repo)
    for task in tasks:
        out_path = task_dir / f"{task.id}.yaml"
        dump_task(task, out_path)
        storage.upsert_task(task, out_path)
    return tasks


def create_manual_task(
    repo: Path,
    title: str,
    instructions: str,
    verification_commands: list[str] | None = None,
) -> TaskSpec:
    storage = Storage(repo)
    existing = storage.list_tasks()
    task = TaskSpec(
        id=f"task_{len(existing) + 1:03d}",
        title=title,
        source="manual",
        repo_path=".",
        instructions=instructions,
        verification=VerificationSpec(commands=verification_commands or ["pytest"]),
    )
    out_path = harness_dir(repo) / "tasks" / f"{task.id}.yaml"
    dump_task(task, out_path)
    storage.upsert_task(task, out_path)
    return task


def task_from_text(path: Path, index: int) -> TaskSpec:
    text = path.read_text()
    title = path.stem.replace("_", " ").replace("-", " ").title()
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    return TaskSpec(
        id=f"task_{index:03d}",
        title=title,
        source="local",
        repo_path=".",
        instructions=text.strip(),
        verification=VerificationSpec(commands=["pytest"]),
        metadata={"harvested_from": str(path)},
    )
