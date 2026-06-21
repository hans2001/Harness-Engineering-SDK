from __future__ import annotations

from harness_runtime.adapters.base import AgentAdapter
from harness_runtime.adapters.codex import CodexAdapter
from harness_runtime.adapters.shell import ShellAdapter


def list_adapters() -> dict[str, AgentAdapter]:
    return {
        "codex": CodexAdapter(),
        "shell": ShellAdapter(),
    }


def get_adapter(name: str) -> AgentAdapter:
    adapters = list_adapters()
    try:
        return adapters[name]
    except KeyError as error:
        available = ", ".join(sorted(adapters))
        raise ValueError(f"Unknown adapter: {name}. Available adapters: {available}") from error
