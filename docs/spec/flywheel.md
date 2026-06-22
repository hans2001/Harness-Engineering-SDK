# Harness Flywheel Spec v0.1

Harness Runtime models harness improvement as a closed loop over repository-native evidence.

```text
Execute -> Verify -> Trace -> Diagnose -> Patch harness -> Promote -> Re-run -> Measure delta
```

This document defines the interchange objects for that loop.

## HarnessTrace

Structured evidence for one run.

| Field | Type | Description |
| --- | --- | --- |
| `trace_id` | string | Stable trace identifier |
| `run_id` | string | Associated run |
| `task_id` | string | Associated task |
| `repo` | string | Harness repo root |
| `events` | HarnessTraceEvent[] | Ordered runtime events |
| `failure_tags` | string[] | Machine-readable failure classes |
| `failure_summary` | string? | Human-readable failure summary |
| `trace_path` | string? | Persisted trace location |

### HarnessTraceEvent

| Field | Type | Description |
| --- | --- | --- |
| `event` | string | Event kind (`run_started`, `agent_completed`, `verification_finished`, ...) |
| `timestamp` | datetime | Event time |
| `run_id` | string | Run id |
| `task_id` | string? | Task id |
| `payload` | object | Event-specific metadata |

## HarnessPatch

A proposed or promoted change to the harness layer.

| Field | Type | Description |
| --- | --- | --- |
| `patch_id` | string | Patch identifier |
| `round_id` | string | Flywheel round that produced the patch |
| `kind` | string | `skill`, `policy`, or `verification_hint` |
| `target_path` | string | File path under `.harness/` |
| `title` | string | Short patch title |
| `content` | string | Patch body |
| `evidence_run_ids` | string[] | Supporting runs |
| `evidence_task_ids` | string[] | Supporting tasks |
| `failure_tags` | string[] | Failure classes addressed |
| `prediction` | HarnessPatchPrediction | Expected impact |
| `status` | string | `proposed`, `promoted`, or `rejected` |

### HarnessPatchPrediction

| Field | Type | Description |
| --- | --- | --- |
| `expected_fixes` | string[] | Task ids expected to improve |
| `at_risk_regressions` | string[] | Task ids that may regress |
| `rationale` | string | Why this patch should help |

## FlywheelRound

One benchmark-analyze-promote cycle.

| Field | Type | Description |
| --- | --- | --- |
| `round_id` | string | Round identifier |
| `round_number` | integer | 1-based round index |
| `benchmark_id` | string? | Benchmark executed in the round |
| `pass_rate_before` | number? | Pass rate entering the round |
| `pass_rate_after` | number? | Pass rate after benchmark |
| `patches_proposed` | string[] | Patch ids proposed |
| `patches_promoted` | string[] | Patch ids promoted |
| `task_ids` | string[] | Tasks in the round |

## FlywheelSummary

Aggregate result for a flywheel session.

| Field | Type | Description |
| --- | --- | --- |
| `flywheel_id` | string | Session identifier |
| `rounds` | FlywheelRound[] | Executed rounds |
| `initial_pass_rate` | number | Pass rate before training |
| `final_pass_rate` | number | Pass rate after training |

## Storage Layout

```text
.harness/
  skills/                 # promoted harness playbooks
  traces/                 # materialized HarnessTrace JSON
  flywheel/
    patches/              # HarnessPatch JSON
    rounds/               # FlywheelRound JSON
    latest.json           # latest FlywheelSummary
    flywheel_*.md         # human-readable flywheel report
  reports/
    benchmark_*.json      # machine-readable benchmark summaries
    benchmark_*.md        # human-readable benchmark reports
```

## CLI

```bash
harness flywheel run \
  --repo-filter example/smoke \
  --target-repo-path examples/benchmark_repo \
  --adapter shell \
  --agent "python examples/agents/heuristic_edit_agent.py" \
  --rounds 2

harness flywheel analyze --benchmark-id latest
harness flywheel promote patch_verify_before_finish_ab12cd34
harness flywheel status
```

## Reference Implementation

The canonical Python models live in `harness_runtime/schemas.py`.
The reference runtime lives in `harness_runtime/flywheel.py`.
