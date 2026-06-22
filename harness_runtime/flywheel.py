from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from harness_runtime.benchmark import run_reference_benchmark
from harness_runtime.config import harness_dir
from harness_runtime.schemas import (
    BenchmarkSummary,
    BenchmarkTaskResult,
    FlywheelRound,
    FlywheelSummary,
    HarnessPatch,
    HarnessPatchKind,
    HarnessPatchPrediction,
    HarnessPatchStatus,
    utc_now,
)


PATCH_TEMPLATES: dict[str, tuple[str, str]] = {
    "verification_failed": (
        "verify-before-finish",
        (
            "Before declaring the task complete, run every verification command from the task spec "
            "in the workspace and fix failures until they pass."
        ),
    ),
    "agent_failed": (
        "read-agent-errors",
        (
            "If the agent command fails, inspect stdout/stderr artifacts and make the smallest change "
            "that addresses the reported error before retrying."
        ),
    ),
    "timeout": (
        "respect-time-budget",
        (
            "Work incrementally: make one focused change, verify quickly, and avoid exploratory loops "
            "that consume the full runtime budget."
        ),
    ),
}


def flywheel_dir(repo: Path) -> Path:
    return harness_dir(repo) / "flywheel"


def patches_dir(repo: Path) -> Path:
    path = flywheel_dir(repo) / "patches"
    path.mkdir(parents=True, exist_ok=True)
    return path


def rounds_dir(repo: Path) -> Path:
    path = flywheel_dir(repo) / "rounds"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_patch(repo: Path, patch: HarnessPatch) -> Path:
    path = patches_dir(repo) / f"{patch.patch_id}.json"
    path.write_text(patch.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_patch(repo: Path, patch_id: str) -> HarnessPatch:
    path = patches_dir(repo) / f"{patch_id}.json"
    if not path.exists():
        raise KeyError(f"Harness patch not found: {patch_id}")
    return HarnessPatch.model_validate_json(path.read_text(encoding="utf-8"))


def list_patches(repo: Path) -> list[HarnessPatch]:
    directory = patches_dir(repo)
    patches: list[HarnessPatch] = []
    for path in sorted(directory.glob("*.json")):
        patches.append(HarnessPatch.model_validate_json(path.read_text(encoding="utf-8")))
    return patches


def load_benchmark_summary(repo: Path, benchmark_id: str = "latest") -> BenchmarkSummary:
    report_dir = harness_dir(repo) / "reports"
    if benchmark_id == "latest":
        candidates = sorted(report_dir.glob("benchmark_*.json"))
        if not candidates:
            raise KeyError("No benchmark summaries found. Run `harness benchmark` first.")
        path = candidates[-1]
    else:
        path = report_dir / f"{benchmark_id}.json"
        if not path.exists():
            raise KeyError(f"Benchmark summary not found: {benchmark_id}")
    return BenchmarkSummary.model_validate_json(path.read_text(encoding="utf-8"))


def infer_tags_from_task_result(result: BenchmarkTaskResult) -> list[str]:
    tags: list[str] = []
    if result.run_status == "failed":
        tags.append("agent_failed")
    if result.verification_passed is False:
        tags.append("verification_failed")
    for note in result.failure_notes:
        if "timed out" in note.lower():
            tags.append("timeout")
    for command in result.verification_failed_commands:
        tags.append(f"command_failed:{command[:80]}")
    return tags or ["verification_failed"]


def build_patch_for_tag(
    repo: Path,
    *,
    round_id: str,
    tag: str,
    result: BenchmarkTaskResult,
) -> HarnessPatch:
    base_tag = tag.split(":", 1)[0]
    slug, body = PATCH_TEMPLATES.get(
        base_tag,
        (
            "general-failure-recovery",
            "Review the failing task artifacts, keep changes minimal, and align the workspace with the task instructions.",
        ),
    )
    patch_id = f"patch_{slug}_{uuid.uuid4().hex[:8]}"
    target_path = str(harness_dir(repo) / "skills" / f"{slug}.md")
    prediction = HarnessPatchPrediction(
        expected_fixes=[result.task_id],
        at_risk_regressions=[],
        rationale=f"Observed `{base_tag}` while running task `{result.task_id}`.",
    )
    content = "\n".join(
        [
            f"# {slug.replace('-', ' ').title()}",
            "",
            body,
            "",
            "## Evidence",
            "",
            f"- Task: `{result.task_id}`",
            f"- Title: {result.title}",
            f"- Failure tags: {', '.join(infer_tags_from_task_result(result))}",
        ]
    )
    if result.failure_notes:
        content += "\n- Notes:\n"
        for note in result.failure_notes:
            content += f"  - {note}\n"
    return HarnessPatch(
        patch_id=patch_id,
        round_id=round_id,
        kind=HarnessPatchKind.skill,
        target_path=target_path,
        title=slug.replace("-", " ").title(),
        content=content,
        evidence_run_ids=[result.run_id] if result.run_id else [],
        evidence_task_ids=[result.task_id],
        failure_tags=[tag],
        prediction=prediction,
    )


def analyze_benchmark_failures(
    repo: Path,
    summary: BenchmarkSummary,
    *,
    round_id: str | None = None,
) -> list[HarnessPatch]:
    round_id = round_id or f"round_{time.strftime('%Y%m%d_%H%M%S')}"
    patches: list[HarnessPatch] = []
    seen_base_tags: set[str] = set()
    for result in summary.task_results:
        if result.verification_passed:
            continue
        for tag in infer_tags_from_task_result(result):
            base_tag = tag.split(":", 1)[0]
            if base_tag in seen_base_tags:
                continue
            seen_base_tags.add(base_tag)
            patch = build_patch_for_tag(repo, round_id=round_id, tag=tag, result=result)
            save_patch(repo, patch)
            patches.append(patch)
    return patches


def promote_patch(repo: Path, patch: HarnessPatch | str) -> HarnessPatch:
    if isinstance(patch, str):
        patch = load_patch(repo, patch)
    target = Path(patch.target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(patch.content.strip() + "\n", encoding="utf-8")
    patch.status = HarnessPatchStatus.promoted
    save_patch(repo, patch)
    return patch


def reject_patch(repo: Path, patch_id: str) -> HarnessPatch:
    patch = load_patch(repo, patch_id)
    patch.status = HarnessPatchStatus.rejected
    save_patch(repo, patch)
    return patch


def write_flywheel_report(repo: Path, summary: FlywheelSummary) -> Path:
    report_dir = flywheel_dir(repo)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{summary.flywheel_id}.md"
    lines = [
        f"# Flywheel {summary.flywheel_id}",
        "",
        f"- Initial pass rate: {summary.initial_pass_rate * 100:.1f}%",
        f"- Final pass rate: {summary.final_pass_rate * 100:.1f}%",
        f"- Rounds: {len(summary.rounds)}",
        "",
        "## Rounds",
        "",
        "| Round | Benchmark | Pass Rate | Promoted Patches |",
        "| --- | --- | ---: | --- |",
    ]
    for round_record in summary.rounds:
        pass_rate = round_record.pass_rate_after
        pass_text = f"{pass_rate * 100:.1f}%" if pass_rate is not None else "n/a"
        lines.append(
            f"| {round_record.round_number} | `{round_record.benchmark_id or ''}` | "
            f"{pass_text} | {', '.join(f'`{item}`' for item in round_record.patches_promoted) or '-'} |"
        )
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary.report_path = str(report_path)
    latest_path = flywheel_dir(repo) / "latest.json"
    latest_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return report_path


def run_flywheel(
    repo: Path,
    *,
    repo_filter: str,
    target_repo_path: str,
    adapter: str,
    agent: str | None = None,
    limit: int | None = None,
    verification_commands: list[str] | None = None,
    timeout: int | None = None,
    rounds: int = 2,
    auto_promote: bool = True,
) -> FlywheelSummary:
    flywheel_id = f"flywheel_{time.strftime('%Y%m%d_%H%M%S')}"
    flywheel_rounds: list[FlywheelRound] = []
    initial_pass_rate = 0.0
    final_pass_rate = 0.0
    previous_pass_rate: float | None = None

    for round_number in range(1, max(rounds, 1) + 1):
        round_id = f"{flywheel_id}_round_{round_number}"
        benchmark = run_reference_benchmark(
            repo,
            repo_filter=repo_filter,
            target_repo_path=target_repo_path,
            adapter=adapter,
            agent=agent,
            limit=limit,
            verification_commands=verification_commands,
            timeout=timeout,
        )
        final_pass_rate = benchmark.pass_rate
        if round_number == 1:
            initial_pass_rate = benchmark.pass_rate

        proposed = analyze_benchmark_failures(repo, benchmark, round_id=round_id)
        promoted_ids: list[str] = []
        if auto_promote:
            for patch in proposed:
                promote_patch(repo, patch)
                promoted_ids.append(patch.patch_id)

        round_record = FlywheelRound(
            round_id=round_id,
            round_number=round_number,
            ended_at=utc_now(),
            benchmark_id=benchmark.benchmark_id,
            pass_rate_before=previous_pass_rate,
            pass_rate_after=benchmark.pass_rate,
            patches_proposed=[patch.patch_id for patch in proposed],
            patches_promoted=promoted_ids,
            task_ids=[result.task_id for result in benchmark.task_results],
            adapter=adapter,
            report_path=benchmark.report_path,
        )
        rounds_dir(repo).joinpath(f"{round_id}.json").write_text(
            round_record.model_dump_json(indent=2),
            encoding="utf-8",
        )
        flywheel_rounds.append(round_record)
        previous_pass_rate = benchmark.pass_rate

        if benchmark.pass_rate >= 1.0:
            break

    summary = FlywheelSummary(
        flywheel_id=flywheel_id,
        rounds=flywheel_rounds,
        initial_pass_rate=initial_pass_rate,
        final_pass_rate=final_pass_rate,
    )
    write_flywheel_report(repo, summary)
    return summary


def flywheel_status(repo: Path) -> dict[str, object]:
    latest_path = flywheel_dir(repo) / "latest.json"
    status: dict[str, object] = {
        "skills": sorted(path.name for path in (harness_dir(repo) / "skills").glob("*.md")),
        "patches": [patch.model_dump(mode="json") for patch in list_patches(repo)],
    }
    if latest_path.exists():
        status["latest"] = json.loads(latest_path.read_text(encoding="utf-8"))
    return status
