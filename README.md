# Repo-Native Agent Harness Runtime

An open-source, local-first framework for turning coding-agent experiments inside real repositories into a repeatable improvement loop:

```text
task harvesting -> isolated execution -> verification -> trace capture -> dataset update -> skill/playbook improvement
```

This is not another coding agent. It is the harness layer around any coding agent: Codex, Claude Code, Aider, OpenHands, a local model, or a custom script.

## Why this exists

Engineering teams are moving from one-off coding-agent prompts to repeatable workflows. The hard part is not only the model. The hard part is making runs reproducible, verifiable, auditable, and useful for continuous improvement.

This project provides:

- Repo-native task specs stored next to the code.
- Isolated execution through git worktrees when available, with a copy fallback for local demos.
- Verification through normal project commands like `pytest`, `npm test`, `ruff check`, and `mypy`.
- Local artifacts: stdout, stderr, diffs, verification logs, traces, and reports.
- SQLite metadata through a SQLAlchemy ORM storage layer.
- A minimal Python SDK and Typer CLI.
- An adapter layer so agent execution is not locked to raw shell strings.
- A privacy stance suitable for enterprise repositories: local-only by default, no cloud service required.

## Install

From this repository:

```bash
python -m pip install -e ".[dev]"
```

## Quick Demo

Run the local-only demo from this directory:

```bash
harness init
harness harvest --from examples/tasks
harness providers
harness adapters
harness harvest --issue-provider github --issue-resource owner/repo --issue-comment-limit 10
harness dataset --kind github-linked-prs --repo-filter owner/repo --materialize-tasks --target-repo-path ../target-repo
harness run task_001 --adapter mock
harness runs
harness verify --cleanup latest
harness eval
harness report
```

The demo task starts with a failing test under `examples/sample_repo`. The mock agent edits the implementation in the isolated workspace, verification runs pytest, and the report links to the run artifacts.

## CLI

```bash
harness init
harness harvest --from examples/tasks
harness providers
harness adapters
harness harvest --issue-provider github --issue-resource owner/repo --issue-comment-limit 10
harness dataset --kind github-linked-prs --repo-filter owner/repo --materialize-tasks --target-repo-path ../target-repo
harness run task_001 --adapter mock
harness runs
harness verify latest
harness eval
harness eval --adapter mock
harness report
```

`verify` accepts a full run id, `latest`, or a unique run id prefix. `run` keeps workspaces by default so verification can happen later. Use `verify --cleanup latest` to remove the isolated workspace after verification while keeping run artifacts. Use `--adapter shell --agent "..."` for arbitrary agent commands, or built-in adapters such as `mock`.

## Python SDK

```python
from harness_runtime import Harness

h = Harness(repo=".")
h.init()
h.harvest(source="examples/tasks")
h.harvest_issues(provider="github", resource="owner/repo", token="ghp_...", comment_limit=10)
h.harvest_github(repo_full_name="owner/repo", token="ghp_...", comment_limit=10)
h.build_github_eval_dataset(repo_filter="owner/repo")
h.materialize_eval_tasks(target_repo_path="../target-repo", repo_filter="owner/repo")
run = h.run(task_id="task_001", adapter="mock")
h.verify(run.id)
h.eval(adapter="mock")
h.report()
```

## Project Layout

```text
harness_runtime/
  cli.py
  config.py
  schemas.py
  sdk.py
  repo.py
  harvesters/
  runners/
  verification/
  datasets/
  reports/
  storage/
  telemetry/
examples/
  tasks/
  mock_agent.py
  sample_repo/
tests/
docs/
```

## Privacy and Compliance

Default behavior is local-only:

- No code, prompts, diffs, logs, traces, or verification output are uploaded by this framework.
- `.harness/` contains all local state and should normally stay uncommitted.
- Agent commands are bring-your-own. If your chosen agent calls an external model API, that network behavior belongs to that agent, not the harness runtime.
- The harness captures artifacts for auditability and redacts common secret patterns in command logs.
- Cloud exporters should be explicit opt-in integrations, not defaults.
- Issue harvesting is provider-based. GitHub is the first implementation. GitLab, Bitbucket, Jira, and internal systems should plug into the same interface instead of changing the core harness design.
- GitHub harvesting requires a user-supplied token through `GITHUB_TOKEN`, `--issue-token`, or `--github-token`.
- The GitHub harvester now captures issue comments, labels, assignees, milestone, author, timestamps, state reason, and linked pull requests so harvested tasks are usable as real eval inputs instead of thin prompts.
- The dataset builder can turn harvested GitHub issues with linked PRs into a local JSONL eval set for real OSS benchmark runs.

## Workspace Isolation

The runner uses a git worktree only when `repo_path` is the actual git repository root. If the project is an untracked nested directory inside a larger git repository, the runner uses a copy workspace instead. This avoids dropping untracked demo files from the isolated workspace.

By default, `run` keeps the workspace under `.harness/worktrees/` for debugging and later verification. Use `run --cleanup` only when you do not need to verify that run later, or prefer `verify --cleanup` after verification succeeds.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design.
