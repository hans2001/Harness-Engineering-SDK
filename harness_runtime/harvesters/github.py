from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from harness_runtime.config import harness_dir
from harness_runtime.schemas import TaskSpec, VerificationSpec, dump_task
from harness_runtime.storage import Storage


def harvest_github_issues(
    repo: Path,
    repo_full_name: str,
    token: str | None = None,
    state: str = "open",
    limit: int = 20,
    comment_limit: int = 10,
    verification_commands: list[str] | None = None,
) -> list[TaskSpec]:
    token = token or os.environ.get("GITHUB_TOKEN")

    issues = fetch_github_issues(repo_full_name, token=token, state=state, limit=limit)
    tasks = [
        task_from_issue(
            issue,
            repo_full_name=repo_full_name,
            comments=fetch_issue_comments(
                repo_full_name,
                issue["number"],
                token=token,
                limit=comment_limit,
            ),
            linked_pull_requests=fetch_linked_pull_requests(
                repo_full_name,
                issue["number"],
                token=token,
            ),
            verification_commands=verification_commands,
        )
        for issue in issues
        if "pull_request" not in issue
    ]

    task_dir = harness_dir(repo) / "tasks"
    storage = Storage(repo)
    for task in tasks:
        out_path = task_dir / f"{task.id}.yaml"
        dump_task(task, out_path)
        storage.upsert_task(task, out_path)
    return tasks


def fetch_github_issues(
    repo_full_name: str,
    token: str | None,
    state: str = "open",
    limit: int = 20,
) -> list[dict]:
    owner, name = repo_full_name.split("/", 1)
    per_page = min(max(limit, 30), 100)
    page = 1
    collected: list[dict] = []
    while len(collected) < limit:
        params = urlencode({"state": state, "per_page": per_page, "page": page})
        url = f"https://api.github.com/repos/{owner}/{name}/issues?{params}"
        payload = github_get(url, token=token, accept="application/vnd.github+json")
        if not payload:
            break
        collected.extend(issue for issue in payload if "pull_request" not in issue)
        if len(payload) < per_page:
            break
        page += 1
    return collected[:limit]


def fetch_issue_comments(
    repo_full_name: str,
    issue_number: int,
    token: str | None,
    limit: int = 10,
) -> list[dict]:
    owner, name = repo_full_name.split("/", 1)
    params = urlencode({"per_page": min(limit, 100)})
    url = f"https://api.github.com/repos/{owner}/{name}/issues/{issue_number}/comments?{params}"
    payload = github_get(url, token=token, accept="application/vnd.github+json")
    return payload[:limit]


def fetch_linked_pull_requests(
    repo_full_name: str,
    issue_number: int,
    token: str | None,
) -> list[dict]:
    owner, name = repo_full_name.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/issues/{issue_number}/timeline"
    payload = github_get(url, token=token, accept="application/vnd.github+json")
    linked_prs: list[dict] = []
    for event in payload:
        source = event.get("source") or {}
        issue = source.get("issue") or {}
        pull_request = issue.get("pull_request")
        if event.get("event") == "cross-referenced" and pull_request:
            pr_number = issue.get("number")
            linked_prs.append(
                {
                    "number": pr_number,
                    "title": issue.get("title"),
                    "url": issue.get("html_url"),
                    "state": issue.get("state"),
                    "files": fetch_pull_request_files(repo_full_name, pr_number, token=token),
                }
            )
    return dedupe_pull_requests(linked_prs)


def fetch_pull_request_files(
    repo_full_name: str,
    pull_request_number: int | None,
    token: str | None,
    limit: int = 20,
) -> list[str]:
    if not isinstance(pull_request_number, int):
        return []
    owner, name = repo_full_name.split("/", 1)
    page = 1
    per_page = min(max(limit, 1), 100)
    files: list[str] = []
    while len(files) < limit:
        params = urlencode({"per_page": per_page, "page": page})
        url = f"https://api.github.com/repos/{owner}/{name}/pulls/{pull_request_number}/files?{params}"
        payload = github_get(url, token=token, accept="application/vnd.github+json")
        if not payload:
            break
        files.extend(item["filename"] for item in payload if item.get("filename"))
        if len(payload) < per_page:
            break
        page += 1
    return files[:limit]


def github_get(url: str, token: str | None, accept: str) -> list[dict]:
    headers = {
        "Accept": accept,
        "User-Agent": "harness-runtime",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed with {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed: {error.reason}") from error


def task_from_issue(
    issue: dict,
    repo_full_name: str,
    comments: list[dict] | None = None,
    linked_pull_requests: list[dict] | None = None,
    verification_commands: list[str] | None = None,
) -> TaskSpec:
    number = issue["number"]
    body = (issue.get("body") or "").strip()
    comments = comments or []
    linked_pull_requests = linked_pull_requests or []
    instructions = render_issue_instructions(issue, body, comments, linked_pull_requests)
    return TaskSpec(
        id=f"github_{repo_full_name.replace('/', '_')}_{number}",
        title=issue["title"],
        source="github",
        repo_path=".",
        instructions=instructions,
        verification=VerificationSpec(commands=verification_commands or ["pytest"]),
        metadata={
            "repo_full_name": repo_full_name,
            "issue_number": number,
            "issue_url": issue.get("html_url"),
            "author": (issue.get("user") or {}).get("login"),
            "labels": [label["name"] for label in issue.get("labels", [])],
            "assignees": [assignee["login"] for assignee in issue.get("assignees", [])],
            "milestone": (issue.get("milestone") or {}).get("title"),
            "state": issue.get("state"),
            "state_reason": issue.get("state_reason"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "closed_at": issue.get("closed_at"),
            "comments": [
                {
                    "author": (comment.get("user") or {}).get("login"),
                    "body": comment.get("body", ""),
                    "created_at": comment.get("created_at"),
                    "updated_at": comment.get("updated_at"),
                    "url": comment.get("html_url"),
                }
                for comment in comments
            ],
            "linked_pull_requests": linked_pull_requests,
        },
    )


def render_issue_instructions(
    issue: dict,
    body: str,
    comments: list[dict],
    linked_pull_requests: list[dict],
) -> str:
    lines = [issue["title"], ""]
    if body:
        lines.extend([body, ""])

    if comments:
        lines.append("Issue comments:")
        for comment in comments:
            author = (comment.get("user") or {}).get("login") or "unknown"
            comment_body = (comment.get("body") or "").strip()
            if comment_body:
                lines.append(f"- {author}: {comment_body}")
        lines.append("")

    if linked_pull_requests:
        lines.append("Linked pull requests:")
        for pull_request in linked_pull_requests:
            title = pull_request.get("title") or "Untitled PR"
            number = pull_request.get("number")
            state = pull_request.get("state") or "unknown"
            lines.append(f"- PR #{number}: {title} [{state}]")
            files = pull_request.get("files") or []
            if files:
                lines.append(f"  touched files: {', '.join(files[:8])}")
        lines.append("")

    return "\n".join(lines).strip()


def dedupe_pull_requests(linked_pull_requests: list[dict]) -> list[dict]:
    seen: set[int] = set()
    deduped: list[dict] = []
    for pull_request in linked_pull_requests:
        number = pull_request.get("number")
        if not isinstance(number, int) or number in seen:
            continue
        seen.add(number)
        deduped.append(pull_request)
    return deduped
