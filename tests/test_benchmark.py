from harness_runtime import Harness
from pathlib import Path


def test_benchmark_runs_reference_tasks_and_writes_report(tmp_path):
    target_repo = tmp_path / "target"
    task_dir = tmp_path / ".harness" / "tasks"
    target_repo.mkdir()

    harness = Harness(tmp_path)
    harness.init()
    task_dir.mkdir(parents=True, exist_ok=True)
    (target_repo / "state.txt").write_text("broken\n")
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
  issue_number: 12
  issue_url: https://github.com/acme/widgets/issues/12
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
        agent='python -c "from pathlib import Path; Path(\'state.txt\').write_text(\'fixed\\\\n\')"',
        limit=1,
    )

    assert summary.total_tasks == 1
    assert summary.executed_runs == 1
    assert summary.verified_runs == 1
    assert summary.passed_runs == 1
    assert summary.report_path is not None
    report = Path(summary.report_path).read_text()
    assert "Pass rate: 100.0%" in report
    assert "| Task | Title | Repo Ref | Preflight | Run | Duration | Verify | Artifacts |" in report
    assert "All verified runs passed." in report


def test_shell_benchmark_with_deterministic_agent_reaches_full_pass_rate(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    fixture_repo = tmp_path / "fixture_repo"
    fixture_tasks = tmp_path / "fixture_tasks"
    fixture_repo.mkdir()
    fixture_tasks.mkdir()
    (fixture_repo / "state.txt").write_text("broken\n")
    (fixture_repo / "feature_flag.txt").write_text("disabled\n")
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
  issue_number: 1
  issue_url: https://example.invalid/issues/1
  reference_paths:
    - state.txt
  linked_pull_requests:
    - number: 1
      title: Fix state marker
      url: https://example.invalid/pull/1
      state: closed
"""
    )
    (fixture_tasks / "github_example_smoke_002.yaml").write_text(
        """
id: github_example_smoke_002
title: Enable feature flag
source: github
repo_path: .
instructions: Update `feature_flag.txt` so the file contains `enabled` instead of `disabled`.
verification:
  commands:
    - python -c "from pathlib import Path; raise SystemExit(0 if Path('feature_flag.txt').read_text().strip() == 'enabled' else 1)"
metadata:
  repo_full_name: example/smoke
  issue_number: 2
  issue_url: https://example.invalid/issues/2
  reference_paths:
    - feature_flag.txt
  linked_pull_requests:
    - number: 2
      title: Enable feature flag
      url: https://example.invalid/pull/2
      state: closed
"""
    )

    harness = Harness(tmp_path)
    harness.init()
    harness.harvest(fixture_tasks)
    summary = harness.benchmark(
        repo_filter="example/smoke",
        target_repo_path="fixture_repo",
        adapter="shell",
        agent=f"{repo_root / '.venv' / 'bin' / 'python'} {repo_root / 'examples' / 'agents' / 'heuristic_edit_agent.py'}",
        limit=2,
    )

    assert summary.total_tasks == 2
    assert summary.executed_runs == 2
    assert summary.verified_runs == 2
    assert summary.passed_runs == 2
    assert summary.pass_rate == 1.0
