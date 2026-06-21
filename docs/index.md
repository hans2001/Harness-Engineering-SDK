<div class="hero" markdown>

# Harness Runtime

Harness Runtime is the SDK and local runtime for repo-native harness engineering.

Turn ad hoc coding-agent runs into a repeatable engineering loop:

```text
harvest tasks -> run in isolation -> verify -> capture artifacts -> update evals -> improve playbooks
```

Bring your own repository, agent, model, verifier, and workflow. Harness Runtime provides the control layer around them.

<div class="hero-actions" markdown>

[Get Started](quickstart.md){ .md-button .md-button--primary }
[Read the Concepts](concepts.md){ .md-button }
[Browse the SDK](sdk.md){ .md-button }
[View the CLI](cli.md){ .md-button }

</div>
</div>

## What This Project Is

<div class="grid cards pillars" markdown>

- **A Python SDK and CLI**

  For building harness layers around real repositories.

- **A local-first runtime**

  For isolated execution, verification, artifact capture, and eval generation.

- **A language-agnostic control plane**

  For Python, Rust, Go, TypeScript, and polyglot monorepos.

</div>

## Built For

<div class="grid cards" markdown>

- **Platform teams**

  Building internal coding-agent infrastructure, evaluation loops, or repo automation standards.

- **Repository owners**

  Turning one-off agent experiments into repeatable, reviewable repository workflows.

- **Applied AI and tooling engineers**

  Experimenting with harness engineering, artifact capture, benchmark design, and task materialization.

</div>

## What It Is Not

<div class="grid cards" markdown>

- **Not another coding-agent framework**

  The agent is pluggable. The harness is the product.

- **Not a hosted SaaS control plane**

  Artifacts and state stay local by default.

- **Not Python-only in repo support**

  Python is the package language, not the repository constraint.

</div>

## Why Teams Need It

Most coding-agent workflows fail outside the model:

- task intake is inconsistent
- execution happens in a dirty working tree
- verification is manual or flaky
- artifacts are lost
- failures never become eval inputs
- improvements are driven by anecdotes instead of traces

Harness Runtime focuses on that missing layer.

## Why Not Just Use An Agent Framework?

Agent frameworks usually focus on planning, tool use, or multi-agent orchestration.

Harness Runtime focuses on the repository execution substrate around agents:

- task intake from repo-native sources
- isolated workspaces
- deterministic verification
- artifact capture
- replayable eval tasks
- benchmark and reporting loops

If your team already has an agent, this project is the layer that makes that agent measurable and improvable inside a real codebase.

## How Developers Use It

<div class="grid cards" markdown>

- **Bring your own repo**

  Operate directly on the repository your team already owns.

- **Bring your own agent**

  Use `codex`, `cursor`, `shell`, or a future internal adapter.

- **Bring your own verifier**

  Run `pytest`, `cargo test`, `npm test`, `go test`, or your own command set.

</div>

## System View

```text
repo / issues / failed tests
          |
          v
      harvest tasks
          |
          v
   materialize eval tasks
          |
          v
  isolated agent execution
          |
          v
      verification
          |
          v
 artifacts + reports + datasets
          |
          v
  prompts / policies / playbooks improve
```

## Common Use Cases

<div class="grid cards" markdown>

- **Local harness for one repo**

  A team wants isolated agent runs, verification, and artifacts without adopting a hosted platform.

- **Benchmarking a coding workflow**

  A team wants to replay tasks against `repo_ref` baselines and compare agents or prompting strategies.

- **Internal harness engineering SDK**

  A platform team wants Python syntax sugar around a neutral runtime while supporting many repository languages.

</div>

## Start Paths

<div class="grid cards section-tight" markdown>

- **New here**

  Start with [Quick Start](quickstart.md) and [Concepts](concepts.md).

- **Building with the SDK**

  Go to [SDK](sdk.md) and [Core Abstractions](CORE_ABSTRACTIONS.md).

- **Running benchmarks**

  Go to [Benchmarks](benchmarks.md) and [CLI](cli.md).

- **Designing extensions**

  Go to [Plugin System](PLUGIN_SYSTEM.md) and [Core vs Plugin](CORE_VS_PLUGIN.md).

</div>

## Core Design Principles

- **Local-first:** artifacts and state stay in `.harness/` by default.
- **Repo-native:** tasks, diffs, refs, and verification commands are shaped around real repositories.
- **Agent-agnostic:** bring your own agent, model, and provider.
- **Verification-first:** pass/fail comes from commands, not agent self-report.
- **Composable:** providers, adapters, verification profiles, and policies should remain swappable.

## Documentation Map

- [Quick Start](quickstart.md)
- [Concepts](concepts.md)
- [SDK](sdk.md)
- [CLI](cli.md)
- [Benchmarks](benchmarks.md)
- [Architecture](architecture.md)

Deep dives:

- [Core Abstractions](CORE_ABSTRACTIONS.md)
- [Plugin System](PLUGIN_SYSTEM.md)
- [Multi-Language Support Model](MULTI_LANGUAGE.md)
- [Core vs Plugin Boundary](CORE_VS_PLUGIN.md)
- [SDK Surface Notes](SDK_SURFACE.md)
