from __future__ import annotations

import sys
from pathlib import Path

from harness_runtime.adapters.base import AdapterExecution, AgentAdapter


class MockAdapter(AgentAdapter):
    name = "mock"

    def build_execution(
        self,
        *,
        repo: Path,
        workspace_path: Path,
        agent_input: str | None,
        env: dict[str, str],
    ) -> AdapterExecution:
        command = f'"{Path(sys.executable)}" examples/mock_agent.py'
        return AdapterExecution(command=command, cwd=workspace_path, env=env, shell=True)

