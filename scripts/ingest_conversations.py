#!/usr/bin/env python3
"""Ingest Antigravity conversations into CR database"""

import json
import os
import sys
import logging
import psycopg2
from datetime import datetime

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
    """Main ingestion function."""
    # Database connection
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Load exported conversations
    json_path = "/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming/antigravity_conversations_full.json"
    try:
        with open(json_path) as f:
            sessions = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {json_path}")
        sys.exit(1)

    logger.info(f"Processing {len(sessions)} sessions...")

    inserted_chats = 0
    inserted_messages = 0

    try:
        for session in sessions:
            sid = session["session_id"]
            title = session.get("title", "Untitled")
            messages = session.get("messages", [])
            
            # Insert or update chat
            cur.execute("""
                INSERT INTO antigravity_chats (conversation_id, title, message_count, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    message_count = EXCLUDED.message_count,
                    last_modified = NOW()
                RETURNING id
            """, (sid, title, len(messages), "imported"))
            
            inserted_chats += 1
            
            # Delete existing messages for this conversation (for clean re-sync)
            cur.execute("""
                DELETE FROM antigravity_messages WHERE conversation_id = %s
            """, (sid,))
            
            # Insert messages
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                cur.execute("""
                    INSERT INTO antigravity_messages (conversation_id, role, content, source, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (sid, role, content, "antigravity_export", json.dumps({"message_index": i})))
                inserted_messages += 1
            
            if inserted_chats % 5 == 0:
                logger.info(f"Processed {inserted_chats}/{len(sessions)} sessions, {inserted_messages} messages")

        conn.commit()
        logger.info(f"Done! Chats: {inserted_chats}, Messages: {inserted_messages}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during ingestion: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
