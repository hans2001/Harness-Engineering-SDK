from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    workspace = Path(os.environ.get("HARNESS_WORKSPACE", "."))
    target = workspace / "examples" / "sample_repo" / "calculator.py"
    text = target.read_text()
    target.write_text(text.replace("return a + b  # bug", "return a * b"))
    print(f"fixed {target}")


if __name__ == "__main__":
    main()

