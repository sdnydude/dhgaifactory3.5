"""
Tests for the Intake Prefill Agent (intake_prefill_agent.py).

Covers:
- Graph construction and node inventory
- Individual node functions with mocked LLM
- Validation logic
- Error handling / fallback behaviour

Run with: pytest langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import intake_prefill_agent as ipa


class TestGraphStructure:
    """Verify the compiled graph has the expected nodes and edges."""

    def test_graph_has_four_nodes(self):
        nodes = list(ipa.graph.nodes)
        expected = {"search_literature", "build_context", "generate_prefill", "validate_output"}
        # LangGraph adds __start__ and __end__ automatically
        agent_nodes = {n for n in nodes if not n.startswith("__")}
        assert agent_nodes == expected

    def test_graph_exports_as_graph(self):
        """The module-level `graph` is a compiled StateGraph."""
        assert hasattr(ipa, "graph")
        assert hasattr(ipa.graph, "invoke")
