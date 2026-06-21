import json

from harness_runtime import Harness


def test_build_github_eval_dataset_from_harvested_tasks(tmp_path):
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
    entries = harness.build_github_eval_dataset(repo_filter="acme/widgets")

    assert len(entries) == 1
    assert entries[0].task_id == "github_acme_widgets_12"
    assert entries[0].repo_ref == "baseline_parent_sha"
    assert entries[0].linked_pull_request_numbers == [45]
    assert entries[0].linked_pull_request_urls == ["https://github.com/acme/widgets/pull/45"]
    assert entries[0].reference_paths == ["python/widgets/parser.py", "tests/test_parser.py"]

    jsonl_path = tmp_path / ".harness" / "datasets" / "github_linked_pr_eval.jsonl"
    lines = jsonl_path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["repo_full_name"] == "acme/widgets"


def test_explicit_repo_ref_wins_over_inferred_baseline(tmp_path):
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
repo_ref: explicit_ref_sha
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
      baseline_sha: inferred_baseline_sha
"""
    )

    harness.harvest(".harness/tasks")
    entries = harness.build_github_eval_dataset(repo_filter="acme/widgets")

    assert len(entries) == 1
    assert entries[0].repo_ref == "explicit_ref_sha"
