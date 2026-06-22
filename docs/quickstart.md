# Quick Start

## Install

```bash
python -m pip install -e ".[dev,docs]"
```

## Initialize a Repository

```bash
harness init
```

This creates:

```text
.harness/
  config.yaml
  tasks/
  runs/
  datasets/
  skills/
  reports/
  traces/
  policies/
  worktrees/
```

## Basic Local Flow

```bash
harness harvest --from tasks
harness run task_001 --adapter shell --agent "python your_agent.py"
harness verify latest --cleanup
harness report
```

## Reference-Eval Flow

```bash
harness harvest \
  --issue-provider github \
  --issue-resource owner/repo

harness dataset \
  --kind github-linked-prs \
  --repo-filter owner/repo \
  --materialize-tasks \
  --target-repo-path ../target-repo

harness benchmark \
  --repo-filter owner/repo \
  --target-repo-path ../target-repo \
  --adapter cursor \
  --limit 5
```

Or with Codex:

```bash
harness benchmark \
  --repo-filter owner/repo \
  --target-repo-path ../target-repo \
  --adapter codex \
  --limit 5
```

## Deterministic Smoke Benchmark

```bash
harness harvest --from examples/benchmark_tasks
harness benchmark \
  --repo-filter example/smoke \
  --target-repo-path examples/benchmark_repo \
  --adapter shell \
  --agent "$PWD/.venv/bin/python $PWD/examples/agents/heuristic_edit_agent.py" \
  --limit 2
```

This is useful when you want to validate harness solve-rate and artifact flow independent of frontier-model variance.
