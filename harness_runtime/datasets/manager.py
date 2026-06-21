from __future__ import annotations

import json
from pathlib import Path

from harness_runtime.config import harness_dir
from harness_runtime.repo import is_git_repo, resolve_github_pull_request_baseline
from harness_runtime.schemas import EvalDatasetEntry, EvalSummary, TaskSpec, VerificationSpec, dump_task
from harness_runtime.storage import Storage
from harness_runtime.verification.profiles import suggest_verification_commands


def build_eval_summary(repo: Path) -> EvalSummary:
    storage = Storage(repo)
    runs = storage.list_runs()
    verifications = storage.list_verifications()
    passed = [item for item in verifications if item.passed]
    runtimes = [run.duration_seconds for run in runs if run.duration_seconds is not None]
    failed_commands = sorted(
        {
            command.command
            for result in verifications
            for command in result.commands
            if not command.passed
        }
    )
    summary = EvalSummary(
        total_runs=len(runs),
        verified_runs=len(verifications),
        passed_runs=len(passed),
        pass_rate=(len(passed) / len(verifications)) if verifications else 0.0,
        average_runtime_seconds=(sum(runtimes) / len(runtimes)) if runtimes else None,
        failed_commands=failed_commands,
        regressions=[result.run_id for result in verifications if not result.passed],
    )
    out_path = harness_dir(repo) / "datasets" / "latest_eval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary.model_dump_json(indent=2))
    return summary


def build_github_reference_dataset(
    repo: Path,
    *,
    repo_filter: str | None = None,
    limit: int | None = None,
) -> list[EvalDatasetEntry]:
    storage = Storage(repo)
    tasks = storage.list_tasks()
    entries: list[EvalDatasetEntry] = []
    for task in tasks:
        if str(task.source) != "github":
            continue
        metadata = task.metadata
        repo_full_name = metadata.get("repo_full_name")
        if not repo_full_name:
            continue
        if repo_filter and repo_full_name != repo_filter:
            continue
        linked_pull_requests = metadata.get("linked_pull_requests") or []
        if not linked_pull_requests:
            continue

        entries.append(task_to_eval_entry(task))
        if limit is not None and len(entries) >= limit:
            break

    dataset_dir = harness_dir(repo) / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = dataset_dir / "github_linked_pr_eval.jsonl"
    summary_path = dataset_dir / "github_linked_pr_eval.summary.json"
    jsonl_path.write_text("\n".join(entry.model_dump_json() for entry in entries) + ("\n" if entries else ""))
    summary_path.write_text(
        json.dumps(
            {
                "entries": len(entries),
                "repo_filter": repo_filter,
                "reference_kind": "linked_pull_request",
            },
            indent=2,
        )
    )
    return entries


def task_to_eval_entry(task: TaskSpec) -> EvalDatasetEntry:
    metadata = task.metadata
    linked_pull_requests = metadata.get("linked_pull_requests") or []
    linked_numbers = [item.get("number") for item in linked_pull_requests if isinstance(item.get("number"), int)]
    linked_urls = [item.get("url") for item in linked_pull_requests if item.get("url")]
    inferred_repo_ref = task.repo_ref or infer_repo_ref(linked_pull_requests)
    reference_paths = merge_reference_paths(
        metadata.get("reference_paths") or [],
        collect_reference_paths(linked_pull_requests),
    )
    return EvalDatasetEntry(
        task_id=task.id,
        title=task.title,
        source=str(task.source),
        repo_full_name=metadata.get("repo_full_name", ""),
        repo_ref=inferred_repo_ref,
        issue_number=metadata.get("issue_number"),
        issue_url=metadata.get("issue_url"),
        instructions=task.instructions,
        verification_commands=list(task.verification.commands),
        labels=list(metadata.get("labels") or []),
        assignees=list(metadata.get("assignees") or []),
        milestone=metadata.get("milestone"),
        reference_paths=reference_paths,
        linked_pull_request_numbers=linked_numbers,
        linked_pull_request_urls=linked_urls,
        metadata={
            "author": metadata.get("author"),
            "state": metadata.get("state"),
            "state_reason": metadata.get("state_reason"),
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "closed_at": metadata.get("closed_at"),
            "repo_ref_source": "explicit" if task.repo_ref else ("inferred" if inferred_repo_ref else None),
        },
    )


def materialize_eval_tasks(
    repo: Path,
    *,
    repo_filter: str | None = None,
    target_repo_path: str,
    verification_commands: list[str] | None = None,
    limit: int | None = None,
) -> list[TaskSpec]:
    entries = build_github_reference_dataset(repo, repo_filter=repo_filter, limit=limit)
    task_dir = harness_dir(repo) / "tasks" / "generated"
    task_dir.mkdir(parents=True, exist_ok=True)
    storage = Storage(repo)
    tasks: list[TaskSpec] = []
    for entry in entries:
        resolved_repo_ref = entry.repo_ref or resolve_materialization_repo_ref(Path(repo / target_repo_path), entry)
        instructions = render_eval_instructions(entry)
        seed_task = TaskSpec(
            id=entry.task_id,
            title=entry.title,
            source=entry.source,
            repo_path=target_repo_path,
            repo_ref=resolved_repo_ref,
            instructions=instructions,
            verification=VerificationSpec(commands=list(entry.verification_commands)),
            metadata={
                **entry.metadata,
                "repo_full_name": entry.repo_full_name,
                "issue_number": entry.issue_number,
                "issue_url": entry.issue_url,
                "labels": entry.labels,
                "assignees": entry.assignees,
                "milestone": entry.milestone,
                "reference_paths": entry.reference_paths,
                "linked_pull_request_numbers": entry.linked_pull_request_numbers,
                "linked_pull_request_urls": entry.linked_pull_request_urls,
                "reference_kind": entry.reference_kind,
            },
        )
        resolved_verification = verification_commands or suggest_verification_commands(seed_task)
        task = TaskSpec(
            id=f"eval_{entry.task_id}",
            title=entry.title,
            source=entry.source,
            repo_path=target_repo_path,
            repo_ref=resolved_repo_ref,
            instructions=instructions,
            verification=VerificationSpec(commands=resolved_verification),
            metadata={
                **seed_task.metadata,
                "dataset_entry_task_id": entry.task_id,
            },
        )
        out_path = task_dir / f"{task.id}.yaml"
        dump_task(task, out_path)
        storage.upsert_task(task, out_path)
        tasks.append(task)
    return tasks


def collect_reference_paths(linked_pull_requests: list[dict]) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for pull_request in linked_pull_requests:
        for path in pull_request.get("files") or []:
            if not isinstance(path, str) or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def merge_reference_paths(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for path in group:
            if not isinstance(path, str) or path in seen:
                continue
            seen.add(path)
            merged.append(path)
    return merged


def infer_repo_ref(linked_pull_requests: list[dict]) -> str | None:
    for pull_request in linked_pull_requests:
        baseline_sha = pull_request.get("baseline_sha")
        if isinstance(baseline_sha, str) and baseline_sha:
            return baseline_sha
    return None


def resolve_materialization_repo_ref(target_repo_path: Path, entry: EvalDatasetEntry) -> str | None:
    repo_ref_source = entry.metadata.get("repo_ref_source")
    if repo_ref_source == "explicit" and entry.repo_ref:
        return entry.repo_ref
    if entry.source != "github":
        return entry.repo_ref
    if target_repo_path.exists() and is_git_repo(target_repo_path):
        for pull_request_number in entry.linked_pull_request_numbers:
            resolved = resolve_github_pull_request_baseline(target_repo_path, pull_request_number)
            if resolved:
                return resolved
    return entry.repo_ref


def render_eval_instructions(entry: EvalDatasetEntry) -> str:
    if not entry.reference_paths:
        return entry.instructions

    lines = [entry.instructions.rstrip(), "", "Reference fix file hints:"]
    for path in entry.reference_paths[:12]:
        lines.append(f"- {path}")
    return "\n".join(lines).strip()
