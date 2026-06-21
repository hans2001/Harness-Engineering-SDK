from harness_runtime import Harness
from harness_runtime.datasets import manager as dataset_manager


def test_materialize_eval_tasks_creates_generated_tasks(tmp_path):
    harness = Harness(tmp_path)
    harness.init()
    task_dir = tmp_path / ".harness" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "github_acme_widgets_12.yaml").write_text(
        """
id: github_acme_widgets_12
title: Fix flaky parser
source: github
repo_path: .
instructions: Fix flaky parser.
verification:
  commands:
    - pytest
metadata:
  repo_full_name: acme/widgets
  issue_number: 12
  issue_url: https://github.com/acme/widgets/issues/12
  labels:
    - bug
  assignees:
    - alice
  milestone: v1.0
  author: reporter
  state: open
  state_reason:
  created_at: 2026-01-01T00:00:00Z
  updated_at: 2026-01-02T00:00:00Z
  closed_at:
  linked_pull_requests:
    - number: 45
      title: Fix parser edge case
      url: https://github.com/acme/widgets/pull/45
      state: closed
      baseline_sha: baseline_parent_sha
      head_sha: commit_head_sha
      files:
        - python/widgets/parser.py
        - tests/test_parser.py
"""
    )

    harness.harvest(".harness/tasks")
    tasks = harness.materialize_eval_tasks(
        target_repo_path="../sglang-target",
        repo_filter="acme/widgets",
        verification_commands=["python -m pytest tests"],
    )

    assert len(tasks) == 1
    assert tasks[0].id == "eval_github_acme_widgets_12"
    assert tasks[0].repo_path == "../sglang-target"
    assert tasks[0].repo_ref == "baseline_parent_sha"
    assert tasks[0].verification.commands == ["python -m pytest tests"]
    assert "Reference fix file hints:" in tasks[0].instructions
    assert "python/widgets/parser.py" in tasks[0].instructions


def test_materialize_eval_tasks_resolves_repo_ref_from_target_repo(tmp_path, monkeypatch):
    harness = Harness(tmp_path)
    harness.init()
    task_dir = tmp_path / ".harness" / "tasks"
    target_repo_dir = tmp_path / "sglang-target"
    task_dir.mkdir(parents=True, exist_ok=True)
    target_repo_dir.mkdir()
    (task_dir / "github_acme_widgets_12.yaml").write_text(
        """
id: github_acme_widgets_12
title: Fix flaky parser
source: github
repo_path: .
instructions: Fix flaky parser.
verification:
  commands:
    - pytest
metadata:
  repo_full_name: acme/widgets
  issue_number: 12
  issue_url: https://github.com/acme/widgets/issues/12
  linked_pull_requests:
    - number: 45
      title: Fix parser edge case
      url: https://github.com/acme/widgets/pull/45
      state: closed
"""
    )

    monkeypatch.setattr(
        dataset_manager,
        "resolve_github_pull_request_baseline",
        lambda target_repo_path, pr_number: "resolved_from_target_repo_sha",
    )
    monkeypatch.setattr(dataset_manager, "is_git_repo", lambda path: True)

    harness.harvest(".harness/tasks")
    tasks = harness.materialize_eval_tasks(target_repo_path="sglang-target", repo_filter="acme/widgets")

    assert len(tasks) == 1
    assert tasks[0].repo_ref == "resolved_from_target_repo_sha"
