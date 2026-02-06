#!/usr/bin/env python3
"""
Sync Google Drive documents to CR database using Google API.

First time setup:
    python sync_gdrive.py --auth-flow --user-id <uuid>

Subsequent syncs:
    python sync_gdrive.py --user-id <uuid>
"""
import argparse
import io
import logging
import os
import pickle
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Paths
CREDENTIALS_DIR = Path.home() / '.config' / 'dhg-ai-factory' / 'google'
TOKEN_FILE = CREDENTIALS_DIR / 'drive_token.pickle'
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

# Supported MIME types for text extraction
EXPORTABLE_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
}

TEXT_TYPES = [
    'text/plain',
    'text/markdown',
    'text/csv',
    'application/json',
]


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )


def get_embedding(text: str) -> Optional[list]:
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
    creds = None
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    if TOKEN_FILE.exists() and not force_new:
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def get_file_content(service, file_id: str, mime_type: str) -> str:
    """Download or export file content as text."""
    try:
        if mime_type in EXPORTABLE_TYPES:
            # Export Google Docs/Sheets/Slides
            export_type = EXPORTABLE_TYPES[mime_type]
            request = service.files().export_media(fileId=file_id, mimeType=export_type)
        elif any(mime_type.startswith(t) for t in TEXT_TYPES):
            # Download text files directly
            request = service.files().get_media(fileId=file_id)
        else:
            return ""
        
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        return buffer.getvalue().decode('utf-8', errors='ignore')[:50000]  # Limit size
    except Exception as e:
        logger.warning(f"Error getting content for {file_id}: {e}")
        return ""


def sync_documents(service, user_id: str, org_id: Optional[str], max_results: int = 200, generate_embeddings: bool = True):
    """Sync documents from Google Drive to database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get existing document IDs
    cur.execute("SELECT drive_id FROM gws_documents WHERE user_id = %s", (user_id,))
    existing_ids = {row[0] for row in cur.fetchall()}
    logger.info(f"Found {len(existing_ids)} existing documents in database")
    
    # Fetch file list
    logger.info("Fetching file list from Google Drive...")
    files = []
    page_token = None
    
    # Query for documents, spreadsheets, presentations, and text files
    query = "mimeType contains 'vnd.google-apps' or mimeType contains 'text/'"
    
    while len(files) < max_results:
        try:
            results = service.files().list(
                q=query,
                pageSize=min(100, max_results - len(files)),
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, owners)"
            ).execute()
            
            batch = results.get('files', [])
            files.extend(batch)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            logger.error(f"Error fetching files: {e}")
            break
    
    logger.info(f"Found {len(files)} documents in Google Drive")
    
    imported = 0
    skipped = 0
    
    for i, file in enumerate(files):
        file_id = file['id']
        
        if file_id in existing_ids:
            skipped += 1
            continue
        
        try:
            mime_type = file.get('mimeType', '')
            
            # Get content
            content = get_file_content(service, file_id, mime_type)
            
            # Parse date
            last_modified = None
            if file.get('modifiedTime'):
                try:
                    last_modified = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Get owner
            owners = file.get('owners', [])
            owner = owners[0].get('emailAddress', '') if owners else ''
            
            # Generate embedding
            embedding = None
            if generate_embeddings and content:
                embed_text = f"{file['name']} {content[:2000]}"
                embedding = get_embedding(embed_text)
            
            # Insert
            cur.execute("""
                INSERT INTO gws_documents 
                (user_id, organization_id, drive_id, title, mime_type, content_text, 
                 last_modified, owner, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, org_id, file_id, file['name'], mime_type,
                content, last_modified, owner, embedding
            ))
            
            imported += 1
            
            if imported % 20 == 0:
                logger.info(f"Progress: {imported} imported, {skipped} skipped, {i+1}/{len(files)} processed")
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Done! Imported {imported} documents, skipped {skipped} existing")


def main():
    parser = argparse.ArgumentParser(description='Sync Google Drive to CR database')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--auth-flow', action='store_true', help='Force new OAuth authentication')
    parser.add_argument('--max-results', '-m', type=int, default=200, help='Max documents to sync')
    parser.add_argument('--no-embeddings', action='store_true', help='Skip embedding generation')
    args = parser.parse_args()
    
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info("Authenticating with Google Drive...")
    creds = authenticate(force_new=args.auth_flow)
    
    logger.info("Building Drive service...")
    service = build('drive', 'v3', credentials=creds)
    
    logger.info(f"Starting sync for user: {args.user_id}")
    sync_documents(
        service, user_id=args.user_id, org_id=args.org_id,
        max_results=args.max_results,
        generate_embeddings=not args.no_embeddings
    )


if __name__ == '__main__':
    main()
