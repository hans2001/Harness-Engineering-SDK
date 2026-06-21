from __future__ import annotations

from harness_runtime.schemas import TaskSpec


def suggest_verification_commands(task: TaskSpec) -> list[str]:
    repo_full_name = str(task.metadata.get("repo_full_name") or "")
    title = task.title.lower()
    instructions = task.instructions.lower()
    reference_paths = referenced_paths(task)

    if repo_full_name == "sgl-project/sglang":
        if any(path.startswith("experimental/sgl-router/") for path in reference_paths):
            return ["cargo test --manifest-path experimental/sgl-router/Cargo.toml"]
        if any(path.startswith("sgl-model-gateway/") for path in reference_paths):
            return ["cargo test --manifest-path sgl-model-gateway/Cargo.toml"]
        if "[router]" in title or "router" in instructions:
            return ["cargo test --manifest-path sgl-model-gateway/Cargo.toml"]
        return ["python -m pytest test -q"]

    return list(task.verification.commands) or ["pytest"]


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
