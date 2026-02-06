#!/usr/bin/env python3
"""
Sync Google Calendar events to CR database using Google API.

First time setup:
    python sync_gcal.py --auth-flow --user-id <uuid>

Subsequent syncs:
    python sync_gcal.py --user-id <uuid>
"""
import argparse
import logging
import os
import pickle
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import psycopg2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

CREDENTIALS_DIR = Path.home() / '.config' / 'dhg-ai-factory' / 'google'
TOKEN_FILE = CREDENTIALS_DIR / 'calendar_token.pickle'
CREDENTIALS_FILE = CREDENTIALS_DIR / 'credentials.json'

DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_USER = os.getenv('POSTGRES_USER', 'dhg')
DB_PASS = os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
DB_NAME = os.getenv('POSTGRES_DB', 'dhg_registry')


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )


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


def parse_datetime(dt_obj: dict) -> Optional[datetime]:
    """Parse Google Calendar datetime object."""
    if not dt_obj:
        return None
    
    # Could be dateTime or date (all-day event)
    dt_str = dt_obj.get('dateTime') or dt_obj.get('date')
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return None


def sync_calendar(service, user_id: str, org_id: Optional[str], days_back: int = 365, days_forward: int = 90):
    """Sync calendar events to database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get existing event IDs
    cur.execute("SELECT event_id FROM gws_calendar WHERE user_id = %s", (user_id,))
    existing_ids = {row[0] for row in cur.fetchall()}
    logger.info(f"Found {len(existing_ids)} existing events in database")
    
    # Time range
    now = datetime.utcnow()
    time_min = (now - timedelta(days=days_back)).isoformat() + 'Z'
    time_max = (now + timedelta(days=days_forward)).isoformat() + 'Z'
    
    logger.info(f"Fetching events from {days_back} days ago to {days_forward} days ahead...")
    
    events = []
    page_token = None
    
    while True:
        try:
            results = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=250,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            
            batch = results.get('items', [])
            events.extend(batch)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            break
    
    logger.info(f"Found {len(events)} events in Google Calendar")
    
    imported = 0
    skipped = 0
    
    for event in events:
        event_id = event['id']
        
        if event_id in existing_ids:
            skipped += 1
            continue
        
        try:
            start_time = parse_datetime(event.get('start', {}))
            end_time = parse_datetime(event.get('end', {}))
            
            # Extract attendees
            attendees = []
            for att in event.get('attendees', []):
                attendees.append({
                    'email': att.get('email', ''),
                    'name': att.get('displayName', ''),
                    'response': att.get('responseStatus', '')
                })
            
            cur.execute("""
                INSERT INTO gws_calendar 
                (user_id, organization_id, event_id, title, description, 
                 start_time, end_time, location, attendees)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, org_id, event_id,
                event.get('summary', 'Untitled'),
                event.get('description', ''),
                start_time, end_time,
                event.get('location', ''),
                psycopg2.extras.Json(attendees) if attendees else None
            ))
            
            imported += 1
            
            if imported % 50 == 0:
                logger.info(f"Progress: {imported} imported, {skipped} skipped")
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Done! Imported {imported} events, skipped {skipped} existing")


def main():
    parser = argparse.ArgumentParser(description='Sync Google Calendar to CR database')
    parser.add_argument('--user-id', '-u', required=True, help='User UUID')
    parser.add_argument('--org-id', '-o', help='Organization UUID (optional)')
    parser.add_argument('--auth-flow', action='store_true', help='Force new OAuth authentication')
    parser.add_argument('--days-back', type=int, default=365, help='Days of history to sync')
    parser.add_argument('--days-forward', type=int, default=90, help='Days ahead to sync')
    args = parser.parse_args()
    
    try:
        uuid.UUID(args.user_id)
        if args.org_id:
            uuid.UUID(args.org_id)
    except ValueError as e:
        logger.error(f"Invalid UUID: {e}")
        sys.exit(1)
    
    logger.info("Authenticating with Google Calendar...")
    creds = authenticate(force_new=args.auth_flow)
    
    logger.info("Building Calendar service...")
    service = build('calendar', 'v3', credentials=creds)
    
    logger.info(f"Starting sync for user: {args.user_id}")
    sync_calendar(
        service, user_id=args.user_id, org_id=args.org_id,
        days_back=args.days_back,
        days_forward=args.days_forward
    )


if __name__ == '__main__':
    main()
