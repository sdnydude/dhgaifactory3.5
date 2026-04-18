# medkb Architecture — Gemini Nano Banana Diagram Prompts

> **Purpose:** Copy-paste prompts for generating polished DHG-branded architecture illustrations from `MEDKB_ARCHITECTURE.md` using Gemini 2.5 Flash Image ("Nano Banana").
> **Companion to:** `docs/architecture/MEDKB_ARCHITECTURE.md`
> **Output target:** Widescreen 16:9 landscape PNGs unless noted otherwise. Render at 2048 × 1152 for presentation-grade output.

---

## Shared visual system (include at top of every prompt)

Paste this block at the head of each individual prompt below:

```
STYLE SYSTEM — DHG Brand Infographic

Render: modern enterprise technical infographic, flat 2D vector aesthetic with
subtle 2-4px soft shadow depth. Clean geometric shapes, 8px rounded corners on
all rectangles, 1.5px stroke weights, generous whitespace. No gradients except
optional subtle radial halos on focal elements. No 3D, no skeuomorphism, no
clip-art.

Background: warm off-white #FAF9F7 (NOT pure white).
Typography: Inter, variable weights (500 regular, 700 bold), crisp at all sizes.
Section headings in DHG Graphite #32374A, bold, 24pt equivalent. Body labels in
Graphite #32374A, medium, 14pt. Inline tags in medium grey #71717A, 11pt.

DHG Palette (60-30-10 discipline):
  60% — Graphite #32374A and neutrals (#FFFFFF surfaces, #E4E4E7 borders,
         #71717A secondary text) for structural elements, containers, labels
  30% — DHG Purple #663399 for primary actions, the medkb service itself,
         data-flow arrows, and any "active path" highlighting
  10% — DHG Orange #F77E2D ONLY for accents, emphasis, alerts, or the most
         important node on the canvas

Arrows: Purple #663399 for request / happy-path flow. Orange #F77E2D for
error / degradation / regeneration loops. Graphite #32374A for structural
containment. All arrowheads filled, 8px triangle, no open outlines.

Iconography: Minimalist line icons inside rounded-square chips (24x24 icons
in 48x48 chips). Consistent 1.5px stroke. NO emoji, NO photographic imagery.

Composition: Asymmetric balance, clear left-to-right or top-to-bottom reading
order. Group related elements inside faint #E4E4E7 border rectangles with
8% opacity #663399 fill tint. Label groups with small uppercase Graphite
captions above each group.

Footer corner: tiny "DHG AI Factory" wordmark in Graphite, 10pt, bottom-right.
```

---

## 1. System Context (Panoramic)

**Story this tells:** medkb is the single retrieval hub — every DHG consumer calls it, it fans out to local + external knowledge sources, and every call is observable.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: Four-column panoramic landscape, 16:9. Reading order left-to-right.

LEFT COLUMN — "DHG CONSUMERS" (neutral group, graphite captions):
Four stacked rounded cards, each with a small monochrome line icon:
  • "17+ LangGraph Agents" (graph-network icon)
  • "Next.js Frontend :3000" (browser-window icon)
  • "Node-RED Flows" (flow-diagram icon)
  • "Future Divisions" (dashed-outline card, suggesting "to come")

CENTER-LEFT — the hero panel "medkb" (DHG PURPLE halo, slight glow):
A large rounded container, Purple #663399 border 2px, very subtle Purple 6%
fill tint. Inside it, four sub-chips arranged 2x2:
  • "dhg-medkb-api  :8015"  (API icon — interlocking brackets)
  • "dhg-medkb-ingestor"     (worker-cog icon)
  • "dhg-medkb-db  :5433"    (cylinder icon, labeled "PostgreSQL + pgvector")
  • "dhg-medkb-cache :6380"  (lightning-bolt icon, labeled "Redis")

The medkb panel should visually DOMINATE — it is the hero. Purple 10% fill
haze behind it. Small caption above the panel: "CENTRAL RETRIEVAL PLANE"
in uppercase Graphite 11pt.

CENTER-RIGHT — "EXTERNAL DEPENDENCIES":
Five small chips in a vertical stack:
  • "dhg-ollama :11434"   (llama silhouette icon)
  • "Anthropic API"        (Claude spark icon)
  • "PubMed MCP"           (book-medical icon)
  • "ClinicalTrials MCP"   (clipboard-pulse icon)
  • "NPI Registry MCP"     (id-card icon)

FAR RIGHT — "OBSERVABILITY" (light graphite group):
Four chips in a vertical stack:
  • "Tempo :3200"        (waveform icon)
  • "Prometheus :9090"   (flame icon)
  • "Loki :3100"         (log-lines icon)
  • "LangSmith Cloud"    (cloud icon)

ARROWS:
- All consumers → medkb: thick Purple arrows labeled "HTTP /v1/query" in
  small graphite text mid-arrow.
- medkb → external dependencies: thinner Purple arrows, labels
  "embeddings", "generation", "external retrievers".
- medkb → observability: dashed Orange 1.5px arrows (signaling telemetry
  export, not request flow), labeled "@traced_node", "metrics",
  "logs via Promtail", "@traceable + feedback".

Bottom caption strip: "All DHG services share dhgaifactory35_dhg-network"
in small Graphite 11pt italic.
```

---

## 2. Layered Architecture (Vertical Stack)

**Story this tells:** Separation of concerns — each layer has one job, talks only to the one below.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: Vertical 4-layer stack, 9:16 portrait orientation, centered.

Top-most pill (Graphite #32374A fill, white text, small):
  "CONSUMER — Agent / Frontend / Node-RED"

Below that, 4 horizontal bands stacked tightly, each a full-width rounded
rectangle with a subtle drop-shadow, separated by 16px gaps. Each band has:
  - A numbered circle on the far left ("L4", "L3", "L2", "L1")
    in Graphite with white number
  - A bold Purple title
  - A smaller Graphite subtitle describing the layer's job
  - 3-4 small chip tags on the right showing key technologies

LAYER 4 (topmost band, Purple 8% tint):
  Title: "API & Routing"
  Subtitle: "FastAPI · Auth · Rate Limit · Redaction Gate · Token Budget"
  Chips: "FastAPI", "Cloudflare JWT", "presidio", "token-bucket"

LAYER 3 (Purple 12% tint — slightly darker to indicate this is the heart):
  Title: "Tunable RAG Graph"
  Subtitle: "LangGraph StateGraph with conditional edges"
  Chips: "regular", "CRAG", "SRAG", "agentic", "auto"
  Add a small ORANGE "tunable" badge in the corner — this is the hero layer.

LAYER 2 (Purple 8% tint):
  Title: "Retriever Abstraction"
  Subtitle: "Pluggable Retriever protocol · composable wrappers"
  Chips: "pgvector", "BM25", "Hybrid", "MCP tools"

LAYER 1 (Purple 6% tint):
  Title: "Storage"
  Subtitle: "pgvector · Redis · BM25 via tsvector"
  Chips: "PostgreSQL 15", "HNSW index", "tsvector", "Redis 7"

Between each pair of layers: a single thick Purple downward arrow with a
label next to it:
  L4 → L3:  "invokes with RAGConfig"
  L3 → L2:  "uses retrievers"
  L2 → L1:  "reads storage"

Top arrow (from Consumer pill into L4): "HTTP POST /v1/query"

Right-side annotation rail: small uppercase Graphite caption
  "EACH LAYER: ONE CONCERN · ONE INTERFACE TO THE LAYER BELOW"
rotated 90 degrees.
```

---

## 3. The Tunable RAG Graph (Flowchart)

**Story this tells:** One compiled graph with conditional edges — a single query can skip, loop, or escalate through optional nodes depending on strategy and runtime signals.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape flowchart, reading left-to-right with a central
spine and branching loops. This is a complex diagram — keep labels short
and the layout breathable.

NODE TYPES:
- Process nodes: rounded rectangles, white surface, Purple 2px border,
  Graphite bold title + small Graphite subtitle. 160x60px.
- Decision diamonds: hexagonal shape (softened, not spiky), Purple 2px
  border, Graphite label with "?" at end. 120x80px.
- START/END nodes: small pill shape, Graphite fill, white text.

HIGHLIGHT TWO SPECIAL NODES:
- "redact" node filled with ORANGE #F77E2D at 15% opacity, Orange 2px
  border (signals "safety gate, pay attention").
- "emit_feedback" node filled with a soft green-tinted Purple wash
  (signals "eval / learning loop"). Use #D4C5E8 fill.

FLOW (left to right):

[START · "Query arrives"] →
  [redact · "PII/PHI gate"] →
    [analyze_query · "classify intent + pick strategy"] →
      <<should_retrieve?>>
         ├── no  → [generate_direct] → [format_cite]
         └── yes → [expand_queries · "MultiQuery rephrasings"] →
                     [retrieve_fan · "parallel across retrievers"] →
                       [rerank · "RRF + optional cross-encoder"] →
                         <<grade_docs>>
                            ├── good → [generate · "LLM with context"]
                            └── bad  → [rewrite_query] —loops back to
                                       retrieve_fan (ORANGE dashed arrow,
                                       labeled "max 3 retries")
                                       After max retries: falls through
                                       to [generate] anyway.
                     [generate] →
                       <<check_grounded>>
                          ├── good       → [format_cite]
                          └── bad (1st)  → [regenerate] → [format_cite]
                                           (ORANGE dashed loop)
         [format_cite] →
           [emit_feedback · "RAGAS inline eval to LangSmith"] →
             [END · "Response"]

LEGEND CHIP (bottom-left):
 — Purple solid arrow   = happy path
 — Orange dashed arrow  = retry / regeneration loop
 — Orange fill          = safety gate
 — Green-purple wash    = evaluation / feedback

STRATEGY TABLE (right side, small reference card, Graphite borders):
 Header: "STRATEGY → ACTIVE NODES"
   regular  : linear spine only
   crag     : + expand + grade + rewrite loop
   srag     : + check_grounded + regenerate
   agentic  : full graph + tool fan-out
   auto     : analyze_query picks one (default)

CAPTION under diagram (small italic Graphite):
"One compiled StateGraph. Conditional edges read RAGConfig from state to
skip optional nodes. One LangSmith trace per query, regardless of path."
```

---

## 4. Retriever Abstraction (Class / Composition Tree)

**Story this tells:** Retriever is a Protocol — anything that implements it slots in. Wrappers compose to any depth.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape, centered composition with the Protocol at the
TOP and implementations fanning out BELOW. Think UML-inspired but softened
and illustrative, not a literal UML class diagram. Use fewer, larger labels
rather than cramming every method — Nano Banana handles small text poorly.

TOP — The Protocol (hero element, ORANGE accent):
A large rounded tablet, Purple border 2px, Orange #F77E2D 3px top edge,
centered horizontally. Inside:
  Header badge: "PROTOCOL" (tiny Orange uppercase)
  Title: "Retriever"  (Graphite, 28pt bold)
  Method signature on one line:
    "retrieve(query, k, filters, corpus_ids) → List[RetrievedChunk]"
    (monospace, small, Graphite)

Below that tablet, a thin Graphite dashed downward line splits into
TWO BRANCHES (label the split with a small uppercase caption
"IMPLEMENTATIONS   |   WRAPPERS").

LEFT BRANCH — Concrete Retrievers (6 tiles in a 2x3 grid):
Each tile is a rounded square, white surface, Purple border 1px, icon at
top, title bold Graphite, one-line description in #71717A.
  • PgVectorRetriever   — cylinder+dot icon     — "Dense HNSW similarity"
  • BM25Retriever       — text-lines icon       — "Sparse full-text tsvector"
  • HybridRetriever     — overlap icon          — "Dense + sparse via RRF"
  • PubMedRetriever     — book-medical icon     — "PubMed MCP tool"
  • ClinicalTrialsRetriever — clipboard icon    — "ClinicalTrials.gov MCP"
  • NPIRetriever        — id-card icon          — "NPI registry MCP"

RIGHT BRANCH — Composable Wrappers (4 tiles stacked vertically, each
slightly indented to suggest nesting, with a Purple "wraps →" connector
pointing into the left branch):
  • MultiQueryWrapper      — "3-5 query rephrasings"
  • ParentDocumentWrapper  — "retrieves chunks, returns parents"
  • EnsembleRetriever      — "weighted RRF over N retrievers"
  • CrossEncoderReranker   — "Phase 5 · bge-reranker-base" (grey out
                             slightly, with a small ORANGE "Phase 5"
                             badge — signals "future")

BOTTOM CENTER — Composition example (code-style card):
A dark Graphite card (#32374A fill, #FAF9F7 text, monospace), 480px wide:

    retriever = MultiQueryWrapper(
        HybridRetriever(
            dense=PgVectorRetriever(),
            sparse=BM25Retriever(),
            weight_dense=0.7,
        ),
        num_queries=4,
    )

Small Graphite caption below the card:
  "A retriever registry maps corpus → default composition.
   Callers override per-query via retriever_spec."

Add faint Purple connector lines from the code example up to the 3
referenced classes to illustrate the composition visually.
```

---

## 5. Data Model (Entity Relationship)

**Story this tells:** Corpora are the tenancy primitive; dual-embedding enables zero-downtime model migration; PHI audit hashes queries.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. Six entity cards arranged with `corpora` as the
central hub. Cards are rounded rectangles with a title header bar and a
field list below. Header bars in DHG Purple, title in white. Field list
in white surface, Graphite text, monospace 11pt.

CENTRAL HUB — "corpora" (larger than others, Orange #F77E2D header bar
instead of Purple — this is the tenancy primitive):
  id          UUID (PK, bold)
  name        TEXT (unique)
  owner       TEXT
  visibility  TEXT
  contains_phi  BOOL
  default_chunker  TEXT
Add small tag chip above: "TENANCY PRIMITIVE"

AROUND IT, arranged in a hexagon with `corpora` at center:

TOP-LEFT — "documents":
  id, corpus_id (FK), source, source_id, title, audience, authority,
  valid_from, valid_to, superseded_by (FK→self, dashed arrow),
  metadata (JSONB)

TOP-RIGHT — "chunks" (HIGHLIGHT — ORANGE left edge 3px, this is where
dual-embedding lives):
  id, document_id (FK), corpus_id (FK), parent_chunk_id (FK→self),
  chunk_index, chunk_text,
  embedding_v1  vector(768)  ← Orange text, bold
  embedding_v2  vector(768)  ← Orange text, bold
  active_version  INT         ← Orange text
  tsv  TSVECTOR, metadata

BOTTOM-RIGHT — "ingestion_jobs":
  id, corpus_id (FK), source, scope, status, payload,
  items_done, items_error

BOTTOM-LEFT — "query_audit" (HIGHLIGHT — tiny red-tinted lock icon in header):
  id, run_id, caller_id, corpus_list TEXT[],
  query_hash  ← tag: "sha256 only — NEVER raw text"
  redaction_count

FAR BOTTOM — "embedding_cache" (small, separate, no FK to corpus):
  text_hash (PK), model, embedding

RELATIONSHIP LINES:
- Purple solid lines, labeled with cardinality (1..*, 0..1, etc.)
- corpora 1..*  documents       "contains"
- corpora 1..*  chunks          "contains"
- documents 1..*  chunks        "splits into"
- chunks 0..1 chunks (self)     "parent_chunk_id"  (dashed)
- documents 0..1 documents (self)  "superseded_by"  (dashed)
- corpora 1..*  ingestion_jobs  "queued"
- corpora 1..*  query_audit     "PHI logged"

RIGHT-SIDE CALLOUT PANEL (3 pinned insight cards, each a rounded sticky-note
in Orange 10% tint with Orange 1.5px border):

  1. "active_version enables zero-downtime embedding migration"
  2. "query_audit stores sha256(query), NEVER raw text — HIPAA"
  3. "valid_to IS NULL → authoritative; filter applied before retrieval"

Diagram caption (small Graphite italic, bottom):
"Every chunk has exactly one corpus. RBAC filtering precedes retrieval."
```

---

## 6. Model Routing (Factory Fan-Out)

**Story this tells:** LLM is a per-query parameter — 5 independent model slots, Claude today, local models tomorrow, no code change.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. Horizontal fan-out from a central factory chip
to four backend lanes.

LEFT — "Incoming Query" card (Graphite fill, white text):
  "Query with RAGConfig"
  Beneath it, 5 small Purple chips listing the model slots:
   classifier_model · grader_model · groundedness_model ·
   generation_model · rewriter_model

CENTER — the hero element "get_llm factory"
A large rounded hexagon, Orange #F77E2D 2px border, white fill, Orange 10%
inner halo. Title: "get_llm factory" in bold Graphite. Subtitle: "one
dispatcher for all LLM calls" in small Graphite. The hex is the only Orange
shape on the canvas — emphasizes the single point of model control.

From the query card, 5 thin Purple dashed arrows converge into the
factory, each labeled with a slot name:
  classifier_model →
  grader_model →
  groundedness_model →
  generation_model →
  rewriter_model →

RIGHT — Four destination lanes (stacked vertically, each a rounded tile):

  1. "Anthropic API"  (purple-black Claude swirl icon)
       Model chip: "claude-sonnet-4-6"
       Small tag: "GENERATION · CME critical"

  2. "Ollama · llama3.1:8b"   (green llama silhouette)
       Tag: "fast · classifier / grader / rewriter"

  3. "Ollama · qwen3:14b"     (green llama icon, slightly larger)
       Tag: "mid · reflection / groundedness"

  4. "Ollama · llama3.3:70b"  (green llama icon, ORANGE outline + dashed
                              border — signals "future")
       Tag: "heavy · POST RTX-5090 migration target"
       Small Orange badge in corner: "FUTURE"

Single Purple arrow from factory fans out into all four lanes.

BOTTOM CAPTION STRIP (Graphite italic, small):
  "Every LLM-calling graph node routes through one factory. Five independent
   model slots in RAGConfig. After RTX 5090, generation migrates to
   llama3.3:70b via config flag alone — no code change."

COST CALLOUT PANEL (bottom-right, small Orange sticky-note card):
  "~90% Anthropic cost reduction vs. uniform Claude routing."
```

---

## 7. Resilience & Safety (Concentric Defense)

**Story this tells:** Four concentric defenses against HIPAA, cost runaway, upstream failure, and adversarial content.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. Funnel / concentric shield layout, request
enters from the left and passes through 5 progressively deeper gates before
reaching external services.

ENTRY (far left): A rounded Graphite tile "Incoming /v1/query"

Then, arranged horizontally with the request flowing through:

GATE 1 — "Auth"
  Rounded pill, Purple border, shield icon
  Label: "Cloudflare JWT / API key"
  Below: tiny Graphite caption "reject invalid at perimeter"

GATE 2 — "Rate Limiter" (hexagon, decision-shaped)
  Purple border, stopwatch icon
  Label: "token-bucket · 60 req/min per caller · Redis-backed"
  Orange exit arrow leading to a small red tile "429 rate_limit_exceeded"
  (off to the side, shows the reject path)

GATE 3 — "Redaction Gate" (HIGHLIGHT — ORANGE border 2px, slightly larger)
  presidio-analyzer logo-style icon, small Orange "PHI" badge
  Label: "presidio-analyzer · PII/PHI scrubbing"
  Splits into two sub-paths:
    • MANDATORY path (thick Orange arrow): contains_phi=true corpora →
      "+ audit write to query_audit"
    • OPTIONAL path (thin Purple arrow): other corpora → "configurable"
  Both converge forward.

GATE 4 — "Graph Execution" (large rounded rectangle, Purple 10% tint)
  Contains nested sub-element:
    "Token Budget Counter · 50K default"
    A horizontal budget bar (Graphite track, Purple fill) showing 60% used.
  Orange exit arrow leading to a small card "Partial response · budget_exceeded=true"

GATE 5 — "Circuit Breaker" (decision diamond, Purple border)
  pybreaker fuse icon
  Label: "5 failures in 30s → open for 60s"
  Two outputs:
    • closed → external API tile
    • open   → Orange tile "retriever_unavailable · empty result"

FINAL DESTINATION (far right): Stacked tiles "PubMed · ClinicalTrials · NPI"

LEGEND CHIP (bottom-right, small):
  "Orange path = fail-safe / degraded · Purple path = happy path"

FOUR-DEFENSE CALLOUT PANEL (bottom strip, 4 small cards in a row, each Orange
5% tint with an icon):
  🛡  Rate limit        — 60 req/min per caller
  🔒  PHI redaction     — mandatory for contains_phi=true
  💰  Token budget      — hard-stop at 50K/query
  ⚡  Circuit breaker   — degrade, never crash

  (Use minimal line icons, NOT emoji)

CAPTION (bottom, italic Graphite):
  "Four concentric defenses: HIPAA · cost runaway · upstream failure ·
   adversarial content. Every defense is always-on by default."
```

---

## 8. Observability Correlation (Hub and Spoke)

**Story this tells:** One `run_id` threads through Loki, Tempo, Prometheus, and LangSmith — single-ID pivoting across the whole stack.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. Hub-and-spoke with a glowing central run_id
at the center, four observability systems arranged in quadrants, and a
downstream learning loop below.

CENTER HUB — the hero:
A large rounded hexagon, ORANGE #F77E2D 2px border, Orange 10% fill,
subtle Orange halo glow. Inside, in monospace:
  "run_id = 01HXXX..."
Caption above the hex (tiny uppercase Graphite):
  "ONE ID · FOUR TOOLS · COMPLETE CORRELATION"

FOUR QUADRANTS (each a rounded tile arranged around the hub, connected by
Purple solid arrows emanating outward):

  TOP-LEFT — "Loki"
    log-lines icon, Purple border
    Label: "log entries · run_id: 01HXXX..."
    Sample log line in monospace:
      "{"level":"info","run_id":"01HXXX","node":"retrieve_fan"}"

  TOP-RIGHT — "Tempo"
    waveform / timeline icon
    Label: "spans · trace_id linked to run_id"
    Tiny waterfall sparkline showing 6 nested spans

  BOTTOM-LEFT — "Prometheus"
    flame icon
    Label: "metrics · run_id in exemplars"
    Small sparkline chart

  BOTTOM-RIGHT — "LangSmith Cloud"
    cloud icon, DHG Purple 20% fill (LangSmith is slightly hero'd because
    it's where feedback attaches)
    Label: "trace · run_id as key"

FEEDBACK CASCADE (below LangSmith, flowing downward):

Arrow labeled "feedback attached" from LangSmith down to a stacked list
card titled "FEEDBACK KEYS":
  • rag_groundedness
  • rag_relevance
  • strategy_was_correct
  • user_thumbs
  • human_review_decision

Below feedback card → "Nightly curation job" (small chip)
  → "Weekly / monthly golden dataset" (rounded tile, Orange 10% tint,
     suggesting "immutable baseline")
  → splits into two final outputs:
     • "Eval-gated CI"      (chip with gear icon)
     • "Regression detection" (chip with alert icon)

RIGHT-SIDE CALLOUT PANEL:
  "Grafana Explore enables single-ID pivoting.
   Start with a Prometheus alert → follow to Tempo trace →
   pull matching Loki logs → jump to LangSmith for LLM detail."

Render in Graphite italic on Orange 5% tint background, small.
```

---

## 9. Consumer Integration (Sequence Diagram)

**Story this tells:** Agents never speak raw HTTP — they use `medkb_client.py`. The client handles retry, degradation, and run_id propagation for later feedback.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. UML-inspired sequence diagram but softened —
four vertical swimlanes with rounded actor heads at the top, vertical
dashed lifelines, and horizontal Purple request arrows + dashed Graphite
return arrows between them. Include a time gap marker for the "later,
after human review" transition.

FOUR SWIMLANES (left to right):
  1. "LangGraph Agent"      — actor icon: graph-network, Graphite
  2. "medkb_client.py"      — actor icon: wrench-braces, Purple
  3. "dhg-medkb-api"        — actor icon: server, DHG Purple (hero,
                              slight Orange underline to emphasize this
                              is the service under discussion)
  4. "LangSmith"            — actor icon: cloud, Graphite

Lifelines: thin dashed Graphite vertical lines below each actor head.

FIRST INTERACTION BLOCK (top half):

  Agent → medkb_client:
    Purple solid arrow, labeled (Graphite bold):
    "medkb_client.query(query, corpora, strategy)"

  medkb_client → medkb-api:
    Purple solid arrow, labeled:
    "POST /v1/query"
    Tiny chip next to it: "Cloudflare JWT header injected"

  medkb-api → medkb_client:
    Graphite dashed return arrow, labeled:
    "{run_id, answer, citations, groundedness_score, ...}"

  medkb_client → Agent:
    Graphite dashed return arrow, labeled:
    "QueryResult (with run_id)"

TIME GAP (horizontal strip across all lifelines):
A rounded capsule spanning all four lifelines, Orange 10% tint, Orange
border, centered text in small italic Graphite:
  "— later, after human review —"

SECOND INTERACTION BLOCK (bottom half):

  Agent → medkb_client:
    Purple solid arrow:
    "medkb_client.feedback(run_id, key='human_review_decision', value='approved')"

  medkb_client → medkb-api:
    Purple solid arrow: "POST /v1/feedback"

  medkb-api → LangSmith:
    Purple solid arrow: "client.create_feedback(run_id, ...)"

  LangSmith → medkb-api:
    Graphite dashed return arrow: "ack"

  medkb-api → medkb_client:
    Graphite dashed return: "200"

BOTTOM CALLOUT PANEL (3 small Orange-tinted cards in a row):
  1. "Auth injection" — Cloudflare JWT or API key
  2. "Retry · exponential backoff" — network fault tolerance
  3. "Graceful degradation" — 5xx returns retrieval_unavailable=true,
                              NEVER throws

Caption (bottom, small italic Graphite):
  "Consumer always uses medkb_client.py wrapper — never raw HTTP.
   run_id propagates through business logic so feedback can attach
   hours or days later."
```

---

## 10. Phased Delivery (Timeline)

**Story this tells:** Eleven phases over ~5 months, each must produce visible value and pass a regression check before the next starts.

```
[PASTE SHARED STYLE SYSTEM]

COMPOSITION: 16:9 landscape. Horizontal timeline / swim-lane gantt. This
is a schedule, so prioritize clarity over ornamentation.

HORIZONTAL AXIS (bottom): Months labeled "Apr 2026 · May · Jun · Jul · Aug · Sep"
Tick marks every month, light Graphite gridlines.

THREE HORIZONTAL LANES (grouped with small uppercase captions on the left):

  LANE 1 — "FOUNDATION" (small caption in Graphite uppercase)
    Phase 0 · Skeleton                 — 7 days  · starts 2026-04-21
    Phase 1 · Dense-only retrieval     — 7 days  · follows P0
    Phase 2 · Generation               — 7 days  · follows P1

  LANE 2 — "RETRIEVAL"
    Phase 3 · Hybrid + CRAG            — 10 days · follows P2
    Phase 4 · External retrievers      — 7 days  · follows P3
    Phase 5 · Ingestion worker         — 10 days · follows P4

  LANE 3 — "QUALITY"
    Phase 6 · SRAG + feedback           — 14 days · follows P5
    Phase 7 · Agentic + auto            — 10 days · follows P6

  LANE 4 — "ADOPTION" (DHG Orange caption — this is the prize)
    Phase 8 · research_agent migration  — 30 days · follows P7
    Phase 9 · Frontend SDK              — 7 days  · follows P7 (parallel)
    Phase 10 · Division fan-out         — 21 days · follows P8

BAR STYLING:
- Foundation bars: Purple #663399 solid fill
- Retrieval bars:  Purple 80% fill
- Quality bars:    Purple 60% fill
- Adoption bars:   ORANGE #F77E2D solid fill (these are the outcome — pops
                   visually against the purple)

Each bar has:
  - Phase number badge on the left (small circle)
  - Phase name in white bold text
  - Duration text on the right in white
  - Rounded 8px ends

DEPENDENCY ARROWS: thin Graphite arrows connecting the end of a predecessor
to the start of its successor. Parallel starts (P8 and P9 both after P7)
should show a fork.

TOP-RIGHT CALLOUT (Orange sticky note):
  "SEQUENCING RULE:
   Every phase must produce visible value
   AND pass a regression check before the next starts."

BOTTOM-LEFT LEGEND:
  [Purple bar] = infrastructure & retrieval phases
  [Orange bar] = adoption & consumer migration
  [Arrow]      = predecessor / successor dependency

Title strip at top:
  "medkb Rollout · Foundation to Division Fan-out · ~5 months"
```

---

## Usage notes

### How to run these
1. Copy the **Shared visual system** block.
2. Append the prompt for the diagram you want to generate.
3. Paste into Gemini (the web UI's image generation, or the API with the `gemini-2.5-flash-image` model).
4. Request a 2048 × 1152 landscape PNG (9:16 portrait for diagram #2, Layered Architecture).
5. Iterate with follow-ups like "keep everything but make the orange pops more subtle" or "the redact node needs a bolder highlight."

### Tips for refinement
- **If text comes out garbled**, reduce the label count in the prompt. Nano Banana handles 15-25 short labels well, struggles past ~40.
- **If the color discipline breaks**, repeat the 60-30-10 constraint mid-prompt and explicitly forbid extra colors: *"Use ONLY #FAF9F7, #32374A, #663399, #F77E2D, and grey neutrals. No other colors."*
- **If arrow direction is inconsistent**, spell out start → end pairs explicitly instead of describing shapes.
- **If the style drifts toward clip-art**, add *"vector infographic suitable for McKinsey or Deloitte executive report — no cartoon characters, no hand-drawn quality."*

### What not to expect
- **Exact numeric alignment** (gantt bar positions won't be perfectly to scale). Treat Nano Banana output as illustration-grade, not engineering-grade. For precise schedules, use the Mermaid source.
- **Perfect typography** at very small sizes. Keep labels ≥ 11pt equivalent.
- **Identical runs**. Each generation differs. Pick the best of 3-4 runs per diagram.

---

*For the Mermaid source diagrams, see `MEDKB_ARCHITECTURE.md` in this directory.
For the canonical written spec with every decision and tradeoff, see
`docs/superpowers/specs/2026-04-17-medkb-rag-as-a-service-design.md`.*
