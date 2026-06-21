from __future__ import annotations

import shlex
from pathlib import Path

from harness_runtime.adapters.base import AdapterExecution, AgentAdapter


def build_codex_prompt(instructions: str) -> str:
    return "\n\n".join(
        [
            "You are running inside a repo-native harness workspace.",
            "Modify the checked-out workspace to satisfy the task.",
            "Prefer minimal, correct changes and stop after the implementation is complete.",
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
        agent_input: str | None,
        env: dict[str, str],
    ) -> AdapterExecution:
        prompt = build_codex_prompt(agent_input or env.get("HARNESS_INSTRUCTIONS", ""))
        command = " ".join(
            [
                "codex",
                "exec",
                "-C",
                shlex.quote(str(workspace_path)),
                "--skip-git-repo-check",
                "--sandbox",
                "workspace-write",
                "--color",
                "never",
                shlex.quote(prompt),
            ]
        )
        return AdapterExecution(command=command, cwd=workspace_path, env=env, shell=True)
