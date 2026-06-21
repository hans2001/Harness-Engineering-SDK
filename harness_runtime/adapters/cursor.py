from __future__ import annotations

import shlex
from pathlib import Path

from harness_runtime.adapters.base import AdapterExecution, AgentAdapter
from harness_runtime.config import HarnessConfig


def build_cursor_prompt(
    instructions: str,
    *,
    max_runtime_seconds: int,
    max_steps: int,
    max_patch_lines: int,
) -> str:
    return "\n\n".join(
        [
            "You are running inside a repo-native harness workspace.",
            "Modify the checked-out workspace to satisfy the task.",
            "Prefer minimal, correct changes and stop after the implementation is complete.",
            (
                "Execution budget: "
                f"finish within {max_runtime_seconds} seconds, "
                f"use at most {max_steps} meaningful steps, "
                f"and keep the patch under roughly {max_patch_lines} changed lines."
            ),
            "Do not ask interactive questions. Inspect, edit, verify, and stop.",
            "Task instructions:",
            instructions,
        ]
    )


class CursorAdapter(AgentAdapter):
    name = "cursor"

    def build_execution(
        self,
        *,
        repo: Path,
        workspace_path: Path,
        artifact_path: Path,
        agent_input: str | None,
        env: dict[str, str],
        config: HarnessConfig,
    ) -> AdapterExecution:
        prompt = build_cursor_prompt(
            agent_input or env.get("HARNESS_INSTRUCTIONS", ""),
            max_runtime_seconds=config.task_budget.max_runtime_seconds,
            max_steps=config.task_budget.max_steps,
            max_patch_lines=config.task_budget.max_patch_lines,
        )
        cursor_config = config.cursor
        command_parts = [
            shlex.quote(cursor_config.binary),
            "--print",
            "--trust",
            "--workspace",
            shlex.quote(str(workspace_path)),
        ]
        if cursor_config.force:
            command_parts.append("--force")
        if cursor_config.output_format:
            command_parts.extend(["--output-format", shlex.quote(cursor_config.output_format)])
        if cursor_config.sandbox:
            command_parts.extend(["--sandbox", shlex.quote(cursor_config.sandbox)])
        if cursor_config.model:
            command_parts.extend(["--model", shlex.quote(cursor_config.model)])
        if cursor_config.mode:
            command_parts.extend(["--mode", shlex.quote(cursor_config.mode)])
        command_parts.append(shlex.quote(prompt))
        command = " ".join(command_parts)
        return AdapterExecution(command=command, cwd=workspace_path, env=env, shell=True)
