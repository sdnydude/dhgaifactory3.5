# Multi-Provider BYOK Integration Plan

**Created:** Jan 25, 2026  
**Approach:** BYOK-only (no platform-paid tier for v1)

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                    User Account                   │
├──────────────────────────────────────────────────┤
│  Settings → Integrations                         │
│  ┌────────────────────────────────────────────┐  │
│  │ [+] Add Provider                           │  │
│  │                                            │  │
│  │ Claude      [API Key: ****] ✅ Active      │  │
│  │ ChatGPT     [API Key: ****] ✅ Active      │  │
│  │ Gemini      [Not configured]               │  │
│  │ Perplexity  [API Key: ****] ✅ Active      │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│              Infisical Vault                      │
│  - Encrypted key storage                          │
│  - Per-user isolation                             │
│  - Never exposed to frontend                      │
└──────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│              MCP Server (per provider)            │
│  - Fetches key from Infisical at runtime          │
│  - Proxies requests to provider API               │
│  - Logs usage for analytics                       │
└──────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Integration providers (admin configures)
CREATE TABLE integration_providers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    api_base_url VARCHAR(500),
    auth_type VARCHAR(50) DEFAULT 'api_key',
    is_admin_only BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB
);

-- User integrations (user configures)
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider_id VARCHAR(50) REFERENCES integration_providers(id),
    infisical_secret_path VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    UNIQUE(user_id, provider_id)
);

-- Usage tracking
CREATE TABLE integration_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider_id VARCHAR(50),
    request_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    period_start DATE,
    period_end DATE
);
```

---

## Supported Providers (v1)

### LLMs
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| Claude | `claude` | No |
| ChatGPT | `chatgpt` | No |
| Gemini | `gemini` | No |
| Google AI Studio | `google_ai_studio` | No |
| Llama (local) | `llama` | No |
| Mistral | `mistral` | No |
| Groq | `groq` | No |

### Code & Dev Tools
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| GitHub Copilot | `github_copilot` | No |
| Cursor | `cursor` | No |
| Replit | `replit` | No |
| Vercel | `vercel` | No |

### Search & RAG
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| Perplexity | `perplexity` | No |
| Tavily | `tavily` | No |
| Exa | `exa` | No |

### Media & Audio
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| Whisper (local) | `whisper` | No |
| ElevenLabs | `elevenlabs` | No |
| Descript | `descript` | No |

### Platform Tools
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| LangSmith | `langsmith` | No |
| LibreChat (local) | `librechat` | No |
| **Antigravity** | `antigravity` | **Yes** |
| Manus | `manus` | No |

### Medical/CME (One Product Line)
| Provider | ID | Admin Only? |
|----------|-----|-------------|
| PubMed API | `pubmed` | No |
| NCBI | `ncbi` | No |
| ClinicalTrials.gov | `clinicaltrials` | No |

---

## User Flow

1. User goes to Settings → Integrations
2. Clicks "Add Provider" → selects Claude
3. Enters API key → key stored in Infisical under `/users/{user_id}/claude`
4. System validates key with test request
5. Integration marked active
6. User can now use Claude via platform

---

## Security

- API keys never stored in database (only Infisical path reference)
- Keys fetched at runtime, never cached in memory beyond request
- Per-user namespace isolation in Infisical
- Admin audit log for all key operations

---

## Build Order

1. [ ] Create `integration_providers` table
2. [ ] Create `user_integrations` table  
3. [ ] Create `integration_usage` table
4. [ ] Build Infisical user namespace structure
5. [ ] Create MCP server template for BYOK
6. [ ] Build Settings → Integrations UI
7. [ ] Implement Claude MCP server
8. [ ] Implement ChatGPT MCP server
9. [ ] Implement remaining providers
