# SDK

Harness Runtime is designed to be used as a Python SDK as well as a CLI.

## Minimal Example

```python
from harness_runtime import Harness

h = Harness(repo=".")
h.init()
h.harvest(source="tasks")
run = h.run(task_id="task_001", adapter="shell", agent="python your_agent.py")
h.verify(run.id)
h.report()
```

## Intended SDK Role

The SDK should provide syntax sugar and stable composition points for teams building their own harness workflows.

Typical use cases:

- wrapping task intake in company-specific tooling
- registering internal adapters
- composing custom benchmark loops
- integrating with internal policy layers

## Current Surface

- repo initialization
- local and provider-backed harvesting
- isolated task execution
- verification
- report generation
- dataset building
- benchmark execution

## Extending the Runtime

The SDK is also the extension surface for custom infrastructure.

### Register a Custom Adapter

```python
from harness_runtime import register_adapter
from harness_runtime.adapters import AgentAdapter, AdapterExecution


class MyAdapter(AgentAdapter):
    name = "my-adapter"

    def build_execution(self, *, repo, workspace_path, artifact_path, agent_input, env, config):
        return AdapterExecution(
            command="python internal_agent.py",
            cwd=workspace_path,
            env=env,
            shell=True,
        )


register_adapter("my-adapter", MyAdapter)
```

### Register a Custom Issue Provider

```python
from harness_runtime import IssueProvider, register_issue_provider


def harvest_internal(repo, resource, token, state, limit, comment_limit, verification_commands, refresh_cache):
    return []


register_issue_provider(
    IssueProvider(
        name="internal",
        env_token_var="INTERNAL_TOKEN",
        harvest=harvest_internal,
    )
)
```

### Ship Extensions as Separate Packages

The runtime also supports Python `entry points` for automatic discovery.

Use these groups in an extension package:

- `harness_runtime.adapters`
- `harness_runtime.issue_providers`
- `harness_runtime.verification_profiles`

That allows teams to install an internal package and have adapters or providers discovered automatically without modifying the runtime repository.

### Register a Custom Verification Profile

```python
from harness_runtime import VerificationProfile, register_verification_profile


register_verification_profile(
    VerificationProfile(
        name="go-service",
        priority=20,
        matches=lambda task: task.metadata.get("repo_full_name") == "acme/go-service",
        suggest=lambda task: ["go test ./..."],
    )
)
```

More detailed notes:

- [SDK Surface Notes](SDK_SURFACE.md)
