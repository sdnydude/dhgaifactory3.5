"""CME search service — fulltext, vector, hybrid (RRF), and RAG context retrieval."""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from models import CMEDocument, CMEIntakeField, CMESourceReference

logger = logging.getLogger(__name__)

_RRF_K = 60


def snippet_from_text(text_val: str, max_len: int = 300) -> str:
    if not text_val:
        return ""
    cleaned = " ".join(text_val.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "..."


def fulltext_search(
    db: Session,
    query: str,
    *,
    project_id: str | None = None,
    source_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    if limit < 1 or limit > 100:
        limit = 20

    results: list[dict] = []
    ts_query = func.websearch_to_tsquery("english", query)

    if source_type in (None, "documents"):
        doc_query = db.query(
            CMEDocument.id,
            CMEDocument.project_id,
            CMEDocument.title,
            CMEDocument.content_text,
            CMEDocument.document_type,
            CMEDocument.version,
            CMEDocument.quality_score,
            CMEDocument.word_count,
            func.ts_rank(CMEDocument.search_vector, ts_query).label("rank"),
        ).filter(
            CMEDocument.search_vector.op("@@")(ts_query),
            CMEDocument.is_current.is_(True),
        )
        if project_id:
            doc_query = doc_query.filter(CMEDocument.project_id == project_id)
        doc_query = doc_query.order_by(text("rank DESC")).limit(limit)

        for row in doc_query.all():
            results.append({
                "id": str(row.id),
                "source_table": "cme_documents",
                "project_id": str(row.project_id),
                "title": row.title,
                "snippet": snippet_from_text(row.content_text),
                "score": float(row.rank),
                "metadata": {
                    "document_type": row.document_type,
                    "version": row.version,
                    "quality_score": row.quality_score,
                    "word_count": row.word_count,
                },
            })

    if source_type in (None, "intake_fields"):
        field_query = db.query(
            CMEIntakeField.id,
            CMEIntakeField.project_id,
            CMEIntakeField.section,
            CMEIntakeField.field_label,
            CMEIntakeField.value_text,
            func.ts_rank(CMEIntakeField.search_vector, ts_query).label("rank"),
        ).filter(
            CMEIntakeField.search_vector.op("@@")(ts_query),
        )
        if project_id:
            field_query = field_query.filter(CMEIntakeField.project_id == project_id)
        field_query = field_query.order_by(text("rank DESC")).limit(limit)

        for row in field_query.all():
            results.append({
                "id": str(row.id),
                "source_table": "cme_intake_fields",
                "project_id": str(row.project_id),
                "title": f"{row.section}: {row.field_label}",
                "snippet": snippet_from_text(row.value_text or ""),
                "score": float(row.rank),
                "metadata": {"section": row.section, "field_label": row.field_label},
            })

    if source_type in (None, "references"):
        ref_query = db.query(
            CMESourceReference.id,
            CMESourceReference.project_id,
            CMESourceReference.title,
            CMESourceReference.abstract,
            CMESourceReference.ref_type,
            CMESourceReference.ref_id,
            CMESourceReference.journal,
            CMESourceReference.authors,
            func.ts_rank(CMESourceReference.search_vector, ts_query).label("rank"),
        ).filter(
            CMESourceReference.search_vector.op("@@")(ts_query),
        )
        if project_id:
            ref_query = ref_query.filter(CMESourceReference.project_id == project_id)
        ref_query = ref_query.order_by(text("rank DESC")).limit(limit)

        for row in ref_query.all():
            results.append({
                "id": str(row.id),
                "source_table": "cme_source_references",
                "project_id": str(row.project_id),
                "title": row.title or "Untitled Reference",
                "snippet": snippet_from_text(row.abstract or ""),
                "score": float(row.rank),
                "metadata": {
                    "ref_type": row.ref_type,
                    "ref_id": row.ref_id,
                    "journal": row.journal,
                    "authors": row.authors,
                },
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def vector_similarity_search(
    db: Session,
    query_embedding: list[float],
    *,
    project_id: str | None = None,
    source_tables: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    if source_tables is None:
        source_tables = ["cme_documents", "cme_source_references"]

    embedding_literal = f"[{','.join(str(v) for v in query_embedding)}]"
    results: list[dict] = []

    if "cme_documents" in source_tables:
        sql = text("""
            SELECT id, project_id, title, content_text, document_type, version,
                   quality_score, word_count,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity
            FROM cme_documents
            WHERE embedding IS NOT NULL AND is_current = true
              AND (CAST(:pid AS uuid) IS NULL OR project_id = CAST(:pid AS uuid))
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """)
        rows = db.execute(sql, {
            "emb": embedding_literal,
            "pid": project_id,
            "lim": limit,
        }).fetchall()

        for row in rows:
            results.append({
                "id": str(row.id),
                "source_table": "cme_documents",
                "project_id": str(row.project_id),
                "title": row.title,
                "snippet": snippet_from_text(row.content_text),
                "score": float(row.similarity),
                "metadata": {
                    "document_type": row.document_type,
                    "version": row.version,
                    "quality_score": row.quality_score,
                    "word_count": row.word_count,
                },
            })

    if "cme_source_references" in source_tables:
        sql = text("""
            SELECT id, project_id, title, abstract, ref_type, ref_id,
                   journal, authors,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity
            FROM cme_source_references
            WHERE embedding IS NOT NULL
              AND (CAST(:pid AS uuid) IS NULL OR project_id = CAST(:pid AS uuid))
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """)
        rows = db.execute(sql, {
            "emb": embedding_literal,
            "pid": project_id,
            "lim": limit,
        }).fetchall()

        for row in rows:
            results.append({
                "id": str(row.id),
                "source_table": "cme_source_references",
                "project_id": str(row.project_id),
                "title": row.title or "Untitled Reference",
                "snippet": snippet_from_text(row.abstract or ""),
                "score": float(row.similarity),
                "metadata": {
                    "ref_type": row.ref_type,
                    "ref_id": row.ref_id,
                    "journal": row.journal,
                    "authors": row.authors,
                },
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def hybrid_search(
    db: Session,
    query: str,
    query_embedding: list[float] | None,
    *,
    project_id: str | None = None,
    source_tables: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    if source_tables is None:
        source_tables = ["cme_documents", "cme_intake_fields", "cme_source_references"]

    ts_query = func.websearch_to_tsquery("english", query)
    fused: Dict[str, Dict[str, Any]] = {}

    def _add_to_fused(key: str, item_data: dict, rank: int):
        if key not in fused:
            fused[key] = {"data": item_data, "rrf_score": 0.0}
        fused[key]["rrf_score"] += 1.0 / (_RRF_K + rank)

    # --- Full-text search ---
    if "cme_documents" in source_tables:
        q = db.query(
            CMEDocument.id, CMEDocument.project_id, CMEDocument.title,
            CMEDocument.content_text, CMEDocument.document_type, CMEDocument.version,
            CMEDocument.quality_score, CMEDocument.word_count,
            func.ts_rank(CMEDocument.search_vector, ts_query).label("rank"),
        ).filter(
            CMEDocument.search_vector.op("@@")(ts_query),
            CMEDocument.is_current.is_(True),
        )
        if project_id:
            q = q.filter(CMEDocument.project_id == project_id)
        for rank_idx, row in enumerate(q.order_by(text("rank DESC")).limit(limit).all()):
            key = f"cme_documents:{row.id}"
            _add_to_fused(key, {
                "id": str(row.id), "source_table": "cme_documents",
                "project_id": str(row.project_id), "title": row.title,
                "snippet": snippet_from_text(row.content_text),
                "metadata": {"document_type": row.document_type, "version": row.version,
                             "quality_score": row.quality_score, "word_count": row.word_count},
            }, rank_idx + 1)

    if "cme_intake_fields" in source_tables:
        q = db.query(
            CMEIntakeField.id, CMEIntakeField.project_id, CMEIntakeField.section,
            CMEIntakeField.field_label, CMEIntakeField.value_text,
            func.ts_rank(CMEIntakeField.search_vector, ts_query).label("rank"),
        ).filter(CMEIntakeField.search_vector.op("@@")(ts_query))
        if project_id:
            q = q.filter(CMEIntakeField.project_id == project_id)
        for rank_idx, row in enumerate(q.order_by(text("rank DESC")).limit(limit).all()):
            key = f"cme_intake_fields:{row.id}"
            _add_to_fused(key, {
                "id": str(row.id), "source_table": "cme_intake_fields",
                "project_id": str(row.project_id),
                "title": f"{row.section}: {row.field_label}",
                "snippet": snippet_from_text(row.value_text or ""),
                "metadata": {"section": row.section, "field_label": row.field_label},
            }, rank_idx + 1)

    if "cme_source_references" in source_tables:
        q = db.query(
            CMESourceReference.id, CMESourceReference.project_id, CMESourceReference.title,
            CMESourceReference.abstract, CMESourceReference.ref_type, CMESourceReference.ref_id,
            CMESourceReference.journal, CMESourceReference.authors,
            func.ts_rank(CMESourceReference.search_vector, ts_query).label("rank"),
        ).filter(CMESourceReference.search_vector.op("@@")(ts_query))
        if project_id:
            q = q.filter(CMESourceReference.project_id == project_id)
        for rank_idx, row in enumerate(q.order_by(text("rank DESC")).limit(limit).all()):
            key = f"cme_source_references:{row.id}"
            _add_to_fused(key, {
                "id": str(row.id), "source_table": "cme_source_references",
                "project_id": str(row.project_id),
                "title": row.title or "Untitled Reference",
                "snippet": snippet_from_text(row.abstract or ""),
                "metadata": {"ref_type": row.ref_type, "ref_id": row.ref_id,
                             "journal": row.journal, "authors": row.authors},
            }, rank_idx + 1)

    # --- Vector search (documents + references only) ---
    if query_embedding is not None:
        embedding_literal = f"[{','.join(str(v) for v in query_embedding)}]"

        if "cme_documents" in source_tables:
            sql = text("""
                SELECT id, project_id, title, content_text, document_type, version,
                       quality_score, word_count
                FROM cme_documents
                WHERE embedding IS NOT NULL AND is_current = true
                  AND (CAST(:pid AS uuid) IS NULL OR project_id = CAST(:pid AS uuid))
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :lim
            """)
            rows = db.execute(sql, {"emb": embedding_literal, "pid": project_id, "lim": limit}).fetchall()
            for rank_idx, row in enumerate(rows):
                key = f"cme_documents:{row.id}"
                _add_to_fused(key, {
                    "id": str(row.id), "source_table": "cme_documents",
                    "project_id": str(row.project_id), "title": row.title,
                    "snippet": snippet_from_text(row.content_text),
                    "metadata": {"document_type": row.document_type, "version": row.version,
                                 "quality_score": row.quality_score, "word_count": row.word_count},
                }, rank_idx + 1)

        if "cme_source_references" in source_tables:
            sql = text("""
                SELECT id, project_id, title, abstract, ref_type, ref_id, journal, authors
                FROM cme_source_references
                WHERE embedding IS NOT NULL
                  AND (CAST(:pid AS uuid) IS NULL OR project_id = CAST(:pid AS uuid))
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :lim
            """)
            rows = db.execute(sql, {"emb": embedding_literal, "pid": project_id, "lim": limit}).fetchall()
            for rank_idx, row in enumerate(rows):
                key = f"cme_source_references:{row.id}"
                _add_to_fused(key, {
                    "id": str(row.id), "source_table": "cme_source_references",
                    "project_id": str(row.project_id),
                    "title": row.title or "Untitled Reference",
                    "snippet": snippet_from_text(row.abstract or ""),
                    "metadata": {"ref_type": row.ref_type, "ref_id": row.ref_id,
                                 "journal": row.journal, "authors": row.authors},
                }, rank_idx + 1)

    results = []
    for entry in sorted(fused.values(), key=lambda e: e["rrf_score"], reverse=True)[:limit]:
        d = entry["data"]
        d["score"] = entry["rrf_score"]
        results.append(d)

    return results


def get_rag_context(
    db: Session,
    query: str,
    query_embedding: list[float] | None,
    *,
    project_id: str | None = None,
    max_chunks: int = 5,
    max_tokens: int = 4000,
    include_citations: bool = True,
) -> dict:
    search_results = hybrid_search(
        db, query, query_embedding,
        project_id=project_id,
        source_tables=["cme_documents", "cme_source_references"],
        limit=max_chunks * 2,
    )

    chunks: list[dict] = []
    estimated_tokens = 0
    chars_per_token = 4

    for result in search_results:
        if len(chunks) >= max_chunks:
            break

        content = ""
        if result["source_table"] == "cme_documents":
            doc = db.query(CMEDocument).filter(CMEDocument.id == result["id"]).first()
            if doc:
                content = doc.content_text or ""
        elif result["source_table"] == "cme_source_references":
            ref = db.query(CMESourceReference).filter(CMESourceReference.id == result["id"]).first()
            if ref:
                parts = []
                if ref.title:
                    parts.append(f"Title: {ref.title}")
                if ref.authors:
                    parts.append(f"Authors: {ref.authors}")
                if ref.journal:
                    parts.append(f"Journal: {ref.journal}")
                if ref.abstract:
                    parts.append(f"Abstract: {ref.abstract}")
                content = "\n".join(parts)

        if not content:
            continue

        chunk_tokens = len(content) // chars_per_token
        if estimated_tokens + chunk_tokens > max_tokens:
            remaining_chars = (max_tokens - estimated_tokens) * chars_per_token
            if remaining_chars < 200:
                break
            content = content[:remaining_chars].rsplit(" ", 1)[0] + "..."
            chunk_tokens = len(content) // chars_per_token

        estimated_tokens += chunk_tokens

        chunk_meta = dict(result.get("metadata", {}))
        chunk_meta["search_score"] = result["score"]

        chunks.append({
            "source_table": result["source_table"],
            "document_id": result["id"],
            "title": result["title"],
            "content": content,
            "score": result["score"],
            "metadata": chunk_meta,
        })

    if include_citations and chunks:
        citation_refs = []
        for i, chunk in enumerate(chunks, 1):
            if chunk["source_table"] == "cme_source_references":
                ref = db.query(CMESourceReference).filter(
                    CMESourceReference.id == chunk["document_id"]
                ).first()
                if ref:
                    cite = f"[{i}] {ref.title}"
                    if ref.authors:
                        cite += f" — {ref.authors}"
                    if ref.journal:
                        cite += f", {ref.journal}"
                    if ref.ref_id:
                        cite += f" (PMID: {ref.ref_id})"
                    citation_refs.append(cite)

        if citation_refs:
            citation_block = "\n\n---\nCitations:\n" + "\n".join(citation_refs)
            citation_tokens = len(citation_block) // chars_per_token
            estimated_tokens += citation_tokens

    return {
        "query": query,
        "chunks": chunks,
        "total_chunks": len(chunks),
        "estimated_tokens": estimated_tokens,
        "project_scope": project_id,
    }
