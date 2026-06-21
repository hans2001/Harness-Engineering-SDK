# Architecture

## Positioning

Repo-Native Agent Harness Runtime is infrastructure for training, evaluating, and improving coding-agent workflows inside real repositories.

It deliberately does not implement a coding agent. Instead, it standardizes the execution layer around agents:

```text
task harvesting -> isolated execution -> verification -> artifact capture -> eval dataset update -> report -> skill/playbook update
```

## Design Principles

- **Local-first:** all artifacts are written to `.harness/` by default.
- **Agent-agnostic:** the runner accepts any shell command that can operate on a workspace.
- **Verification-first:** success is based on deterministic verification commands, not agent self-reporting.
- **Repo-native:** tasks, reports, and datasets are shaped around git repos, diffs, tests, and CI failures.
- **Auditable:** every run produces stdout, stderr, diff, run metadata, and verification results.
- **Composable:** harvesters, runners, verifiers, reports, and exporters are separate modules.

## Runtime Data Model

### TaskSpec

A task is a durable unit of work.

```yaml
id: task_001
title: Fix failing test
source: local
repo_path: .
instructions: |
  Fix the failing calculator test.
verification:
  commands:
    - pytest
```

### RunRecord

A run represents one agent attempt against one task.

```text
.harness/runs/<run_id>/
  run.json
  stdout.log
  stderr.log
  diff.patch
  trace.jsonl
  verification.md
  verification.json
```

### VerificationResult

Verification is command-oriented. Each command stores command text, exit code, duration, stdout, stderr, and pass/fail.

## Module Boundaries

| Module | Responsibility |
| --- | --- |
| `config` | Initialize and load `.harness/config.yaml`. |
| `schemas` | Pydantic contracts for tasks, runs, datasets, and verification. |
| `storage` | SQLite metadata for tasks, runs, and verification. |
| `repo` | Git worktree management, fallback copies, and diff capture. |
| `harvesters` | Convert local files, logs, GitHub issues, and manual input into tasks. |
| `runners` | Execute agent commands in isolated workspaces and capture artifacts. |
| `verification` | Run deterministic project checks and persist results. |
| `datasets` | Build eval datasets and aggregate run results. |
| `reports` | Generate local Markdown/HTML reports. |
| `telemetry` | Local traces first; optional exporters later. |

## Security Boundary

The harness controls artifact capture and local process execution. It does not control what a user-supplied agent command sends over the network. That is why the long-term roadmap should include:

- Environment allowlists.
- Secret redaction and artifact ignore rules.
- Docker/devcontainer executor.
- Optional network-disabled executor.
- Policy files under `.harness/policies/`.
- Explicit opt-in exporters for Langfuse, LangSmith, Braintrust, OpenTelemetry, or custom sinks.

## Roadmap

1. Local-only MVP with Typer CLI, SDK, SQLite, local harvesters, run artifacts, verification, eval summary, and Markdown report.
2. First-class agent adapters for Codex, Claude Code, Aider, OpenHands, and custom shell commands.
3. Stronger isolation with Docker/devcontainers and resource limits.
4. Dataset versioning, regression gates, flaky-test handling, and CI integration.
5. Skill/playbook generation from recurring failure modes.
6. Optional enterprise exporters and policy enforcement.
