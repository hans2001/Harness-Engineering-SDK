import pytest
from types import SimpleNamespace

from harness_runtime.harvesters import (
    IssueProvider,
    get_issue_provider,
    issue_providers,
    register_issue_provider,
    reset_issue_providers,
    unregister_issue_provider,
)
from harness_runtime.harvesters import providers as provider_registry


def test_get_issue_provider_returns_github():
    provider = get_issue_provider("github")

    assert provider.name == "github"
    assert provider.env_token_var == "GITHUB_TOKEN"


def test_get_issue_provider_rejects_unknown():
    with pytest.raises(ValueError):
        get_issue_provider("gitlab")


def test_issue_provider_registry_supports_custom_registration(tmp_path):
    def harvest_stub(repo, resource, token, state, limit, comment_limit, verification_commands, refresh_cache):
        return []

    provider = IssueProvider(name="internal", env_token_var="INTERNAL_TOKEN", harvest=harvest_stub)
    reset_issue_providers()
    register_issue_provider(provider)

    try:
        providers = issue_providers()
        assert "internal" in providers
        assert get_issue_provider("internal").env_token_var == "INTERNAL_TOKEN"
    finally:
        unregister_issue_provider("internal")
        reset_issue_providers()


def test_issue_provider_registry_discovers_entry_points(monkeypatch):
    def harvest_stub(repo, resource, token, state, limit, comment_limit, verification_commands, refresh_cache):
        return []

    reset_issue_providers()
    monkeypatch.setattr(
        provider_registry,
        "iter_entry_points",
        lambda group: [
            SimpleNamespace(
                name="entrypoint-internal",
                load=lambda: IssueProvider(name="entrypoint-internal", env_token_var="ENTRY_TOKEN", harvest=harvest_stub),
            )
        ],
    )

    providers = issue_providers()

    assert "entrypoint-internal" in providers
    assert get_issue_provider("entrypoint-internal").env_token_var == "ENTRY_TOKEN"
    reset_issue_providers()
