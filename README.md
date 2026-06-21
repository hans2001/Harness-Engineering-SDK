# <div align="center"><img src="docs/logo.svg" alt="Harness Runtime logo" width="88" /></div>

# <div align="center">Harness Runtime</div>

<div align="center">

[![Version](https://img.shields.io/badge/version-0.1.0-0f172a.svg)](https://github.com/hans2001/Harness-Engineering-SDK/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-2563eb.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/hans2001/Harness-Engineering-SDK)](LICENSE)
[![Open Issues](https://img.shields.io/github/issues/hans2001/Harness-Engineering-SDK)](https://github.com/hans2001/Harness-Engineering-SDK/issues)
[![PyPI](https://img.shields.io/badge/PyPI-coming_soon-f59e0b.svg)](https://pypi.org/)

</div>

<div align="center">

[Docs](docs/index.md) |
[Quick Start](docs/quickstart.md) |
[Concepts](docs/concepts.md) |
[SDK](docs/sdk.md) |
[CLI](docs/cli.md) |
[Architecture](docs/architecture.md)

</div>

Harness Runtime is the SDK and local runtime for repo-native harness engineering.

It helps engineering teams turn ad hoc coding-agent runs into a repeatable loop:

```text
harvest tasks -> run in isolation -> verify -> capture artifacts -> update evals -> improve playbooks
```

Bring your own repository, agent, model, verifier, and workflow. Harness Runtime provides the control layer around them.

## Key Message

Harness Runtime is a language-agnostic harness layer with a Python SDK.

That means:

- the package is installed with Python
- the target repository can be Python, Rust, TypeScript, Go, or a monorepo
- verification is command-based, not framework-locked
- agents and models are bring-your-own

It is not another coding-agent framework and not a hosted control plane.

## Quick Start

```bash
python -m pip install -e ".[dev]"
harness init
harness harvest --from tasks
harness run task_001 --adapter shell --agent "python your_agent.py"
harness verify latest --cleanup
harness report
```

For benchmark and reference-eval flows, start here:

- [Quick Start](docs/quickstart.md)
- [CLI Guide](docs/cli.md)
- [Benchmarks](docs/benchmarks.md)

## Documentation

The project now has a docs structure intended for a GitHub Pages developer site:

- [Docs Home](docs/index.md)
- [Quick Start](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [SDK Surface](docs/sdk.md)
- [CLI Reference](docs/cli.md)
- [Benchmarks](docs/benchmarks.md)
- [Architecture](docs/architecture.md)

Deeper design references:

- [Core Abstractions](docs/CORE_ABSTRACTIONS.md)
- [Plugin System](docs/PLUGIN_SYSTEM.md)
- [SDK Surface Notes](docs/SDK_SURFACE.md)
- [Multi-Language Support Model](docs/MULTI_LANGUAGE.md)
- [Core vs Plugin Boundary](docs/CORE_VS_PLUGIN.md)

## Privacy and Compliance

Harness Runtime is local-first by default:

- no code, prompts, diffs, logs, traces, or verification results are uploaded by the framework
- `.harness/` contains local state and should normally stay uncommitted
- cloud usage belongs to the agent you choose to run, not to the harness itself
- provider integrations should stay explicit opt-in extensions

## License

Apache-2.0
