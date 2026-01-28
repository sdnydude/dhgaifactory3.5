#!/usr/bin/env python3
"""
Ingest Antigravity markdown artifacts into CR database.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Configuration
BACKUP_PATH = "/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming/antigravity-backup-2026-01-26.zip/backup-2026-01-26T18-09-30-502Z/brain"
OUTPUT_JSON = "/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming/antigravity_artifacts.json"

def extract_metadata(filepath):
    """Extract metadata from markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Get filename and session info
    path = Path(filepath)
    session_id = path.parent.name
    filename = path.name
    
    # Calculate content hash
    content_hash = hashlib.md5(content.encode()).hexdigest()
    
    return {
        "session_id": session_id,
        "filename": filename,
        "filepath": str(filepath),
        "content": content,
        "content_hash": content_hash,
        "char_count": len(content),
        "line_count": content.count("\n") + 1,
        "extracted_at": datetime.now().isoformat()
    }

def main():
    brain_path = Path(BACKUP_PATH)
    artifacts = []
    
    print(f"Scanning {brain_path}...")
    
    # Find all markdown files
    for md_file in brain_path.rglob("*.md"):
        # Skip resolved/metadata versions
        if ".resolved" in str(md_file) or ".metadata" in str(md_file):
            continue
        
        try:
            artifact = extract_metadata(md_file)
            artifacts.append(artifact)
            print(f"  Extracted: {artifact[\"session_id\"]}/{artifact[\"filename\"]} ({artifact[\"char_count\"]} chars)")
        except Exception as e:
            print(f"  Error processing {md_file}: {e}")
    
    print(f"\nTotal: {len(artifacts)} artifacts")
    
    # Save to JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2)
    
    print(f"Saved to {OUTPUT_JSON}")
    
    # Summary stats
    total_chars = sum(a["char_count"] for a in artifacts)
    print(f"Total content: {total_chars:,} characters")

if __name__ == "__main__":
    main()
SCRIPT'
