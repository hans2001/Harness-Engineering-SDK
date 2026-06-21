from harness_runtime import Harness


def test_eval_can_run_all_tasks_with_agent(tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (tmp_path / "agent.py").write_text("print('batch')\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Batch Eval
source: local
repo_path: .
instructions: Run batch eval.
verification:
  commands:
    - python -c "print('verified')"
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    summary = harness.eval(agent="python agent.py")

    assert summary.total_runs == 1
    assert summary.verified_runs == 1
    assert summary.pass_rate == 1.0

