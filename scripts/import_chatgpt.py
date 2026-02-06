#!/usr/bin/env python3
"""
Import ChatGPT conversations from export ZIP file into CR database.

Usage:
    python import_chatgpt.py --input ~/Downloads/chatgpt-export.zip --user-id <uuid>
"""
import argparse
import json
import logging
import os
import sys
import uuid
import zipfile
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Database connection
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_USER = os.getenv('POSTGRES_USER', 'dhg')
DB_PASS = os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
DB_NAME = os.getenv('POSTGRES_DB', 'dhg_registry')

# Ollama for embeddings
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBED_MODEL = os.getenv('EMBED_MODEL', 'nomic-embed-text')


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )


def get_embedding(text: str) -> Optional[list]:
    """Get embedding from Ollama."""
    if not text or len(text.strip()) < 10:
        return None
    try:
        # Truncate very long texts
        text = text[:8000] if len(text) > 8000 else text
        response = requests.post(
            f'{OLLAMA_URL}/api/embeddings',
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('embedding')
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
    return None


def parse_chatgpt_export(zip_path: str) -> list:
    """Parse ChatGPT export ZIP and return conversations."""
    conversations = []
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find conversations.json
        for name in zf.namelist():
            if name.endswith('conversations.json'):
                with zf.open(name) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        conversations = data
                    break
    
    logger.info(f"Found {len(conversations)} conversations in export")
    return conversations


def import_conversations(conversations: list, user_id: str, org_id: Optional[str], generate_embeddings: bool = True):
    """Import conversations into database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    total_messages = 0
    imported_convs = 0
    
    for conv in conversations:
        try:
            conv_id = str(uuid.uuid4())
            external_id = conv.get('id', conv_id)
            title = conv.get('title', 'Untitled')
            created_at = None
            if conv.get('create_time'):
                created_at = datetime.fromtimestamp(conv['create_time'])
            updated_at = None
            if conv.get('update_time'):
                updated_at = datetime.fromtimestamp(conv['update_time'])
            
            # Check for duplicate
            cur.execute(
                "SELECT id FROM chatgpt_conversations WHERE external_id = %s AND user_id = %s",
                (external_id, user_id)
            )
            existing = cur.fetchone()
            if existing:
                logger.debug(f"Skipping duplicate conversation: {title}")
                continue
            
            # Insert conversation
            cur.execute("""
                INSERT INTO chatgpt_conversations 
                (id, user_id, organization_id, external_id, title, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (conv_id, user_id, org_id, external_id, title, created_at, updated_at, 
                  json.dumps(conv.get('metadata', {}))))
            
            # Extract messages from mapping
            messages = []
            mapping = conv.get('mapping', {})
            for node_id, node in mapping.items():
                message = node.get('message')
                if not message:
                    continue
                
                author = message.get('author', {})
                role = author.get('role', 'unknown')
                if role not in ('user', 'assistant', 'system'):
                    continue
                
                content_parts = message.get('content', {}).get('parts', [])
                content = '\n'.join(str(p) for p in content_parts if p)
                if not content:
                    continue
                
                timestamp = None
                if message.get('create_time'):
                    timestamp = datetime.fromtimestamp(message['create_time'])
                
                embedding = None
                if generate_embeddings:
                    embedding = get_embedding(content)
                
                messages.append((
                    str(uuid.uuid4()),
                    conv_id,
                    user_id,
                    org_id,
                    role,
                    content,
                    timestamp,
                    embedding
                ))
            
            # Batch insert messages
            if messages:
                execute_values(cur, """
                    INSERT INTO chatgpt_messages 
                    (id, conversation_id, user_id, organization_id, role, content, timestamp, embedding)
                    VALUES %s
                """, messages, template="(%s, %s, %s, %s, %s, %s, %s, %s)")
                total_messages += len(messages)
            
            imported_convs += 1
            if imported_convs % 10 == 0:
                logger.info(f"Progress: {imported_convs}/{len(conversations)} conversations, {total_messages} messages")
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error importing conversation: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Done! Imported {imported_convs} conversations, {total_messages} messages")
    return imported_convs, total_messages


def main():
    parser = argparse.ArgumentParser(description='Import ChatGPT conversations')
    parser.add_argument('--input', '-i', required=True, help='Path to ChatGPT export ZIP')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--no-embeddings', action='store_true', help='Skip embedding generation')
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logger.error(f"File not found: {args.input}")
        sys.exit(1)
    
    # Validate UUID
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info(f"Importing ChatGPT data from: {args.input}")
    logger.info(f"User ID: {args.user_id}")
    
    conversations = parse_chatgpt_export(args.input)
    if not conversations:
        logger.error("No conversations found in export")
        sys.exit(1)
    
    import_conversations(
        conversations, 
        args.user_id, 
        args.org_id,
        generate_embeddings=not args.no_embeddings
    )


if __name__ == '__main__':
    main()
