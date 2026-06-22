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


class BenchmarkTaskResult(BaseModel):
    task_id: str
    title: str
    repo_full_name: str
    repo_ref: str | None = None
    preflight_passed: bool
    run_id: str | None = None
    run_status: str | None = None
    run_duration_seconds: float | None = None
    verification_passed: bool | None = None
    verification_failed_commands: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    failure_notes: list[str] = Field(default_factory=list)


class BenchmarkSummary(BaseModel):
    benchmark_id: str
    kind: str
    repo_filter: str | None = None
    target_repo_path: str
    adapter: str
    total_tasks: int
    executed_runs: int
    verified_runs: int
    passed_runs: int
    task_results: list[BenchmarkTaskResult] = Field(default_factory=list)
    report_path: str | None = None

    @property
    def pass_rate(self) -> float:
        if self.verified_runs == 0:
            return 0.0
        return self.passed_runs / self.verified_runs


class TraceEventKind(StrEnum):
    run_started = "run_started"
    agent_completed = "agent_completed"
    verification_started = "verification_started"
    verification_command_finished = "verification_command_finished"
    verification_finished = "verification_finished"
    diagnosis = "diagnosis"


class HarnessTraceEvent(BaseModel):
    event: TraceEventKind | str
    timestamp: datetime = Field(default_factory=utc_now)
    run_id: str
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class HarnessTrace(BaseModel):
    trace_id: str
    run_id: str
    task_id: str
    repo: str
    created_at: datetime = Field(default_factory=utc_now)
    events: list[HarnessTraceEvent] = Field(default_factory=list)
    failure_tags: list[str] = Field(default_factory=list)
    failure_summary: str | None = None
    trace_path: str | None = None


class HarnessPatchKind(StrEnum):
    skill = "skill"
    policy = "policy"
    verification_hint = "verification_hint"


class HarnessPatchStatus(StrEnum):
    proposed = "proposed"
    promoted = "promoted"
    rejected = "rejected"


class HarnessPatchPrediction(BaseModel):
    expected_fixes: list[str] = Field(default_factory=list)
    at_risk_regressions: list[str] = Field(default_factory=list)
    rationale: str = ""


class HarnessPatch(BaseModel):
    patch_id: str
    round_id: str
    kind: HarnessPatchKind = HarnessPatchKind.skill
    target_path: str
    title: str
    content: str
    evidence_run_ids: list[str] = Field(default_factory=list)
    evidence_task_ids: list[str] = Field(default_factory=list)
    failure_tags: list[str] = Field(default_factory=list)
    prediction: HarnessPatchPrediction = Field(default_factory=HarnessPatchPrediction)
    status: HarnessPatchStatus = HarnessPatchStatus.proposed
    created_at: datetime = Field(default_factory=utc_now)


class FlywheelRound(BaseModel):
    round_id: str
    round_number: int
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    benchmark_id: str | None = None
    pass_rate_before: float | None = None
    pass_rate_after: float | None = None
    patches_proposed: list[str] = Field(default_factory=list)
    patches_promoted: list[str] = Field(default_factory=list)
    patches_rejected: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    adapter: str = "shell"
    report_path: str | None = None


class FlywheelSummary(BaseModel):
    flywheel_id: str
    rounds: list[FlywheelRound] = Field(default_factory=list)
    initial_pass_rate: float = 0.0
    final_pass_rate: float = 0.0
    report_path: str | None = None


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
