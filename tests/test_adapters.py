import os
import stat
from pathlib import Path

from harness_runtime import Harness
from harness_runtime.adapters import get_adapter, list_adapters
from harness_runtime.adapters.codex import build_codex_prompt


def test_adapter_registry_lists_supported_adapters():
    adapters = list_adapters()

    assert "codex" in adapters
    assert "shell" in adapters
    assert "mock" in adapters
    assert get_adapter("codex").name == "codex"
    assert get_adapter("shell").name == "shell"


def test_codex_prompt_contains_task_instructions():
    prompt = build_codex_prompt("Fix the failing router policy test.")

    assert "repo-native harness workspace" in prompt
    assert "Fix the failing router policy test." in prompt


def test_mock_adapter_runs_demo_task(tmp_path):
    examples_dir = tmp_path / "examples"
    sample_repo_dir = examples_dir / "sample_repo"
    sample_repo_tests_dir = sample_repo_dir / "tests"
    sample_repo_tests_dir.mkdir(parents=True)
    (examples_dir / "mock_agent.py").write_text(
        """
import os
from pathlib import Path

workspace = Path(os.environ["HARNESS_WORKSPACE"])
target = workspace / "examples" / "sample_repo" / "calculator.py"
target.write_text("def multiply(a: int, b: int) -> int:\\n    return a * b\\n")
print("fixed")
"""
    )
    (sample_repo_dir / "calculator.py").write_text(
        "def multiply(a: int, b: int) -> int:\n    return a + b\n"
    )
    (sample_repo_tests_dir / "test_calculator.py").write_text(
        """
from examples.sample_repo.calculator import multiply


def test_multiply():
    assert multiply(6, 7) == 42
"""
    )

    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Mock Adapter
source: local
repo_path: .
instructions: Fix the calculator.
verification:
  commands:
    - python -m pytest examples/sample_repo/tests
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", adapter="mock")
    result = harness.verify(run.id)

    assert run.agent_adapter == "mock"
    assert result.passed is True


def test_codex_adapter_runs_with_fake_codex_binary(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    examples_dir = tmp_path / "examples"
    sample_repo_dir = examples_dir / "sample_repo"
    sample_repo_tests_dir = sample_repo_dir / "tests"
    task_dir = tmp_path / "tasks"
    bin_dir.mkdir()
    sample_repo_tests_dir.mkdir(parents=True)
    task_dir.mkdir()

    fake_codex = bin_dir / "codex"
    fake_codex.write_text(
        """#!/bin/sh
target="$HARNESS_WORKSPACE/examples/sample_repo/calculator.py"
cat > "$target" <<'EOF'
def multiply(a: int, b: int) -> int:
    return a * b
EOF
printf 'codex exec stub\\n'
"""
    )
    fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    (sample_repo_dir / "calculator.py").write_text(
        "def multiply(a: int, b: int) -> int:\n    return a + b\n"
    )
    (sample_repo_tests_dir / "test_calculator.py").write_text(
        """
from examples.sample_repo.calculator import multiply


def test_multiply():
    assert multiply(6, 7) == 42
"""
    )
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Codex Adapter
source: local
repo_path: .
instructions: Fix the calculator.
verification:
  commands:
    - python -m pytest examples/sample_repo/tests
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest("tasks")
    run = harness.run("task_001", adapter="codex")
    result = harness.verify(run.id)

    assert run.agent_adapter == "codex"
    assert run.status.value == "completed"
    assert Path(run.stdout_path).read_text() == "codex exec stub\n"
    assert result.passed is True
