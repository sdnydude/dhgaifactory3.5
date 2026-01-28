#!/usr/bin/env python3
"""Ingest Antigravity conversations into CR database"""

import json
import psycopg2
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="dhg_registry",
    user="dhg",
    password="weenie64"
)
cur = conn.cursor()

# Load exported conversations
with open("/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming/antigravity_conversations_full.json") as f:
    sessions = json.load(f)

print(f"Processing {len(sessions)} sessions...")

inserted_chats = 0
inserted_messages = 0

for session in sessions:
    sid = session["session_id"]
    title = session.get("title", "Untitled")
    step_count = session.get("step_count", 0)
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
        print(f"  Processed {inserted_chats}/{len(sessions)} sessions, {inserted_messages} messages")

conn.commit()
cur.close()
conn.close()

print(f"\nDone!")
print(f"  Chats inserted/updated: {inserted_chats}")
print(f"  Messages inserted: {inserted_messages}")
