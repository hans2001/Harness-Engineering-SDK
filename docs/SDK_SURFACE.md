# SDK Surface

Harness Runtime is intended to be used as a Python SDK, not only as a CLI.

## Current Shape

```python
from harness_runtime import Harness

h = Harness(repo=".")
h.init()
h.harvest(source="tasks")
run = h.run(task_id="task_001", adapter="shell", agent="python your_agent.py")
h.verify(run.id)
h.report()
```

## SDK Goals

The SDK should make it easy to compose:

- harvesting
- isolated execution
- verification
- benchmark loops
- report generation
- dataset workflows

## Design Direction

The SDK should expose:

- stable schemas
- predictable side effects
- clear module boundaries
- composable extension points

## Important Distinction

The SDK is implemented in Python.

That does not mean the target repository must be Python.
