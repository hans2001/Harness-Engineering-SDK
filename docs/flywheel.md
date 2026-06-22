# Harness Flywheel

Harness Runtime is not only a benchmark runner. It is a **local training loop for the harness layer** around coding agents.

The flywheel turns failed runs into promoted skills/playbooks that future runs consume automatically.

## Loop

```text
benchmark tasks
  -> capture traces + verification evidence
    -> propose HarnessPatch objects
      -> promote skills into .harness/skills/
        -> re-run benchmark
          -> measure pass-rate delta
```

## Why This Exists

Companies do not need another agent. They need their existing agent stack to get better on **their repository** over time.

The harness layer is where that improvement lives:

- skills / playbooks
- verification habits
- policies and guardrails

Harness Runtime stores those artifacts locally and feeds them back into the next run.

## Quick Start

```bash
harness harvest --from examples/benchmark_tasks
harness flywheel run \
  --repo-filter example/smoke \
  --target-repo-path examples/benchmark_repo \
  --adapter shell \
  --agent "$PWD/.venv/bin/python $PWD/examples/agents/heuristic_edit_agent.py" \
  --rounds 2
harness flywheel status
```

After the flywheel runs:

- `.harness/skills/` contains promoted playbooks
- `.harness/traces/` contains structured run evidence
- `.harness/flywheel/latest.json` contains the latest session summary

## Commands

```bash
harness flywheel run ...
harness flywheel analyze --benchmark-id latest
harness flywheel promote <patch_id>
harness flywheel status
```

## Spec

See [Flywheel Spec v0.1](spec/flywheel.md) for the schema.

## SDK

```python
from harness_runtime import Harness

h = Harness(".")
summary = h.flywheel(
    repo_filter="example/smoke",
    target_repo_path="examples/benchmark_repo",
    adapter="shell",
    agent="python examples/agents/heuristic_edit_agent.py",
    rounds=2,
)
patches = h.analyze_flywheel("latest")
h.promote_patch(patches[0].patch_id)
```

## v0.1 Scope

The first flywheel release uses deterministic heuristics to propose skill patches from benchmark failures.
Future versions can add LLM-based diagnosis, regression gates, and prediction verification against held-out tasks.
