#!/usr/bin/env python3
"""Generate embeddings for planning documents in CR database.

This script:
1. Finds planning documents that need embeddings
2. Chunks content appropriately
3. Generates embeddings via Ollama
4. Stores embeddings in pgvector for RAG search

Usage:
    python3 generate_planning_embeddings.py
"""

import json
import os
import sys
import logging
import psycopg2
from psycopg2.extras import execute_values
import requests
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50

def get_db_connection():
    """Get database connection using environment variables."""
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            database=os.environ.get("DB_NAME", "dhg_registry"),
            user=os.environ.get("DB_USER", "dhg"),
            password=os.environ.get("DB_PASSWORD", os.environ.get("PGPASSWORD"))
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def ensure_embeddings_table(cur):
    """Create embeddings table if it doesn't exist."""
    # First ensure pgvector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS planning_embeddings (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES planning_documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(768),  -- nomic-embed-text dimension
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(document_id, chunk_index)
        )
    """)
    
    # Create index for similarity search
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_planning_embeddings_vector 
        ON planning_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = chunk.rfind('\n\n')
            if para_break > chunk_size // 2:
                chunk = chunk[:para_break]
                end = start + para_break
            else:
                # Look for sentence break
                for sep in ['. ', '.\n', '! ', '? ']:
                    sent_break = chunk.rfind(sep)
                    if sent_break > chunk_size // 2:
                        chunk = chunk[:sent_break + 1]
                        end = start + sent_break + 1
                        break
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def get_embedding(text: str) -> List[float]:
    """Get embedding from Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise

def process_document(cur, doc_id: int, content: str, project_name: str, file_name: str):
    """Process a single document: chunk, embed, store."""
    # Delete existing embeddings for this document
    cur.execute("DELETE FROM planning_embeddings WHERE document_id = %s", (doc_id,))
    
    # Chunk the content
    chunks = chunk_text(content)
    logger.info(f"  {file_name}: {len(chunks)} chunks")
    
    # Generate embeddings and insert
    embeddings_data = []
    for i, chunk in enumerate(chunks):
        # Add context to chunk for better retrieval
        contextualized_chunk = f"Project: {project_name}\nFile: {file_name}\n\n{chunk}"
        
        try:
            embedding = get_embedding(contextualized_chunk)
            embeddings_data.append((doc_id, i, chunk, embedding))
        except Exception as e:
            logger.error(f"  Failed to embed chunk {i}: {e}")
            continue
    
    if embeddings_data:
        execute_values(
            cur,
            """
            INSERT INTO planning_embeddings (document_id, chunk_index, chunk_text, embedding)
            VALUES %s
            """,
            embeddings_data,
            template="(%s, %s, %s, %s::vector)"
        )
    
    return len(embeddings_data)

def main():
    # Check for required environment variable
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)
    
    # Test Ollama connection
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        if EMBEDDING_MODEL not in models and f"{EMBEDDING_MODEL}:latest" not in models:
            logger.warning(f"Model {EMBEDDING_MODEL} not found. Available: {models}")
            logger.info(f"Pulling {EMBEDDING_MODEL}...")
            requests.post(f"{OLLAMA_URL}/api/pull", json={"name": EMBEDDING_MODEL})
    except Exception as e:
        logger.error(f"Ollama not reachable at {OLLAMA_URL}: {e}")
        sys.exit(1)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Ensure table exists
        ensure_embeddings_table(cur)
        conn.commit()
        
        # Find documents needing embeddings
        cur.execute("""
            SELECT id, project_name, file_name, content 
            FROM planning_documents 
            WHERE needs_embedding = TRUE
        """)
        documents = cur.fetchall()
        
        if not documents:
            logger.info("No documents need embedding")
            return
        
        logger.info(f"Processing {len(documents)} documents...")
        
        total_embeddings = 0
        for doc_id, project_name, file_name, content in documents:
            count = process_document(cur, doc_id, content, project_name, file_name)
            total_embeddings += count
            
            # Mark as processed
            cur.execute("""
                UPDATE planning_documents 
                SET needs_embedding = FALSE 
                WHERE id = %s
            """, (doc_id,))
        
        conn.commit()
        logger.info(f"Done! Generated {total_embeddings} embeddings")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
