#!/usr/bin/env python3
"""
Import Claude AI conversations from export JSON file into CR database.

Usage:
    python import_claude.py --input ~/Downloads/claude-export.json --user-id <uuid>
"""
import argparse
import json
import logging
import os
import sys
import uuid
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


def parse_claude_export(file_path: str) -> list:
    """Parse Claude export file and return conversations."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Claude export format may vary - handle different structures
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict):
        # Try common keys
        conversations = data.get('conversations', data.get('chats', []))
        if not conversations and 'chat_messages' in data:
            # Alternative format: grouped by chat
            conversations = [data]
    else:
        conversations = []
    
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
            external_id = conv.get('uuid', conv.get('id', conv_id))
            title = conv.get('name', conv.get('title', 'Untitled'))
            
            # Parse dates - Claude uses ISO format
            created_at = None
            if conv.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            
            updated_at = None
            if conv.get('updated_at'):
                try:
                    updated_at = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Check for duplicate
            cur.execute(
                "SELECT id FROM claude_conversations WHERE external_id = %s AND user_id = %s",
                (external_id, user_id)
            )
            if cur.fetchone():
                logger.debug(f"Skipping duplicate conversation: {title}")
                continue
            
            # Insert conversation
            cur.execute("""
                INSERT INTO claude_conversations 
                (id, user_id, organization_id, external_id, title, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (conv_id, user_id, org_id, external_id, title, created_at, updated_at, 
                  json.dumps(conv.get('metadata', {}))))
            
            # Extract messages
            messages = []
            chat_messages = conv.get('chat_messages', conv.get('messages', []))
            
            for msg in chat_messages:
                # Claude format: sender is 'human' or 'assistant'
                sender = msg.get('sender', msg.get('role', '')).lower()
                if sender == 'human':
                    role = 'user'
                elif sender == 'assistant':
                    role = 'assistant'
                else:
                    role = sender
                
                if role not in ('user', 'assistant', 'system'):
                    continue
                
                # Content may be string or object
                content = msg.get('text', msg.get('content', ''))
                if isinstance(content, dict):
                    content = content.get('text', str(content))
                if not content:
                    continue
                
                timestamp = None
                if msg.get('created_at'):
                    try:
                        timestamp = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
                    except:
                        pass
                
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
                    INSERT INTO claude_messages 
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
    parser = argparse.ArgumentParser(description='Import Claude conversations')
    parser.add_argument('--input', '-i', required=True, help='Path to Claude export JSON')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--no-embeddings', action='store_true', help='Skip embedding generation')
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logger.error(f"File not found: {args.input}")
        sys.exit(1)
    
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info(f"Importing Claude data from: {args.input}")
    logger.info(f"User ID: {args.user_id}")
    
    conversations = parse_claude_export(args.input)
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
