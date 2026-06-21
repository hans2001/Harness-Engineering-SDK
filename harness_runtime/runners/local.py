from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from harness_runtime.adapters import get_adapter
from harness_runtime.config import harness_dir, load_config
from harness_runtime.repo import capture_diff, cleanup_workspace, create_workspace
from harness_runtime.schemas import RunRecord, RunStatus, TaskSpec, utc_now
from harness_runtime.storage import Storage


def run_task(
    repo: Path,
    task: TaskSpec,
    agent_input: str | None,
    adapter_name: str = "shell",
    timeout: int | None = None,
    keep_workspace: bool = True,
) -> RunRecord:
    config = load_config(repo)
    run_id = f"run_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    artifact_path = harness_dir(repo) / "runs" / run_id
    workspace_path = harness_dir(repo) / "worktrees" / run_id
    baseline_path = harness_dir(repo) / "worktrees" / f"{run_id}_baseline"
    artifact_path.mkdir(parents=True, exist_ok=True)

    task_repo_path = (repo / task.repo_path).resolve()
    workspace_ref = task.repo_ref or "HEAD"
    mode, base_sha = create_workspace(
        task_repo_path,
        workspace_path,
        config.ignore_patterns,
        ref=workspace_ref,
    )
    if mode == "copy":
        shutil.copytree(workspace_path, baseline_path)
    adapter = get_adapter(adapter_name)

    run = RunRecord(
        id=run_id,
        task_id=task.id,
        agent_adapter=adapter_name,
        agent_command=agent_input or "",
        repo_path=str(task_repo_path),
        workspace_path=str(workspace_path),
        artifact_path=str(artifact_path),
        base_sha=base_sha,
        status=RunStatus.running,
        stdout_path=str(artifact_path / "stdout.log"),
        stderr_path=str(artifact_path / "stderr.log"),
        diff_path=str(artifact_path / "diff.patch"),
        metadata={"workspace_mode": mode, "workspace_ref": workspace_ref},
    )
    Storage(repo).save_run(run)

    start = time.monotonic()
    env = allowed_env(os.environ, config.env_allowlist)
    env["PATH"] = prepend_current_python_bin(env.get("PATH", ""))
    env.update(
        {
            "HARNESS_RUN_ID": run_id,
            "HARNESS_TASK_ID": task.id,
            "HARNESS_WORKSPACE": str(workspace_path),
            "HARNESS_INSTRUCTIONS": task.instructions,
        }
    )
    execution = adapter.build_execution(
        repo=repo,
        workspace_path=workspace_path,
        agent_input=agent_input,
        env=env,
    )

    result = subprocess.run(
        execution.command,
        cwd=execution.cwd,
        shell=execution.shell,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=execution.env,
        check=False,
    )
    duration = time.monotonic() - start

    Path(run.stdout_path).write_text(redact(result.stdout))
    Path(run.stderr_path).write_text(redact(result.stderr))
    capture_diff(workspace_path, baseline_path if baseline_path.exists() else None, Path(run.diff_path))
    if baseline_path.exists():
        shutil.rmtree(baseline_path)

    run.status = RunStatus.completed if result.returncode == 0 else RunStatus.failed
    run.exit_code = result.returncode
    run.duration_seconds = duration
    run.ended_at = utc_now()
    if not keep_workspace:
        cleanup_workspace(task_repo_path, workspace_path)
        run.metadata["workspace_removed"] = True
    (artifact_path / "run.json").write_text(run.model_dump_json(indent=2))
    (artifact_path / "trace.jsonl").write_text(
        '{"event":"agent_completed","run_id":"%s","adapter":"%s","exit_code":%s}\n'
        % (run_id, adapter_name, result.returncode)
    )
    Storage(repo).save_run(run)
    return run


def allowed_env(source: os._Environ[str], allowlist: list[str]) -> dict[str, str]:
    return {key: source[key] for key in allowlist if key in source}


def prepend_current_python_bin(path: str) -> str:
    python_bin = str(Path(sys.executable).parent)
    return f"{python_bin}{os.pathsep}{path}" if path else python_bin


def redact(text: str) -> str:
    import re

    patterns = [
        r"(?i)(api[_-]?key|token|secret|password)=\S+",
        r"ghp_[A-Za-z0-9_]+",
        r"sk-[A-Za-z0-9_-]+",
    ]
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted
