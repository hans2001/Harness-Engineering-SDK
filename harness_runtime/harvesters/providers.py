from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_runtime.schemas import TaskSpec


IssueHarvester = Callable[[Path, str, str | None, str, int, int, list[str] | None], list[TaskSpec]]


@dataclass(frozen=True)
class IssueProvider:
    name: str
    env_token_var: str
    harvest: IssueHarvester


def get_issue_provider(name: str) -> IssueProvider:
    providers = issue_providers()
    try:
        return providers[name]
    except KeyError as error:
        available = ", ".join(sorted(providers))
        raise ValueError(f"Unknown issue provider: {name}. Available providers: {available}") from error


def issue_providers() -> dict[str, IssueProvider]:
    from harness_runtime.harvesters.github import harvest_github_issues

    return {
        "github": IssueProvider(
            name="github",
            env_token_var="GITHUB_TOKEN",
            harvest=harvest_github_issues,
        ),
    }
