#!/usr/bin/env python3
"""
Import Google Gemini conversations from Google Takeout export into CR database.

Usage:
    python import_gemini.py --input ~/Downloads/Takeout/Gemini --user-id <uuid>
"""
import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
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


def parse_gemini_takeout(input_path: str) -> list:
    """
    Parse Gemini data from Google Takeout.
    
    Takeout structure (may vary):
    - Gemini/
      - conversations/
        - <conversation_id>.json
    or
    - Gemini Apps Activity/
      - My Activity.json
    """
    conversations = []
    input_path = Path(input_path)
    
    if input_path.is_file() and input_path.suffix == '.json':
        # Single JSON file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                # Activity format - group into pseudo-conversations
                conversations = _parse_activity_format(data)
            elif isinstance(data, dict):
                conversations = [data]
    elif input_path.is_dir():
        # Directory with multiple JSON files
        for json_file in input_path.rglob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        conversations.extend(_parse_activity_format(data))
                    elif isinstance(data, dict):
                        conversations.append(data)
            except Exception as e:
                logger.warning(f"Error reading {json_file}: {e}")
    
    logger.info(f"Found {len(conversations)} conversations in Gemini export")
    return conversations


def _parse_activity_format(activities: list) -> list:
    """Parse Google Activity format into conversations."""
    # Group activities by title/conversation
    grouped = {}
    for activity in activities:
        title = activity.get('title', 'Untitled')
        if title not in grouped:
            grouped[title] = {
                'title': title,
                'messages': [],
                'created_at': None,
                'updated_at': None
            }
        
        # Parse activity into message
        time_str = activity.get('time')
        timestamp = None
        if time_str:
            try:
                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except:
                pass
        
        # Update conversation timestamps
        if timestamp:
            if not grouped[title]['created_at'] or timestamp < grouped[title]['created_at']:
                grouped[title]['created_at'] = timestamp
            if not grouped[title]['updated_at'] or timestamp > grouped[title]['updated_at']:
                grouped[title]['updated_at'] = timestamp
        
        # Extract message content
        subtitles = activity.get('subtitles', [])
        for sub in subtitles:
            content = sub.get('name', '')
            if content:
                grouped[title]['messages'].append({
                    'role': 'user',  # Gemini activity typically shows user queries
                    'content': content,
                    'timestamp': timestamp
                })
        
        # Response might be in different fields
        response = activity.get('response', activity.get('details', ''))
        if response:
            grouped[title]['messages'].append({
                'role': 'assistant',
                'content': str(response),
                'timestamp': timestamp
            })
    
    return list(grouped.values())


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
            created_at = conv.get('created_at')
            updated_at = conv.get('updated_at')
            
            # Check for duplicate
            cur.execute(
                "SELECT id FROM gemini_conversations WHERE external_id = %s AND user_id = %s",
                (external_id, user_id)
            )
            if cur.fetchone():
                logger.debug(f"Skipping duplicate conversation: {title}")
                continue
            
            # Insert conversation
            cur.execute("""
                INSERT INTO gemini_conversations 
                (id, user_id, organization_id, external_id, title, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (conv_id, user_id, org_id, external_id, title, created_at, updated_at, 
                  json.dumps(conv.get('metadata', {}))))
            
            # Extract messages
            messages = []
            chat_messages = conv.get('messages', [])
            
            for msg in chat_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if not content:
                    continue
                
                timestamp = msg.get('timestamp')
                
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
                    INSERT INTO gemini_messages 
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
    parser = argparse.ArgumentParser(description='Import Gemini conversations from Google Takeout')
    parser.add_argument('--input', '-i', required=True, help='Path to Gemini export (folder or JSON)')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--no-embeddings', action='store_true', help='Skip embedding generation')
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logger.error(f"Path not found: {args.input}")
        sys.exit(1)
    
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info(f"Importing Gemini data from: {args.input}")
    logger.info(f"User ID: {args.user_id}")
    
    conversations = parse_gemini_takeout(args.input)
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
