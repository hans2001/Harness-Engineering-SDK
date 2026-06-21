from harness_runtime import Harness


def test_report_generation(tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (tmp_path / "agent.py").write_text("print('noop')\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Report
source: local
repo_path: .
instructions: Generate a report.
verification:
  commands:
    - python -c "print('verified')"
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent="python agent.py")
    harness.verify(run.id)
    report = harness.report()

    assert report.exists()
    text = report.read_text()
    assert "Harness Report" in text
    assert run.id in text

