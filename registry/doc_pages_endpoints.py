"""Doc Pages API endpoints.

Routes:
  POST   /api/doc-pages              upsert a single doc page
  POST   /api/doc-pages/bulk         bulk upsert with optional mark-and-sweep
  GET    /api/doc-pages              list with filters (project_name, source_file, limit, offset)
  POST   /api/doc-pages/search       hybrid FTS + vector search with RRF
  DELETE /api/doc-pages/project/:name  delete all pages for a project
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from embedding_utils import get_embedding
import doc_pages_service as svc
from doc_pages_schemas import (
    DocPageCreate,
    DocPageResponse,
    DocPageList,
    DocPageSearch,
    DocPageBulkIngest,
)

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/doc-pages", tags=["doc-pages"])


async def _generate_embedding(content: str, title: Optional[str] = None) -> Optional[list]:
    try:
        embed_text = f"{title or ''} {content}"
        return await get_embedding(embed_text)
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None


@router.post("", response_model=DocPageResponse, status_code=status.HTTP_201_CREATED)
async def upsert_doc_page(
    payload: DocPageCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DocPageResponse:
    start = time.time()
    try:
        embedding = await _generate_embedding(payload.content, payload.title)
        row, created = svc.upsert_page(db, payload, embedding)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="upsert_doc_page").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("upsert_doc_page failed: %s", e)
        registry_errors.labels(error_type="upsert_doc_page_failed").inc()
        raise HTTPException(status_code=500, detail="Upsert failed")


@router.post("/bulk", response_model=dict, status_code=status.HTTP_200_OK)
async def bulk_ingest(
    payload: DocPageBulkIngest,
    db: Session = Depends(get_db),
) -> dict:
    """Bulk upsert doc pages with optional mark-and-sweep stale cleanup."""
    start = time.time()
    try:
        pages_with_embeddings = []
        for page in payload.pages:
            page_data = page.model_copy(update={"project_name": payload.project_name})
            embedding = await _generate_embedding(page_data.content, page_data.title)
            pages_with_embeddings.append((page_data, embedding))

        upserted, swept = svc.bulk_upsert(
            db, payload.project_name, pages_with_embeddings, payload.sweep_stale,
        )

        registry_write_operations.labels(operation="bulk_ingest_doc_pages").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return {"upserted": upserted, "swept": swept, "project_name": payload.project_name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("bulk_ingest failed for project %s: %s", payload.project_name, e)
        registry_errors.labels(error_type="bulk_ingest_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Bulk ingest failed")


@router.get("", response_model=DocPageList)
async def list_doc_pages(
    project_name: Optional[str] = Query(None),
    source_file: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DocPageList:
    start = time.time()
    try:
        rows, total = svc.list_doc_pages(
            db, project_name=project_name, source_file=source_file,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_doc_pages").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DocPageList(doc_pages=rows, total=total)
    except Exception as e:
        logger.error("list_doc_pages failed: %s", e)
        registry_errors.labels(error_type="list_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="List failed")


@router.post("/search", response_model=DocPageList)
async def search_doc_pages(
    body: DocPageSearch,
    db: Session = Depends(get_db),
) -> DocPageList:
    """Hybrid search using Reciprocal Rank Fusion (RRF) over FTS + vector."""
    start = time.time()
    try:
        query_embedding = await get_embedding(body.query)
        result_pages = svc.search_doc_pages(
            db, body.query, query_embedding,
            project_name=body.project_name, tags=body.tags, limit=body.limit,
        )

        registry_read_operations.labels(operation="search_doc_pages").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DocPageList(doc_pages=result_pages, total=len(result_pages))
    except Exception as e:
        logger.error("search_doc_pages failed: %s", e)
        registry_errors.labels(error_type="search_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Search failed")


@router.delete("/project/{project_name}", status_code=status.HTTP_200_OK)
async def delete_project_pages(
    project_name: str,
    db: Session = Depends(get_db),
) -> dict:
    start = time.time()
    try:
        count = svc.delete_project_pages(db, project_name)

        registry_write_operations.labels(operation="delete_project_pages").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return {"deleted": count, "project_name": project_name}
    except Exception as e:
        db.rollback()
        logger.error("delete_project_pages failed for %s: %s", project_name, e)
        registry_errors.labels(error_type="delete_project_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Delete failed")
