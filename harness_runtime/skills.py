from __future__ import annotations

from pathlib import Path

from harness_runtime.config import harness_dir


def load_skills_context(repo: Path) -> str:
    skills_dir = harness_dir(repo) / "skills"
    if not skills_dir.exists():
        return ""

    sections: list[str] = []
    for path in sorted(skills_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        body = path.read_text().strip()
        if not body:
            continue
        sections.append(f"### Skill: {path.stem}\n\n{body}")
    if not sections:
        return ""
    return "Harness skills (learned playbooks from prior failures):\n\n" + "\n\n".join(sections)


def append_harness_context(instructions: str, harness_context: str) -> str:
    if not harness_context.strip():
        return instructions
    return "\n\n".join([instructions, harness_context.strip()])
