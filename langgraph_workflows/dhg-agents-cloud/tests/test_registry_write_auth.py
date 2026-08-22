"""Registry write-auth header support for cloud agents (T13 full coverage)."""


def test_write_headers_from_env(monkeypatch):
    from src.registry_auth import registry_write_headers

    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", "tok-abc")
    assert registry_write_headers() == {"Authorization": "Bearer tok-abc"}


def _import_agent_with_stubs(monkeypatch):
    """agent.py drags in langchain/langgraph; stub them so the registry-client
    class is testable in the plain-pytest env."""
    import sys
    import types

    def stub(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        monkeypatch.setitem(sys.modules, name, m)
        return m

    class _Any:  # placeholder for imported names; absorbs any use
        def __init__(self, *a, **kw):
            pass

        def __getattr__(self, name):
            return lambda *a, **kw: self

        def __call__(self, *a, **kw):
            return self

    stub("langgraph")
    stub("langgraph.graph", StateGraph=_Any, END=object())
    stub("langgraph.graph.message", add_messages=lambda *a, **kw: None)
    stub("langsmith", traceable=lambda *a, **kw: (lambda f: f))
    stub("langchain_anthropic", ChatAnthropic=_Any)
    stub("langchain_core")
    stub("langchain_core.runnables", RunnableConfig=dict)
    stub("langchain_google_genai", ChatGoogleGenerativeAI=_Any)
    stub("langchain_community")
    stub("langchain_community.chat_models", ChatOllama=_Any)
    stub("langchain_core.messages", HumanMessage=_Any, SystemMessage=_Any)
    stub("templates")
    stub("templates.renderer", render_template=lambda *a, **kw: "")

    import importlib
    if "agent" in sys.modules:
        del sys.modules["agent"]
    return importlib.import_module("agent")


def test_registry_write_clients_constructed_with_token_headers(monkeypatch):
    """All four registry-write methods must build their AsyncClient with the
    write-token headers — a dropped headers= kwarg would 401 every cloud-agent
    write under enforce mode with no test catching it (review TC#4)."""
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", "tok-agents")
    agent_mod = _import_agent_with_stubs(monkeypatch)

    captured = []

    class FakeClient:
        def __init__(self, *a, **kw):
            captured.append(kw.get("headers"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {}
            return resp

        async def patch(self, *a, **kw):
            resp = MagicMock()
            resp.status_code = 200
            return resp

    monkeypatch.setattr(agent_mod.httpx, "AsyncClient", FakeClient)
    reg = agent_mod.AIFactoryRegistry(registry_url="http://x")

    asyncio.run(reg.register())
    asyncio.run(reg.heartbeat())
    asyncio.run(reg.log_research_request("t", "u", {}))
    asyncio.run(reg.update_research_request("r1", "completed"))

    assert len(captured) == 4
    for headers in captured:
        assert headers == {"Authorization": "Bearer tok-agents"}, captured


def test_registry_write_failures_log_warnings(monkeypatch, caplog):
    """Non-2xx and unreachable registry writes must leave a log trace — today
    they vanish into falsy sentinels (review important #5). Armed the moment
    enforce-mode 401s these calls without a deployed token."""
    import asyncio
    import logging as _logging
    from unittest.mock import MagicMock

    monkeypatch.delenv("REGISTRY_WRITE_TOKEN", raising=False)
    agent_mod = _import_agent_with_stubs(monkeypatch)

    class FailClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            resp = MagicMock()
            resp.status_code = 401
            return resp

        async def patch(self, *a, **kw):
            resp = MagicMock()
            resp.status_code = 401
            return resp

    monkeypatch.setattr(agent_mod.httpx, "AsyncClient", FailClient)
    reg = agent_mod.AIFactoryRegistry(registry_url="http://x")

    with caplog.at_level(_logging.WARNING):
        asyncio.run(reg.heartbeat())
        asyncio.run(reg.update_research_request("r1", "failed"))
    msgs = [r.message for r in caplog.records]
    assert any("401" in m for m in msgs), f"expected HTTP-code warnings, got {msgs}"
