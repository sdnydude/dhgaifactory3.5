"""Tests for inference_service — nodes, models, interactions, routing."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock

import inference_service as svc
from models import InferenceNode, InferenceModel, LLMInteraction, RoutingConfig


def _mock_row(spec_cls, **attrs):
    row = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(row, k, v)
    return row


def _mock_req(**attrs):
    req = MagicMock()
    for k, v in attrs.items():
        setattr(req, k, v)
    return req


class TestListNodes:
    def test_returns_all_nodes(self):
        db = MagicMock()
        nodes = [_mock_row(InferenceNode, id="n1"), _mock_row(InferenceNode, id="n2")]
        db.query.return_value.all.return_value = nodes
        result = svc.list_nodes(db)
        assert len(result) == 2


class TestRegisterOrUpdateNode:
    def _base_req(self, **overrides):
        defaults = dict(
            node_name="gpu-1", host="10.0.0.100",
            gateway_port=8080, ollama_port=11434,
            gpu_model="RTX 5080", gpu_vram_gb=16,
            ram_gb=64, fallback_enabled=True,
            models=[],
        )
        defaults.update(overrides)
        return _mock_req(**defaults)

    def test_creates_new_node(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q

        req = self._base_req()
        result = svc.register_or_update_node(db, req)

        assert db.add.called
        assert db.commit.called

    def test_updates_existing_node(self):
        db = MagicMock()
        existing = _mock_row(InferenceNode, id="n1", node_name="gpu-1")
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = existing
        db.query.return_value = q

        req = self._base_req(host="10.0.0.200")
        svc.register_or_update_node(db, req)

        assert existing.host == "10.0.0.200"
        assert existing.status == "online"

    def test_syncs_new_model(self):
        db = MagicMock()
        existing_node = _mock_row(InferenceNode, id="n1", node_name="gpu-1")
        call_count = {"n": 0}

        def query_side(model_cls):
            call_count["n"] += 1
            q = MagicMock()
            q.filter.return_value = q
            if call_count["n"] == 1:
                q.first.return_value = existing_node
            else:
                q.first.return_value = None
            return q

        db.query.side_effect = query_side

        model_req = _mock_req(
            model_name="qwen3:14b", model_alias="qwen3",
            task_types=["chat"], priority=1,
            vram_usage_gb=10, max_context_length=4096,
        )
        req = self._base_req(models=[model_req])
        svc.register_or_update_node(db, req)

        assert db.add.called
        assert db.commit.called

    def test_updates_existing_model(self):
        db = MagicMock()
        existing_node = _mock_row(InferenceNode, id="n1", node_name="gpu-1")
        existing_model = _mock_row(InferenceModel, id="m1", model_name="qwen3:14b")
        call_count = {"n": 0}

        def query_side(model_cls):
            call_count["n"] += 1
            q = MagicMock()
            q.filter.return_value = q
            if call_count["n"] == 1:
                q.first.return_value = existing_node
            else:
                q.first.return_value = existing_model
            return q

        db.query.side_effect = query_side

        model_req = _mock_req(
            model_name="qwen3:14b", model_alias="qwen3-updated",
            task_types=["chat", "code"], priority=2,
            vram_usage_gb=12, max_context_length=8192,
        )
        req = self._base_req(models=[model_req])
        svc.register_or_update_node(db, req)

        assert existing_model.model_alias == "qwen3-updated"
        assert existing_model.loaded is True


class TestHeartbeat:
    def test_returns_none_for_unknown_node(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q
        result = svc.heartbeat(db, "unknown")
        assert result is None

    def test_updates_heartbeat(self):
        db = MagicMock()
        node = _mock_row(InferenceNode, id="n1", node_name="gpu-1", status="online")
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = node
        db.query.return_value = q

        result = svc.heartbeat(db, "gpu-1")
        assert db.commit.called

    def test_brings_offline_node_online(self):
        db = MagicMock()
        node = _mock_row(InferenceNode, id="n1", node_name="gpu-1", status="offline")
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = node
        db.query.return_value = q

        svc.heartbeat(db, "gpu-1")
        assert node.status == "online"


class TestSetNodeStatus:
    def test_returns_none_for_unknown(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q
        result = svc.set_node_status(db, "unknown", "draining")
        assert result is None

    def test_sets_status(self):
        db = MagicMock()
        node = _mock_row(InferenceNode, id="n1", status="online")
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = node
        db.query.return_value = q

        svc.set_node_status(db, "gpu-1", "draining")
        assert node.status == "draining"
        assert db.commit.called

    def test_online_status_updates_heartbeat(self):
        db = MagicMock()
        node = _mock_row(InferenceNode, id="n1", status="offline")
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = node
        db.query.return_value = q

        svc.set_node_status(db, "gpu-1", "online")
        assert node.status == "online"


class TestListModels:
    def _setup_db(self, route=None, query_results=None):
        db = MagicMock()
        call_count = {"n": 0}

        def query_side(model_cls, *args):
            call_count["n"] += 1
            q = MagicMock()
            q.join.return_value = q
            q.filter.return_value = q
            q.order_by.return_value = q
            if model_cls == RoutingConfig:
                q.first.return_value = route
            else:
                q.all.return_value = query_results or []
            return q

        db.query.side_effect = query_side
        return db

    def test_no_task_filter(self):
        models = [(_mock_row(InferenceModel), _mock_row(InferenceNode))]
        db = self._setup_db(query_results=models)
        result = svc.list_models(db)
        assert len(result) == 1

    def test_claude_preference_returns_empty(self):
        route = _mock_row(RoutingConfig, prefer="claude", enabled=True)
        db = self._setup_db(route=route)
        result = svc.list_models(db, task_type="summarize")
        assert result == []

    def test_local_alias_routing(self):
        route = _mock_row(RoutingConfig, prefer="local:qwen3", enabled=True)
        models = [(_mock_row(InferenceModel, model_alias="qwen3"),
                    _mock_row(InferenceNode))]
        db = self._setup_db(route=route, query_results=models)
        result = svc.list_models(db, task_type="chat")
        assert db.query.called

    def test_task_type_array_filter(self):
        route = _mock_row(RoutingConfig, prefer="any", enabled=True)
        db = self._setup_db(route=route)
        svc.list_models(db, task_type="code")
        assert db.query.called


class TestLogInteraction:
    def test_creates_interaction(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        node = _mock_row(InferenceNode, id="n1")
        q.first.return_value = node
        db.query.return_value = q

        req = _mock_req(
            node_name="gpu-1", timestamp="2026-01-01T00:00:00",
            user_id="u1", model_name="qwen3", model_source="ollama",
            model_digest="abc", task_type="chat", agent_name="research",
            session_id="s1", prompt_tokens=100, completion_tokens=50,
            latency_ms=1200, input_hash="h1", input_summary="test prompt",
            input_has_image=False, output="response text",
            output_validated=True, output_schema_name=None,
            fallback_used=False, fallback_reason=None,
            retry_count=0, estimated_cost_usd=0.01,
        )
        svc.log_interaction(db, req)

        assert db.add.called
        assert db.commit.called

    def test_handles_unknown_node(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q

        req = _mock_req(
            node_name="unknown", timestamp="2026-01-01T00:00:00",
            user_id="u1", model_name="m1", model_source="ollama",
            model_digest=None, task_type="chat", agent_name=None,
            session_id=None, prompt_tokens=10, completion_tokens=5,
            latency_ms=500, input_hash=None, input_summary=None,
            input_has_image=False, output="out",
            output_validated=False, output_schema_name=None,
            fallback_used=False, fallback_reason=None,
            retry_count=0, estimated_cost_usd=0.0,
        )
        svc.log_interaction(db, req)
        assert db.add.called


class TestQueryInteractions:
    def test_no_filters(self):
        db = MagicMock()
        q = MagicMock()
        q.order_by.return_value = q
        q.filter.return_value = q
        q.limit.return_value = q
        interactions = [_mock_row(LLMInteraction)]
        q.all.return_value = interactions
        db.query.return_value = q

        result = svc.query_interactions(db)
        assert len(result) == 1

    def test_filters_by_task_type(self):
        db = MagicMock()
        q = MagicMock()
        q.order_by.return_value = q
        q.filter.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q

        svc.query_interactions(db, task_type="chat")
        assert q.filter.called

    def test_filters_by_model_source(self):
        db = MagicMock()
        q = MagicMock()
        q.order_by.return_value = q
        q.filter.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q

        svc.query_interactions(db, model_source="ollama")
        assert q.filter.called


class TestListRoutingConfig:
    def test_returns_enabled_routes(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        routes = [_mock_row(RoutingConfig, task_type="chat", prefer="local:qwen3")]
        q.all.return_value = routes
        db.query.return_value = q

        result = svc.list_routing_config(db)
        assert len(result) == 1
