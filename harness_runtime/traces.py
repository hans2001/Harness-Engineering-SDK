from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from harness_runtime.config import harness_dir
from harness_runtime.schemas import (
    HarnessTrace,
    HarnessTraceEvent,
    RunRecord,
    TaskSpec,
    TraceEventKind,
    VerificationResult,
    utc_now,
)


def trace_artifact_path(artifact_path: Path) -> Path:
    return artifact_path / "trace.jsonl"


def trace_store_path(repo: Path, trace_id: str) -> Path:
    return harness_dir(repo) / "traces" / f"{trace_id}.json"


def append_trace_event(trace_path: Path, event: HarnessTraceEvent) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json())
        handle.write("\n")


def load_trace_events(trace_path: Path) -> list[HarnessTraceEvent]:
    if not trace_path.exists():
        return []
    events: list[HarnessTraceEvent] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(HarnessTraceEvent.model_validate_json(line))
    return events


def infer_failure_tags(run: RunRecord, verification: VerificationResult | None) -> list[str]:
    tags: list[str] = []
    if run.metadata.get("timed_out"):
        tags.append("timeout")
    if run.exit_code not in (None, 0):
        tags.append("agent_failed")
    if verification is None:
        return tags
    if not verification.passed:
        tags.append("verification_failed")
        for command in verification.commands:
            if command.passed:
                continue
            tags.append(f"command_failed:{command.command[:80]}")
    return tags


def summarize_failure(run: RunRecord, verification: VerificationResult | None) -> str | None:
    if run.metadata.get("failure_reason"):
        return str(run.metadata["failure_reason"])
    if verification is None:
        if run.exit_code not in (None, 0):
            return f"Agent exited with code {run.exit_code}."
        return None
    if verification.passed:
        return None
    failed = [command.command for command in verification.commands if not command.passed]
    if failed:
        return f"Verification failed for: {', '.join(failed)}"
    return "Verification failed."


def materialize_trace(
    repo: Path,
    *,
    run: RunRecord,
    task: TaskSpec,
    verification: VerificationResult | None = None,
) -> HarnessTrace:
    artifact_path = Path(run.artifact_path)
    trace_path = trace_artifact_path(artifact_path)
    events = load_trace_events(trace_path)
    if not events:
        events = [
            HarnessTraceEvent(
                event=TraceEventKind.agent_completed,
                run_id=run.id,
                task_id=task.id,
                payload={
                    "adapter": run.agent_adapter,
                    "exit_code": run.exit_code,
                    "duration_seconds": run.duration_seconds,
                },
            )
        ]
    trace = HarnessTrace(
        trace_id=f"trace_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        run_id=run.id,
        task_id=task.id,
        repo=str(repo.resolve()),
        events=events,
        failure_tags=infer_failure_tags(run, verification),
        failure_summary=summarize_failure(run, verification),
    )
    store_path = trace_store_path(repo, trace.trace_id)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    trace.trace_path = str(store_path)
    store_path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")
    return trace


def record_verification_trace(
    artifact_path: Path,
    *,
    run_id: str,
    task_id: str,
    verification: VerificationResult,
) -> None:
    trace_path = trace_artifact_path(artifact_path)
    append_trace_event(
        trace_path,
        HarnessTraceEvent(
            event=TraceEventKind.verification_finished,
            run_id=run_id,
            task_id=task_id,
            payload={
                "passed": verification.passed,
                "failed_commands": [
                    command.command for command in verification.commands if not command.passed
                ],
            },
        ),
    )
