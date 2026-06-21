# Core vs Plugin Boundary

This project only stays clean if the boundary between core and extensions is explicit.

## Belongs in Core

- task schema
- run schema
- verification schema
- artifact layout
- workspace isolation
- diff capture
- local metadata storage
- benchmark orchestration
- report generation primitives

## Belongs in Provider / Plugin Layers

- GitHub-specific harvesting logic
- GitLab-specific harvesting logic
- agent-specific execution flags
- repo-family-specific verification defaults
- external telemetry exporters
- enterprise policy packs

## Decision Rule

If a feature is required for the runtime to function in any repository, it likely belongs in core.

If a feature is specific to one ecosystem, provider, agent, or company workflow, it should probably be a plugin.

## Why This Matters

Without this boundary, the runtime becomes:

- too GitHub-specific
- too Python-specific
- too Codex-specific
- too hard to extend cleanly
