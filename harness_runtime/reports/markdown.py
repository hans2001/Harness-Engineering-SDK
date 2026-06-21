from __future__ import annotations

import time
from pathlib import Path

from harness_runtime.config import harness_dir
from harness_runtime.datasets import build_eval_summary
from harness_runtime.storage import Storage


def generate_report(repo: Path) -> Path:
    storage = Storage(repo)
    runs = storage.list_runs()
    verifications = {item.run_id: item for item in storage.list_verifications()}
    summary = build_eval_summary(repo)

    report_path = harness_dir(repo) / "reports" / f"report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Harness Report",
        "",
        "## Summary",
        "",
        f"- Total runs: {summary.total_runs}",
        f"- Verified runs: {summary.verified_runs}",
        f"- Passed runs: {summary.passed_runs}",
        f"- Pass rate: {summary.pass_rate:.1%}",
        "",
        "## Runs",
        "",
        "| Run | Task | Status | Duration | Verification | Artifacts |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for run in runs:
        verification = verifications.get(run.id)
        duration = f"{run.duration_seconds:.2f}s" if run.duration_seconds is not None else ""
        verification_text = "not run" if verification is None else ("passed" if verification.passed else "failed")
        artifact_rel = Path(run.artifact_path).relative_to(repo)
        lines.append(
            f"| `{run.id}` | `{run.task_id}` | `{run.status}` | {duration} | "
            f"{verification_text} | [{artifact_rel}]({artifact_rel}) |"
        )

    lines.extend(["", "## Failed Commands", ""])
    if summary.failed_commands:
        lines.extend(f"- `{command}`" for command in summary.failed_commands)
    else:
        lines.append("- None")
    lines.append("")

    lines.extend(["## Verification Notes", ""])
    noted = False
    for verification in verifications.values():
        for command in verification.commands:
            if not command.failure_reason:
                continue
            lines.append(f"- `{verification.run_id}` `{command.command}`: {command.failure_reason}")
            noted = True
    if not noted:
        lines.append("- None")
    lines.append("")

    report_path.write_text("\n".join(lines))
    return report_path
