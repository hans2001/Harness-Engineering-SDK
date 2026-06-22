from types import SimpleNamespace

from harness_runtime.sdk import Harness
from harness_runtime.verification import (
    VerificationProfile,
    register_verification_profile,
    reset_verification_profiles,
    suggest_verification_commands,
    unregister_verification_profile,
)
from harness_runtime.verification import profiles as profile_registry
from harness_runtime.schemas import TaskSpec, VerificationSpec


def test_sglang_router_task_uses_reference_paths_for_verification_profile(tmp_path):
    harness = Harness(tmp_path)
    harness.init()
    task_dir = tmp_path / ".harness" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "github_sgl-project_sglang_28227.yaml").write_text(
        """
id: github_sgl-project_sglang_28227
title: "[Router] power_of_two policy is O(n) in worker count"
source: github
repo_path: .
instructions: |
  [Router] power_of_two policy is O(n) in worker count
  Since workers is a slice, this should be constant time.
verification:
  commands:
    - pytest
metadata:
  repo_full_name: sgl-project/sglang
  issue_number: 28227
  issue_url: https://github.com/sgl-project/sglang/issues/28227
  reference_paths:
    - experimental/sgl-router/src/policies/power_of_two.rs
  linked_pull_requests:
    - number: 28228
      title: fix
      url: https://github.com/sgl-project/sglang/pull/28228
      state: closed
"""
    )

    harness.harvest(".harness/tasks")
    tasks = harness.materialize_eval_tasks(target_repo_path="../sglang-target", repo_filter="sgl-project/sglang")

    assert len(tasks) == 1
    assert tasks[0].verification.commands == ["cargo test --manifest-path experimental/sgl-router/Cargo.toml"]


def test_custom_verification_profile_can_override_defaults():
    task = TaskSpec(
        id="task_001",
        title="Node smoke",
        source="local",
        repo_path=".",
        instructions="Run node checks.",
        verification=VerificationSpec(commands=[]),
        metadata={"repo_full_name": "acme/web"},
    )
    profile = VerificationProfile(
        name="web-js",
        priority=5,
        matches=lambda candidate: candidate.metadata.get("repo_full_name") == "acme/web",
        suggest=lambda candidate: ["pnpm test", "pnpm lint"],
    )

    reset_verification_profiles()
    register_verification_profile(profile)

    try:
        assert suggest_verification_commands(task) == ["pnpm test", "pnpm lint"]
    finally:
        unregister_verification_profile("web-js")
        reset_verification_profiles()


def test_verification_profile_registry_discovers_entry_points(monkeypatch):
    profile = VerificationProfile(
        name="entry-go",
        priority=1,
        matches=lambda task: task.metadata.get("repo_full_name") == "acme/go-service",
        suggest=lambda task: ["go test ./..."],
    )
    task = TaskSpec(
        id="task_002",
        title="Go service",
        source="local",
        repo_path=".",
        instructions="Run go tests.",
        verification=VerificationSpec(commands=[]),
        metadata={"repo_full_name": "acme/go-service"},
    )

    reset_verification_profiles()
    monkeypatch.setattr(
        profile_registry,
        "iter_entry_points",
        lambda group: [SimpleNamespace(name="entry-go", load=lambda: profile)],
    )

    assert suggest_verification_commands(task) == ["go test ./..."]
    reset_verification_profiles()
