from pathlib import Path

from harness_runtime import Harness


def test_run_artifact_creation(tmp_path):
    repo = tmp_path
    (repo / "agent.py").write_text("print('agent ran')\n")
    task_dir = repo / "tasks"
    task_dir.mkdir()
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Smoke
source: local
repo_path: .
instructions: Run smoke agent.
verification:
  commands:
    - python -c "print('ok')"
"""
    )

    harness = Harness(repo)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent="python agent.py")

    artifact_path = Path(run.artifact_path)
    assert (artifact_path / "run.json").exists()
    assert (artifact_path / "stdout.log").read_text().strip() == "agent ran"
    assert (artifact_path / "stderr.log").exists()
    assert (artifact_path / "diff.patch").exists()
    assert run.agent_adapter == "shell"


def test_run_timeout_still_writes_artifacts(tmp_path):
    repo = tmp_path
    task_dir = repo / "tasks"
    task_dir.mkdir()
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Timeout
source: local
repo_path: .
instructions: Sleep too long.
verification:
  commands:
    - python -c "print('ok')"
"""
    )

    harness = Harness(repo)
    harness.init()
    harness.harvest("tasks")
    run = harness.run(
        "task_001",
        agent='python -c "import time; time.sleep(2)"',
        timeout=1,
    )

    artifact_path = Path(run.artifact_path)
    assert run.status == "failed"
    assert run.exit_code == 124
    assert run.metadata["timed_out"] is True
    assert (artifact_path / "run.json").exists()
    assert (artifact_path / "stderr.log").read_text().strip().endswith("Agent timed out after 1s.")
