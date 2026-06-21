# Multi-Language Support Model

Harness Runtime is a Python package with a language-agnostic execution model.

## What Python Means Here

Python is the implementation language of the SDK and CLI.

Python is not the constraint on target repository language.

## How Multi-Language Support Works

The compatibility model is based on neutral primitives:

- tasks are structured data
- repositories are checked out by git
- execution happens through adapters
- verification happens through shell commands

That makes the runtime usable for:

- Python repos
- Rust repos
- Go repos
- TypeScript / Node repos
- mixed monorepos

## Examples

Python repo verification:

- `pytest`
- `ruff check`

Rust repo verification:

- `cargo test`
- `cargo clippy`

Node repo verification:

- `npm test`
- `pnpm lint`

Go repo verification:

- `go test ./...`

## Principle

Language-specific behavior should usually live in:

- verification profiles
- provider metadata
- repo-specific playbooks

not in the runtime core.
