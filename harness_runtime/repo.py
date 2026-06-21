from __future__ import annotations

import difflib
import filecmp
import shutil
import subprocess
from pathlib import Path


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def resolve_github_pull_request_baseline(repo_path: Path, pull_request_number: int) -> str | None:
    if pull_request_number <= 0:
        return None
    fetch = run_git(repo_path, ["fetch", "origin", f"pull/{pull_request_number}/head"])
    if fetch.returncode != 0:
        return None
    parent = run_git(repo_path, ["rev-parse", "FETCH_HEAD^"])
    if parent.returncode != 0:
        return None
    return parent.stdout.strip() or None


def is_git_repo(path: Path) -> bool:
    result = run_git(path, ["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_root(path: Path) -> Path | None:
    result = run_git(path, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def current_sha(path: Path) -> str | None:
    if not is_git_repo(path):
        return None
    result = run_git(path, ["rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else None


def create_workspace(
    repo_path: Path,
    workspace_path: Path,
    ignore_patterns: list[str],
    ref: str = "HEAD",
) -> tuple[str, str | None]:
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)

    # Only use worktrees when repo_path is the actual git root. If this project is
    # an untracked subdirectory inside a larger git repo, a worktree would omit it.
    if git_root(repo_path) == repo_path.resolve():
        result = run_git(repo_path, ["worktree", "add", "--detach", str(workspace_path), ref])
        if result.returncode != 0 and ref != "HEAD" and looks_like_commit_sha(ref):
            fetch = run_git(repo_path, ["fetch", "origin", ref])
            if fetch.returncode == 0:
                result = run_git(repo_path, ["worktree", "add", "--detach", str(workspace_path), ref])
        if result.returncode == 0:
            return "git_worktree", current_sha(workspace_path)

    if ref != "HEAD":
        raise RuntimeError(
            f"Cannot create workspace at ref {ref!r} because {repo_path} is not the git repository root."
        )

    ignore = shutil.ignore_patterns(*ignore_patterns)
    shutil.copytree(repo_path, workspace_path, ignore=ignore)
    return "copy", None


def looks_like_commit_sha(value: str) -> bool:
    if len(value) < 7:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def cleanup_workspace(repo_path: Path, workspace_path: Path) -> None:
    if is_git_repo(repo_path):
        result = run_git(repo_path, ["worktree", "remove", "--force", str(workspace_path)])
        if result.returncode == 0:
            return
    if workspace_path.exists():
        shutil.rmtree(workspace_path)


def capture_diff(workspace_path: Path, baseline_path: Path | None, output_path: Path) -> None:
    if is_git_repo(workspace_path):
        result = run_git(workspace_path, ["diff", "--binary"])
        output_path.write_text(result.stdout)
        return

    if baseline_path is None:
        output_path.write_text("")
        return

    output_path.write_text(directory_diff(baseline_path, workspace_path))


def directory_diff(before: Path, after: Path) -> str:
    chunks: list[str] = []
    for rel_path in changed_files(before, after):
        before_file = before / rel_path
        after_file = after / rel_path
        before_lines = before_file.read_text(errors="replace").splitlines(keepends=True) if before_file.exists() else []
        after_lines = after_file.read_text(errors="replace").splitlines(keepends=True) if after_file.exists() else []
        chunks.extend(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
        )
    return "".join(chunks)


def changed_files(before: Path, after: Path) -> list[Path]:
    paths: set[Path] = set()
    for root in (before, after):
        for path in root.rglob("*"):
            if should_skip(path):
                continue
            if path.is_file():
                paths.add(path.relative_to(root))

    changed: list[Path] = []
    for rel_path in sorted(paths):
        before_file = before / rel_path
        after_file = after / rel_path
        if not before_file.exists() or not after_file.exists():
            changed.append(rel_path)
            continue
        if not filecmp.cmp(before_file, after_file, shallow=False):
            changed.append(rel_path)
    return changed


def should_skip(path: Path) -> bool:
    return any(part in {".git", ".harness", "__pycache__", ".pytest_cache"} for part in path.parts)
