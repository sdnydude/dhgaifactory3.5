"""Tests for doc_ingest write-auth header support (T13 full coverage)."""


class TestDocIngestAuthHeaders:
    def test_auth_headers_from_env(self, monkeypatch):
        from doc_ingest import _auth_headers

        monkeypatch.setenv("REGISTRY_WRITE_TOKEN", "tok-123")
        assert _auth_headers() == {"Authorization": "Bearer tok-123"}

    def test_ingest_post_sends_auth_header(self, monkeypatch, tmp_path):
        from unittest.mock import MagicMock, patch

        import doc_ingest

        monkeypatch.setenv("REGISTRY_WRITE_TOKEN", "tok-123")
        (tmp_path / "a.md").write_text("# Title\n\nbody\n")
        captured = {}

        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        def fake_post(url, json=None, headers=None):
            captured["headers"] = headers
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"upserted": 1, "swept": 0}
            return resp

        client.post = fake_post
        with patch.object(doc_ingest.httpx, "Client", return_value=client):
            doc_ingest.ingest_project("portage", tmp_path, "http://x", False)
        assert captured["headers"] == {"Authorization": "Bearer tok-123"}
