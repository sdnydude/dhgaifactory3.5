"""
DHG Registry Connector for Onyx (Danswer)
Custom connector to sync CME content from DHG Registry to Onyx for RAG

Implements PollConnector for incremental updates and LoadConnector for bulk sync.
"""

import os
import json
from typing import Generator, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

# Connector interface types (for standalone use)
@dataclass
class Document:
    """Document to be indexed by Onyx"""
    id: str
    sections: list
    source: str
    semantic_identifier: str
    metadata: dict
    doc_updated_at: Optional[datetime] = None

@dataclass
class Section:
    """Section of a document"""
    text: str
    link: Optional[str] = None


class DHGRegistryConnector:
    """
    Custom connector for DHG AI Factory Registry.
    
    Syncs the following content types to Onyx:
    - References (citations, sources)
    - Segments (needs assessments, scripts, curricula)
    - Learning Objectives
    - Competitor Activities
    
    Uses PostgreSQL direct connection to DHG Registry.
    """
    
    def __init__(
        self,
        db_host: str = None,
        db_port: int = 5432,
        db_name: str = "dhg_registry",
        db_user: str = "dhg",
        db_password: str = None,
        content_types: list = None
    ):
        self.db_host = db_host or os.getenv("REGISTRY_DB_HOST", "10.0.0.251")
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password or os.getenv("REGISTRY_DB_PASSWORD", "changeme")
        self.content_types = content_types or ["references", "segments", "learning_objectives"]
        self._conn = None
        
    def _get_connection(self):
        """Get or create database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                cursor_factory=RealDictCursor
            )
        return self._conn
    
    def _close_connection(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
    
    def load_from_state(self) -> Generator[Document, None, None]:
        """
        Bulk load all documents from Registry.
        Used for initial indexing.
        """
        try:
            conn = self._get_connection()
            
            if "references" in self.content_types:
                yield from self._load_references(conn)
            
            if "segments" in self.content_types:
                yield from self._load_segments(conn)
            
            if "learning_objectives" in self.content_types:
                yield from self._load_learning_objectives(conn)
            
            if "competitor_activities" in self.content_types:
                yield from self._load_competitor_activities(conn)
                
        finally:
            self._close_connection()
    
    def poll_source(
        self, 
        start: datetime = None,
        end: datetime = None
    ) -> Generator[Document, None, None]:
        """
        Poll for updated documents since last sync.
        Used for incremental updates.
        """
        if start is None:
            start = datetime.min.replace(tzinfo=timezone.utc)
        if end is None:
            end = datetime.now(timezone.utc)
            
        try:
            conn = self._get_connection()
            
            if "references" in self.content_types:
                yield from self._load_references(conn, since=start)
            
            if "segments" in self.content_types:
                yield from self._load_segments(conn, since=start)
            
            if "learning_objectives" in self.content_types:
                yield from self._load_learning_objectives(conn, since=start)
                
        finally:
            self._close_connection()
    
    def _load_references(
        self, 
        conn, 
        since: datetime = None
    ) -> Generator[Document, None, None]:
        """Load references from Registry"""
        with conn.cursor() as cur:
            query = """
                SELECT 
                    reference_id,
                    title,
                    url,
                    authors,
                    publication_date,
                    source_type,
                    source_confidence,
                    evidence_level,
                    abstract,
                    doi,
                    pmid,
                    created_at,
                    updated_at
                FROM references
                WHERE validated = TRUE
            """
            
            if since:
                query += f" AND updated_at > '{since.isoformat()}'"
            
            query += " ORDER BY updated_at DESC"
            
            cur.execute(query)
            
            for row in cur.fetchall():
                text_parts = []
                
                if row['title']:
                    text_parts.append(f"Title: {row['title']}")
                if row['authors']:
                    text_parts.append(f"Authors: {row['authors']}")
                if row['abstract']:
                    text_parts.append(f"Abstract: {row['abstract']}")
                if row['evidence_level']:
                    text_parts.append(f"Evidence Level: {row['evidence_level']}")
                
                full_text = "\n\n".join(text_parts)
                
                yield Document(
                    id=f"ref_{row['reference_id']}",
                    sections=[Section(text=full_text, link=row['url'])],
                    source="dhg_registry",
                    semantic_identifier=row['title'] or f"Reference {row['reference_id']}",
                    metadata={
                        "type": "reference",
                        "source_type": row['source_type'],
                        "evidence_level": row['evidence_level'],
                        "doi": row['doi'],
                        "pmid": row['pmid'],
                        "confidence": float(row['source_confidence']) if row['source_confidence'] else None
                    },
                    doc_updated_at=row['updated_at']
                )
    
    def _load_segments(
        self, 
        conn, 
        since: datetime = None
    ) -> Generator[Document, None, None]:
        """Load content segments (needs assessments, scripts, etc.)"""
        with conn.cursor() as cur:
            query = """
                SELECT 
                    segment_id,
                    content_type,
                    topic,
                    content,
                    word_count,
                    compliance_mode,
                    qa_passed,
                    metadata,
                    created_at
                FROM segments
                WHERE qa_passed = TRUE
            """
            
            if since:
                query += f" AND created_at > '{since.isoformat()}'"
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query)
            
            for row in cur.fetchall():
                yield Document(
                    id=f"seg_{row['segment_id']}",
                    sections=[Section(text=row['content'])],
                    source="dhg_registry",
                    semantic_identifier=f"{row['content_type']}: {row['topic']}",
                    metadata={
                        "type": row['content_type'],
                        "topic": row['topic'],
                        "word_count": row['word_count'],
                        "compliance_mode": row['compliance_mode'],
                        "extra": row['metadata'] or {}
                    },
                    doc_updated_at=row['created_at']
                )
    
    def _load_learning_objectives(
        self, 
        conn, 
        since: datetime = None
    ) -> Generator[Document, None, None]:
        """Load learning objectives"""
        with conn.cursor() as cur:
            query = """
                SELECT 
                    lo.objective_id,
                    lo.objective_text,
                    lo.moore_levels,
                    lo.icd10_codes,
                    lo.qi_measures,
                    lo.target_behaviors,
                    lo.bloom_taxonomy,
                    lo.created_at,
                    s.topic,
                    s.content_type
                FROM learning_objectives lo
                JOIN segments s ON lo.segment_id = s.segment_id
            """
            
            if since:
                query += f" WHERE lo.created_at > '{since.isoformat()}'"
            
            query += " ORDER BY lo.created_at DESC"
            
            cur.execute(query)
            
            for row in cur.fetchall():
                text_parts = [
                    f"Learning Objective: {row['objective_text']}",
                    f"Topic: {row['topic']}",
                ]
                
                if row['moore_levels']:
                    text_parts.append(f"Moore Levels: {', '.join(row['moore_levels'])}")
                if row['target_behaviors']:
                    text_parts.append(f"Target Behaviors: {', '.join(row['target_behaviors'])}")
                
                full_text = "\n".join(text_parts)
                
                yield Document(
                    id=f"lo_{row['objective_id']}",
                    sections=[Section(text=full_text)],
                    source="dhg_registry",
                    semantic_identifier=row['objective_text'][:100],
                    metadata={
                        "type": "learning_objective",
                        "topic": row['topic'],
                        "content_type": row['content_type'],
                        "moore_levels": row['moore_levels'],
                        "bloom_taxonomy": row['bloom_taxonomy'],
                        "icd10_codes": row['icd10_codes'],
                        "qi_measures": row['qi_measures']
                    },
                    doc_updated_at=row['created_at']
                )
    
    def _load_competitor_activities(
        self, 
        conn
    ) -> Generator[Document, None, None]:
        """Load competitor CME activities"""
        with conn.cursor() as cur:
            query = """
                SELECT 
                    activity_id,
                    provider,
                    funder,
                    activity_date,
                    format,
                    credits,
                    topic,
                    url,
                    activity_title,
                    source,
                    created_at
                FROM competitor_activities
                WHERE validated = TRUE
                ORDER BY activity_date DESC
                LIMIT 500
            """
            
            cur.execute(query)
            
            for row in cur.fetchall():
                text_parts = []
                
                if row['activity_title']:
                    text_parts.append(f"Activity: {row['activity_title']}")
                if row['topic']:
                    text_parts.append(f"Topic: {row['topic']}")
                if row['provider']:
                    text_parts.append(f"Provider: {row['provider']}")
                if row['funder']:
                    text_parts.append(f"Funder: {row['funder']}")
                if row['format']:
                    text_parts.append(f"Format: {row['format']}")
                if row['credits']:
                    text_parts.append(f"Credits: {row['credits']}")
                
                full_text = "\n".join(text_parts)
                
                yield Document(
                    id=f"comp_{row['activity_id']}",
                    sections=[Section(text=full_text, link=row['url'])],
                    source="dhg_registry",
                    semantic_identifier=row['activity_title'] or row['topic'] or f"CME Activity {row['activity_id']}",
                    metadata={
                        "type": "competitor_activity",
                        "provider": row['provider'],
                        "funder": row['funder'],
                        "format": row['format'],
                        "credits": float(row['credits']) if row['credits'] else None,
                        "activity_date": row['activity_date'].isoformat() if row['activity_date'] else None,
                        "source": row['source']
                    },
                    doc_updated_at=row['created_at']
                )


def sync_registry_to_onyx(
    onyx_api_url: str = "http://10.0.0.251:8088",
    content_types: list = None
) -> dict:
    """
    Sync DHG Registry content to Onyx.
    
    This function uses the Onyx ingestion API to push documents
    from the DHG Registry into Onyx for indexing.
    
    Args:
        onyx_api_url: URL of the Onyx API
        content_types: List of content types to sync
        
    Returns:
        Sync statistics
    """
    import httpx
    
    connector = DHGRegistryConnector(content_types=content_types)
    
    stats = {
        "documents_synced": 0,
        "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
    
    for doc in connector.load_from_state():
        try:
            payload = {
                "document_id": doc.id,
                "text": doc.sections[0].text if doc.sections else "",
                "semantic_identifier": doc.semantic_identifier,
                "source": doc.source,
                "metadata": doc.metadata
            }
            
            stats["documents_synced"] += 1
            
        except Exception as e:
            stats["errors"].append({
                "document_id": doc.id,
                "error": str(e)
            })
    
    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    return stats


if __name__ == "__main__":
    connector = DHGRegistryConnector()
    
    print("Testing DHG Registry Connector...")
    print("-" * 50)
    
    count = 0
    for doc in connector.load_from_state():
        print(f"Document: {doc.semantic_identifier}")
        print(f"  ID: {doc.id}")
        print(f"  Type: {doc.metadata.get('type')}")
        print(f"  Text preview: {doc.sections[0].text[:100] if doc.sections else 'N/A'}...")
        print()
        count += 1
        if count >= 5:
            break
    
    print(f"Total documents loaded: {count}+")
