#!/usr/bin/env python3
"""
Sync Antigravity session to Central Registry and Onyx
Run this after each session to capture conversation and files
"""

import httpx
import asyncio
from datetime import datetime
from pathlib import Path
import json

# Configuration
REGISTRY_URL = "http://10.0.0.251:8500"
ONYX_URL = "http://onyx-url"  # Update with actual Onyx URL
SESSION_ID = "2026-01-24-langsmith-architecture"
USER_ID = "swebber64"

# Files created in this session
FILES_CREATED = [
    "/Users/swebber64/Desktop/renderer_simple.py",
    "/Users/swebber64/Desktop/registry_research_schemas.py",
    "/Users/swebber64/Desktop/DEPLOY_ALL.sh",
    "/Users/swebber64/Desktop/DEPLOY_TO_SERVER.sh",
    "/Users/swebber64/Desktop/enhanced_agent_graph.py",
    "/Users/swebber64/Desktop/GRAPH_VISUALIZATION_GUIDE.md",
    "/Users/swebber64/Desktop/DHG_LANGSMITH_ARCHITECTURE.md"
]

async def sync_to_registry():
    """Sync session data to Central Registry"""
    
    async with httpx.AsyncClient() as client:
        
        # Track each file
        for file_path in FILES_CREATED:
            path = Path(file_path)
            if not path.exists():
                print(f"⚠️  File not found: {file_path}")
                continue
            
            content = path.read_text()
            
            response = await client.post(
                f"{REGISTRY_URL}/api/v1/antigravity/files",
                json={
                    "user_id": USER_ID,
                    "session_id": SESSION_ID,
                    "file_path": str(path),
                    "file_name": path.name,
                    "file_type": path.suffix.lstrip('.'),
                    "file_size": len(content),
                    "purpose": "documentation" if path.suffix == ".md" else "code",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "session_topic": "LangSmith Cloud Architecture",
                        "session_duration_hours": 6
                    }
                }
            )
            
            if response.status_code == 201:
                print(f"✅ Tracked: {path.name}")
            else:
                print(f"❌ Failed to track: {path.name} - {response.text}")
        
        # Track session summary
        session_summary = {
            "user_id": USER_ID,
            "session_id": SESSION_ID,
            "user_message": "Implement LangSmith Cloud multi-agent architecture",
            "assistant_response": "Created comprehensive architecture with parallel branches, conditional routing, subgraphs, and assistants",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "files_created": len(FILES_CREATED),
                "topics_covered": [
                    "LangSmith Studio setup",
                    "Assistants configuration",
                    "Parallel branches",
                    "Conditional routing",
                    "Subgraphs",
                    "Multi-agent architecture"
                ],
                "duration_hours": 6,
                "total_tokens": 102000,
                "estimated_cost": 0.50
            }
        }
        
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/antigravity/chats",
            json=session_summary
        )
        
        if response.status_code == 201:
            print(f"✅ Session summary tracked")
        else:
            print(f"❌ Failed to track session: {response.text}")


async def index_in_onyx():
    """Index documentation in Onyx knowledge base"""
    
    # Documents to index
    docs_to_index = [
        {
            "file": "/Users/swebber64/Desktop/DHG_LANGSMITH_ARCHITECTURE.md",
            "title": "DHG AI Factory - LangSmith Cloud Multi-Agent Architecture",
            "tags": ["architecture", "langsmith", "multi-agent", "langgraph"]
        },
        {
            "file": "/Users/swebber64/Desktop/GRAPH_VISUALIZATION_GUIDE.md",
            "title": "LangGraph Visualization Guide",
            "tags": ["langgraph", "visualization", "graphs"]
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for doc in docs_to_index:
            path = Path(doc["file"])
            if not path.exists():
                print(f"⚠️  File not found: {doc['file']}")
                continue
            
            content = path.read_text()
            
            # Index in Onyx
            response = await client.post(
                f"{ONYX_URL}/api/documents",
                json={
                    "title": doc["title"],
                    "content": content,
                    "metadata": {
                        "author": "Antigravity Assistant",
                        "created_at": datetime.now().isoformat(),
                        "document_type": "architecture_guide",
                        "tags": doc["tags"],
                        "source": "antigravity_session",
                        "session_id": SESSION_ID
                    }
                }
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Indexed in Onyx: {doc['title']}")
            else:
                print(f"❌ Failed to index: {doc['title']} - {response.text}")


async def main():
    """Run sync"""
    print("🚀 Starting Antigravity session sync...\n")
    
    print("📝 Syncing to Central Registry...")
    await sync_to_registry()
    print()
    
    print("🔍 Indexing in Onyx...")
    await index_in_onyx()
    print()
    
    print("✅ Sync complete!")


if __name__ == "__main__":
    asyncio.run(main())
