from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AdapterExecution:
    command: str
    cwd: Path
    env: dict[str, str]
    shell: bool = True


class AgentAdapter:
    name: str

    def build_execution(
        self,
        *,
        repo: Path,
        workspace_path: Path,
        agent_input: str | None,
        env: dict[str, str],
    ) -> AdapterExecution:
        raise NotImplementedError

