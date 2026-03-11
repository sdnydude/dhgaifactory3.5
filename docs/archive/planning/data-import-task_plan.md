# Data Import Pipeline: ChatGPT, Claude AI, Google Workspace → CR

**Goal:** Centralize all AI conversation data and Google Workspace content in CR database

**Status:** Planning

---

## Phase 1: Research Export Formats
### 1.1 ChatGPT Export
- [ ] Export data from ChatGPT (Settings → Data Controls → Export) <!-- id: 1 -->
- [ ] Analyze export ZIP structure <!-- id: 2 -->
- [ ] Document conversations.json schema <!-- id: 3 -->
- [ ] Identify message format, timestamps, metadata <!-- id: 4 -->

### 1.2 Claude AI Export
- [ ] Export data from Claude (if available via API or export) <!-- id: 5 -->
- [ ] Analyze export format (JSON/ZIP) <!-- id: 6 -->
- [ ] Document conversation schema <!-- id: 7 -->
- [ ] Identify message format, timestamps, metadata <!-- id: 8 -->

### 1.3 Google Workspace
- [ ] Identify target data: Gmail, Docs, Drive, Calendar? <!-- id: 9 -->
- [ ] Research Google Workspace Admin SDK vs individual APIs <!-- id: 10 -->
- [ ] Document authentication requirements (OAuth, Service Account) <!-- id: 11 -->
- [ ] Identify rate limits and quotas <!-- id: 12 -->

---

## Phase 2: Database Schema Design
### 2.1 Unified Conversation Schema
- [ ] Design `ai_conversations` table (source, title, created_at, metadata) <!-- id: 13 -->
- [ ] Design `ai_messages` table (conversation_id, role, content, timestamp) <!-- id: 14 -->
- [ ] Add vector embedding column for RAG <!-- id: 15 -->
- [ ] Create indexes for search and filtering <!-- id: 16 -->

### 2.2 Google Workspace Schema
- [ ] Design `gws_emails` table (subject, from, to, body, date) <!-- id: 17 -->
- [ ] Design `gws_documents` table (title, content, last_modified) <!-- id: 18 -->
- [ ] Design `gws_calendar` table (event_title, start, end, attendees) <!-- id: 19 -->
- [ ] Add embedding columns for RAG <!-- id: 20 -->

### 2.3 Migration
- [ ] Create Alembic migration for new tables <!-- id: 21 -->
- [ ] Run migration on CR database <!-- id: 22 -->

---

## Phase 3: ChatGPT Import Script
- [ ] Create `scripts/import_chatgpt.py` <!-- id: 23 -->
- [ ] Parse ZIP file and extract conversations.json <!-- id: 24 -->
- [ ] Map ChatGPT format to unified schema <!-- id: 25 -->
- [ ] Handle duplicates (upsert by conversation_id) <!-- id: 26 -->
- [ ] Generate embeddings for messages <!-- id: 27 -->
- [ ] Add CLI with progress bar <!-- id: 28 -->

---

## Phase 4: Claude AI Import Script
- [ ] Create `scripts/import_claude.py` <!-- id: 29 -->
- [ ] Parse export format <!-- id: 30 -->
- [ ] Map Claude format to unified schema <!-- id: 31 -->
- [ ] Handle duplicates <!-- id: 32 -->
- [ ] Generate embeddings <!-- id: 33 -->
- [ ] Add CLI with progress bar <!-- id: 34 -->

---

## Phase 5: Google Workspace Integration
### 5.1 Authentication Setup
- [ ] Create Google Cloud project (or use existing) <!-- id: 35 -->
- [ ] Enable required APIs (Gmail, Drive, Docs, Calendar) <!-- id: 36 -->
- [ ] Create OAuth credentials or Service Account <!-- id: 37 -->
- [ ] Store credentials securely in Infisical <!-- id: 38 -->

### 5.2 Gmail Sync
- [ ] Create `scripts/sync_gmail.py` <!-- id: 39 -->
- [ ] Implement OAuth flow or service account auth <!-- id: 40 -->
- [ ] Fetch emails with pagination <!-- id: 41 -->
- [ ] Parse email content (handle HTML/text) <!-- id: 42 -->
- [ ] Store in gws_emails table <!-- id: 43 -->
- [ ] Track sync state (last_synced timestamp) <!-- id: 44 -->

### 5.3 Google Docs Sync
- [ ] Create `scripts/sync_gdocs.py` <!-- id: 45 -->
- [ ] Fetch documents from Drive <!-- id: 46 -->
- [ ] Export document content as text <!-- id: 47 -->
- [ ] Store in gws_documents table <!-- id: 48 -->
- [ ] Generate embeddings for RAG <!-- id: 49 -->

### 5.4 Calendar Sync (Optional)
- [ ] Create `scripts/sync_gcal.py` <!-- id: 50 -->
- [ ] Fetch events from Calendar API <!-- id: 51 -->
- [ ] Store in gws_calendar table <!-- id: 52 -->

---

## Phase 6: Automation (Optional)
- [ ] Create scheduled job for Google Workspace sync <!-- id: 53 -->
- [ ] Set up cron or Docker-based scheduler <!-- id: 54 -->
- [ ] Add monitoring/alerting for sync failures <!-- id: 55 -->

---

## Questions for User

1. **Google Workspace scope:** Which services? Gmail, Docs, Drive, Calendar, all?
2. **Gmail scope:** All emails or specific labels/folders?
3. **Sync frequency:** Manual only or automated (hourly/daily)?
4. **Authentication:** Your personal account or organization-wide?

---

## Estimated Effort

| Phase | Tasks | Time |
|-------|-------|------|
| 1. Research | 12 | 1-2 hrs |
| 2. Schema | 10 | 1 hr |
| 3. ChatGPT | 6 | 2 hrs |
| 4. Claude | 6 | 2 hrs |
| 5. Google Workspace | 18 | 4-6 hrs |
| 6. Automation | 3 | 1 hr |
| **Total** | **55** | **11-14 hrs** |
