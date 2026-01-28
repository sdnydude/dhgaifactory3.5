#!/usr/bin/env python3
"""Generate embeddings for antigravity_messages using sentence-transformers"""

import os
import sys
import logging
import psycopg2
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

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

def main():
    """Main embedding generation function."""
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)

    # Load model
    logger.info("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    conn = get_db_connection()
    cur = conn.cursor()

    # Get messages without embeddings
    cur.execute("""
        SELECT id, content FROM antigravity_messages 
        WHERE embedding IS NULL AND content IS NOT NULL AND LENGTH(content) > 10
        LIMIT 500
    """)
    rows = cur.fetchall()

    logger.info(f"Processing {len(rows)} messages...")

    batch_size = 50
    updated = 0

    try:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            ids = [r[0] for r in batch]
            texts = [r[1][:8000] for r in batch]  # Truncate long texts
            
            embeddings = model.encode(texts)
            
            for msg_id, embedding in zip(ids, embeddings):
                cur.execute(
                    "UPDATE antigravity_messages SET embedding = %s WHERE id = %s",
                    (embedding.tolist(), msg_id)
                )
                updated += 1
            
            conn.commit()
            logger.info(f"Processed {min(i+batch_size, len(rows))}/{len(rows)}")

        logger.info(f"Done! Updated {updated} messages with embeddings.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during embedding generation: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
