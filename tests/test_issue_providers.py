import pytest

from harness_runtime.harvesters import get_issue_provider


def test_get_issue_provider_returns_github():
    provider = get_issue_provider("github")

    assert provider.name == "github"
    assert provider.env_token_var == "GITHUB_TOKEN"


def test_get_issue_provider_rejects_unknown():
    with pytest.raises(ValueError):
        get_issue_provider("gitlab")
