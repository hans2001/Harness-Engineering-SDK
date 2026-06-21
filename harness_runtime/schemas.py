from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskSource(StrEnum):
    local = "local"
    github = "github"
    failed_test_log = "failed_test_log"
    manual = "manual"


class VerificationSpec(BaseModel):
    commands: list[str] = Field(default_factory=list)


class TaskSpec(BaseModel):
    id: str
    title: str
    source: TaskSource | str = TaskSource.local
    repo_path: str = "."
    repo_ref: str | None = None
    instructions: str
    verification: VerificationSpec = Field(default_factory=VerificationSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandResult(BaseModel):
    command: str
    exit_code: int
    duration_seconds: float
    stdout_path: str | None = None
    stderr_path: str | None = None
    passed: bool
    failure_reason: str | None = None


class VerificationResult(BaseModel):
    run_id: str
    task_id: str
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    passed: bool = False
    commands: list[CommandResult] = Field(default_factory=list)


class PreflightCheck(BaseModel):
    command: str
    executable: str | None = None
    available: bool
    message: str


class PreflightResult(BaseModel):
    repo: str
    commands: list[PreflightCheck] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(command.available for command in self.commands)


class RunStatus(StrEnum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    verified = "verified"


class RunRecord(BaseModel):
    id: str
    task_id: str
    agent_adapter: str = "shell"
    agent_command: str
    repo_path: str
    workspace_path: str
    artifact_path: str
    base_sha: str | None = None
    status: RunStatus = RunStatus.created
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    exit_code: int | None = None
    duration_seconds: float | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    diff_path: str | None = None
    verification_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalSummary(BaseModel):
    total_runs: int
    verified_runs: int
    passed_runs: int
    pass_rate: float
    average_runtime_seconds: float | None = None
    failed_commands: list[str] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)


class EvalDatasetEntry(BaseModel):
    task_id: str
    title: str
    source: str
    repo_full_name: str
    repo_ref: str | None = None
    issue_number: int | None = None
    issue_url: str | None = None
    instructions: str
    verification_commands: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    milestone: str | None = None
    reference_paths: list[str] = Field(default_factory=list)
    linked_pull_request_numbers: list[int] = Field(default_factory=list)
    linked_pull_request_urls: list[str] = Field(default_factory=list)
    reference_kind: str = "linked_pull_request"
    metadata: dict[str, Any] = Field(default_factory=dict)


def load_task(path: Path) -> TaskSpec:
    import yaml

    data = yaml.safe_load(path.read_text()) or {}
    return TaskSpec.model_validate(data)


def dump_task(task: TaskSpec, path: Path) -> None:
    import yaml

    path.write_text(yaml.safe_dump(task.model_dump(mode="json"), sort_keys=False))
