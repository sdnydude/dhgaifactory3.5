# DHG AI Factory - WebSocket Event Schema
**Version**: 1.0  
**Date**: November 30, 2025  
**Protocol**: WebSocket (RFC 6455)  
**Format**: JSON

---

## Connection Architecture

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│   React PWA     │ ◄─────────────────────────► │  FastAPI Server │
│   (Client)      │    wss://api.dhg.ai/ws     │  (Orchestrator) │
└─────────────────┘                             └────────┬────────┘
                                                         │
                                    ┌────────────────────┼────────────────────┐
                                    │                    │                    │
                              ┌─────▼─────┐       ┌──────▼──────┐      ┌──────▼──────┐
                              │  Research │       │ Medical LLM │      │     QA      │
                              │   Agent   │       │    Agent    │      │   Agent     │
                              └───────────┘       └─────────────┘      └─────────────┘
```

---

## Connection Lifecycle

### 1. Connection Handshake

**Client → Server**
```json
{
  "type": "connection.init",
  "payload": {
    "client_id": "uuid-v4",
    "token": "jwt-auth-token",
    "client_version": "1.0.0",
    "capabilities": ["streaming", "binary", "compression"]
  }
}
```

**Server → Client**
```json
{
  "type": "connection.ack",
  "payload": {
    "session_id": "sess_abc123",
    "server_version": "1.0.0",
    "heartbeat_interval": 30000,
    "agents_available": [
      "orchestrator",
      "research",
      "medical_llm",
      "curriculum",
      "outcomes",
      "competitor_intel",
      "qa_compliance"
    ]
  }
}
```

### 2. Heartbeat (Keep-Alive)

**Client → Server** (every 30s)
```json
{
  "type": "ping",
  "timestamp": "2025-11-30T10:00:00.000Z"
}
```

**Server → Client**
```json
{
  "type": "pong",
  "timestamp": "2025-11-30T10:00:00.005Z"
}
```

### 3. Disconnection

**Client → Server**
```json
{
  "type": "connection.terminate",
  "reason": "user_logout"
}
```

---

## Core Event Types

### Event Envelope Structure

All events follow this envelope structure:

```typescript
interface WebSocketEvent {
  // Event identification
  type: string;                    // Event type (namespaced)
  id: string;                      // Unique event ID (uuid-v4)
  timestamp: string;               // ISO 8601 timestamp
  
  // Context
  session_id: string;              // WebSocket session ID
  request_id?: string;             // Parent request ID (for tracking)
  correlation_id?: string;         // For request-response pairing
  
  // Payload
  payload: Record<string, any>;    // Event-specific data
  
  // Metadata
  meta?: {
    agent_id?: string;             // Source agent
    sequence?: number;             // Event sequence number
    retry_count?: number;          // Retry attempts
  };
}
```

---

## Request Events (Client → Server)

### `request.submit` - Submit CME Generation Request

```json
{
  "type": "request.submit",
  "id": "evt_001",
  "timestamp": "2025-11-30T10:00:00.000Z",
  "session_id": "sess_abc123",
  "payload": {
    "task_type": "needs_assessment",
    "topic": "Type 2 Diabetes Management in Primary Care",
    "compliance_mode": "cme",
    "target_audience": "Primary Care Physicians",
    "funder": "Novo Nordisk",
    "moore_levels": ["3a", "4"],
    "word_count_target": 1500,
    "reference_count": 12,
    "additional_context": {
      "therapeutic_area": "Endocrinology",
      "prior_content_ids": ["req_xyz789"]
    }
  }
}
```

**Server Acknowledgment**
```json
{
  "type": "request.accepted",
  "id": "evt_002",
  "timestamp": "2025-11-30T10:00:00.100Z",
  "correlation_id": "evt_001",
  "payload": {
    "request_id": "req_def456",
    "estimated_duration": 45000,
    "queue_position": 0
  }
}
```

### `request.cancel` - Cancel In-Progress Request

```json
{
  "type": "request.cancel",
  "id": "evt_010",
  "timestamp": "2025-11-30T10:01:00.000Z",
  "session_id": "sess_abc123",
  "payload": {
    "request_id": "req_def456",
    "reason": "user_cancelled"
  }
}
```

### `chat.message` - Send Chat Message to Orchestrator

```json
{
  "type": "chat.message",
  "id": "evt_020",
  "timestamp": "2025-11-30T10:02:00.000Z",
  "session_id": "sess_abc123",
  "payload": {
    "content": "Can you add more focus on SGLT2 inhibitors?",
    "request_id": "req_def456",
    "attachments": []
  }
}
```

---

## Agent Status Events (Server → Client)

### `agent.status` - Agent Status Change

```json
{
  "type": "agent.status",
  "id": "evt_100",
  "timestamp": "2025-11-30T10:00:05.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "agent_id": "research",
    "agent_name": "Research Agent",
    "status": "working",
    "previous_status": "idle",
    "task_description": "Querying PubMed for recent diabetes studies",
    "progress": {
      "current": 0,
      "total": 100,
      "unit": "percent"
    }
  },
  "meta": {
    "agent_id": "research",
    "sequence": 1
  }
}
```

**Status Values**
| Status | Description | Color (from Design Brief) |
|--------|-------------|---------------------------|
| `idle` | Agent ready, no active task | Gray (#9CA3AF) |
| `working` | Agent actively processing | Agent's primary color |
| `waiting` | Waiting for dependency | Amber (#D97706) |
| `complete` | Task finished successfully | Green (#059669) |
| `error` | Task failed | Red (#DC2626) |
| `cancelled` | Task was cancelled | Gray (#6B7280) |

### `agent.progress` - Progress Update

```json
{
  "type": "agent.progress",
  "id": "evt_101",
  "timestamp": "2025-11-30T10:00:10.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "agent_id": "research",
    "progress": {
      "current": 65,
      "total": 100,
      "unit": "percent"
    },
    "message": "Found 23 relevant articles, analyzing abstracts...",
    "details": {
      "articles_found": 23,
      "articles_analyzed": 15,
      "sources": ["PubMed", "Cochrane"]
    }
  }
}
```

### `agent.log` - Agent Log Entry

```json
{
  "type": "agent.log",
  "id": "evt_102",
  "timestamp": "2025-11-30T10:00:12.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "agent_id": "research",
    "level": "info",
    "message": "PubMed query returned 156 results, filtering by relevance",
    "data": {
      "query": "type 2 diabetes SGLT2 inhibitors 2024",
      "result_count": 156,
      "filtered_count": 23
    }
  }
}
```

**Log Levels**: `debug`, `info`, `warning`, `error`

---

## Content Generation Events (Server → Client)

### `content.chunk` - Streaming Content Chunk

```json
{
  "type": "content.chunk",
  "id": "evt_200",
  "timestamp": "2025-11-30T10:00:30.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "chunk_index": 0,
    "content": "## Educational Gap Analysis\n\nType 2 diabetes affects approximately 37 million Americans...",
    "section": "introduction",
    "is_final": false,
    "agent_id": "medical_llm"
  }
}
```

### `content.section.complete` - Section Completed

```json
{
  "type": "content.section.complete",
  "id": "evt_201",
  "timestamp": "2025-11-30T10:00:45.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "section": "introduction",
    "word_count": 245,
    "references_used": ["pmid:38123456", "pmid:38234567"],
    "validation_status": "pending"
  }
}
```

### `content.complete` - Full Content Generated

```json
{
  "type": "content.complete",
  "id": "evt_210",
  "timestamp": "2025-11-30T10:01:30.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "content_id": "cnt_ghi789",
    "title": "Needs Assessment: Type 2 Diabetes Management",
    "format": "markdown",
    "content": "# Full markdown content here...",
    "metadata": {
      "word_count": 1523,
      "reference_count": 12,
      "sections": ["introduction", "gap_analysis", "outcomes", "recommendations"],
      "generation_time_ms": 45230,
      "compliance_mode": "cme",
      "moore_levels_addressed": ["3a", "4"]
    }
  }
}
```

---

## Validation Events (Server → Client)

### `validation.started` - QA Validation Started

```json
{
  "type": "validation.started",
  "id": "evt_300",
  "timestamp": "2025-11-30T10:01:35.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "content_id": "cnt_ghi789",
    "checks": [
      "source_verification",
      "reference_validation",
      "word_count",
      "accme_compliance",
      "fair_balance",
      "hallucination_detection"
    ]
  }
}
```

### `validation.check.complete` - Individual Check Complete

```json
{
  "type": "validation.check.complete",
  "id": "evt_301",
  "timestamp": "2025-11-30T10:01:40.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "check": "reference_validation",
    "status": "passed",
    "details": {
      "total_references": 12,
      "verified": 12,
      "failed": 0,
      "warnings": 1
    },
    "message": "All references verified against source databases"
  }
}
```

### `validation.complete` - Full Validation Complete

```json
{
  "type": "validation.complete",
  "id": "evt_310",
  "timestamp": "2025-11-30T10:02:00.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "content_id": "cnt_ghi789",
    "overall_status": "passed",
    "checks": {
      "source_verification": { "status": "passed", "score": 100 },
      "reference_validation": { "status": "passed", "score": 100 },
      "word_count": { "status": "passed", "score": 100 },
      "accme_compliance": { "status": "passed", "score": 100 },
      "fair_balance": { "status": "passed", "score": 95 },
      "hallucination_detection": { "status": "passed", "score": 100 }
    },
    "violations": [],
    "warnings": [
      {
        "code": "SDOH_CONTEXT",
        "message": "Consider adding social determinants of health context",
        "severity": "low",
        "section": "gap_analysis"
      }
    ],
    "validation_time_ms": 25000
  }
}
```

---

## Chat Events (Server → Client)

### `chat.response` - Orchestrator Response

```json
{
  "type": "chat.response",
  "id": "evt_400",
  "timestamp": "2025-11-30T10:02:30.000Z",
  "session_id": "sess_abc123",
  "correlation_id": "evt_020",
  "payload": {
    "content": "I've noted your request to emphasize SGLT2 inhibitors. I'll instruct the Medical LLM agent to expand that section. Would you like me to also include recent cardiovascular outcome data?",
    "agent_id": "orchestrator",
    "suggestions": [
      "Add CV outcome data",
      "Include dosing guidelines",
      "Compare to GLP-1 agonists"
    ]
  }
}
```

### `chat.typing` - Agent Typing Indicator

```json
{
  "type": "chat.typing",
  "id": "evt_401",
  "timestamp": "2025-11-30T10:02:28.000Z",
  "session_id": "sess_abc123",
  "payload": {
    "agent_id": "orchestrator",
    "is_typing": true
  }
}
```

---

## Error Events

### `error` - Error Notification

```json
{
  "type": "error",
  "id": "evt_500",
  "timestamp": "2025-11-30T10:03:00.000Z",
  "session_id": "sess_abc123",
  "request_id": "req_def456",
  "payload": {
    "code": "AGENT_TIMEOUT",
    "message": "Research agent did not respond within timeout period",
    "severity": "error",
    "recoverable": true,
    "agent_id": "research",
    "details": {
      "timeout_ms": 30000,
      "last_status": "working"
    }
  }
}
```

**Error Codes**
| Code | Description | Recoverable |
|------|-------------|-------------|
| `AGENT_TIMEOUT` | Agent exceeded time limit | Yes |
| `AGENT_ERROR` | Agent threw exception | Yes |
| `VALIDATION_FAILED` | Content failed validation | Yes |
| `RATE_LIMIT` | API rate limit exceeded | Yes |
| `AUTH_EXPIRED` | JWT token expired | Yes |
| `INTERNAL_ERROR` | Server internal error | No |
| `SERVICE_UNAVAILABLE` | Backend service down | No |

---

## Request Lifecycle Summary

```
Client                          Server                          Agents
  │                               │                               │
  │──request.submit──────────────►│                               │
  │◄─────────request.accepted─────│                               │
  │                               │                               │
  │◄─────────agent.status─────────│◄──────dispatch────────────────│
  │                               │                      Research │
  │◄─────────agent.progress───────│◄──────progress────────────────│
  │◄─────────agent.log────────────│◄──────log─────────────────────│
  │◄─────────agent.status─────────│◄──────complete────────────────│
  │                               │                               │
  │◄─────────agent.status─────────│◄──────dispatch────────────────│
  │                               │                   Medical LLM │
  │◄─────────content.chunk────────│◄──────stream──────────────────│
  │◄─────────content.chunk────────│◄──────stream──────────────────│
  │◄─────────content.complete─────│◄──────complete────────────────│
  │                               │                               │
  │◄─────────validation.started───│◄──────dispatch────────────────│
  │                               │                            QA │
  │◄─────────validation.check─────│◄──────check───────────────────│
  │◄─────────validation.complete──│◄──────complete────────────────│
  │                               │                               │
```

---

## TypeScript Type Definitions

```typescript
// Base event types
type AgentId = 
  | 'orchestrator' 
  | 'research' 
  | 'medical_llm' 
  | 'curriculum' 
  | 'outcomes' 
  | 'competitor_intel' 
  | 'qa_compliance';

type AgentStatus = 'idle' | 'working' | 'waiting' | 'complete' | 'error' | 'cancelled';

type ComplianceMode = 'auto' | 'cme' | 'non_cme';

type MooreLevel = '1' | '2' | '3a' | '3b' | '4' | '5' | '6' | '7';

// Request payload
interface CMERequestPayload {
  task_type: 'needs_assessment' | 'curriculum' | 'competitor_analysis' | 'outcomes_analysis';
  topic: string;
  compliance_mode: ComplianceMode;
  target_audience: string;
  funder?: string;
  moore_levels?: MooreLevel[];
  word_count_target?: number;
  reference_count?: number;
  additional_context?: Record<string, any>;
}

// Agent status payload
interface AgentStatusPayload {
  agent_id: AgentId;
  agent_name: string;
  status: AgentStatus;
  previous_status?: AgentStatus;
  task_description?: string;
  progress?: {
    current: number;
    total: number;
    unit: 'percent' | 'items' | 'steps';
  };
}

// Validation result
interface ValidationResult {
  content_id: string;
  overall_status: 'passed' | 'failed' | 'warning';
  checks: Record<string, {
    status: 'passed' | 'failed' | 'warning';
    score: number;
  }>;
  violations: ValidationIssue[];
  warnings: ValidationIssue[];
  validation_time_ms: number;
}

interface ValidationIssue {
  code: string;
  message: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  section?: string;
  line?: number;
}
```

---

## Client Implementation Notes

### React Hook Example

```typescript
import { useEffect, useRef, useCallback } from 'react';

export function useAgentWebSocket(sessionId: string) {
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  
  const connect = useCallback(() => {
    ws.current = new WebSocket(`wss://api.dhg.ai/ws?session=${sessionId}`);
    
    ws.current.onopen = () => {
      reconnectAttempts.current = 0;
      // Send connection init
      ws.current?.send(JSON.stringify({
        type: 'connection.init',
        payload: { client_id: sessionId, token: getAuthToken() }
      }));
    };
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Dispatch to appropriate handler based on data.type
      handleEvent(data);
    };
    
    ws.current.onclose = () => {
      // Exponential backoff reconnection
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectAttempts.current++;
      setTimeout(connect, delay);
    };
  }, [sessionId]);
  
  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);
  
  return ws;
}
```

---

## Server Implementation Notes

### FastAPI WebSocket Endpoint

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    async def broadcast_to_session(self, session_id: str, event: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(event)
    
    async def broadcast_agent_status(
        self, 
        session_id: str, 
        request_id: str,
        agent_id: str, 
        status: str,
        **kwargs
    ):
        event = {
            "type": "agent.status",
            "id": generate_event_id(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "request_id": request_id,
            "payload": {
                "agent_id": agent_id,
                "status": status,
                **kwargs
            }
        }
        await self.broadcast_to_session(session_id, event)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session: str):
    await manager.connect(websocket, session)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_event(session, data)
    except WebSocketDisconnect:
        del manager.active_connections[session]
```

---

**Next**: See `react-components.tsx` for UI implementation using this schema.
