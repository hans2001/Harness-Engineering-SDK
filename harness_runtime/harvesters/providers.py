from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Callable

from harness_runtime.schemas import TaskSpec


IssueHarvester = Callable[[Path, str, str | None, str, int, int, list[str] | None, bool], list[TaskSpec]]
ENTRY_POINT_GROUP = "harness_runtime.issue_providers"


@dataclass(frozen=True)
class IssueProvider:
    name: str
    env_token_var: str
    harvest: IssueHarvester


_ISSUE_PROVIDERS: dict[str, IssueProvider] = {}
_DISCOVERED_ENTRY_POINTS = False


def register_issue_provider(provider: IssueProvider, *, replace: bool = False) -> None:
    if not provider.name:
        raise ValueError("Issue provider name must be non-empty.")
    if not replace and provider.name in _ISSUE_PROVIDERS:
        raise ValueError(f"Issue provider already registered: {provider.name}")
    _ISSUE_PROVIDERS[provider.name] = provider


def unregister_issue_provider(name: str) -> None:
    _ISSUE_PROVIDERS.pop(name, None)


def reset_issue_providers() -> None:
    global _DISCOVERED_ENTRY_POINTS
    _ISSUE_PROVIDERS.clear()
    _DISCOVERED_ENTRY_POINTS = False
    register_builtin_issue_providers()


def register_builtin_issue_providers() -> None:
    from harness_runtime.harvesters.github import harvest_github_issues

    register_issue_provider(
        IssueProvider(
            name="github",
            env_token_var="GITHUB_TOKEN",
            harvest=harvest_github_issues,
        ),
        replace=True,
    )


def discover_entry_point_issue_providers() -> None:
    global _DISCOVERED_ENTRY_POINTS
    if _DISCOVERED_ENTRY_POINTS:
        return
    for entry_point in iter_entry_points(ENTRY_POINT_GROUP):
        loaded = entry_point.load()
        provider = normalize_issue_provider(loaded)
        register_issue_provider(provider, replace=True)
    _DISCOVERED_ENTRY_POINTS = True


def get_issue_provider(name: str) -> IssueProvider:
    providers = issue_providers()
    try:
        return providers[name]
    except KeyError as error:
        available = ", ".join(sorted(providers))
        raise ValueError(f"Unknown issue provider: {name}. Available providers: {available}") from error


def issue_providers() -> dict[str, IssueProvider]:
    if not _ISSUE_PROVIDERS:
        register_builtin_issue_providers()
    discover_entry_point_issue_providers()
    return dict(sorted(_ISSUE_PROVIDERS.items()))


def normalize_issue_provider(value: object) -> IssueProvider:
    if isinstance(value, IssueProvider):
        return value
    if callable(value):
        created = value()
        if not isinstance(created, IssueProvider):
            raise TypeError("Issue provider entry point factory must return an IssueProvider instance.")
        return created
    raise TypeError("Issue provider entry point must be an IssueProvider instance or factory.")


def iter_entry_points(group: str) -> list[importlib_metadata.EntryPoint]:
    try:
        return list(importlib_metadata.entry_points(group=group))
    except TypeError:
        return list(importlib_metadata.entry_points().select(group=group))


register_builtin_issue_providers()
