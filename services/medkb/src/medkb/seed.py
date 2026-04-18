from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from medkb.config import Settings
from medkb.db import close_db, get_session, init_db

logger = logging.getLogger(__name__)

SEED_CORPUS_NAME = "dhg_cme_sample"

SEED_DOCUMENTS = [
    {
        "source": "dhg_internal",
        "source_id": "cme-sample-001",
        "title": "Pembrolizumab in Non-Small Cell Lung Cancer: A Review",
        "audience": "clinician",
        "authority": "peer_reviewed",
        "chunks": [
            ("abstract", "Pembrolizumab (Keytruda) is an anti-PD-1 monoclonal antibody approved for multiple indications in non-small cell lung cancer (NSCLC). This review covers the pivotal KEYNOTE trials that established pembrolizumab as a standard of care for PD-L1 positive NSCLC patients.", 42),
            ("methods", "We conducted a systematic review of Phase II and Phase III clinical trials evaluating pembrolizumab in NSCLC published between 2015 and 2024. PubMed and ClinicalTrials.gov were searched using standardized terms.", 38),
            ("results", "KEYNOTE-024 demonstrated superior progression-free survival (PFS) of 10.3 months versus 6.0 months with platinum-based chemotherapy in patients with PD-L1 tumor proportion score (TPS) of 50% or greater. Overall survival was also significantly improved.", 43),
            ("discussion", "The integration of pembrolizumab into first-line treatment algorithms represents a paradigm shift in NSCLC management. Biomarker-driven selection using PD-L1 TPS remains the primary approach for patient identification, though emerging evidence suggests additional predictive markers.", 39),
        ],
    },
    {
        "source": "dhg_internal",
        "source_id": "cme-sample-002",
        "title": "Educational Needs Assessment for Oncology CME Programs",
        "audience": "clinician",
        "authority": "guideline_body",
        "chunks": [
            ("abstract", "Continuing medical education in oncology must address rapidly evolving treatment landscapes. This needs assessment identifies key knowledge gaps among practicing oncologists regarding immunotherapy combinations and biomarker testing.", 36),
            ("results", "Survey of 450 oncologists revealed that 62% reported uncertainty about optimal sequencing of immunotherapy regimens. Only 38% correctly identified all FDA-approved biomarker tests for pembrolizumab eligibility.", 35),
            ("recommendations", "CME programs should prioritize hands-on biomarker interpretation workshops, case-based learning for treatment sequencing decisions, and regular updates on emerging trial data. Accreditation standards from ACCME require demonstrated improvement in competence.", 38),
        ],
    },
    {
        "source": "dhg_internal",
        "source_id": "cme-sample-003",
        "title": "Immunotherapy Adverse Events: A Practical Guide",
        "audience": "clinician",
        "authority": "peer_reviewed",
        "chunks": [
            ("abstract", "Immune checkpoint inhibitors including pembrolizumab and nivolumab can cause immune-related adverse events (irAEs) affecting virtually any organ system. Early recognition and management are critical for patient safety.", 35),
            ("management", "Grade 1-2 irAEs generally permit continuation of immunotherapy with close monitoring. Grade 3-4 events require immediate immunotherapy interruption and high-dose corticosteroid therapy. Endocrinopathies such as thyroiditis may require lifelong hormone replacement.", 40),
            ("monitoring", "Baseline labs should include thyroid function, liver enzymes, complete blood count, and glucose. Monitoring frequency depends on the specific agent and patient risk factors. Patient education about symptom recognition is essential for early detection.", 38),
        ],
    },
]


async def seed_corpus(session: AsyncSession) -> None:
    existing = await session.execute(
        text("SELECT id FROM medkb.corpora WHERE name = :name"),
        {"name": SEED_CORPUS_NAME},
    )
    if existing.first():
        logger.info("Seed corpus '%s' already exists — skipping", SEED_CORPUS_NAME)
        return

    corpus_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO medkb.corpora (id, name, description, owner, visibility, contains_phi)
            VALUES (:id, :name, :desc, :owner, :vis, false)
        """),
        {
            "id": corpus_id,
            "name": SEED_CORPUS_NAME,
            "desc": "Sample CME corpus for medkb development and testing",
            "owner": "dhg_cme",
            "vis": "dhg_internal",
        },
    )

    for doc in SEED_DOCUMENTS:
        doc_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO medkb.documents (id, corpus_id, source, source_id, title, audience, authority)
                VALUES (:id, :corpus_id, :source, :source_id, :title, :audience, :authority)
            """),
            {
                "id": doc_id,
                "corpus_id": corpus_id,
                "source": doc["source"],
                "source_id": doc["source_id"],
                "title": doc["title"],
                "audience": doc["audience"],
                "authority": doc["authority"],
            },
        )

        for idx, (section, text_content, tokens) in enumerate(doc["chunks"]):
            chunk_id = uuid.uuid4()
            await session.execute(
                text("""
                    INSERT INTO medkb.chunks
                        (id, document_id, corpus_id, chunk_index, chunk_text,
                         chunk_tokens, section, word_count)
                    VALUES (:id, :doc_id, :corpus_id, :idx, :text,
                            :tokens, :section, :words)
                """),
                {
                    "id": chunk_id,
                    "doc_id": doc_id,
                    "corpus_id": corpus_id,
                    "idx": idx,
                    "text": text_content,
                    "tokens": tokens,
                    "section": section,
                    "words": len(text_content.split()),
                },
            )

    await session.commit()
    logger.info("Seeded corpus '%s' with %d documents", SEED_CORPUS_NAME, len(SEED_DOCUMENTS))


async def main():
    settings = Settings()
    init_db(settings.medkb_db_url)
    async for session in get_session():
        await seed_corpus(session)
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
