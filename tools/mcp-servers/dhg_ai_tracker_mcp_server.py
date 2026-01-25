"""
DHG AI Tracker MCP Server
Universal tracking for Claude, ChatGPT, Manus (Antigravity), and Perplexity
With configurable on/off toggles for each AI system
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx
from datetime import datetime
from pathlib import Path
import json
import os
from typing import Optional

# Initialize MCP server
server = Server("dhg-ai-tracker")

# Configuration from environment variables
REGISTRY_URL = os.getenv("REGISTRY_URL", "http://10.0.0.251:8500")
ONYX_URL = os.getenv("ONYX_URL", "http://10.0.0.251:8080")

# Tracking toggles
TRACK_CLAUDE = os.getenv("TRACK_CLAUDE", "true").lower() == "true"
TRACK_CHATGPT = os.getenv("TRACK_CHATGPT", "true").lower() == "true"
TRACK_MANUS = os.getenv("TRACK_MANUS", "true").lower() == "true"
TRACK_PERPLEXITY = os.getenv("TRACK_PERPLEXITY", "true").lower() == "true"
AUTO_TRACK_FILES = os.getenv("AUTO_TRACK_FILES", "true").lower() == "true"
AUTO_TRACK_CHATS = os.getenv("AUTO_TRACK_CHATS", "true").lower() == "true"

# Session management
SESSION_ID = os.getenv("SESSION_ID", "auto")
if SESSION_ID == "auto":
    SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


# =============================================================================
# CONFIGURATION TOOLS
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        # Configuration tools
        Tool(
            name="configure_tracking",
            description="Enable/disable tracking for specific AI systems",
            inputSchema={
                "type": "object",
                "properties": {
                    "claude": {"type": "boolean", "description": "Track Claude conversations"},
                    "chatgpt": {"type": "boolean", "description": "Track ChatGPT conversations"},
                    "manus": {"type": "boolean", "description": "Track Manus/Antigravity conversations"},
                    "perplexity": {"type": "boolean", "description": "Track Perplexity searches"},
                    "auto_track_files": {"type": "boolean", "description": "Automatically track file creations"},
                    "auto_track_chats": {"type": "boolean", "description": "Automatically track chat messages"}
                }
            }
        ),
        
        Tool(
            name="get_tracking_status",
            description="Get current tracking configuration",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Tracking tools
        Tool(
            name="track_conversation",
            description="Track a conversation from any AI system",
            inputSchema={
                "type": "object",
                "properties": {
                    "ai_system": {
                        "type": "string",
                        "enum": ["claude", "chatgpt", "manus", "perplexity"],
                        "description": "Which AI system this is from"
                    },
                    "user_message": {"type": "string", "description": "User's message"},
                    "ai_response": {"type": "string", "description": "AI's response"},
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (tokens, cost, model, etc.)"
                    }
                },
                "required": ["ai_system", "user_message", "ai_response"]
            }
        ),
        
        Tool(
            name="track_file",
            description="Track a file created by any AI system",
            inputSchema={
                "type": "object",
                "properties": {
                    "ai_system": {
                        "type": "string",
                        "enum": ["claude", "chatgpt", "manus", "perplexity"],
                        "description": "Which AI system created this file"
                    },
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "file_purpose": {"type": "string", "description": "Purpose of the file"},
                    "index_in_onyx": {"type": "boolean", "description": "Also index in Onyx", "default": True}
                },
                "required": ["ai_system", "file_path"]
            }
        ),
        
        Tool(
            name="track_search",
            description="Track a Perplexity search query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "results_count": {"type": "integer", "description": "Number of results"},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "Sources used"}
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="get_session_history",
            description="Get conversation history for current session",
            inputSchema={
                "type": "object",
                "properties": {
                    "ai_system": {
                        "type": "string",
                        "enum": ["claude", "chatgpt", "manus", "perplexity", "all"],
                        "description": "Filter by AI system"
                    },
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                }
            }
        ),
        
        Tool(
            name="search_all_ai_history",
            description="Search across all AI system conversations",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "ai_systems": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by AI systems"
                    },
                    "limit": {"type": "integer", "description": "Max results", "default": 20}
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="export_session",
            description="Export current session data to file",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown", "csv"],
                        "description": "Export format"
                    },
                    "output_path": {"type": "string", "description": "Where to save the export"}
                },
                "required": ["format", "output_path"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool calls"""
    
    if name == "configure_tracking":
        return await configure_tracking(arguments)
    elif name == "get_tracking_status":
        return await get_tracking_status()
    elif name == "track_conversation":
        return await track_conversation(arguments)
    elif name == "track_file":
        return await track_file(arguments)
    elif name == "track_search":
        return await track_search(arguments)
    elif name == "get_session_history":
        return await get_session_history(arguments)
    elif name == "search_all_ai_history":
        return await search_all_ai_history(arguments)
    elif name == "export_session":
        return await export_session(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================

async def configure_tracking(args: dict) -> list[TextContent]:
    """Configure tracking settings"""
    global TRACK_CLAUDE, TRACK_CHATGPT, TRACK_MANUS, TRACK_PERPLEXITY
    global AUTO_TRACK_FILES, AUTO_TRACK_CHATS
    
    if "claude" in args:
        TRACK_CLAUDE = args["claude"]
    if "chatgpt" in args:
        TRACK_CHATGPT = args["chatgpt"]
    if "manus" in args:
        TRACK_MANUS = args["manus"]
    if "perplexity" in args:
        TRACK_PERPLEXITY = args["perplexity"]
    if "auto_track_files" in args:
        AUTO_TRACK_FILES = args["auto_track_files"]
    if "auto_track_chats" in args:
        AUTO_TRACK_CHATS = args["auto_track_chats"]
    
    status = await get_tracking_status()
    return [TextContent(
        type="text",
        text=f"✅ Tracking configuration updated\n\n{status[0].text}"
    )]


async def get_tracking_status() -> list[TextContent]:
    """Get current tracking status"""
    status = f"""
📊 DHG AI Tracker Status

Session ID: {SESSION_ID}
Registry URL: {REGISTRY_URL}
Onyx URL: {ONYX_URL}

AI System Tracking:
  Claude:      {'✅ Enabled' if TRACK_CLAUDE else '❌ Disabled'}
  ChatGPT:     {'✅ Enabled' if TRACK_CHATGPT else '❌ Disabled'}
  Manus:       {'✅ Enabled' if TRACK_MANUS else '❌ Disabled'}
  Perplexity:  {'✅ Enabled' if TRACK_PERPLEXITY else '❌ Disabled'}

Auto-Tracking:
  Files:       {'✅ Enabled' if AUTO_TRACK_FILES else '❌ Disabled'}
  Chats:       {'✅ Enabled' if AUTO_TRACK_CHATS else '❌ Disabled'}
"""
    return [TextContent(type="text", text=status)]


# =============================================================================
# TRACKING FUNCTIONS
# =============================================================================

async def track_conversation(args: dict) -> list[TextContent]:
    """Track a conversation"""
    ai_system = args["ai_system"]
    
    # Check if tracking is enabled for this AI system
    tracking_enabled = {
        "claude": TRACK_CLAUDE,
        "chatgpt": TRACK_CHATGPT,
        "manus": TRACK_MANUS,
        "perplexity": TRACK_PERPLEXITY
    }
    
    if not tracking_enabled.get(ai_system, False):
        return [TextContent(
            type="text",
            text=f"⚠️  Tracking disabled for {ai_system}. Use configure_tracking to enable."
        )]
    
    if not AUTO_TRACK_CHATS:
        return [TextContent(
            type="text",
            text=f"⚠️  Auto-tracking disabled. Use configure_tracking to enable."
        )]
    
    # Track to Central Registry
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/ai-conversations",
            json={
                "session_id": SESSION_ID,
                "ai_system": ai_system,
                "user_id": "swebber64",
                "user_message": args["user_message"],
                "ai_response": args["ai_response"],
                "timestamp": datetime.now().isoformat(),
                "metadata": args.get("metadata", {})
            }
        )
        
        if response.status_code == 201:
            result = response.json()
            return [TextContent(
                type="text",
                text=f"✅ Conversation tracked ({ai_system}). ID: {result.get('id')}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to track conversation: {response.text}"
            )]


async def track_file(args: dict) -> list[TextContent]:
    """Track a file creation"""
    ai_system = args["ai_system"]
    file_path = Path(args["file_path"])
    
    # Check if tracking is enabled
    tracking_enabled = {
        "claude": TRACK_CLAUDE,
        "chatgpt": TRACK_CHATGPT,
        "manus": TRACK_MANUS,
        "perplexity": TRACK_PERPLEXITY
    }
    
    if not tracking_enabled.get(ai_system, False):
        return [TextContent(
            type="text",
            text=f"⚠️  Tracking disabled for {ai_system}"
        )]
    
    if not AUTO_TRACK_FILES:
        return [TextContent(
            type="text",
            text=f"⚠️  Auto file tracking disabled"
        )]
    
    if not file_path.exists():
        return [TextContent(type="text", text=f"❌ File not found: {file_path}")]
    
    content = file_path.read_text()
    
    # Track to Registry
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/ai-files",
            json={
                "session_id": SESSION_ID,
                "ai_system": ai_system,
                "user_id": "swebber64",
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lstrip('.'),
                "file_size": len(content),
                "purpose": args.get("file_purpose", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        result_text = ""
        
        if response.status_code == 201:
            result_text = f"✅ File tracked ({ai_system}): {file_path.name}\n"
        else:
            result_text = f"❌ Failed to track file: {response.text}\n"
        
        # Also index in Onyx if requested
        if args.get("index_in_onyx", True) and file_path.suffix in ['.md', '.txt', '.py']:
            onyx_response = await client.post(
                f"{ONYX_URL}/api/documents",
                json={
                    "title": file_path.stem,
                    "content": content,
                    "metadata": {
                        "author": f"{ai_system}_ai",
                        "created_at": datetime.now().isoformat(),
                        "source": ai_system,
                        "session_id": SESSION_ID,
                        "file_type": file_path.suffix.lstrip('.')
                    }
                }
            )
            
            if onyx_response.status_code in [200, 201]:
                result_text += f"✅ Indexed in Onyx: {file_path.name}"
            else:
                result_text += f"⚠️  Failed to index in Onyx: {onyx_response.text}"
        
        return [TextContent(type="text", text=result_text)]


async def track_search(args: dict) -> list[TextContent]:
    """Track a Perplexity search"""
    if not TRACK_PERPLEXITY:
        return [TextContent(type="text", text="⚠️  Perplexity tracking disabled")]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REGISTRY_URL}/api/v1/ai-searches",
            json={
                "session_id": SESSION_ID,
                "ai_system": "perplexity",
                "user_id": "swebber64",
                "query": args["query"],
                "results_count": args.get("results_count", 0),
                "sources": args.get("sources", []),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if response.status_code == 201:
            return [TextContent(type="text", text=f"✅ Search tracked: {args['query']}")]
        else:
            return [TextContent(type="text", text=f"❌ Failed to track search: {response.text}")]


async def get_session_history(args: dict) -> list[TextContent]:
    """Get session history"""
    ai_system = args.get("ai_system", "all")
    limit = args.get("limit", 10)
    
    async with httpx.AsyncClient() as client:
        params = {"session_id": SESSION_ID, "limit": limit}
        if ai_system != "all":
            params["ai_system"] = ai_system
        
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/ai-conversations",
            params=params
        )
        
        if response.status_code == 200:
            conversations = response.json()
            
            if not conversations:
                return [TextContent(type="text", text="No conversations found in this session")]
            
            output = f"📜 Session History ({len(conversations)} conversations)\n\n"
            
            for conv in conversations:
                output += f"[{conv['ai_system'].upper()}] {conv['timestamp']}\n"
                output += f"User: {conv['user_message'][:100]}...\n"
                output += f"AI: {conv['ai_response'][:100]}...\n\n"
            
            return [TextContent(type="text", text=output)]
        else:
            return [TextContent(type="text", text=f"❌ Failed to get history: {response.text}")]


async def search_all_ai_history(args: dict) -> list[TextContent]:
    """Search across all AI conversations"""
    query = args["query"]
    ai_systems = args.get("ai_systems", ["claude", "chatgpt", "manus", "perplexity"])
    limit = args.get("limit", 20)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/ai-conversations/search",
            params={
                "query": query,
                "ai_systems": ",".join(ai_systems),
                "limit": limit
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            
            if not results:
                return [TextContent(type="text", text=f"No results found for: {query}")]
            
            output = f"🔍 Search Results for '{query}' ({len(results)} found)\n\n"
            
            for result in results:
                output += f"[{result['ai_system'].upper()}] {result['timestamp']}\n"
                output += f"User: {result['user_message'][:100]}...\n"
                output += f"AI: {result['ai_response'][:100]}...\n\n"
            
            return [TextContent(type="text", text=output)]
        else:
            return [TextContent(type="text", text=f"❌ Search failed: {response.text}")]


async def export_session(args: dict) -> list[TextContent]:
    """Export session data"""
    format_type = args["format"]
    output_path = Path(args["output_path"])
    
    # Get all session data
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/sessions/{SESSION_ID}/export",
            params={"format": format_type}
        )
        
        if response.status_code == 200:
            output_path.write_text(response.text)
            return [TextContent(
                type="text",
                text=f"✅ Session exported to: {output_path}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Export failed: {response.text}"
            )]


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


# =============================================================================
# NOTEBOOKLM INTEGRATION
# =============================================================================

# Add NotebookLM tracking toggle
TRACK_NOTEBOOKLM = os.getenv("TRACK_NOTEBOOKLM", "true").lower() == "true"

# Import NotebookLM integration
import sys
sys.path.insert(0, "/Users/swebber64/Desktop")
from notebooklm_integration import NotebookLMIntegration

notebooklm = NotebookLMIntegration()

# Add NotebookLM to list_tools (append to existing tools list)
# This would be added in the actual list_tools() function
