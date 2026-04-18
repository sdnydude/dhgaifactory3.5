import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medkb.graph.builder import build_rag_graph
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_crag_strategy_grades_and_generates():
    chunk = RetrievedChunk(
        chunk_id="c1", document_id="d1", corpus_id="corp1",
        text="Relevant medical content", section="abstract",
        metadata={"title": "Test"}, retriever_source="pgvector",
        raw_score=0.9, fusion_rank=1,
    )
    mock_retriever = AsyncMock()
    mock_retriever.name = "pgvector"
    mock_retriever.retrieve = AsyncMock(return_value=[chunk])

    grade_response = MagicMock()
    grade_response.content = "relevant"
    grade_response.usage_metadata = {"input_tokens": 200, "output_tokens": 5}

    gen_response = MagicMock()
    gen_response.content = "Answer based on evidence."
    gen_response.usage_metadata = {"input_tokens": 500, "output_tokens": 50}

    graph = build_rag_graph()
    config = RAGConfig(
        strategy="crag", corpora=["test"], k=8,
        generate_answer=True, generation_model="claude-sonnet-4-6",
        grader_model="ollama:qwen3:14b", max_retries=2,
        include_citations=True, max_total_tokens=50000,
    )
    state = make_initial_state(
        query="test query", config=config,
        run_id="run-1", caller_id="test",
    )
    state["_retrievers"] = [mock_retriever]

    with patch("medkb.graph.nodes.grade.get_llm") as mock_grade_llm, \
         patch("medkb.graph.nodes.generate.get_llm") as mock_gen_llm:

        grade_llm = AsyncMock()
        grade_llm.ainvoke = AsyncMock(return_value=grade_response)
        mock_grade_llm.return_value = grade_llm

        gen_llm = AsyncMock()
        gen_llm.ainvoke = AsyncMock(return_value=gen_response)
        mock_gen_llm.return_value = gen_llm

        result = await graph.ainvoke(state)
        assert "grade_docs" in result["nodes_visited"]
        assert "generate" in result["nodes_visited"]
        assert result["doc_grade"] == "good"
        assert "Answer" in result["answer"]


@pytest.mark.asyncio
async def test_crag_rewrites_on_bad_grade():
    bad_chunk = RetrievedChunk(
        chunk_id="c1", document_id="d1", corpus_id="corp1",
        text="Irrelevant content", section=None, metadata={},
        retriever_source="pgvector", raw_score=0.5, fusion_rank=1,
    )
    good_chunk = RetrievedChunk(
        chunk_id="c2", document_id="d1", corpus_id="corp1",
        text="Relevant after rewrite", section=None, metadata={"title": "Good"},
        retriever_source="pgvector", raw_score=0.9, fusion_rank=1,
    )

    call_count = 0

    async def retrieve_side_effect(query, *, k, corpus_ids=None, filters=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [bad_chunk]
        return [good_chunk]

    mock_retriever = AsyncMock()
    mock_retriever.name = "pgvector"
    mock_retriever.retrieve = AsyncMock(side_effect=retrieve_side_effect)

    bad_grade = MagicMock()
    bad_grade.content = "not_relevant"
    bad_grade.usage_metadata = {"input_tokens": 200, "output_tokens": 5}

    good_grade = MagicMock()
    good_grade.content = "relevant"
    good_grade.usage_metadata = {"input_tokens": 200, "output_tokens": 5}

    rewrite_response = MagicMock()
    rewrite_response.content = "Rewritten query for better results"
    rewrite_response.usage_metadata = {"input_tokens": 100, "output_tokens": 20}

    gen_response = MagicMock()
    gen_response.content = "Answer from rewritten query."
    gen_response.usage_metadata = {"input_tokens": 500, "output_tokens": 50}

    grade_call_count = 0

    graph = build_rag_graph()
    config = RAGConfig(
        strategy="crag", corpora=["test"], k=8,
        generate_answer=True, generation_model="claude-sonnet-4-6",
        grader_model="ollama:qwen3:14b", rewriter_model="ollama:llama3.1:8b",
        max_retries=2, include_citations=True, max_total_tokens=50000,
    )
    state = make_initial_state(
        query="test query", config=config,
        run_id="run-1", caller_id="test",
    )
    state["_retrievers"] = [mock_retriever]

    async def grade_side_effect(messages):
        nonlocal grade_call_count
        grade_call_count += 1
        if grade_call_count == 1:
            return bad_grade
        return good_grade

    with patch("medkb.graph.nodes.grade.get_llm") as mock_grade_llm, \
         patch("medkb.graph.nodes.rewrite.get_llm") as mock_rewrite_llm, \
         patch("medkb.graph.nodes.generate.get_llm") as mock_gen_llm:

        grade_llm = AsyncMock()
        grade_llm.ainvoke = AsyncMock(side_effect=grade_side_effect)
        mock_grade_llm.return_value = grade_llm

        rewrite_llm = AsyncMock()
        rewrite_llm.ainvoke = AsyncMock(return_value=rewrite_response)
        mock_rewrite_llm.return_value = rewrite_llm

        gen_llm = AsyncMock()
        gen_llm.ainvoke = AsyncMock(return_value=gen_response)
        mock_gen_llm.return_value = gen_llm

        result = await graph.ainvoke(state)
        assert "rewrite_query" in result["nodes_visited"]
        assert result["rewrite_count"] >= 1
