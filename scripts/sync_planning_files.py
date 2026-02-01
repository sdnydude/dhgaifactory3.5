#!/usr/bin/env python3
"""Sync planning files (task_plan.md, findings.md, progress.md) to CR database.

This script:
1. Scans for planning files in project directories
2. Inserts/updates them in the planning_documents table
3. Prepares them for embedding generation

Usage:
    python3 sync_planning_files.py [--project-dir /path/to/project]
    
If no project-dir specified, uses current directory.
"""

import json
import os
import sys
import logging
import hashlib
import psycopg2
from datetime import datetime
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

PLANNING_FILES = ["task_plan.md", "findings.md", "progress.md"]

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

def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for change detection."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_metadata(content: str, file_type: str) -> dict:
    """Extract metadata from planning file content."""
    metadata = {
        "file_type": file_type,
        "line_count": len(content.split('\n')),
        "char_count": len(content),
    }
    
    if file_type == "task_plan":
        # Count tasks
        metadata["total_tasks"] = content.count("- [ ]") + content.count("- [x]") + content.count("- [/]")
        metadata["completed_tasks"] = content.count("- [x]")
        metadata["in_progress_tasks"] = content.count("- [/]")
        metadata["pending_tasks"] = content.count("- [ ]")
        
        # Extract current phase if present
        if "## Current Phase" in content:
            try:
                phase_section = content.split("## Current Phase")[1].split("##")[0]
                metadata["current_phase"] = phase_section.strip().split('\n')[0]
            except:
                pass
                
    elif file_type == "findings":
        # Count discoveries
        metadata["discovery_count"] = content.count("- ")
        
    elif file_type == "progress":
        # Count sessions
        metadata["session_count"] = content.count("## Session:")
        
    return metadata

def ensure_table_exists(cur):
    """Create planning_documents table if it doesn't exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS planning_documents (
            id SERIAL PRIMARY KEY,
            project_path TEXT NOT NULL,
            project_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            needs_embedding BOOLEAN DEFAULT TRUE,
            UNIQUE(project_path, file_name)
        )
    """)
    
    # Create index for faster lookups
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_planning_docs_project 
        ON planning_documents(project_path)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_planning_docs_needs_embedding 
        ON planning_documents(needs_embedding) WHERE needs_embedding = TRUE
    """)

def sync_file(cur, project_path: str, project_name: str, file_path: Path):
    """Sync a single planning file to the database."""
    file_name = file_path.name
    file_type = file_name.replace(".md", "").replace("_", "_")
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return False
    
    content_hash = compute_content_hash(content)
    metadata = extract_metadata(content, file_type)
    
    # Check if content has changed
    cur.execute("""
        SELECT content_hash FROM planning_documents 
        WHERE project_path = %s AND file_name = %s
    """, (project_path, file_name))
    
    existing = cur.fetchone()
    
    if existing and existing[0] == content_hash:
        logger.info(f"  {file_name}: No changes detected, skipping")
        return False
    
    # Upsert the document
    cur.execute("""
        INSERT INTO planning_documents 
        (project_path, project_name, file_type, file_name, content, content_hash, metadata, needs_embedding, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
        ON CONFLICT (project_path, file_name) DO UPDATE SET
            content = EXCLUDED.content,
            content_hash = EXCLUDED.content_hash,
            metadata = EXCLUDED.metadata,
            needs_embedding = TRUE,
            updated_at = NOW()
    """, (project_path, project_name, file_type, file_name, content, content_hash, json.dumps(metadata)))
    
    action = "Updated" if existing else "Inserted"
    logger.info(f"  {file_name}: {action} ({metadata.get('line_count', 0)} lines)")
    return True

def main():
    parser = argparse.ArgumentParser(description="Sync planning files to CR database")
    parser.add_argument("--project-dir", "-p", default=".", help="Project directory to scan")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories for planning files")
    args = parser.parse_args()
    
    project_dir = Path(args.project_dir).resolve()
    project_name = project_dir.name
    project_path = str(project_dir)
    
    logger.info(f"Scanning project: {project_name}")
    logger.info(f"Path: {project_path}")
    
    # Check for required environment variable
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)
    
    # Connect to database
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Ensure table exists
        ensure_table_exists(cur)
        conn.commit()
        
        # Find planning files
        files_found = []
        for file_name in PLANNING_FILES:
            file_path = project_dir / file_name
            if file_path.exists():
                files_found.append(file_path)
        
        if not files_found:
            logger.warning(f"No planning files found in {project_dir}")
            logger.info(f"Expected files: {', '.join(PLANNING_FILES)}")
            sys.exit(0)
        
        logger.info(f"Found {len(files_found)} planning files")
        
        # Sync each file
        synced_count = 0
        for file_path in files_found:
            if sync_file(cur, project_path, project_name, file_path):
                synced_count += 1
        
        conn.commit()
        
        logger.info(f"Sync complete: {synced_count} files updated")
        
        # Report on files needing embedding
        cur.execute("""
            SELECT COUNT(*) FROM planning_documents WHERE needs_embedding = TRUE
        """)
        needs_embedding = cur.fetchone()[0]
        if needs_embedding > 0:
            logger.info(f"Note: {needs_embedding} documents need embedding generation")
            logger.info("Run: python3 scripts/generate_planning_embeddings.py")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during sync: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
