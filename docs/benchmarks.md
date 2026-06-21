# Benchmarks

Harness Runtime currently uses two benchmark categories.

## Real OSS Replay Benchmarks

Examples already exercised in this repository:

- `sgl-project/sglang`
- `vllm-project/vllm`

These are used to prove that the runtime can:

- harvest real issue work
- materialize tasks against a pre-fix `repo_ref`
- run an agent in isolation
- verify results
- capture artifacts and reports

These benchmarks validate the infrastructure path more than the raw solve-rate of the current agent.

## Deterministic Smoke Benchmark

The repository also includes a local deterministic benchmark:

- `example/smoke`

Run it with:

```bash
harness harvest --from examples/benchmark_tasks
harness benchmark \
  --repo-filter example/smoke \
  --target-repo-path examples/benchmark_repo \
  --adapter shell \
  --agent "$PWD/.venv/bin/python $PWD/examples/agents/heuristic_edit_agent.py" \
  --limit 2
```

This benchmark is useful for validating:

- solve-rate accounting
- report generation
- artifact layout
- benchmark orchestration

without depending on frontier-model variability.
