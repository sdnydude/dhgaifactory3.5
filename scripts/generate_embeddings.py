#!/usr/bin/env python3
"""Generate embeddings for antigravity_messages using sentence-transformers"""

import psycopg2
from sentence_transformers import SentenceTransformer
import sys

# Load model
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="dhg_registry",
    user="dhg",
    password="weenie64"
)
cur = conn.cursor()

# Get messages without embeddings
cur.execute("""
    SELECT id, content FROM antigravity_messages 
    WHERE embedding IS NULL AND content IS NOT NULL AND LENGTH(content) > 10
    LIMIT 500
""")
rows = cur.fetchall()

print(f"Processing {len(rows)} messages...")

batch_size = 50
updated = 0

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
    print(f"  Processed {min(i+batch_size, len(rows))}/{len(rows)}")

cur.close()
conn.close()

print(f"\nDone! Updated {updated} messages with embeddings.")
