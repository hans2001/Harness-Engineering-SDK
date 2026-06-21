# Architecture

Harness Runtime has two layers:

- a small runtime core
- pluggable provider and adapter edges

## Core Responsibilities

- workspace isolation
- task and run schemas
- verification orchestration
- artifact capture
- local metadata storage
- benchmark execution
- report generation

## Extension Responsibilities

- issue-provider integrations
- agent-specific execution details
- verification profiles
- external exporters
- enterprise policy integrations

## Read the Full Design Docs

- [Plugin System](PLUGIN_SYSTEM.md)
- [Core vs Plugin Boundary](CORE_VS_PLUGIN.md)
- [Multi-Language Support Model](MULTI_LANGUAGE.md)
