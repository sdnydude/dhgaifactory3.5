#!/usr/bin/env python3
"""Ingest Antigravity artifacts into CR database"""

import os
import sys
import logging
import json
import psycopg2
from pathlib import Path

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
    """Main artifact ingestion function."""
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)

    conn = get_db_connection()
    cur = conn.cursor()

    # Find artifact files
    artifacts_dir = Path("/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming")
    
    if not artifacts_dir.exists():
        logger.error(f"Artifacts directory not found: {artifacts_dir}")
        sys.exit(1)

    # Find markdown files
    md_files = list(artifacts_dir.rglob("*.md"))
    logger.info(f"Found {len(md_files)} markdown artifacts")

    inserted = 0
    try:
        for md_file in md_files:
            content = md_file.read_text(errors="ignore")
            filename = md_file.name
            filepath = str(md_file)
            
            cur.execute("""
                INSERT INTO antigravity_artifacts (filename, filepath, content, file_type, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (filepath) DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = NOW()
            """, (filename, filepath, content, "markdown", "antigravity_export"))
            
            inserted += 1
            
        conn.commit()
        logger.info(f"Done! Inserted/updated {inserted} artifacts.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during artifact ingestion: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
