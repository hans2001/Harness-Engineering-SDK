from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

from harness_runtime.config import harness_dir
from harness_runtime.schemas import BenchmarkSummary, BenchmarkTaskResult


def run_reference_benchmark(
    repo: Path,
    *,
    repo_filter: str,
    target_repo_path: str,
    adapter: str,
    agent: str | None = None,
    limit: int | None = None,
    verification_commands: list[str] | None = None,
    timeout: int | None = None,
) -> BenchmarkSummary:
    from harness_runtime.sdk import Harness

    harness = Harness(repo)
    tasks = harness.materialize_eval_tasks(
        target_repo_path=target_repo_path,
        repo_filter=repo_filter,
        verification_commands=verification_commands,
        limit=limit,
    )
    benchmark_id = f"benchmark_{time.strftime('%Y%m%d_%H%M%S')}"
    task_results: list[BenchmarkTaskResult] = []
    executed_runs = 0
    verified_runs = 0
    passed_runs = 0

    for task in tasks:
        preflight = harness.preflight(task_id=task.id)
        notes = [item.message for item in preflight.commands if not item.available]
        result = BenchmarkTaskResult(
            task_id=task.id,
            title=task.title,
            repo_full_name=str(task.metadata.get("repo_full_name") or ""),
            repo_ref=task.repo_ref,
            preflight_passed=preflight.passed,
            failure_notes=notes,
        )
        run = harness.run(task.id, agent=agent, adapter=adapter, timeout=timeout)
        executed_runs += 1
        result.run_id = run.id
        result.run_status = str(run.status)
        result.run_duration_seconds = run.duration_seconds
        result.artifact_path = run.artifact_path

        verification = harness.verify(run.id)
        verified_runs += 1
        result.verification_passed = verification.passed
        if verification.passed:
            passed_runs += 1
        else:
            result.verification_failed_commands = [
                command.command for command in verification.commands if not command.passed
            ]
            result.failure_notes.extend(
                command.failure_reason or f"{command.command} exited {command.exit_code}"
                for command in verification.commands
                if not command.passed
            )

        task_results.append(result)

    summary = BenchmarkSummary(
        benchmark_id=benchmark_id,
        kind="github-linked-prs",
        repo_filter=repo_filter,
        target_repo_path=target_repo_path,
        adapter=adapter,
        total_tasks=len(tasks),
        executed_runs=executed_runs,
        verified_runs=verified_runs,
        passed_runs=passed_runs,
        task_results=task_results,
    )
    report_path = write_benchmark_report(repo, summary)
    summary.report_path = str(report_path)
    return summary


def write_benchmark_report(repo: Path, summary: BenchmarkSummary) -> Path:
    def short_ref(value: str | None) -> str:
        if not value:
            return ""
        return value[:12]

    def format_duration(value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:.2f}s"

    def status_icon(value: bool | None) -> str:
        if value is True:
            return "PASS"
        if value is False:
            return "FAIL"
        return "N/A"

    report_dir = harness_dir(repo) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{summary.benchmark_id}.md"
    failed_command_counts = Counter()
    for item in summary.task_results:
        failed_command_counts.update(item.verification_failed_commands)
    lines = [
        f"# Benchmark {summary.benchmark_id}",
        "",
        f"- Kind: `{summary.kind}`",
        f"- Repo filter: `{summary.repo_filter}`",
        f"- Target repo path: `{summary.target_repo_path}`",
        f"- Adapter: `{summary.adapter}`",
        f"- Total tasks: {summary.total_tasks}",
        f"- Executed runs: {summary.executed_runs}",
        f"- Verified runs: {summary.verified_runs}",
        f"- Passed runs: {summary.passed_runs}",
        f"- Pass rate: {summary.pass_rate * 100:.1f}%",
        "",
        "## Summary",
        "",
    ]
    if failed_command_counts:
        lines.extend(
            [
                "Most common failed verification commands:",
                "",
            ]
        )
        for command, count in failed_command_counts.most_common():
            lines.append(f"- `{command}`: {count}")
        lines.append("")
    else:
        lines.extend(
            [
                "All verified runs passed.",
                "",
            ]
        )
    lines.extend(
        [
        "## Task Results",
        "",
        "| Task | Title | Repo Ref | Preflight | Run | Duration | Verify | Artifacts |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    repo = repo.resolve()
    for item in summary.task_results:
        artifacts = "-"
        if item.artifact_path:
            artifact_rel = Path(item.artifact_path).relative_to(repo)
            artifacts = f"[{artifact_rel}]({artifact_rel})"
        lines.append(
            f"| `{item.task_id}` | {item.title} | `{short_ref(item.repo_ref)}` | "
            f"`{status_icon(item.preflight_passed)}` | `{item.run_status or ''}` | "
            f"`{format_duration(item.run_duration_seconds)}` | "
            f"`{status_icon(item.verification_passed)}` | {artifacts} |"
        )
        if item.failure_notes:
            lines.append("")
            lines.append(f"Task `{item.task_id}` failures:")
            for failed_command in item.verification_failed_commands:
                lines.append(f"- Failed command: `{failed_command}`")
            for note in item.failure_notes:
                lines.append(f"- Note: {note}")
            lines.append("")
    lines.append("")
    report_path.write_text("\n".join(lines))
    json_path = report_dir / f"{summary.benchmark_id}.json"
    json_path.write_text(summary.model_dump_json(indent=2))
    return report_path
