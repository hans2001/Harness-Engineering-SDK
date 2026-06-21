# Plugin System

Harness Runtime should keep the core small and neutral.

That requires a plugin-oriented architecture around the runtime.

## Why Plugins

Different teams use different:

- issue trackers
- coding agents
- model providers
- verification conventions
- artifact exporters

Those should not be hard-coded into the core.

## Candidate Plugin Areas

- task providers
- agent adapters
- verification profiles
- report exporters
- policy packs
- dataset builders

## Principle

The runtime core owns stable execution primitives.

Plugins own ecosystem-specific behavior.

## Examples

Core should understand:

- task
- run
- verification
- report

Plugins should supply:

- GitHub issue harvesting
- GitLab issue harvesting
- Codex adapter
- Cursor agent adapter
- Claude Code adapter
- custom enterprise issue adapters
