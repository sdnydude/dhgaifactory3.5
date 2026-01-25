# LangGraph Visualization Guide
# Advanced layout and styling options for CME Research Agent

## 1. LAYOUT DIRECTIONS

### Vertical (Top to Bottom) - DEFAULT
```python
graph_config = {"rankdir": "TB"}
```
Result: START at top, END at bottom

### Horizontal (Left to Right)
```python
graph_config = {"rankdir": "LR"}
```
Result: START at left, END at right

### Bottom to Top
```python
graph_config = {"rankdir": "BT"}
```

### Right to Left
```python
graph_config = {"rankdir": "RL"}
```

---

## 2. NODE STYLING

### Colors by Phase
```python
metadata = {
    "color": "#4A90E2",  # Blue for data collection
    "fill": "#E8F4F8",   # Light blue background
    "stroke": "#2E86DE", # Darker blue border
    "stroke-width": "2px"
}
```

### Icons and Emojis
```python
metadata = {
    "icon": "📚",  # PubMed
    "icon": "🔍",  # Search
    "icon": "⭐",  # Quality
    "icon": "🎯",  # Gaps
    "icon": "🧬",  # Synthesis
}
```

### Size Variations
```python
metadata = {
    "width": "200px",   # Wider for important nodes
    "height": "100px",  # Taller for complex nodes
    "shape": "rectangle" | "circle" | "diamond" | "hexagon"
}
```

---

## 3. EDGE STYLING

### Conditional Edges (Dashed)
```python
workflow.add_conditional_edges(
    "route",
    route_function,
    {
        "path_a": "node_a",
        "path_b": "node_b"
    },
    edge_data={"style": "dashed", "label": "condition"}
)
```

### Weighted Edges (Thickness)
```python
workflow.add_edge("node_a", "node_b", edge_data={
    "weight": 3,  # Thicker line
    "label": "High Priority",
    "color": "#E74C3C"
})
```

### Labeled Edges
```python
workflow.add_edge("search", "analyze", edge_data={
    "label": "Results: 50 papers",
    "tooltip": "Passing 50 research papers to analysis"
})
```

---

## 4. GROUPING & SWIMLANES

### Group by Phase
```python
workflow.add_node("pubmed", search_pubmed, metadata={
    "group": "data_collection",
    "swimlane": "Literature Search"
})

workflow.add_node("perplexity", search_perplexity, metadata={
    "group": "data_collection",
    "swimlane": "Current Practice"
})
```

### Subgraphs (Nested)
```python
# Create subgraph
data_collection = StateGraph(ResearchState)
data_collection.add_node("pubmed", search_pubmed)
data_collection.add_node("perplexity", search_perplexity)

# Add to main graph
workflow.add_node("collect_data", data_collection.compile(), metadata={
    "expandable": True,
    "collapsed_label": "Data Collection (3 sources)"
})
```

---

## 5. PARALLEL EXECUTION VISUALIZATION

### Fan-Out Pattern
```python
# One node triggers multiple parallel nodes
workflow.add_edge("trigger", "parallel_1")
workflow.add_edge("trigger", "parallel_2")
workflow.add_edge("trigger", "parallel_3")

# Visualizes as:
#        ┌─→ parallel_1 ─┐
# trigger├─→ parallel_2 ─┤→ next
#        └─→ parallel_3 ─┘
```

### Fan-In Pattern
```python
# Multiple nodes converge to one
workflow.add_edge("parallel_1", "converge")
workflow.add_edge("parallel_2", "converge")
workflow.add_edge("parallel_3", "converge")

# Visualizes as:
# parallel_1 ─┐
# parallel_2 ─┤→ converge
# parallel_3 ─┘
```

---

## 6. DECISION POINTS

### Diamond Shapes for Routing
```python
workflow.add_node("route", route_function, metadata={
    "shape": "diamond",
    "description": "Route based on query type",
    "decision_point": True
})
```

### Multiple Outcomes
```python
workflow.add_conditional_edges(
    "quality_check",
    lambda s: "pass" if s["quality"] > 0.8 else "fail",
    {
        "pass": "continue",
        "fail": "retry"
    }
)
```

---

## 7. PROGRESS INDICATORS

### Phase Labels
```python
metadata = {
    "phase": "1. Data Collection",
    "progress": "33%",
    "estimated_time": "5-10s"
}
```

### Status Colors
```python
# Not started: Gray
# In progress: Blue
# Complete: Green
# Error: Red
metadata = {
    "status_color": {
        "pending": "#95A5A6",
        "running": "#3498DB",
        "complete": "#27AE60",
        "error": "#E74C3C"
    }
}
```

---

## 8. TOOLTIPS & DESCRIPTIONS

### Rich Metadata
```python
metadata = {
    "description": "Search PubMed for peer-reviewed literature",
    "tooltip": "Searches last 36 months by default\nFilters by evidence level\nReturns up to 50 results",
    "documentation_url": "https://docs.example.com/pubmed-search",
    "estimated_cost": "$0.02 per search"
}
```

---

## 9. CUSTOM MERMAID STYLING

### Full Custom Mermaid
```python
custom_mermaid = '''
graph LR
    classDef dataCollection fill:#4A90E2,stroke:#2E86DE,color:#fff
    classDef analysis fill:#9013FE,stroke:#6C3FB5,color:#fff
    classDef output fill:#27AE60,stroke:#1E8449,color:#fff
    
    START([Start]):::first
    PUBMED[📚 PubMed]:::dataCollection
    GRADE[⭐ Grade]:::analysis
    OUTPUT[📄 Output]:::output
    END([End]):::last
    
    START --> PUBMED
    PUBMED --> GRADE
    GRADE --> OUTPUT
    OUTPUT --> END
'''
```

---

## 10. LANGSMITH STUDIO FEATURES

### Interactive Elements
- Click nodes to see execution details
- Hover for tooltips
- Expand/collapse subgraphs
- Filter by phase/status
- Timeline view of execution

### Real-Time Updates
- Nodes highlight as they execute
- Progress bars show completion
- Error nodes turn red
- Execution path is traced

---

## RECOMMENDED LAYOUT FOR CME RESEARCH AGENT

```python
# Horizontal layout with swimlanes
graph_config = {
    "rankdir": "LR",  # Left to right
    "ranksep": "1.5",  # More space between ranks
    "nodesep": "1.0",  # More space between nodes
    "splines": "ortho"  # Orthogonal edges (right angles)
}

# Color scheme by phase
COLORS = {
    "initialization": "#3498DB",  # Blue
    "data_collection": "#1ABC9C",  # Teal
    "analysis": "#9B59B6",  # Purple
    "synthesis": "#E67E22",  # Orange
    "output": "#27AE60"  # Green
}

# Icons by function
ICONS = {
    "search": "🔍",
    "database": "📚",
    "analysis": "⭐",
    "synthesis": "🧬",
    "output": "📄",
    "decision": "🔀",
    "error": "❌",
    "success": "✅"
}
```

---

## EXAMPLE: COMPLETE STYLED GRAPH

See `enhanced_agent_graph.py` for full implementation with:
- ✅ Horizontal layout
- ✅ Color-coded phases
- ✅ Icons for each node
- ✅ Parallel execution paths
- ✅ Conditional routing
- ✅ Rich metadata
- ✅ Progress indicators
- ✅ Estimated times
- ✅ Tooltips

---

## VIEWING IN LANGSMITH STUDIO

1. Deploy agent to LangSmith Cloud
2. Open Studio: https://smith.langchain.com/studio/?baseUrl=http://10.0.0.251:2026
3. Click "Graph" tab
4. Interactive visualization with all metadata
5. Click nodes to see:
   - Description
   - Execution time
   - Input/output
   - Errors (if any)
   - Configuration

---

## NEXT STEPS

1. Update `src/agent.py` with enhanced graph
2. Add metadata to all nodes
3. Configure layout direction
4. Test in Studio
5. Iterate on visualization based on feedback
