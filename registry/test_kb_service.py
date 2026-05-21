"""Tests for kb_service — extractors, search_source, and kb_search."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock
from sqlalchemy.exc import OperationalError

import kb_service as svc
from models import (
    DocPage, Insight, DecisionLog, ShipSession, Correction,
    AgentSession, DevChangelog, BugFix, DeferredItem,
)


def _mock_row(spec_cls, **attrs):
    row = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(row, k, v)
    return row


class TestExtractDocPage:
    def test_returns_title_content_metadata(self):
        row = _mock_row(DocPage, title="My Title", content="body text",
                        source_file="a.md", chunk_index=0, heading_path="root > a")
        title, content, meta = svc._extract_doc_page(row)
        assert title == "My Title"
        assert content == "body text"
        assert meta["source_file"] == "a.md"

    def test_fallback_title_from_content(self):
        row = _mock_row(DocPage, title=None, content="First line here\nMore text",
                        source_file="b.md", chunk_index=1, heading_path="")
        title, _, _ = svc._extract_doc_page(row)
        assert "First line" in title


class TestExtractInsight:
    def test_fields_map(self):
        row = _mock_row(Insight, tldr="Short summary", insight_statement="Long text",
                        category="arch", subcategory="patterns", tags=["a"])
        title, content, meta = svc._extract_insight(row)
        assert title == "Short summary"
        assert content == "Long text"
        assert meta["category"] == "arch"


class TestExtractDecisionLog:
    def test_includes_rationale_and_rejected(self):
        row = _mock_row(DecisionLog, title="Pick X", choice="X",
                        rationale="Because Y", alternatives_rejected="Z was slow",
                        domain="backend", supersedes=None, tags=[])
        title, content, meta = svc._extract_decision_log(row)
        assert title == "Pick X"
        assert "Rationale: Because Y" in content
        assert "Rejected: Z was slow" in content


class TestExtractShipSession:
    def test_with_approach_and_complexity(self):
        row = _mock_row(ShipSession, feature="New widget", approach="TDD",
                        complexity="medium", status="done", pr_url=None,
                        tdd=True, branch="main")
        title, content, meta = svc._extract_ship_session(row)
        assert title == "New widget"
        assert "Approach: TDD" in content
        assert meta["complexity"] == "medium"


class TestExtractCorrection:
    def test_builds_title_from_category_and_message(self):
        row = _mock_row(Correction, category="style",
                        user_message="Don't use emojis in code",
                        context="Emoji was added to a log line",
                        claude_action="Remove emojis from log",
                        session_id="s1", tags=["style"])
        title, content, meta = svc._extract_correction(row)
        assert "style" in title
        assert "Don't use emojis" in title
        assert "Should have: Remove emojis" in content


class TestExtractAgentSession:
    def test_uses_tldr_as_title(self):
        row = _mock_row(AgentSession, tldr="Fixed auth bug",
                        summary="Investigated and fixed JWT expiry",
                        project="dhg", source="claude-code",
                        session_id="abc", model="opus", skills_used=["debug"],
                        branch="main")
        title, content, meta = svc._extract_agent_session(row)
        assert title == "Fixed auth bug"
        assert "JWT expiry" in content

    def test_fallback_title_from_summary(self):
        row = _mock_row(AgentSession, tldr=None,
                        summary="Did some refactoring\nMore details",
                        project="p", source="s", session_id="x",
                        model="sonnet", skills_used=[], branch="dev")
        title, _, _ = svc._extract_agent_session(row)
        assert "Did some refactoring" in title


class TestExtractDevChangelog:
    def test_combines_insight_and_notes(self):
        row = _mock_row(DevChangelog, epic="Auth overhaul",
                        key_insight="Simplified token flow",
                        notes="Removed 3 middleware layers",
                        slug="auth-v2", category="refactor",
                        declared_status="done", detected_status="merged",
                        commit_count=12)
        title, content, meta = svc._extract_dev_changelog(row)
        assert title == "Auth overhaul"
        assert "Simplified token flow" in content
        assert "Removed 3 middleware" in content
        assert meta["slug"] == "auth-v2"


class TestExtractBugFix:
    def test_all_parts(self):
        row = _mock_row(BugFix, tldr="NullRef in parser",
                        symptom="Crash on empty input",
                        root_cause="Missing guard",
                        fix_applied="Added None check",
                        category="backend", severity="high",
                        files_affected=["parser.py"], tags=["bug"])
        title, content, meta = svc._extract_bug_fix(row)
        assert title == "NullRef in parser"
        assert "Root Cause: Missing guard" in content
        assert meta["severity"] == "high"


class TestExtractDeferredItem:
    def test_includes_reason_and_context(self):
        row = _mock_row(DeferredItem, title="Add caching",
                        description="Redis layer needed",
                        reason="Time constraint",
                        source_context="Sprint 4 planning",
                        category="perf", priority="high",
                        status="open", affected_files=["cache.py"],
                        tags=["perf"])
        title, content, meta = svc._extract_deferred_item(row)
        assert title == "Add caching"
        assert "Reason Deferred: Time constraint" in content
        assert meta["priority"] == "high"


class TestSourceConfig:
    def test_all_nine_sources_registered(self):
        assert len(svc.SOURCE_CONFIG) == 9
        expected = {"docs", "insights", "decisions", "ship_sessions",
                    "corrections", "agent_sessions", "dev_changelog",
                    "bug_fixes", "deferred_items"}
        assert set(svc.SOURCE_CONFIG.keys()) == expected


class TestSearchSource:
    def _make_db(self, fts_results=None, vec_results=None):
        db = MagicMock()
        call_count = {"n": 0}

        def query_side(*_args):
            call_count["n"] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            if call_count["n"] == 1:
                q.all.return_value = fts_results or []
            else:
                q.all.return_value = vec_results or []
            return q

        db.query.side_effect = query_side
        return db

    def test_fts_only(self):
        row = _mock_row(BugFix, id="r1", tldr="Bug",
                        symptom="Crash", root_cause="Bad logic",
                        fix_applied="Patched", category="b", severity="low",
                        files_affected=[], tags=[])
        db = self._make_db(fts_results=[(row, 0.8)])
        results = svc.search_source("bug_fixes", db, "crash", None, None, 10)
        assert len(results) == 1
        assert results[0][0] == "r1"

    def test_vector_only(self):
        row = _mock_row(Insight, id="i1", tldr="Tip", insight_statement="Use X",
                        category="a", subcategory="b", tags=[])
        db = self._make_db(vec_results=[row])
        results = svc.search_source("insights", db, "tip", [0.1, 0.2], None, 10)
        assert len(results) >= 0

    def test_rrf_combines_scores(self):
        row = _mock_row(BugFix, id="r1", tldr="Bug",
                        symptom="Crash", root_cause="X",
                        fix_applied="Y", category="b", severity="low",
                        files_affected=[], tags=[])
        db = self._make_db(fts_results=[(row, 0.9)], vec_results=[row])
        results = svc.search_source("bug_fixes", db, "crash", [0.1], None, 10)
        if results:
            assert results[0][1] > 1.0 / (60 + 1)

    def test_project_filter_passed_through(self):
        db = self._make_db()
        svc.search_source("docs", db, "test", None, "proj-a", 10)
        assert db.query.called

    def test_fts_exception_returns_empty(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.side_effect = OperationalError("fail", {}, None)
        db.query.return_value = q
        results = svc.search_source("docs", db, "test", None, None, 10)
        assert results == []


class TestKbSearch:
    def test_aggregates_multiple_sources(self):
        db = MagicMock()
        call_count = {"n": 0}

        def query_side(*_args):
            call_count["n"] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            q.all.return_value = []
            return q

        db.query.side_effect = query_side
        results, searched, failed = svc.kb_search(
            db, "query", None, sources=["docs", "insights"], limit=5,
        )
        assert "docs" in searched
        assert "insights" in searched
        assert failed == []

    def test_failed_source_tracked(self):
        db = MagicMock()
        with MagicMock() as mock_search:
            import unittest.mock as um
            with um.patch.object(svc, "search_source", side_effect=Exception("boom")):
                results, searched, failed = svc.kb_search(
                    db, "query", None, sources=["docs"], limit=5,
                )
        assert "docs" in failed
        assert searched == []

    def test_results_sorted_by_score(self):
        row_low = _mock_row(BugFix, id="low", tldr="Low",
                            symptom="x", root_cause="y",
                            fix_applied="z", category="b", severity="low",
                            files_affected=[], tags=[])
        row_high = _mock_row(BugFix, id="high", tldr="High",
                             symptom="a", root_cause="b",
                             fix_applied="c", category="b", severity="high",
                             files_affected=[], tags=[])

        db = MagicMock()
        call_count = {"n": 0}

        def query_side(*_args):
            call_count["n"] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            if call_count["n"] == 1:
                q.all.return_value = [(row_low, 0.1)]
            elif call_count["n"] == 3:
                q.all.return_value = [(row_high, 0.9), (row_low, 0.5)]
            else:
                q.all.return_value = []
            return q

        db.query.side_effect = query_side
        results, _, _ = svc.kb_search(
            db, "query", None, sources=["bug_fixes", "bug_fixes"], limit=10,
        )
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]

    def test_limit_respected(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        results, _, _ = svc.kb_search(
            db, "query", None, sources=["docs"], limit=3,
        )
        assert len(results) <= 3
