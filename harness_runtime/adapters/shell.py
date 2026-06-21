from __future__ import annotations

from pathlib import Path

from harness_runtime.adapters.base import AdapterExecution, AgentAdapter


class ShellAdapter(AgentAdapter):
    name = "shell"

    def build_execution(
        self,
        *,
        repo: Path,
        workspace_path: Path,
        agent_input: str | None,
        env: dict[str, str],
    ) -> AdapterExecution:
        if not agent_input:
            raise ValueError("Shell adapter requires an agent command.")
        return AdapterExecution(command=agent_input, cwd=workspace_path, env=env, shell=True)

