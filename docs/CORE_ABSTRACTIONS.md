# Core Abstractions

Harness Runtime should be understood through a small set of stable primitives.

## Task

A `TaskSpec` is a durable unit of work.

It describes:

- what problem should be solved
- which repository path should be used
- which baseline ref should be checked out
- which verification commands define success

## Run

A `RunRecord` is one concrete agent attempt against one task.

It captures:

- workspace path
- adapter used
- agent command
- runtime status
- diff
- stdout and stderr

## Verification

Verification is command-oriented, not model-oriented.

Success is determined by repository-native commands such as:

- `pytest`
- `cargo test`
- `npm test`
- `ruff check`
- `mypy .`

## Adapter

An adapter is the execution bridge between the harness runtime and an agent.

Examples:

- `shell`
- `codex`

The adapter does not define the task. It defines how the task is given to an agent.

## Provider

A provider harvests tasks from an upstream source.

Examples:

- local markdown files
- manual CLI input
- GitHub issues
- future GitLab / Bitbucket / internal trackers

## Dataset Entry

A dataset entry is a benchmarkable record derived from harvested repository work.

For reference-backed tasks it may include:

- `repo_ref`
- `reference_paths`
- linked pull request metadata

## Report

A report is a human-readable summary of run and verification outcomes.

It should help developers answer:

- what was attempted
- what changed
- what passed
- what failed
- where the artifacts live
