# Antigravity MCP Server Setup Guide

## What This Enables

The Antigravity MCP Server allows **any MCP-compatible AI system** (Claude Desktop, ChatGPT, etc.) to:

1. ✅ Track Antigravity conversations to Central Registry
2. ✅ Track files created by Antigravity
3. ✅ Index documents in Onyx knowledge base
4. ✅ Search previous Antigravity sessions
5. ✅ Get session summaries

---

## Installation

### 1. Install Dependencies

```bash
pip install mcp httpx
```

### 2. Configure MCP Server

Add to your MCP configuration file (`~/.gemini/antigravity/mcp_config.json` or Claude Desktop config):

```json
{
  "mcpServers": {
    "antigravity-tracker": {
      "command": "python3",
      "args": ["/Users/swebber64/Desktop/antigravity_mcp_server.py"],
      "env": {
        "REGISTRY_URL": "http://10.0.0.251:8500",
        "ONYX_URL": "http://onyx-url"
      }
    }
  }
}
```

### 3. Start the Server

The server will start automatically when you use an MCP-compatible AI client.

---

## Available Tools

### 1. `track_chat_message`

Track an Antigravity conversation to Central Registry.

**Parameters:**
- `user_message` (string, required): The user's message
- `assistant_response` (string, required): The assistant's response
- `session_id` (string, required): Session identifier
- `metadata` (object, optional): Additional metadata

**Example:**
```json
{
  "user_message": "Create a LangGraph workflow",
  "assistant_response": "Here's a complete workflow...",
  "session_id": "2026-01-24-session",
  "metadata": {
    "tokens": 1234,
    "cost": 0.01
  }
}
```

---

### 2. `track_file_creation`

Track a file created by Antigravity.

**Parameters:**
- `file_path` (string, required): Path to the file
- `session_id` (string, required): Session identifier
- `file_purpose` (string, optional): Purpose of the file

**Example:**
```json
{
  "file_path": "/Users/swebber64/Desktop/agent.py",
  "session_id": "2026-01-24-session",
  "file_purpose": "agent_code"
}
```

---

### 3. `index_document_in_onyx`

Index a document in Onyx knowledge base.

**Parameters:**
- `file_path` (string, required): Path to the document
- `title` (string, required): Document title
- `tags` (array, optional): Tags for categorization

**Example:**
```json
{
  "file_path": "/Users/swebber64/Desktop/architecture.md",
  "title": "DHG AI Factory Architecture",
  "tags": ["architecture", "langsmith", "multi-agent"]
}
```

---

### 4. `get_session_summary`

Get summary of an Antigravity session.

**Parameters:**
- `session_id` (string, required): Session identifier

**Example:**
```json
{
  "session_id": "2026-01-24-session"
}
```

---

### 5. `search_antigravity_history`

Search previous Antigravity conversations.

**Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Max results (default: 10)

**Example:**
```json
{
  "query": "LangSmith architecture",
  "limit": 5
}
```

---

## Usage Examples

### In Claude Desktop

Once configured, you can use these tools in conversation:

```
You: Track this conversation to the registry

Claude: I'll use the track_chat_message tool to save our conversation.
[Uses tool: track_chat_message]
✅ Chat message tracked successfully. ID: chat_123
```

### In Custom AI Application

```python
from mcp import ClientSession

async with ClientSession() as session:
    # Connect to Antigravity MCP server
    await session.initialize()
    
    # Track a chat message
    result = await session.call_tool(
        "track_chat_message",
        {
            "user_message": "Create a workflow",
            "assistant_response": "Here's the workflow...",
            "session_id": "my-session"
        }
    )
    
    print(result)  # ✅ Chat message tracked successfully
```

---

## Automatic Tracking

### Option 1: Post-Session Hook

Add a hook that runs after each Antigravity session:

```python
# In Antigravity configuration
{
  "hooks": {
    "on_session_end": "python3 /path/to/sync_session.py"
  }
}
```

### Option 2: Real-Time Tracking

Modify Antigravity to call MCP tools in real-time:

```python
# In Antigravity code (hypothetical)
async def on_message_sent(user_msg, assistant_msg):
    await mcp_client.call_tool(
        "track_chat_message",
        {
            "user_message": user_msg,
            "assistant_response": assistant_msg,
            "session_id": current_session_id
        }
    )
```

---

## Integration with DHG AI Factory

### Workflow

```
1. User chats with Antigravity
   ↓
2. Antigravity creates files/documents
   ↓
3. MCP Server tracks to Central Registry
   ↓
4. MCP Server indexes in Onyx
   ↓
5. Other agents can search/reference this knowledge
```

### Benefits

- **Complete History**: All Antigravity sessions tracked
- **Knowledge Base**: All documents indexed and searchable
- **Cross-Agent Learning**: Other agents can learn from Antigravity sessions
- **Analytics**: Track usage, costs, patterns
- **Compliance**: Audit trail of all AI interactions

---

## Testing

### Test the Server

```bash
# Start the server manually
python3 /Users/swebber64/Desktop/antigravity_mcp_server.py

# In another terminal, send a test request
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | python3 antigravity_mcp_server.py
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python3 /Users/swebber64/Desktop/antigravity_mcp_server.py
```

---

## Troubleshooting

### Server Not Starting

Check logs:
```bash
tail -f ~/.mcp/logs/antigravity-tracker.log
```

### Tools Not Appearing

Verify configuration:
```bash
cat ~/.gemini/antigravity/mcp_config.json
```

### Connection Errors

Check Registry is running:
```bash
curl http://10.0.0.251:8500/api/v1/health
```

---

## Next Steps

1. ✅ Install and configure MCP server
2. ✅ Test with a simple chat tracking
3. ✅ Set up automatic file tracking
4. ✅ Index existing documentation in Onyx
5. ✅ Integrate with other DHG AI Factory agents

---

## Advanced: Custom Tools

You can extend the MCP server with custom tools:

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools ...
        
        Tool(
            name="analyze_session_patterns",
            description="Analyze patterns in Antigravity sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_range": {"type": "string"},
                    "user_id": {"type": "string"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "analyze_session_patterns":
        return await analyze_patterns(arguments)
    # ... handle other tools ...
```

---

**This MCP server gives you a standardized way to track and manage all Antigravity interactions!**
