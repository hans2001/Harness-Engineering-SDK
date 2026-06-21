from harness_runtime.schemas import TaskSpec, load_task


def test_task_parsing(tmp_path):
    path = tmp_path / "task.yaml"
    path.write_text(
        """
id: task_001
title: Fix failing test
source: local
repo_path: .
instructions: Fix it.
verification:
  commands:
    - pytest
"""
    )

    task = load_task(path)

    assert isinstance(task, TaskSpec)
    assert task.id == "task_001"
    assert task.verification.commands == ["pytest"]

