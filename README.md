# <div align="center"><img src="docs/logo.svg" alt="Harness Runtime logo" width="88" /></div>

# <div align="center">Harness Runtime</div>

<div align="center">

[![Version](https://img.shields.io/badge/version-0.1.0-0f172a.svg)](https://github.com/hans2001/Harness-Engineering-SDK/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-2563eb.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/hans2001/Harness-Engineering-SDK)](LICENSE)
[![Open Issues](https://img.shields.io/github/issues/hans2001/Harness-Engineering-SDK)](https://github.com/hans2001/Harness-Engineering-SDK/issues)
[![Repo Status](https://img.shields.io/badge/local--first-yes-059669.svg)](docs/ARCHITECTURE.md)
[![PyPI](https://img.shields.io/badge/PyPI-coming_soon-f59e0b.svg)](https://pypi.org/)

</div>

<div align="center">

[Quick Start](#getting-started) |
[Architecture](docs/ARCHITECTURE.md) |
[Roadmap](#roadmap) |
[Issues](https://github.com/hans2001/Harness-Engineering-SDK/issues) |
[Releases](https://github.com/hans2001/Harness-Engineering-SDK/releases)

</div>

<br />

Harness Runtime is a repo-native harness layer for coding agents.

It turns ad hoc agent runs inside real repositories into a repeatable engineering loop:

```text
task harvesting -> isolated execution -> verification -> trace capture -> eval dataset update -> skill/playbook improvement
```

This project is not another autonomous agent framework. It is the infrastructure around agents: the execution, evaluation, artifact capture, and feedback loop that teams need to improve coding-agent performance inside their own repositories.

## Project News

- `[2026/06]` Added reference-aware eval tasks with `repo_ref` and `reference_paths` so closed-issue benchmarks can run against pre-fix repository states.
- `[2026/06]` Added first-class agent adapters for `shell`, `mock`, and `codex`.
- `[2026/06]` Added provider-based GitHub issue harvesting with comments, labels, assignees, milestone, linked pull requests, and local dataset materialization.
- `[2026/06]` Added `harness preflight` and verification-time dependency checks for clearer failure diagnosis in real repository runs.

## About

Modern engineering teams do not only need a stronger model. They need a repeatable system for:

- turning issues, docs, failed tests, and human requests into structured tasks
- running agents in isolated workspaces instead of on the developer's live checkout
- verifying changes with normal project commands such as `pytest`, `cargo test`, `npm test`, `ruff`, and `mypy`
- capturing diffs, logs, traces, and metadata for later analysis
- building local eval datasets from real repository work
- improving prompts, adapters, policies, and skills based on evidence instead of anecdotes

Harness Runtime is designed for that workflow. It is local-first, repository-native, and intentionally modular so teams can bring their own code agent, model provider, and repository conventions.

## Core Capabilities

- Repo initialization with a standard `.harness/` layout for tasks, runs, datasets, skills, and reports
- Task harvesting from local markdown, manual CLI input, and provider-based issue systems
- Provider abstraction for issue trackers, with GitHub as the first implementation
- Isolated execution via git worktrees when possible, with a filesystem copy fallback for nested or demo repositories
- Verification using ordinary repository commands rather than harness-specific test abstractions
- Artifact capture for stdout, stderr, diffs, verification logs, and run metadata
- Local metadata storage through SQLite with a SQLAlchemy ORM layer
- Adapter-based agent execution, including `shell`, `mock`, and `codex`
- Dataset materialization from harvested GitHub issues linked to real pull requests
- Reference-aware task generation through `repo_ref` and `reference_paths`, so eval runs can target pre-fix repository states instead of current `HEAD`
- Preflight dependency checks so missing tools are surfaced clearly before or during verification

## Why This Exists

Most agent workflows fail in the same place:

- tasks are vague
- execution happens in a mutable working tree
- verification is inconsistent
- artifacts are lost
- failures are not converted into eval inputs
- improvements are driven by memory, not traces

Harness Runtime treats agent work like software delivery infrastructure. The agent is only one component. The harness is what makes experiments reproducible, reviewable, and useful over time.

## Getting Started

### Installation

```bash
python -m pip install -e ".[dev]"
```

### Initialize a Repository

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

### Run the Local Demo

```bash
harness init
harness harvest --from examples/tasks
harness adapters
harness run task_001 --adapter mock
harness verify latest --cleanup
harness report
```

The demo task starts with a failing test under `examples/sample_repo`, applies a mock agent fix in an isolated workspace, verifies the result with `pytest`, and writes a local report with linked artifacts.

## CLI Workflow

### Basic Commands

```bash
harness init
harness harvest --from examples/tasks
harness providers
harness adapters
harness runs
harness report
```

### Run and Verify

```bash
harness run task_001 --adapter mock
harness verify latest
harness preflight task_001
```

`run` keeps the workspace by default so verification can happen later. Use `harness verify latest --cleanup` to remove the workspace after verification while preserving artifacts.

### Use an Arbitrary Agent Command

```bash
harness run task_001 --adapter shell --agent "python examples/mock_agent.py"
```

### Harvest GitHub Issues

```bash
harness harvest \
  --issue-provider github \
  --issue-resource owner/repo \
  --issue-comment-limit 10
```

### Build a Reference Dataset

```bash
harness dataset \
  --kind github-linked-prs \
  --repo-filter owner/repo \
  --materialize-tasks \
  --target-repo-path ../target-repo
```

This produces a local JSONL dataset and runnable eval task files from harvested GitHub issues that have linked pull requests.

## Python SDK

```python
from harness_runtime import Harness

h = Harness(repo=".")
h.init()
h.harvest(source="examples/tasks")
h.harvest_issues(provider="github", resource="owner/repo", comment_limit=10)
h.build_github_eval_dataset(repo_filter="owner/repo")
h.materialize_eval_tasks(
    target_repo_path="../target-repo",
    repo_filter="owner/repo",
)
run = h.run(task_id="task_001", adapter="mock")
h.verify(run.id)
h.report()
```

## Real-Repository Evaluation Model

Harness Runtime is built for real repositories, not synthetic toy environments.

For reference-backed eval tasks, the system can store:

- `repo_path`: which repository should be checked out
- `repo_ref`: which baseline commit or ref should be used
- `reference_paths`: which files were actually touched by the known fix

That matters because a useful benchmark should answer:

- can the agent solve the task from the pre-fix state
- does it modify the right subsystem
- does it pass the right verification commands
- what diff, runtime, and failure traces were produced

Without `repo_ref`, many closed-issue evals are invalid because they run against already-fixed `HEAD`. Without `reference_paths`, large monorepos create too much search ambiguity for agent runs.

## Architecture

```text
harness_runtime/
  cli.py
  config.py
  schemas.py
  sdk.py
  repo.py
  preflight.py
  adapters/
  harvesters/
  runners/
  verification/
  datasets/
  reports/
  storage/
examples/
  tasks/
  mock_agent.py
  sample_repo/
tests/
docs/
```

System design details live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Privacy and Compliance

Harness Runtime is local-first by default:

- no code, prompts, diffs, logs, traces, or verification results are uploaded by the framework
- `.harness/` contains local state and should normally stay uncommitted
- cloud usage belongs to the agent you choose to run, not to the harness itself
- artifact capture is explicit and intended for auditability
- common secret patterns are redacted from captured command logs
- provider integrations should be explicit opt-in extensions, not hidden defaults

This design is intentional. Many engineering teams want the harness layer without surrendering repository contents to a third-party control plane.

## Current Status

Current local MVP includes:

- `harness init`
- `harness harvest`
- `harness run`
- `harness verify`
- `harness eval`
- `harness report`
- `harness preflight`
- SDK support for harvest, run, verify, report, and dataset workflows

Implemented issue-provider support:

- GitHub

Implemented agent adapters:

- `shell`
- `mock`
- `codex`

## Roadmap

- Add GitLab, Bitbucket, and internal tracker providers through the same provider interface
- Auto-resolve GitHub linked pull requests into pre-fix baseline refs without manual task editing
- Expand artifact and trace schemas for richer evaluation metrics
- Add skill and playbook packaging for repeatable repo-specific agent workflows
- Add optional export layers for teams that want to ship eval results into their own internal systems

## Contributing

This repository is early, but it is being structured as a long-lived open-source project rather than a one-off prototype.

Good contributions include:

- provider integrations
- adapter integrations
- verification and preflight improvements
- dataset builders
- report improvements
- real-repository benchmarks and fixture design
- documentation and architecture feedback

Open an issue with the repository, task source, and verification strategy you want to support.

## License

Apache-2.0
