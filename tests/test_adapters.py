import os
import stat
from pathlib import Path
from types import SimpleNamespace

from harness_runtime import Harness
from harness_runtime.adapters import get_adapter, list_adapters, register_adapter, reset_adapters, unregister_adapter
from harness_runtime.adapters.codex import CodexAdapter, build_codex_prompt
from harness_runtime.adapters.cursor import CursorAdapter, build_cursor_prompt
from harness_runtime.adapters.base import AgentAdapter, AdapterExecution
from harness_runtime.config import HarnessConfig
from harness_runtime.adapters import registry as adapter_registry


def test_adapter_registry_lists_supported_adapters():
    adapters = list_adapters()

    assert "codex" in adapters
    assert "cursor" in adapters
    assert "shell" in adapters
    assert get_adapter("codex").name == "codex"
    assert get_adapter("cursor").name == "cursor"
    assert get_adapter("shell").name == "shell"


class DemoAdapter(AgentAdapter):
    name = "demo"

    def build_execution(
        self,
        *,
        repo: Path,
        workspace_path: Path,
        artifact_path: Path,
        agent_input: str | None,
        env: dict[str, str],
        config: HarnessConfig,
    ) -> AdapterExecution:
        return AdapterExecution(command="true", cwd=workspace_path, env=env, shell=True)


def test_adapter_registry_supports_custom_registration():
    reset_adapters()
    register_adapter("demo", DemoAdapter)

    try:
        adapters = list_adapters()
        assert "demo" in adapters
        assert get_adapter("demo").name == "demo"
    finally:
        unregister_adapter("demo")
        reset_adapters()


def test_adapter_registry_discovers_entry_points(monkeypatch):
    reset_adapters()
    monkeypatch.setattr(
        adapter_registry,
        "iter_entry_points",
        lambda group: [SimpleNamespace(name="plugin-demo", load=lambda: DemoAdapter)],
    )

    adapters = list_adapters()

    assert "plugin-demo" in adapters
    assert get_adapter("plugin-demo").name == "demo"
    reset_adapters()


def test_codex_prompt_contains_task_instructions():
    prompt = build_codex_prompt(
        "Fix the failing router policy test.",
        max_runtime_seconds=60,
        max_steps=8,
        max_patch_lines=120,
    )

    assert "repo-native harness workspace" in prompt
    assert "Fix the failing router policy test." in prompt
    assert "finish within 60 seconds" in prompt
    assert "at most 8 meaningful steps" in prompt


def test_codex_adapter_builds_non_interactive_command(tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    adapter = CodexAdapter()
    execution = adapter.build_execution(
        repo=tmp_path,
        workspace_path=tmp_path,
        artifact_path=artifact_path,
        agent_input="Fix it.",
        env={},
        config=HarnessConfig(),
    )

    assert "--json" in execution.command
    assert "--ephemeral" in execution.command
    assert "--ignore-user-config" in execution.command
    assert "--ignore-rules" in execution.command
    assert "agent_last_message.txt" in execution.command


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


def test_cursor_prompt_contains_task_instructions():
    prompt = build_cursor_prompt(
        "Fix the failing router policy test.",
        max_runtime_seconds=60,
        max_steps=8,
        max_patch_lines=120,
    )

    assert "repo-native harness workspace" in prompt
    assert "Fix the failing router policy test." in prompt
    assert "finish within 60 seconds" in prompt
    assert "at most 8 meaningful steps" in prompt


def test_cursor_adapter_builds_non_interactive_command(tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    adapter = CursorAdapter()
    execution = adapter.build_execution(
        repo=tmp_path,
        workspace_path=tmp_path,
        artifact_path=artifact_path,
        agent_input="Fix it.",
        env={},
        config=HarnessConfig(),
    )

    assert "agent" in execution.command
    assert "--print" in execution.command
    assert "--trust" in execution.command
    assert "--workspace" in execution.command
    assert "--force" in execution.command
    assert "Fix it." in execution.command


def test_cursor_adapter_runs_with_fake_agent_binary(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    task_dir = tmp_path / "tasks"
    bin_dir.mkdir()
    task_dir.mkdir()

    fake_agent = bin_dir / "agent"
    fake_agent.write_text(
        """#!/bin/sh
target="$HARNESS_WORKSPACE/state.txt"
cat > "$target" <<'EOF'
fixed
EOF
printf 'cursor agent stub\\n'
"""
    )
    fake_agent.chmod(fake_agent.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    (tmp_path / "state.txt").write_text("broken\n")
    (task_dir / "task_001.yaml").write_text(
        """
id: task_001
title: Cursor Adapter
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
    run = harness.run("task_001", adapter="cursor")
    result = harness.verify(run.id)

    assert run.agent_adapter == "cursor"
    assert run.status.value == "completed"
    assert Path(run.stdout_path).read_text() == "cursor agent stub\n"
    assert result.passed is True
