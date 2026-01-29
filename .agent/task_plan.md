# Task Plan: DHG AI Factory - Front-Facing Agent Completion

## Goal
Complete two fully operational, front-facing agents (CME Research and Visuals) integrated with LibreChat, RAGFlow, and LangSmith.

## Current Phase
Phase 1

## Phases

### Phase 1: CME Research Agent Completion
- [ ] Verify research agent at :8003 is functional
- [ ] Integrate with RAGFlow for medical literature retrieval
- [ ] Create LibreChat form integration for structured input
- [ ] Implement output templates (CME Proposal, Gap Report, Podcast Script)
- [ ] Test end-to-end in LibreChat
- **Status:** in_progress

### Phase 2: Visuals Agent with Control Panel
- [ ] Verify visuals agent is functional
- [ ] Create control panel (Streamlit or LibreChat Artifacts)
- [ ] Integrate with LibreChat
- [ ] Add gallery for generated images
- [ ] Test end-to-end
- **Status:** pending

### Phase 3: RAGFlow Knowledge Base Setup
- [ ] Configure RAGFlow with LLM connection
- [ ] Create knowledge bases (PubMed, CME docs, brand guidelines)
- [ ] Test retrieval quality
- [ ] Document API integration
- **Status:** pending

### Phase 4: LangSmith Tracing & Verification
- [ ] Verify traces appear in LangSmith Cloud
- [ ] Create dashboards for agent monitoring
- [ ] Document query patterns
- **Status:** pending

### Phase 5: Production Hardening
- [ ] Add error handling and logging
- [ ] Performance optimization
- [ ] Security review
- [ ] Documentation
- **Status:** pending

## Key Questions
1. What LLM should RAGFlow use for retrieval? (Qwen3:14b local or OpenAI API?)
2. Streamlit control panel or LibreChat Artifacts for Visuals?
3. What content to index first in RAGFlow?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| planning-with-files pattern | Prevents context loss across sessions |
| CME Research first | Higher business value, existing infrastructure |
| Server-first (.251) | User preference, GPU resources |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Context loss | ongoing | Implemented planning-with-files pattern |

## Notes
- Read /pre-response before every response
- Query CR database for lost context
- Update this file after each phase milestone
