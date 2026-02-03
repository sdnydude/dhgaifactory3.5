#!/usr/bin/env python3
"""Generate embeddings for antigravity_messages using Ollama API"""

import os
import sys
import logging
import psycopg2
import requests
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

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

def get_embedding(text):
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
        return None

def main():
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)

    # Test Ollama
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except Exception as e:
        logger.error(f"Ollama unreachable: {e}")
        sys.exit(1)

    conn = get_db_connection()
    cur = conn.cursor()

    # Get messages without embeddings
    cur.execute("""
        SELECT id, content FROM antigravity_messages 
        WHERE embedding IS NULL AND content IS NOT NULL AND LENGTH(content) > 5
        LIMIT 1000
    """)
    rows = cur.fetchall()

    logger.info(f"Processing {len(rows)} messages with {EMBEDDING_MODEL}...")

    updated = 0
    errors = 0

    try:
        for i, (msg_id, content) in enumerate(rows):
            # Truncate if too long (Ollama/Nomic has limits)
            truncated_content = content[:8000]
            
            embedding = get_embedding(truncated_content)
            
            if embedding:
                cur.execute(
                    "UPDATE antigravity_messages SET embedding = %s::vector WHERE id = %s",
                    (embedding, msg_id)
                )
                updated += 1
            else:
                errors += 1

            if i % 20 == 0 and i > 0:
                conn.commit()
                logger.info(f"Progress: {i}/{len(rows)} messages embedded")

        conn.commit()
        logger.info(f"Done! Updated {updated} messages. Errors: {errors}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during loop: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
