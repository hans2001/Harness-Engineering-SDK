from __future__ import annotations

from collections.abc import Callable
from importlib import metadata as importlib_metadata

from harness_runtime.adapters.base import AgentAdapter
from harness_runtime.adapters.codex import CodexAdapter
from harness_runtime.adapters.cursor import CursorAdapter
from harness_runtime.adapters.shell import ShellAdapter


AdapterFactory = Callable[[], AgentAdapter]
ENTRY_POINT_GROUP = "harness_runtime.adapters"

_ADAPTER_FACTORIES: dict[str, AdapterFactory] = {}
_DISCOVERED_ENTRY_POINTS = False


def register_adapter(name: str, factory: AdapterFactory, *, replace: bool = False) -> None:
    if not name:
        raise ValueError("Adapter name must be non-empty.")
    if not replace and name in _ADAPTER_FACTORIES:
        raise ValueError(f"Adapter already registered: {name}")
    _ADAPTER_FACTORIES[name] = factory


def unregister_adapter(name: str) -> None:
    _ADAPTER_FACTORIES.pop(name, None)


def reset_adapters() -> None:
    global _DISCOVERED_ENTRY_POINTS
    _ADAPTER_FACTORIES.clear()
    _DISCOVERED_ENTRY_POINTS = False
    register_builtin_adapters()


def register_builtin_adapters() -> None:
    register_adapter("codex", CodexAdapter, replace=True)
    register_adapter("cursor", CursorAdapter, replace=True)
    register_adapter("shell", ShellAdapter, replace=True)


def discover_entry_point_adapters() -> None:
    global _DISCOVERED_ENTRY_POINTS
    if _DISCOVERED_ENTRY_POINTS:
        return
    for entry_point in iter_entry_points(ENTRY_POINT_GROUP):
        loaded = entry_point.load()
        factory = normalize_adapter_factory(loaded)
        register_adapter(entry_point.name, factory, replace=True)
    _DISCOVERED_ENTRY_POINTS = True


def list_adapters() -> dict[str, AgentAdapter]:
    if not _ADAPTER_FACTORIES:
        register_builtin_adapters()
    discover_entry_point_adapters()
    return {name: factory() for name, factory in sorted(_ADAPTER_FACTORIES.items())}


def get_adapter(name: str) -> AgentAdapter:
    adapters = list_adapters()
    try:
        return adapters[name]
    except KeyError as error:
        available = ", ".join(sorted(adapters))
        raise ValueError(f"Unknown adapter: {name}. Available adapters: {available}") from error


def normalize_adapter_factory(value: object) -> AdapterFactory:
    if isinstance(value, AgentAdapter):
        return lambda: value
    if isinstance(value, type) and issubclass(value, AgentAdapter):
        return value
    if callable(value):
        def factory() -> AgentAdapter:
            created = value()
            if not isinstance(created, AgentAdapter):
                raise TypeError("Adapter entry point factory must return an AgentAdapter instance.")
            return created

        return factory
    raise TypeError("Adapter entry point must be an AgentAdapter instance, subclass, or factory.")


def iter_entry_points(group: str) -> list[importlib_metadata.EntryPoint]:
    try:
        return list(importlib_metadata.entry_points(group=group))
    except TypeError:
        return list(importlib_metadata.entry_points().select(group=group))


register_builtin_adapters()
