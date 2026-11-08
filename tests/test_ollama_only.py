"""Regression coverage for the service's mandatory external model backend."""

import pytest
from fastapi.testclient import TestClient

from app import create_app
from engine import LFM3Engine
from ollama_backend import engine_from_env
from options import SETTINGS


def test_explicitly_empty_backend_url_is_an_error(monkeypatch):
    monkeypatch.setenv("SERVICE_OLLAMA_URL", "  ")
    with pytest.raises(ValueError, match="SERVICE_OLLAMA_URL must not be empty"):
        engine_from_env("SERVICE_", LFM3Engine, "m")


def test_local_backend_is_default_when_url_is_unset(monkeypatch):
    monkeypatch.delenv("SERVICE_OLLAMA_URL", raising=False)
    assert engine_from_env("SERVICE_", LFM3Engine, "m") is not None


def test_unreachable_backend_keeps_service_available_and_chat_is_503(monkeypatch):
    import urllib.error
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    monkeypatch.setenv("SERVICE_OLLAMA_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("SERVICE_OLLAMA_MODEL", "m")
    with TestClient(create_app(warm=True)) as http:
        assert http.get("/health").json()["ready"] is False
        assert http.get("/admin/").status_code == 200
        for stream in (False, True):
            reply = http.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}], "stream": stream})
            assert reply.status_code == 503
            assert "start Ollama and pull m" in reply.json()["detail"]
            assert "127.0.0.1" not in reply.text


def test_settings_only_describe_supported_controls():
    assert {item.key for item in SETTINGS} == {
        "update_check_hours", "max_inflight", "cache_size", "thinking", "hide_reasoning", "warm",
    }


def test_missing_model_returns_503_then_recovers_when_pulled(monkeypatch):
    import io
    import json
    import urllib.error

    monkeypatch.setenv("SERVICE_OLLAMA_URL", "http://ollama.invalid:11434")
    monkeypatch.setenv("SERVICE_OLLAMA_MODEL", "m")
    installed = False

    def request(req, **kwargs):
        if not installed:
            raise urllib.error.HTTPError(req.full_url, 404, "missing", {}, io.BytesIO(b'{"error":"internal path"}'))
        body = {"done": True} if req.full_url.endswith("/api/generate") else {"message": {"content": "hello"}}
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr("urllib.request.urlopen", request)
    with TestClient(create_app(warm=True)) as http:
        reply = http.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
        assert reply.status_code == 503
        assert "internal path" not in reply.text
        assert http.get("/health").json()["ready"] is False
        installed = True
        assert http.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]}).json()["content"] == "hello"
        assert http.get("/health").json()["ready"] is True


def test_reasoning_visibility_changes_do_not_reuse_old_cached_answers(monkeypatch, tmp_path):
    import io
    import json

    from settings import Config
    from tokens import TokenStore

    def request(req, **kwargs):
        body = {"done": True} if req.full_url.endswith("/api/generate") else {"message": {"content": "reason</think>answer"}}
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr("urllib.request.urlopen", request)
    store = TokenStore(tmp_path / "t.json")
    config = Config(store.settings_path, SETTINGS)
    config.set({"warm": False, "update_check_hours": 0})
    with TestClient(create_app(tokens=store, config=config)) as http:
        body = {"messages": [{"role": "user", "content": "hi"}]}
        assert http.post("/v1/chat", json=body).json()["content"] == "answer"
        assert http.post("/v1/chat", json=body).headers["X-Cache"] == "hit"
        config.set({"hide_reasoning": False})
        shown = http.post("/v1/chat", json=body)
        assert shown.headers["X-Cache"] == "miss"
        assert shown.json()["content"] == "reason</think>answer"
        config.set({"thinking": "on"})
        assert http.post("/v1/chat", json=body).headers["X-Cache"] == "miss"


def test_explicit_download_pulls_an_already_installed_model(monkeypatch, tmp_path):
    import io
    import json

    seen = []

    def request(req, **kwargs):
        seen.append(req.full_url.rsplit("/", 1)[-1])
        body = {"models": [{"name": "m", "digest": "same"}]} if req.full_url.endswith("/tags") else {"status": "success"}
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setenv("SERVICE_OLLAMA_MODEL", "m")
    monkeypatch.setattr("urllib.request.urlopen", request)
    engine = engine_from_env("SERVICE_", LFM3Engine, "m", marker=tmp_path / "marker")
    with TestClient(create_app(engine, admin_password="admin")) as http:
        assert http.post("/admin/updates/check", headers={"X-Internal-Token": "admin"}).json()["weights"][0]["update"] is True
        reply = http.post("/admin/updates/weights", headers={"X-Internal-Token": "admin"})
        assert reply.status_code == 200
        assert "pull" in seen
        assert engine.generation == 1 and (tmp_path / "marker").exists()


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("broken", ["timeout", "reset", "incomplete", "invalid-json", "invalid-body", "truncated-stream"])
def test_backend_read_failures_are_sanitized_503_and_clear_readiness(monkeypatch, broken, stream):
    import http.client
    import io
    import json

    def request(req, **kwargs):
        if req.full_url.endswith("/generate"):
            return io.BytesIO(b'{"done":true}')
        if broken == "truncated-stream":
            return io.BytesIO(b'{"message":{"content":"unfinished"}}\n' if stream else b'{"message":')
        if broken == "invalid-json":
            return io.BytesIO(b'bad backend.internal/path')
        if broken == "invalid-body":
            return io.BytesIO(b'[]')

        class BrokenResponse(io.BytesIO):
            def read(self, *args):
                if broken == "timeout":
                    raise TimeoutError("backend.internal/path")
                if broken == "reset":
                    raise ConnectionResetError("backend.internal/path")
                raise http.client.IncompleteRead(b"backend.internal/path")

            def __iter__(self):
                self.read()
                return iter(())

        return BrokenResponse()

    monkeypatch.setenv("SERVICE_OLLAMA_MODEL", "m")
    monkeypatch.setattr("urllib.request.urlopen", request)
    with TestClient(create_app()) as http:
        reply = http.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}], "stream": stream})
        assert reply.status_code == 503
        assert "start Ollama and pull m" in reply.json()["detail"]
        assert "backend.internal/path" not in reply.text
        assert http.get("/health").json()["ready"] is False


def test_truncation_after_first_stream_piece_reports_503_error_line(monkeypatch):
    import io
    import json

    def request(req, **kwargs):
        return io.BytesIO(b'{"done":true}' if req.full_url.endswith("/generate") else b'{"message":{"content":"hello"}}\n')

    monkeypatch.setenv("SERVICE_OLLAMA_MODEL", "m")
    monkeypatch.setenv("SERVICE_HIDE_REASONING", "false")
    monkeypatch.setattr("urllib.request.urlopen", request)
    with TestClient(create_app()) as http:
        reply = http.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}], "stream": True})
        assert reply.status_code == 200
        lines = [json.loads(line) for line in reply.text.splitlines()]
        assert lines[0] == {"type": "content", "text": "hello"}
        assert lines[-1]["type"] == "error" and lines[-1]["status"] == 503
        assert "start Ollama and pull m" in lines[-1]["message"]
        assert http.get("/health").json()["ready"] is False


def test_token_routes_refuse_restrictions_and_hide_legacy_scope_labels(tmp_path):
    from tokens import TokenStore

    store = TokenStore(tmp_path / "t.json")
    old = store.create("legacy", ["old-project"])
    with TestClient(create_app(admin_password="admin", tokens=store)) as http:
        headers = {"X-Internal-Token": "admin"}
        for projects in ([], ["app-a"]):
            assert http.post("/admin/tokens", headers=headers, json={"name": "new", "projects": projects}).status_code == 422
            assert http.put(f"/admin/tokens/{old['id']}", headers=headers, json={"projects": projects}).status_code == 422
        assert http.get("/admin/tokens", headers=headers).json()["tokens"][0]["projects"] is None
        assert http.post("/admin/tokens", headers=headers, json={"name": "new", "projects": None}).status_code == 200
