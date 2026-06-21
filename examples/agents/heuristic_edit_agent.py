from __future__ import annotations

import json
import os
from pathlib import Path


REPLACEMENTS = [
    ("broken", "fixed"),
    ("disabled", "enabled"),
    ("off", "on"),
]


def candidate_files(workspace: Path, reference_paths: list[str]) -> list[Path]:
    if reference_paths:
        return [workspace / rel_path for rel_path in reference_paths]
    return [path for path in workspace.rglob("*") if path.is_file() and ".git" not in path.parts]


def apply_replacements(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(errors="replace")
    updated = text
    for before, after in REPLACEMENTS:
        updated = updated.replace(before, after)
    if updated == text:
        return False
    path.write_text(updated)
    return True


def main() -> int:
    workspace = Path(os.environ["HARNESS_WORKSPACE"])
    reference_paths = json.loads(os.environ.get("HARNESS_REFERENCE_PATHS_JSON", "[]"))
    changed = 0
    for path in candidate_files(workspace, reference_paths):
        if apply_replacements(path):
            changed += 1
    print(f"heuristic_edit_agent changed_files={changed}")
    return 0 if changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
