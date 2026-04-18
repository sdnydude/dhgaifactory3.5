from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medkb.db import get_session
from medkb.models import Corpus
from medkb.schemas import CorpusCreate, CorpusOut

router = APIRouter(prefix="/v1")


@router.get("/corpora", response_model=list[CorpusOut])
async def list_corpora(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Corpus).order_by(Corpus.name))
    corpora = result.scalars().all()
    return [
        CorpusOut(
            id=c.id,
            name=c.name,
            description=c.description,
            owner=c.owner,
            visibility=c.visibility,
            contains_phi=c.contains_phi,
            default_chunker=c.default_chunker,
        )
        for c in corpora
    ]


@router.post("/corpora", response_model=CorpusOut, status_code=201)
async def create_corpus(
    body: CorpusCreate,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(Corpus).where(Corpus.name == body.name)
    )
    if existing.scalars().first():
        raise HTTPException(409, detail=f"Corpus '{body.name}' already exists")

    corpus = Corpus(
        name=body.name,
        description=body.description,
        owner=body.owner,
        visibility=body.visibility,
        contains_phi=body.contains_phi,
        default_chunker=body.default_chunker,
    )
    session.add(corpus)
    await session.commit()
    await session.refresh(corpus)
    return CorpusOut(
        id=corpus.id,
        name=corpus.name,
        description=corpus.description,
        owner=corpus.owner,
        visibility=corpus.visibility,
        contains_phi=corpus.contains_phi,
        default_chunker=corpus.default_chunker,
    )
