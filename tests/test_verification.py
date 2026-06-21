from harness_runtime import Harness


def test_verification_records_pass(tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (tmp_path / "agent.py").write_text("print('noop')\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Verify
source: local
repo_path: .
instructions: Verify command should pass.
verification:
  commands:
    - python -c "raise SystemExit(0)"
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent="python agent.py")
    result = harness.verify(run.id)

    assert result.passed is True
    assert result.commands[0].exit_code == 0


def test_verification_records_missing_executable(tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (tmp_path / "agent.py").write_text("print('noop')\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Verify missing tool
source: local
repo_path: .
instructions: Verification command should fail preflight.
verification:
  commands:
    - missing-verifier --flag
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent="python agent.py")
    result = harness.verify(run.id)

    assert result.passed is False
    assert result.commands[0].exit_code == 127
    assert result.commands[0].failure_reason == "Missing executable on PATH: missing-verifier"
