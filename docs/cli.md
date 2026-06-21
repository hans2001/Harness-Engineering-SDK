# CLI

## Core Commands

```bash
harness init
harness harvest
harness run
harness verify
harness eval
harness report
harness benchmark
```

## Common Flows

### Local Task Flow

```bash
harness harvest --from tasks
harness run task_001 --adapter shell --agent "python your_agent.py"
harness verify latest --cleanup
```

### GitHub Reference-Eval Flow

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
  --adapter codex \
  --limit 5
```

### Cursor Agent CLI

Use the built-in `cursor` adapter when the [Cursor Agent CLI](https://cursor.com/cli) (`agent`) is installed and authenticated:

```bash
harness run task_001 --adapter cursor
harness benchmark \
  --repo-filter owner/repo \
  --target-repo-path ../target-repo \
  --adapter cursor \
  --limit 5
```

The adapter runs `agent --print --trust --workspace <workspace> --force` with harness task instructions. Configure defaults in `.harness/config.yaml` under `cursor` (`binary`, `model`, `mode`, `sandbox`, `output_format`, `force`).

### Preflight

```bash
harness preflight task_001
```

This checks whether required executables for verification are available before you spend time on a run.
