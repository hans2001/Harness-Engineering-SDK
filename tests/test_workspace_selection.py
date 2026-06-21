import subprocess

from harness_runtime.repo import create_workspace


def test_nested_untracked_project_uses_copy_workspace(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    subprocess.run(["git", "init"], cwd=parent, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=parent, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=parent, check=True)
    (parent / "README.md").write_text("# parent\n")
    subprocess.run(["git", "add", "README.md"], cwd=parent, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=parent, check=True, capture_output=True)

    project = parent / "nested_project"
    project.mkdir()
    (project / "agent.py").write_text("print('agent')\n")

    workspace = tmp_path / "workspace"
    mode, base_sha = create_workspace(project, workspace, ignore_patterns=[".git"])

    assert mode == "copy"
    assert base_sha is None
    assert (workspace / "agent.py").exists()

