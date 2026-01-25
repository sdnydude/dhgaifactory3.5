# LangSmith MCP Server

**Give Claude direct access to LangSmith Cloud for observability, debugging, and evaluation.**

## Features

| Tool | Description |
|------|-------------|
| `langsmith_list_projects` | List all projects |
| `langsmith_list_runs` | List runs with filters (type, errors, time) |
| `langsmith_get_run` | Get full run details (inputs/outputs) |
| `langsmith_get_run_trace` | Get complete trace tree |
| `langsmith_project_stats` | Project statistics (costs, latency, errors) |
| `langsmith_submit_feedback` | Submit quality feedback |
| `langsmith_list_datasets` | List evaluation datasets |
| `langsmith_get_dataset` | Get dataset with examples |
| `langsmith_create_dataset` | Create new dataset |
| `langsmith_add_example` | Add example to dataset |
| `langsmith_search_runs` | Search runs by content |
| `langsmith_compare_runs` | Compare two runs side-by-side |

---

## Installation

### Option A: Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "langsmith": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/langsmith-mcp-server",
      "env": {
        "LANGCHAIN_API_KEY": "lsv2_pt_your-key-here"
      }
    }
  }
}
```

### Option B: Install as Package

```bash
cd langsmith-mcp-server
pip install -e .

# Then in Claude Desktop config:
{
  "mcpServers": {
    "langsmith": {
      "command": "langsmith-mcp",
      "env": {
        "LANGCHAIN_API_KEY": "lsv2_pt_your-key-here"
      }
    }
  }
}
```

### Option C: Docker

```bash
docker build -t langsmith-mcp .
docker run -e LANGCHAIN_API_KEY=lsv2_pt_xxx langsmith-mcp
```

---

## Usage Examples

Once connected, ask Claude:

**Project Overview:**
> "Show me stats for my dhg-cme-research-agent project from the last 7 days"

**Debug Errors:**
> "List runs with errors in dhg-cme-research-agent from the last 24 hours"

**Analyze Run:**
> "Get the full trace for run abc-123 and explain what went wrong"

**Compare Performance:**
> "Compare runs xyz-1 and xyz-2 - which was more efficient?"

**Submit Feedback:**
> "Give run abc-123 a quality score of 0.9 with comment 'Excellent synthesis'"

**Build Datasets:**
> "Create a dataset called 'cme-gap-analysis-eval' and add 3 examples from today's successful runs"

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGCHAIN_API_KEY` | Yes | LangSmith API key |
| `LANGCHAIN_ENDPOINT` | No | Custom endpoint (default: api.smith.langchain.com) |

---

## Example Conversation

```
You: Show me the stats for dhg-cme-research-agent

Claude: [calls langsmith_project_stats]

Here's the summary for dhg-cme-research-agent over the last 7 days:

- **Total Runs:** 47
- **Error Rate:** 4.3% (2 errors)
- **Total Tokens:** 284,521
- **Total Cost:** $1.84
- **Avg Latency:** 3,240ms
- **P95 Latency:** 8,120ms

Run breakdown:
- chain: 28
- retriever: 12
- llm: 7

The 2 errors were both in perplexity_search runs. Want me to get the details?
```

---

## License

MIT - Digital Harmony Group
