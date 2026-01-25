"""
Antigravity MCP Server
Exposes Antigravity session tracking and document management via MCP protocol
"""

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
import httpx
from datetime import datetime
from pathlib import Path
import json

# Initialize MCP server
server = Server("antigravity-tracker")

# Configuration
REGISTRY_URL = "http://10.0.0.251:8500"
ONYX_URL = "http://onyx-url"  # Update with actual URL


# =============================================================================
# TOOLS
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="track_chat_message",
            description="Track an Antigravity chat message to Central Registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_message": {
                        "type": "string",
                        "description": "The user's message"
                    },
                    "assistant_response": {
                        "type": "string",
                        "description": "The assistant's response"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (tokens, cost, etc.)"
                    }
                },
                "required": ["user_message", "assistant_response", "session_id"]
            }
        ),
        
        Tool(
            name="track_file_creation",
            description="Track a file created by Antigravity to Central Registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the created file"
                    },
                    "file_purpose": {
                        "type": "string",
                        "description": "Purpose of the file (documentation, code, etc.)"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier"
                    }
                },
                "required": ["file_path", "session_id"]
            }
        ),
        
        Tool(
            name="index_document_in_onyx",
            description="Index a document in Onyx knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document"
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    }
                },
                "required": ["file_path", "title"]
            }
        ),
        
        Tool(
            name="get_session_summary",
            description="Get summary of current Antigravity session from Central Registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier"
                    }
                },
                "required": ["session_id"]
            }
        ),
        
        Tool(
            name="search_antigravity_history",
            description="Search previous Antigravity conversations in Central Registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool calls"""
    
    if name == "track_chat_message":
        return await track_chat_message(arguments)
    
    elif name == "track_file_creation":
        return await track_file_creation(arguments)
    
    elif name == "index_document_in_onyx":
        return await index_document_in_onyx(arguments)
    
    elif name == "get_session_summary":
        return await get_session_summary(arguments)
    
    elif name == "search_antigravity_history":
        return await search_antigravity_history(arguments)
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

async def track_chat_message(args: dict) -> list[TextContent]:
    """Track chat message to Central Registry"""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/antigravity/chats",
            json={
                "user_id": "swebber64",
                "session_id": args["session_id"],
                "user_message": args["user_message"],
                "assistant_response": args["assistant_response"],
                "timestamp": datetime.now().isoformat(),
                "metadata": args.get("metadata", {})
            }
        )
        
        if response.status_code == 201:
            result = response.json()
            return [TextContent(
                type="text",
                text=f"✅ Chat message tracked successfully. ID: {result.get('id')}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to track chat: {response.text}"
            )]


async def track_file_creation(args: dict) -> list[TextContent]:
    """Track file creation to Central Registry"""
    
    file_path = Path(args["file_path"])
    
    if not file_path.exists():
        return [TextContent(
            type="text",
            text=f"❌ File not found: {file_path}"
        )]
    
    content = file_path.read_text()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/antigravity/files",
            json={
                "user_id": "swebber64",
                "session_id": args["session_id"],
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lstrip('.'),
                "file_size": len(content),
                "purpose": args.get("file_purpose", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if response.status_code == 201:
            result = response.json()
            return [TextContent(
                type="text",
                text=f"✅ File tracked successfully. ID: {result.get('id')}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to track file: {response.text}"
            )]


async def index_document_in_onyx(args: dict) -> list[TextContent]:
    """Index document in Onyx knowledge base"""
    
    file_path = Path(args["file_path"])
    
    if not file_path.exists():
        return [TextContent(
            type="text",
            text=f"❌ File not found: {file_path}"
        )]
    
    content = file_path.read_text()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ONYX_URL}/api/documents",
            json={
                "title": args["title"],
                "content": content,
                "metadata": {
                    "author": "Antigravity Assistant",
                    "created_at": datetime.now().isoformat(),
                    "tags": args.get("tags", []),
                    "source": "antigravity_mcp_server"
                }
            }
        )
        
        if response.status_code in [200, 201]:
            return [TextContent(
                type="text",
                text=f"✅ Document indexed in Onyx: {args['title']}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to index document: {response.text}"
            )]


async def get_session_summary(args: dict) -> list[TextContent]:
    """Get session summary from Central Registry"""
    
    async with httpx.AsyncClient() as client:
        # Get all chats for this session
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/antigravity/chats",
            params={"session_id": args["session_id"]}
        )
        
        if response.status_code == 200:
            chats = response.json()
            
            summary = f"""
Session Summary: {args['session_id']}
Total messages: {len(chats)}
First message: {chats[0]['timestamp'] if chats else 'N/A'}
Last message: {chats[-1]['timestamp'] if chats else 'N/A'}

Recent conversations:
"""
            for chat in chats[-5:]:  # Last 5 messages
                summary += f"\n- User: {chat['user_message'][:100]}..."
                summary += f"\n  Assistant: {chat['assistant_response'][:100]}...\n"
            
            return [TextContent(type="text", text=summary)]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to get session summary: {response.text}"
            )]


async def search_antigravity_history(args: dict) -> list[TextContent]:
    """Search Antigravity conversation history"""
    
    async with httpx.AsyncClient() as client:
        # Search in Central Registry
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/antigravity/chats/search",
            params={
                "query": args["query"],
                "limit": args.get("limit", 10)
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"No results found for: {args['query']}"
                )]
            
            output = f"Found {len(results)} results for '{args['query']}':\n\n"
            
            for i, result in enumerate(results, 1):
                output += f"{i}. Session: {result['session_id']}\n"
                output += f"   Date: {result['timestamp']}\n"
                output += f"   User: {result['user_message'][:100]}...\n"
                output += f"   Assistant: {result['assistant_response'][:100]}...\n\n"
            
            return [TextContent(type="text", text=output)]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Search failed: {response.text}"
            )]


# =============================================================================
# RESOURCES (Optional)
# =============================================================================

@server.list_resources()
async def list_resources():
    """List available resources"""
    return [
        {
            "uri": "antigravity://sessions/current",
            "name": "Current Session",
            "description": "Current Antigravity session data",
            "mimeType": "application/json"
        },
        {
            "uri": "antigravity://files/recent",
            "name": "Recent Files",
            "description": "Recently created files",
            "mimeType": "application/json"
        }
    ]


@server.read_resource()
async def read_resource(uri: str):
    """Read resource content"""
    
    if uri == "antigravity://sessions/current":
        # Return current session data
        return {
            "contents": [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "session_id": "current",
                        "start_time": datetime.now().isoformat(),
                        "user_id": "swebber64"
                    }, indent=2)
                )
            ]
        }
    
    elif uri == "antigravity://files/recent":
        # Return recent files
        desktop = Path("/Users/swebber64/Desktop")
        recent_files = sorted(
            desktop.glob("*.{py,md,sh}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:10]
        
        files_data = [
            {
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in recent_files
        ]
        
        return {
            "contents": [
                TextContent(
                    type="text",
                    text=json.dumps(files_data, indent=2)
                )
            ]
        }


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    asyncio.run(main())
