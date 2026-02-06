#!/usr/bin/env python3
"""
Sync Gmail messages to CR database using Google API.

First time setup:
    python sync_gmail.py --auth-flow --user-id <uuid>

Subsequent syncs:
    python sync_gmail.py --user-id <uuid>
"""
import argparse
import base64
import json
import logging
import os
import pickle
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Paths
CREDENTIALS_DIR = Path.home() / '.config' / 'dhg-ai-factory' / 'google'
TOKEN_FILE = CREDENTIALS_DIR / 'gmail_token.pickle'
CREDENTIALS_FILE = CREDENTIALS_DIR / 'credentials.json'

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


def authenticate(force_new: bool = False) -> Credentials:
    """Authenticate with Google OAuth2."""
    creds = None
    
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for existing token
    if TOKEN_FILE.exists() and not force_new:
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                logger.error("Please download OAuth client credentials from Google Cloud Console")
                logger.error("and save it as: ~/.config/dhg-ai-factory/google/credentials.json")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def get_message_body(payload: dict) -> str:
    """Extract message body from Gmail payload."""
    body = ""
    
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
            elif mime_type.startswith('multipart/'):
                body = get_message_body(part)
                if body:
                    break
    
    return body


def parse_headers(headers: list) -> dict:
    """Parse email headers into dict."""
    result = {}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name in ('from', 'to', 'cc', 'subject', 'date'):
            result[name] = value
    return result


def sync_emails(service, user_id: str, org_id: Optional[str], max_results: int = 500, generate_embeddings: bool = True):
    """Sync emails from Gmail to database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get existing message IDs
    cur.execute("SELECT message_id FROM gws_emails WHERE user_id = %s", (user_id,))
    existing_ids = {row[0] for row in cur.fetchall()}
    logger.info(f"Found {len(existing_ids)} existing emails in database")
    
    # Fetch message list
    logger.info("Fetching message list from Gmail...")
    messages = []
    page_token = None
    
    while len(messages) < max_results:
        try:
            results = service.users().messages().list(
                userId='me',
                maxResults=min(100, max_results - len(messages)),
                pageToken=page_token
            ).execute()
            
            batch = results.get('messages', [])
            messages.extend(batch)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            break
    
    logger.info(f"Found {len(messages)} messages in Gmail")
    
    # Process messages
    imported = 0
    skipped = 0
    
    for i, msg_ref in enumerate(messages):
        msg_id = msg_ref['id']
        
        if msg_id in existing_ids:
            skipped += 1
            continue
        
        try:
            # Fetch full message
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            payload = msg.get('payload', {})
            headers = parse_headers(payload.get('headers', []))
            
            # Parse recipients
            to_addrs = [addr.strip() for addr in headers.get('to', '').split(',') if addr.strip()]
            cc_addrs = [addr.strip() for addr in headers.get('cc', '').split(',') if addr.strip()]
            
            # Parse date
            date = None
            if headers.get('date'):
                try:
                    # Gmail date format varies, try internal date
                    internal_date = msg.get('internalDate')
                    if internal_date:
                        date = datetime.fromtimestamp(int(internal_date) / 1000)
                except:
                    pass
            
            # Get body
            body = get_message_body(payload)
            
            # Get labels
            labels = msg.get('labelIds', [])
            
            # Generate embedding
            embedding = None
            if generate_embeddings:
                embed_text = f"{headers.get('subject', '')} {body[:2000]}"
                embedding = get_embedding(embed_text)
            
            # Insert
            cur.execute("""
                INSERT INTO gws_emails 
                (user_id, organization_id, message_id, thread_id, subject, from_addr, 
                 to_addrs, cc_addrs, body_text, date, labels, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, org_id, msg_id, msg.get('threadId'),
                headers.get('subject', ''), headers.get('from', ''),
                to_addrs, cc_addrs, body, date, labels, embedding
            ))
            
            imported += 1
            
            if imported % 50 == 0:
                logger.info(f"Progress: {imported} imported, {skipped} skipped, {i+1}/{len(messages)} processed")
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Done! Imported {imported} emails, skipped {skipped} existing")


def main():
    parser = argparse.ArgumentParser(description='Sync Gmail to CR database')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--auth-flow', action='store_true', help='Force new OAuth authentication')
    parser.add_argument('--max-results', '-m', type=int, default=500, help='Max emails to sync')
    parser.add_argument('--no-embeddings', action='store_true', help='Skip embedding generation')
    args = parser.parse_args()
    
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info("Authenticating with Gmail...")
    creds = authenticate(force_new=args.auth_flow)
    
    logger.info("Building Gmail service...")
    service = build('gmail', 'v1', credentials=creds)
    
    logger.info(f"Starting sync for user: {args.user_id}")
    sync_emails(
        service, 
        args.user_id, 
        args.org_id,
        max_results=args.max_results,
        generate_embeddings=not args.no_embeddings
    )


if __name__ == '__main__':
    main()
