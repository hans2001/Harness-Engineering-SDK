from __future__ import annotations

import shlex
from pathlib import Path

from harness_runtime.config import HarnessConfig
from harness_runtime.adapters.base import AdapterExecution, AgentAdapter
from harness_runtime.skills import append_harness_context


def build_codex_prompt(
    instructions: str,
    *,
    max_runtime_seconds: int,
    max_steps: int,
    max_patch_lines: int,
    harness_context: str = "",
) -> str:
    instructions = append_harness_context(instructions, harness_context)
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


class CodexAdapter(AgentAdapter):
    name = "codex"

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
        prompt = build_codex_prompt(
            agent_input or env.get("HARNESS_INSTRUCTIONS", ""),
            max_runtime_seconds=config.task_budget.max_runtime_seconds,
            max_steps=config.task_budget.max_steps,
            max_patch_lines=config.task_budget.max_patch_lines,
            harness_context=env.get("HARNESS_SKILLS_CONTEXT", ""),
        )
        codex_config = config.codex
        last_message_path = artifact_path / "agent_last_message.txt"
        command_parts = [
            "codex",
            "exec",
            "-C",
            shlex.quote(str(workspace_path)),
            "--skip-git-repo-check",
            "--sandbox",
            shlex.quote(codex_config.sandbox),
            "--color",
            shlex.quote(codex_config.color),
        ]
        if codex_config.json_output:
            command_parts.append("--json")
        if codex_config.ephemeral:
            command_parts.append("--ephemeral")
        if codex_config.ignore_user_config:
            command_parts.append("--ignore-user-config")
        if codex_config.ignore_rules:
            command_parts.append("--ignore-rules")
        if codex_config.output_last_message:
            command_parts.extend(["-o", shlex.quote(str(last_message_path))])
        if codex_config.model:
            command_parts.extend(["--model", shlex.quote(codex_config.model)])
        if codex_config.profile:
            command_parts.extend(["--profile", shlex.quote(codex_config.profile)])
        command_parts.append(shlex.quote(prompt))
        command = " ".join(command_parts)
        return AdapterExecution(command=command, cwd=workspace_path, env=env, shell=True)
