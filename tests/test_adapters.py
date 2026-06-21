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
    assert get_adapter("codex").name == "codex"
    assert get_adapter("shell").name == "shell"


def test_codex_prompt_contains_task_instructions():
    prompt = build_codex_prompt("Fix the failing router policy test.")

    assert "repo-native harness workspace" in prompt
    assert "Fix the failing router policy test." in prompt


def test_codex_adapter_runs_with_fake_codex_binary(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    task_dir = tmp_path / "tasks"
    bin_dir.mkdir()
    task_dir.mkdir()

    fake_codex = bin_dir / "codex"
    fake_codex.write_text(
        """#!/bin/sh
target="$HARNESS_WORKSPACE/state.txt"
cat > "$target" <<'EOF'
fixed
EOF
printf 'codex exec stub\\n'
"""
    )
    fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    (tmp_path / "state.txt").write_text("broken\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Codex Adapter
source: local
repo_path: .
instructions: Fix the state file.
verification:
  commands:
    - python -c "from pathlib import Path; raise SystemExit(0 if Path('state.txt').read_text().strip() == 'fixed' else 1)"
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
