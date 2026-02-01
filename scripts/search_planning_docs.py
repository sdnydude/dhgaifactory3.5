#!/usr/bin/env python3
"""Search planning documents using RAG (Retrieval-Augmented Generation).

This script:
1. Takes a natural language query
2. Generates embedding for the query
3. Finds similar chunks via pgvector
4. Returns relevant planning document excerpts

Usage:
    python3 search_planning_docs.py "How did we fix Docker networking issues?"
    python3 search_planning_docs.py --project librechat "what was the CME panel status?"
"""

import argparse
import json
import os
import sys
import logging
import psycopg2
import requests
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

def get_db_connection():
    """Get database connection."""
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

def get_embedding(text: str) -> List[float]:
    """Get embedding from Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise

def search(query: str, project_filter: str = None, limit: int = 5) -> List[Dict]:
    """Search planning documents for relevant content."""
    
    # Get query embedding
    query_embedding = get_embedding(query)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Build query with optional project filter
        base_query = """
            SELECT 
                pe.chunk_text,
                pd.project_name,
                pd.file_name,
                pd.metadata,
                1 - (pe.embedding <=> %s::vector) as similarity
            FROM planning_embeddings pe
            JOIN planning_documents pd ON pe.document_id = pd.id
        """
        
        if project_filter:
            query_sql = base_query + """
                WHERE pd.project_name ILIKE %s
                ORDER BY similarity DESC
                LIMIT %s
            """
            cur.execute(query_sql, (query_embedding, f"%{project_filter}%", limit))
        else:
            query_sql = base_query + """
                ORDER BY similarity DESC
                LIMIT %s
            """
            cur.execute(query_sql, (query_embedding, limit))
        
        results = []
        for chunk_text, project, file_name, metadata, similarity in cur.fetchall():
            results.append({
                "text": chunk_text,
                "project": project,
                "file": file_name,
                "metadata": metadata,
                "similarity": float(similarity)
            })
        
        return results
        
    finally:
        cur.close()
        conn.close()

def format_results(results: List[Dict], verbose: bool = False) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."
    
    output = []
    for i, r in enumerate(results, 1):
        output.append(f"\n{'='*60}")
        output.append(f"Result {i} (similarity: {r['similarity']:.3f})")
        output.append(f"Project: {r['project']} | File: {r['file']}")
        output.append(f"{'='*60}")
        output.append(r['text'])
        
        if verbose and r.get('metadata'):
            output.append(f"\nMetadata: {json.dumps(r['metadata'], indent=2)}")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description="Search planning documents")
    parser.add_argument("query", help="Natural language search query")
    parser.add_argument("--project", "-p", help="Filter by project name")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Number of results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show metadata")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    # Check for required environment variable
    if not os.environ.get("DB_PASSWORD") and not os.environ.get("PGPASSWORD"):
        logger.error("DB_PASSWORD or PGPASSWORD environment variable required")
        sys.exit(1)
    
    logger.info(f"Searching for: {args.query}")
    
    results = search(args.query, project_filter=args.project, limit=args.limit)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_results(results, verbose=args.verbose))

if __name__ == "__main__":
    main()
