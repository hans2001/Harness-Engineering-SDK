from pathlib import Path

from harness_runtime import Harness


def test_run_uses_task_repo_ref_for_workspace_checkout(tmp_path):
    repo_dir = tmp_path / "repo"
    tasks_dir = tmp_path / "tasks"
    repo_dir.mkdir()
    tasks_dir.mkdir()

    git = lambda *args: __import__("subprocess").run(  # noqa: E731
        ["git", *args],
        cwd=repo_dir,
        text=True,
        capture_output=True,
        check=True,
    )

    git("init")
    git("config", "user.name", "Harness Test")
    git("config", "user.email", "harness@example.com")

    (repo_dir / "state.txt").write_text("old\n")
    git("add", "state.txt")
    git("commit", "-m", "old")
    first_sha = git("rev-parse", "HEAD").stdout.strip()

    (repo_dir / "state.txt").write_text("new\n")
    git("commit", "-am", "new")

    (tasks_dir / "task_001.yaml").write_text(
        f"""
id: task_001
title: Check workspace ref
source: local
repo_path: repo
repo_ref: {first_sha}
instructions: Print the checked out state.
verification:
  commands: []
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", agent='python -c "print(open(\'state.txt\').read().strip())"')

    assert run.status.value == "completed"
    assert Path(run.stdout_path).read_text().strip() == "old"
    assert run.metadata["workspace_ref"] == first_sha
