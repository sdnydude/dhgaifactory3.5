"""Registry write-auth header support for cloud agents (T13 full coverage)."""


def test_write_headers_from_env(monkeypatch):
    from src.registry_auth import registry_write_headers

    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", "tok-abc")
    assert registry_write_headers() == {"Authorization": "Bearer tok-abc"}
