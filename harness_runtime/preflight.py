from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

from harness_runtime.schemas import PreflightCheck, PreflightResult, TaskSpec


def run_preflight(repo: Path, commands: list[str]) -> PreflightResult:
    return PreflightResult(
        repo=str(repo),
        commands=[check_command(command, env=preflight_env()) for command in commands],
    )


def task_preflight(repo: Path, task: TaskSpec) -> PreflightResult:
    return run_preflight(repo, list(task.verification.commands))


def check_command(command: str, env: dict[str, str] | None = None) -> PreflightCheck:
    executable = first_executable(command)
    if executable is None:
        return PreflightCheck(
            command=command,
            executable=None,
            available=True,
            message="Skipped executable detection for shell-only command.",
        )

    resolved = shutil.which(executable, path=(env or os.environ).get("PATH"))
    if resolved:
        return PreflightCheck(
            command=command,
            executable=executable,
            available=True,
            message=f"Found executable at {resolved}",
        )
    return PreflightCheck(
        command=command,
        executable=executable,
        available=False,
        message=f"Missing executable on PATH: {executable}",
    )


def first_executable(command: str) -> str | None:
    try:
        parts = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not parts:
        return None

    executable = parts[0]
    if executable in {"env", "command"} and len(parts) > 1:
        executable = next_non_assignment(parts[1:])
    if executable is None:
        return None
    if has_shell_metachar(executable):
        return None
    return executable


def next_non_assignment(parts: list[str]) -> str | None:
    for part in parts:
        if "=" in part and not part.startswith(("/", "./", "../")):
            key, _, value = part.partition("=")
            if key.isidentifier() and value:
                continue
        return part
    return None


def has_shell_metachar(value: str) -> bool:
    return any(char in value for char in "|&;()<>*$?")


def preflight_env() -> dict[str, str]:
    env = os.environ.copy()
    python_bin = str(Path(sys.executable).parent)
    env["PATH"] = f"{python_bin}{os.pathsep}{env.get('PATH', '')}"
    return env
