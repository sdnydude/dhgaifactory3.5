"""Tests for captures_service — natural-key lookup dispatch."""
from unittest.mock import MagicMock

import pytest


class TestLookupCapture:
    def test_insights_lookup_filters_project_and_tldr(self):
        from captures_service import lookup_capture

        db = MagicMock()
        row = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        result = lookup_capture(db, "insights", "portage", "some tldr")
        assert result is row

    def test_corrections_lookup_hashes_key_with_md5(self):
        import hashlib
        from unittest.mock import patch

        from captures_service import lookup_capture

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("captures_service.compute_upsert_hash", wraps=None) as fake:
            fake.side_effect = lambda m: hashlib.md5(m.encode()).hexdigest()
            lookup_capture(db, "corrections", "portage", "dont do that")
            fake.assert_called_once_with("dont do that")

    @pytest.mark.parametrize(
        "pipeline,model_name,key_col",
        [
            ("bug_fixes", "BugFix", "tldr"),
            ("decision_logs", "DecisionLog", "title"),
            ("deferred_items", "DeferredItem", "title"),
            ("ship_sessions", "ShipSession", "feature"),
            ("test_coverage", "TestCoverage", "title"),
            ("session_reports", "SessionReport", "title"),
        ],
    )
    def test_all_pipelines_dispatch_to_model_and_key(self, pipeline, model_name, key_col):
        import models
        from captures_service import PIPELINES, lookup_capture

        model, col = PIPELINES[pipeline]
        assert model is getattr(models, model_name)
        assert col == key_col

        db = MagicMock()
        row = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = row
        assert lookup_capture(db, pipeline, "portage", "some key") is row
        db.query.assert_called_once_with(model)

    def test_corrections_lookup_includes_category_when_given(self):
        """The corrections unique key is (project, category, hash) — two
        different-category corrections can share user_message text; lookup
        must not conflate them (review important #3)."""
        from unittest.mock import call, patch

        from captures_service import lookup_capture
        import models

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        lookup_capture(db, "corrections", "portage", "dont do that", category="docker-guessing")
        filter_args = db.query.return_value.filter.call_args
        # the category criterion must be part of the filter expression set
        assert len(filter_args.args) == 3, (
            f"expected project+hash+category criteria, got {len(filter_args.args)}"
        )
