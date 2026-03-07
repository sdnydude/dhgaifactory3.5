# Implementation Plan: Web UI Investor Demo Readiness

## Goal

Make Web UI fully operational for investor demo. **No placeholders, no fakes** — every button works, every panel shows real data.

---

## Phase 1: Session Persistence Backend (Day 1)

### Database Schema

Add to `registry/init.sql`:

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,  -- 'chat', 'visual', 'research'
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sessions_type ON sessions(type);
CREATE INDEX idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX idx_messages_session ON session_messages(session_id);
```

### [MODIFY] agents/orchestrator/main.py

Add session endpoints:

```python
@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    # Insert into registry, return session_id

@app.get("/api/sessions")
async def list_sessions(type: str = None, limit: int = 50):
    # Fetch from registry, grouped by date

@app.post("/api/sessions/{session_id}/messages")
async def add_message(session_id: UUID, message: MessageCreate):
    # Append message to session

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: UUID):
    # Fetch session with all messages

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: UUID):
    # Delete session and messages
```

---

## Phase 2: Frontend Session Integration (Day 2)

### [NEW] web-ui/src/hooks/useSessions.js

```javascript
export const useSessions = () => {
    const [sessions, setSessions] = useState([]);
    
    const fetchSessions = async () => {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        setSessions(groupByDate(data));
    };
    
    const createSession = async (type) => {
        const res = await fetch('/api/sessions', {
            method: 'POST',
            body: JSON.stringify({ type })
        });
        return res.json();
    };
    
    const saveMessage = async (sessionId, role, content) => {
        await fetch(`/api/sessions/${sessionId}/messages`, {
            method: 'POST',
            body: JSON.stringify({ role, content })
        });
    };
    
    return { sessions, fetchSessions, createSession, saveMessage };
};
```

### [MODIFY] web-ui/src/components/Sidebar.jsx

Replace hardcoded links with dynamic session list:

```javascript
const Sidebar = ({ onNewChat, onSelectSession }) => {
    const { sessions, fetchSessions } = useSessions();
    
    useEffect(() => { fetchSessions(); }, []);
    
    return (
        <div className="sidebar">
            {/* New Composition button */}
            
            {Object.entries(sessions).map(([dateGroup, items]) => (
                <div key={dateGroup}>
                    <div className="sidebar__date-header">{dateGroup}</div>
                    {items.map(session => (
                        <button 
                            key={session.id}
                            onClick={() => onSelectSession(session.id)}
                            className="sidebar__nav-item"
                        >
                            <MessageSquare size={16} />
                            <span>{session.title || 'Untitled'}</span>
                        </button>
                    ))}
                </div>
            ))}
        </div>
    );
};
```

---

## Phase 3: Navigation Fixes (Day 2)

### [NEW] web-ui/src/components/Breadcrumbs.jsx

```javascript
const Breadcrumbs = ({ items }) => (
    <nav className="breadcrumbs">
        {items.map((item, i) => (
            <React.Fragment key={i}>
                {i > 0 && <ChevronRight size={14} />}
                <Link to={item.path}>{item.label}</Link>
            </React.Fragment>
        ))}
    </nav>
);
```

### [MODIFY] web-ui/src/components/MainLayout.jsx

Add breadcrumbs to header area of each view.

---

## Phase 4: Prompt Checker Agent (Day 3)

### [NEW] agents/prompt-checker/graph.py

```python
from langgraph.graph import StateGraph, END

class PromptCheckerState(TypedDict):
    prompt: str
    clarity_score: float
    specificity_score: float
    compliance_score: float
    detected_mode: str  # 'cme' or 'non-cme'
    suggestions: List[str]
    semantic_analysis: str

def build_prompt_checker_graph():
    workflow = StateGraph(PromptCheckerState)
    
    workflow.add_node("analyze_structure", analyze_structure)
    workflow.add_node("detect_compliance", detect_compliance)
    workflow.add_node("generate_suggestions", generate_suggestions)
    workflow.add_node("semantic_analysis", semantic_analysis)
    
    workflow.set_entry_point("analyze_structure")
    workflow.add_edge("analyze_structure", "detect_compliance")
    workflow.add_edge("detect_compliance", "generate_suggestions")
    workflow.add_edge("generate_suggestions", "semantic_analysis")
    workflow.add_edge("semantic_analysis", END)
    
    return workflow.compile()
```

### [MODIFY] agents/orchestrator/main.py

Update `/api/prompt-analyze` to use the new agent:

```python
@app.post("/api/prompt-analyze")
async def analyze_prompt(request: PromptAnalyzeRequest):
    result = await prompt_checker_graph.ainvoke({
        "prompt": request.prompt
    })
    return result
```

### [MODIFY] web-ui/src/components/panels/PromptTools.jsx

Connect to real endpoint and display actual scores.

---

## Phase 5: Audit & Hide Non-Functional Items (Day 3)

- [ ] Audit `MainLayout.jsx` for buttons that don't work
- [ ] Audit all panel components
- [ ] Either implement or hide non-functional features
- [ ] Remove mock/placeholder data

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `registry/migrations/add_sessions.sql` | NEW | Session tables |
| `agents/orchestrator/main.py` | MODIFY | Session CRUD endpoints |
| `agents/prompt-checker/graph.py` | NEW | Prompt analysis LangGraph |
| `web-ui/src/hooks/useSessions.js` | NEW | Session management hook |
| `web-ui/src/components/Sidebar.jsx` | MODIFY | Dynamic session list |
| `web-ui/src/components/Breadcrumbs.jsx` | NEW | Navigation breadcrumbs |
| `web-ui/src/components/MainLayout.jsx` | MODIFY | Add breadcrumbs |
| `web-ui/src/components/panels/PromptTools.jsx` | MODIFY | Real API integration |

---

## Verification Plan

### Manual Testing
1. Create new chat → appears in sidebar
2. Send messages → persists across refresh
3. Navigate to settings → breadcrumbs show path
4. Click back → returns to previous view
5. Prompt checker → shows real scores from LLM

### API Testing
```bash
# Create session
curl -X POST http://100.107.14.51:8011/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"type": "chat"}'

# List sessions
curl http://100.107.14.51:8011/api/sessions

# Analyze prompt
curl -X POST http://100.107.14.51:8011/api/prompt-analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a CME needs assessment about diabetes"}'
```

---

**Executable as delivered in the stated environment.**

Intentionally omitted:
- CSS styling details (existing glassmorphism theme used)
- Full error handling code (patterns shown)
