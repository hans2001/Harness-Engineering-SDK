from pathlib import Path

from harness_runtime import Harness


def test_flywheel_analyze_and_promote_from_failed_benchmark(tmp_path):
    target_repo = tmp_path / "target"
    task_dir = tmp_path / ".harness" / "tasks"
    target_repo.mkdir()
    task_dir.mkdir(parents=True, exist_ok=True)
    (target_repo / "state.txt").write_text("broken\n")

    harness = Harness(tmp_path)
    harness.init()
    (task_dir / "github_acme_widgets_12.yaml").write_text(
        """
id: github_acme_widgets_12
title: Fix state
source: github
repo_path: .
instructions: Fix state.
verification:
  commands:
    - python -c "from pathlib import Path; raise SystemExit(0 if Path('state.txt').read_text().strip() == 'fixed' else 1)"
metadata:
  repo_full_name: acme/widgets
  linked_pull_requests:
    - number: 45
      title: Fix state
      url: https://github.com/acme/widgets/pull/45
      state: closed
"""
    )
    harness.harvest(".harness/tasks")
    summary = harness.benchmark(
        repo_filter="acme/widgets",
        target_repo_path="target",
        adapter="shell",
        agent='python -c "import sys; sys.exit(1)"',
        limit=1,
    )

    assert summary.passed_runs == 0
    benchmark_json = Path(summary.report_path).with_suffix(".json")
    assert benchmark_json.exists()

    patches = harness.analyze_flywheel(summary.benchmark_id)
    assert patches
    patch = harness.promote_patch(patches[0].patch_id)
    skill_path = Path(patch.target_path)
    assert skill_path.exists()
    assert "Evidence" in skill_path.read_text()


def test_flywheel_run_promotes_skills_from_verification_failures(tmp_path):
    fixture_repo = tmp_path / "fixture_repo"
    fixture_tasks = tmp_path / "fixture_tasks"
    fixture_repo.mkdir()
    fixture_tasks.mkdir()
    (fixture_repo / "state.txt").write_text("broken\n")
    (fixture_tasks / "github_example_smoke_001.yaml").write_text(
        """
id: github_example_smoke_001
title: Fix state marker
source: github
repo_path: .
instructions: Update `state.txt` so the file contains `fixed` instead of `broken`.
verification:
  commands:
    - python -c "from pathlib import Path; raise SystemExit(0 if Path('state.txt').read_text().strip() == 'fixed' else 1)"
metadata:
  repo_full_name: example/smoke
  linked_pull_requests:
    - number: 1
      title: Fix state marker
      url: https://example.invalid/pull/1
      state: closed
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest(fixture_tasks)
    summary = harness.flywheel(
        repo_filter="example/smoke",
        target_repo_path="fixture_repo",
        adapter="shell",
        agent='python -c "print(\'no-op\')"',
        limit=1,
        rounds=2,
    )

    assert summary.initial_pass_rate == 0.0
    assert summary.rounds
    assert summary.rounds[0].patches_promoted
    skills_dir = tmp_path / ".harness" / "skills"
    assert any(skills_dir.glob("*.md"))
    assert (tmp_path / ".harness" / "flywheel" / "latest.json").exists()


def test_run_loads_promoted_skills_into_instructions(tmp_path):
    harness = Harness(tmp_path)
    harness.init()
    skills_dir = tmp_path / ".harness" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "verify-before-finish.md").write_text("Always run verification before finishing.\n")
    (tmp_path / "tasks").mkdir()
    (tmp_path / "state.txt").write_text("broken\n")
    (tmp_path / "tasks" / "task_001.yaml").write_text(
        """
id: task_001
title: Fix state
source: local
repo_path: .
instructions: Fix the state file.
verification:
  commands:
    - python -c "from pathlib import Path; raise SystemExit(0 if Path('state.txt').read_text().strip() == 'fixed' else 1)"
"""
    )

    harness.harvest("tasks")
    run = harness.run(
        "task_001",
        adapter="shell",
        agent='python -c "from pathlib import Path; Path(\'state.txt\').write_text(\'fixed\\\\n\')"',
    )

    trace_path = Path(run.artifact_path) / "trace.jsonl"
    assert trace_path.exists()
    assert "skills_loaded" in trace_path.read_text()
