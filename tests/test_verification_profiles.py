from harness_runtime.datasets.manager import materialize_eval_tasks
from harness_runtime.sdk import Harness


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
