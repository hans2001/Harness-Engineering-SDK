from pathlib import Path

from harness_runtime import Harness


def test_verify_cleanup_removes_workspace_but_keeps_artifacts(tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (tmp_path / "agent.py").write_text("print('noop')\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Cleanup
source: local
repo_path: .
instructions: Verify then cleanup.
verification:
  commands:
    - python -c "print('verified')"
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent="python agent.py")
    workspace_path = Path(run.workspace_path)
    artifact_path = Path(run.artifact_path)

    assert workspace_path.exists()
    result = harness.verify(run.id, cleanup=True)

    assert result.passed is True
    assert not workspace_path.exists()
    assert (artifact_path / "run.json").exists()
    assert (artifact_path / "verification.json").exists()

