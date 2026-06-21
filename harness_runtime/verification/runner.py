from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from harness_runtime.preflight import check_command
from harness_runtime.repo import cleanup_workspace
from harness_runtime.schemas import CommandResult, RunStatus, TaskSpec, VerificationResult, utc_now
from harness_runtime.storage import Storage


def verify_run(repo: Path, run_id: str, task: TaskSpec, cleanup: bool = False) -> VerificationResult:
    storage = Storage(repo)
    run = storage.get_run(run_id)
    artifact_path = Path(run.artifact_path)
    workspace_path = Path(run.workspace_path)
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace for {run_id} is missing. Re-run without --cleanup, or verify before cleanup."
        )

    result = VerificationResult(run_id=run_id, task_id=task.id)
    log_dir = artifact_path / "verification"
    log_dir.mkdir(parents=True, exist_ok=True)

    for index, command in enumerate(task.verification.commands, start=1):
        preflight = check_command(command, env=verification_env())
        stdout_path = log_dir / f"{index}_stdout.log"
        stderr_path = log_dir / f"{index}_stderr.log"
        if not preflight.available:
            stdout_path.write_text("")
            stderr_path.write_text(preflight.message)
            result.commands.append(
                CommandResult(
                    command=command,
                    exit_code=127,
                    duration_seconds=0.0,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    passed=False,
                    failure_reason=preflight.message,
                )
            )
            continue

        start = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=workspace_path,
            shell=True,
            text=True,
            capture_output=True,
            env=verification_env(),
            check=False,
        )
        duration = time.monotonic() - start
        stdout_path.write_text(completed.stdout)
        stderr_path.write_text(completed.stderr)
        result.commands.append(
            CommandResult(
                command=command,
                exit_code=completed.returncode,
                duration_seconds=duration,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                passed=completed.returncode == 0,
                failure_reason=None if completed.returncode == 0 else "Command exited non-zero.",
            )
        )

    result.ended_at = utc_now()
    result.passed = all(command.passed for command in result.commands)
    verification_json = artifact_path / "verification.json"
    verification_md = artifact_path / "verification.md"
    verification_json.write_text(result.model_dump_json(indent=2))
    verification_md.write_text(render_verification(result))

    run.status = RunStatus.verified
    run.verification_path = str(verification_md)
    if cleanup:
        cleanup_workspace(Path(run.repo_path), workspace_path)
        run.metadata["workspace_removed"] = True
    storage.save_run(run)
    storage.save_verification(result)
    return result


def render_verification(result: VerificationResult) -> str:
    lines = [
        f"# Verification {result.run_id}",
        "",
        f"Passed: `{result.passed}`",
        "",
        "| Command | Exit Code | Duration | Passed |",
        "| --- | ---: | ---: | --- |",
    ]
    for command in result.commands:
        lines.append(
            f"| `{command.command}` | {command.exit_code} | "
            f"{command.duration_seconds:.2f}s | `{command.passed}` |"
        )
        if command.failure_reason:
            lines.append(f"- Failure: {command.failure_reason}")
    lines.append("")
    return "\n".join(lines)


def verification_env() -> dict[str, str]:
    env = os.environ.copy()
    python_bin = str(Path(sys.executable).parent)
    env["PATH"] = f"{python_bin}{os.pathsep}{env.get('PATH', '')}"
    return env
