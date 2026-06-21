from harness_runtime import Harness
from harness_runtime.harvesters import github as github_harvester


class FakeResponse:
    def __init__(self, payload: str):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_github_harvest_creates_tasks(tmp_path, monkeypatch):
    issues_payload = """
    [
      {
        "number": 12,
        "title": "Fix flaky parser",
        "body": "The parser fails on empty input.",
        "html_url": "https://github.com/acme/widgets/issues/12",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "alice"}],
        "milestone": {"title": "v1.0"},
        "user": {"login": "reporter"},
        "state": "open",
        "state_reason": null,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "closed_at": null
      }
    ]
    """
    comments_payload = """
    [
      {
        "body": "Confirmed. This breaks empty prompts too.",
        "html_url": "https://github.com/acme/widgets/issues/12#issuecomment-1",
        "created_at": "2026-01-01T01:00:00Z",
        "updated_at": "2026-01-01T01:00:00Z",
        "user": {"login": "maintainer"}
      }
    ]
    """
    timeline_payload = """
    [
      {
        "event": "cross-referenced",
        "source": {
          "issue": {
            "number": 45,
            "title": "Fix parser edge case",
            "html_url": "https://github.com/acme/widgets/pull/45",
            "state": "closed",
            "pull_request": {"url": "https://api.github.com/repos/acme/widgets/pulls/45"}
          }
        }
      }
    ]
    """
    pr_files_payload = """
    [
      {
        "filename": "python/widgets/parser.py"
      },
      {
        "filename": "tests/test_parser.py"
      }
    ]
    """

    def fake_urlopen(request):
        url = request.full_url
        if "/issues?state=open&per_page=30&page=1" in url:
            return FakeResponse(issues_payload)
        if "/issues/12/comments" in url:
            return FakeResponse(comments_payload)
        if url.endswith("/issues/12/timeline"):
            return FakeResponse(timeline_payload)
        if "/pulls/45/files?per_page=20&page=1" in url:
            return FakeResponse(pr_files_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(github_harvester, "urlopen", fake_urlopen)

    harness = Harness(tmp_path)
    harness.init()
    tasks = harness.harvest_github(
        repo_full_name="acme/widgets",
        token="test-token",
        verification_commands=["pytest", "ruff check"],
    )

    assert len(tasks) == 1
    assert tasks[0].id == "github_acme_widgets_12"
    assert tasks[0].source == "github"
    assert tasks[0].verification.commands == ["pytest", "ruff check"]
    assert tasks[0].metadata["issue_number"] == 12
    assert tasks[0].metadata["assignees"] == ["alice"]
    assert tasks[0].metadata["milestone"] == "v1.0"
    assert tasks[0].metadata["author"] == "reporter"
    assert tasks[0].metadata["comments"][0]["author"] == "maintainer"
    assert tasks[0].metadata["linked_pull_requests"][0]["number"] == 45
    assert tasks[0].metadata["linked_pull_requests"][0]["files"] == [
        "python/widgets/parser.py",
        "tests/test_parser.py",
    ]
    assert "Issue comments:" in tasks[0].instructions
    assert "Linked pull requests:" in tasks[0].instructions
    assert "touched files:" in tasks[0].instructions
