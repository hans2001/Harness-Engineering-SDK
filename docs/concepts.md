# Concepts

Harness Runtime stays understandable if you keep a small mental model.

## Task

A task is a durable unit of work with:

- instructions
- repo path
- optional repo ref
- verification commands

## Run

A run is one attempt by one agent against one task in an isolated workspace.

## Verification

Verification is command-based and repository-native.

Examples:

- `pytest`
- `cargo test`
- `npm test`
- `go test ./...`

## Adapter

An adapter is how the runtime talks to an agent.

Current examples:

- `shell`
- `codex`

## Provider

A provider is how tasks are harvested.

Current example:

- GitHub

## Dataset

A dataset entry is a benchmarkable record derived from harvested work.

For real repository replay this may include:

- `repo_ref`
- `reference_paths`
- linked pull request metadata

## Report

A report is the human-readable output of runs and benchmarks.

Use the deep-dive docs for the formal model:

- [Core Abstractions](CORE_ABSTRACTIONS.md)
- [Core vs Plugin Boundary](CORE_VS_PLUGIN.md)
