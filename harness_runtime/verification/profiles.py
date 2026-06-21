from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Callable

from harness_runtime.schemas import TaskSpec


VerificationProfileMatcher = Callable[[TaskSpec], bool]
VerificationCommandSuggester = Callable[[TaskSpec], list[str]]
ENTRY_POINT_GROUP = "harness_runtime.verification_profiles"


@dataclass(frozen=True)
class VerificationProfile:
    name: str
    matches: VerificationProfileMatcher
    suggest: VerificationCommandSuggester
    priority: int = 100


_VERIFICATION_PROFILES: dict[str, VerificationProfile] = {}
_DISCOVERED_ENTRY_POINTS = False


def register_verification_profile(profile: VerificationProfile, *, replace: bool = False) -> None:
    if not profile.name:
        raise ValueError("Verification profile name must be non-empty.")
    if not replace and profile.name in _VERIFICATION_PROFILES:
        raise ValueError(f"Verification profile already registered: {profile.name}")
    _VERIFICATION_PROFILES[profile.name] = profile


def unregister_verification_profile(name: str) -> None:
    _VERIFICATION_PROFILES.pop(name, None)


def reset_verification_profiles() -> None:
    global _DISCOVERED_ENTRY_POINTS
    _VERIFICATION_PROFILES.clear()
    _DISCOVERED_ENTRY_POINTS = False
    register_builtin_verification_profiles()


def register_builtin_verification_profiles() -> None:
    register_verification_profile(
        VerificationProfile(
            name="sglang",
            matches=lambda task: str(task.metadata.get("repo_full_name") or "") == "sgl-project/sglang",
            suggest=suggest_sglang_verification_commands,
            priority=10,
        ),
        replace=True,
    )


def discover_entry_point_verification_profiles() -> None:
    global _DISCOVERED_ENTRY_POINTS
    if _DISCOVERED_ENTRY_POINTS:
        return
    for entry_point in iter_entry_points(ENTRY_POINT_GROUP):
        loaded = entry_point.load()
        profile = normalize_verification_profile(loaded)
        register_verification_profile(profile, replace=True)
    _DISCOVERED_ENTRY_POINTS = True


def verification_profiles() -> dict[str, VerificationProfile]:
    if not _VERIFICATION_PROFILES:
        register_builtin_verification_profiles()
    discover_entry_point_verification_profiles()
    return dict(sorted(_VERIFICATION_PROFILES.items()))


def suggest_verification_commands(task: TaskSpec) -> list[str]:
    for profile in sorted(verification_profiles().values(), key=lambda item: (item.priority, item.name)):
        if profile.matches(task):
            return profile.suggest(task)
    return list(task.verification.commands) or ["pytest"]


def suggest_sglang_verification_commands(task: TaskSpec) -> list[str]:
    title = task.title.lower()
    instructions = task.instructions.lower()
    reference_paths = referenced_paths(task)

    if any(path.startswith("experimental/sgl-router/") for path in reference_paths):
        return ["cargo test --manifest-path experimental/sgl-router/Cargo.toml"]
    if any(path.startswith("sgl-model-gateway/") for path in reference_paths):
        return ["cargo test --manifest-path sgl-model-gateway/Cargo.toml"]
    if "[router]" in title or "router" in instructions:
        return ["cargo test --manifest-path sgl-model-gateway/Cargo.toml"]
    return ["python -m pytest test -q"]


def referenced_paths(task: TaskSpec) -> list[str]:
    paths = list(task.metadata.get("reference_paths") or [])
    if paths:
        return [path for path in paths if isinstance(path, str)]

    linked_pull_requests = task.metadata.get("linked_pull_requests") or []
    discovered: list[str] = []
    for pull_request in linked_pull_requests:
        for path in pull_request.get("files") or []:
            if isinstance(path, str):
                discovered.append(path)
    return discovered


def normalize_verification_profile(value: object) -> VerificationProfile:
    if isinstance(value, VerificationProfile):
        return value
    if callable(value):
        created = value()
        if not isinstance(created, VerificationProfile):
            raise TypeError("Verification profile entry point factory must return a VerificationProfile instance.")
        return created
    raise TypeError("Verification profile entry point must be a VerificationProfile instance or factory.")


def iter_entry_points(group: str) -> list[importlib_metadata.EntryPoint]:
    try:
        return list(importlib_metadata.entry_points(group=group))
    except TypeError:
        return list(importlib_metadata.entry_points().select(group=group))


register_builtin_verification_profiles()
