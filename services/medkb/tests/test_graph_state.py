from medkb.graph.state import RAGConfig, make_initial_state


def test_make_initial_state_defaults():
    config = RAGConfig(
        strategy="regular",
        corpora=["dhg_internal"],
        k=8,
    )
    state = make_initial_state(
        query="test query",
        config=config,
        run_id="run-123",
        caller_id="test-agent",
    )
    assert state["query"] == "test query"
    assert state["original_query"] == "test query"
    assert state["run_id"] == "run-123"
    assert state["config"]["strategy"] == "regular"
    assert state["retrieved_chunks"] == []
    assert state["rewrite_count"] == 0
    assert state["tokens_used"] == 0
    assert state["nodes_visited"] == []


def test_rag_config_optional_fields():
    config = RAGConfig(
        strategy="crag",
        corpora=["pubmed"],
        k=10,
        generation_model="ollama:qwen3:14b",
    )
    assert config["generation_model"] == "ollama:qwen3:14b"
    assert config.get("grader_model") is None
