"""P5 T10 — logs_chat unit checks (plain-python runnable; no pytest in prod image)."""
import logs_chat_service as svc


def test_local_only_no_anthropic_import():
    import re
    src = open(svc.__file__).read()
    assert not re.search(r"^\s*(import|from)\s+anthropic", src, re.M), "cloud SDK import found"
    assert "ANTHROPIC_API_KEY" not in src


def test_build_queries_deterministic_error_intent():
    qs = svc.build_queries("portage-api", 60, "why did portage-api error tonight?")
    assert qs[0].logql.startswith('{container="portage-api"}')
    assert "error" in qs[0].logql.lower() and len(qs) == 2


def test_build_queries_no_container_falls_back_to_job_errors():
    qs = svc.build_queries(None, 30, "anything failing?")
    assert [q.model_dump() for q in qs] == [{"desc": "error-level lines, all containers (30m)",
        "logql": '{job="dhg-ai-factory"} | level=~`(?i)error|fatal|panic|critical`', "lines": 0}]


def test_resolve_container_fuzzy():
    known = ["portage-api", "dhg-registry-api", "dhg-loki"]
    assert svc.resolve_container("", "portage-appi", known) == "portage-api"
    assert svc.resolve_container("what is dhg-loki doing", None, known) == "dhg-loki"
    assert svc.resolve_container("nothing relevant here", None, known) is None


def test_ground_answer_flags_unknown_container_names():
    text = "dhg-loki restarted; dhg-imaginary-svc crashed."
    _, unknown = svc.ground_answer(text, ["dhg-loki"])
    assert unknown == ["dhg-imaginary-svc"]


def test_ground_answer_allows_names_quoted_from_context():
    text = "dhg-loki mentions dhg-eval-db and job dhg-ai-factory."
    ctx = ["[dhg-loki] query for {container=\"dhg-eval-db\"} job=dhg-ai-factory ok"]
    _, unknown = svc.ground_answer(text, ["dhg-loki"], ctx)
    assert unknown == []


def test_context_char_cap_is_8k_tokens():
    assert svc.MAX_CONTEXT_CHARS == 32_000 and svc.BUDGET_TOTAL_S == 45.0


def test_token_ok_table():
    """_token_ok: the entire auth gate — verify every rejection branch + accept."""
    import os
    import logs_chat_endpoints as ep
    old = os.environ.get("LOGS_CHAT_TOKEN")
    try:
        os.environ["LOGS_CHAT_TOKEN"] = "sekrit"
        assert ep._token_ok("Bearer sekrit") is True
        assert ep._token_ok("Bearer wrong") is False
        assert ep._token_ok("sekrit") is False          # no scheme
        assert ep._token_ok("Token sekrit") is False    # wrong scheme
        assert ep._token_ok(None) is False
        os.environ["LOGS_CHAT_TOKEN"] = ""
        assert ep._token_ok("Bearer ") is False         # empty expected → closed
    finally:
        if old is None:
            os.environ.pop("LOGS_CHAT_TOKEN", None)
        else:
            os.environ["LOGS_CHAT_TOKEN"] = old


def test_fetch_context_deadline_past_skips_queries():
    import asyncio, time
    import logs_chat_service as s

    class NoCallClient:
        async def get(self, *a, **k):
            raise AssertionError("must not query past deadline")

    from logs_chat_schemas import QuerySpec
    qs = [QuerySpec(desc="d", logql='{container="x"}')]
    out, lines = asyncio.run(s.fetch_context(NoCallClient(), qs, 5, time.time() - 1))
    assert out[0].lines == 0 and lines == []


def test_fetch_context_char_budget_drops_overflow():
    import asyncio, time
    import logs_chat_service as s

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            big = "x" * (s.MAX_CONTEXT_CHARS - 10)
            return {"data": {"result": [{"stream": {"container": "c"},
                    "values": [["1", big], ["2", "second line that cannot fit"]]}]}}

    class FakeClient:
        async def get(self, *a, **k): return FakeResp()

    from logs_chat_schemas import QuerySpec
    qs = [QuerySpec(desc="d", logql='{container="c"}')]
    out, lines = asyncio.run(s.fetch_context(FakeClient(), qs, 5, time.time() + 30))
    assert len(lines) >= 1
    assert all(len(e) <= 410 or "x" in e for e in lines)
    total = sum(len(e) for e in lines)
    assert total <= s.MAX_CONTEXT_CHARS
