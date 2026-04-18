# medkb Architecture — Claude Design Brief

> **Purpose:** Drive Claude Design (Anthropic Labs, launched 2026-04-17, powered by Claude Opus 4.7) to produce an executive-grade visual deck of the medkb architecture, branded to DHG.
> **Source narrative:** `docs/architecture/MEDKB_ARCHITECTURE.md`
> **Companion to:** `docs/architecture/MEDKB_DIAGRAM_PROMPTS.md` (Gemini Nano Banana version — single-shot image prompts)
> **Why both exist:** Nano Banana is for one-off illustrations; Claude Design is for an iterating multi-slide deck with a persistent DHG design system. Use whichever fits the moment.

---

## How Claude Design differs from one-shot image generators

Three things make Claude Design a different beast from a text-to-image model:

1. **It holds a design system across a project.** Onboard once with DHG colors, typography, and component tokens — every slide, prototype, and one-pager respects them automatically. No need to re-state the palette in every prompt.
2. **It accepts source documents and codebases as input.** Point it at `MEDKB_ARCHITECTURE.md`, the existing DHG `CLAUDE.md`, the frontend `tailwind.config.ts`, even the `tokens.css` file — Claude Design reads them and infers the system.
3. **Refinement is conversational + direct-manipulation.** Inline comments, adjustment knobs (spacing, color, layout sliders Claude generates per element), and "apply this change to the whole deck" all replace re-prompting. You're directing a designer, not re-rolling an image.

Treat the master prompt below as an *opening brief to a designer*, not a finished spec. Plan to iterate.

---

## Project setup (do this once, before the master prompt)

### 1. Create the project

In Claude.ai, click the palette icon in the left navigation → "New Design Project" → name it **"medkb Architecture Deck"**.

### 2. Onboard the DHG design system

Upload or reference these to populate the system:

| Source | What Claude Design extracts |
|--------|------------------------------|
| `frontend/src/styles/tokens.css` (or `globals.css`) | Color CSS variables, semantic token names |
| `frontend/tailwind.config.ts` | Type ramp, spacing scale, breakpoints |
| `CLAUDE.md` § "DHG Brand" | Tagline, palette intent, 60-30-10 layout rule |
| Any existing pitch deck PPTX | Component patterns, photo treatments, voice |
| The DHG logo (SVG preferred) | Mark for slide chrome |

If those files aren't readily uploadable, paste this **fallback design system spec** into the project's "Design System" panel:

```
DHG AI FACTORY — DESIGN SYSTEM

Brand identity
  Name        : Digital Harmony Group / DHG AI Factory
  Tagline     : "AI Agents In Tune With You"
  Voice       : Confident, technical, executive-grade. Producer-director clarity.
                Fortune 500 polish. No marketing fluff.

Color palette  (60-30-10 weight discipline)
  Graphite        #32374A   primary structural / text
  DHG Purple      #663399   primary accent / actions / brand pop
  DHG Orange      #F77E2D   10% emphasis / highlights / safety alerts ONLY

  Light surface    #FAF9F7  warm off-white background (NEVER pure white)
  Light card       #FFFFFF
  Light border     #E4E4E7
  Light secondary  #71717A  secondary text
  Light placeholder #A1A1AA

  Dark background  #1A1D24
  Dark surface     #27272A
  Dark elevated    #32374A
  Dark text        #FAF9F7
  Dark accent      #A78BFA  light purple for focus on dark

Typography
  Family       : Inter (variable)
  Weights      : 500 regular body, 700 bold heads, 900 display
  Heading 1    : 40pt / 1.1 line-height / -0.02em tracking
  Heading 2    : 28pt / 1.15 / -0.01em
  Body         : 16pt / 1.5
  Caption      : 11pt uppercase tracked +0.06em
  Code         : JetBrains Mono or Inconsolata, 14pt

Layout
  Slide canvas    : 16:9, 1920×1080
  Margins         : 64px outer
  Grid            : 12 columns, 24px gutter
  Card radius     : 12px
  Elevation       : 0-2-4-8 dp scale, soft shadows only
  Color ratio     : 60% neutral / 30% purple / 10% orange. Enforce strictly.

Component vocabulary
  Pill          : 24px tall, 12px x-padding, capsule shape
  Chip          : rounded square, icon + label, 48×48 with 24×24 icon
  Card          : 12px radius, 1px border #E4E4E7, optional 6% purple tint
  Decision diamond : softened hexagon (not spiky), 2px border
  Hero element  : same as card but with 2-4px DHG Orange accent edge
  Arrow         : 1.5px stroke, filled triangle head 8px,
                  Purple solid = happy path, Orange dashed = retry/safety,
                  Graphite = structural containment

Iconography
  Style       : monoline 1.5px stroke, geometric, no fills inside icons
  Inspiration : Lucide / Phosphor regular weight
  NEVER       : emoji, 3D, isometric clipart, stock illustration figures

Tone
  This is a CTO / VP-Engineering presentation, not a marketing deck.
  Diagrams over decoration. Whitespace over density. Crispness over cleverness.
  Every slide should look like it could appear in a McKinsey or Deloitte report.
```

### 3. Attach the source narrative

Upload `docs/architecture/MEDKB_ARCHITECTURE.md` to the project as a reference document. Claude Design will cite it for slide content (the strategy table, the four-defenses table, the design-decisions table — these are the "speaker notes" baked into the source).

### 4. Set output target

Tell Claude Design up front what you'll export to. This shapes the layout decisions:

- **PPTX** — executive presentation. Slides should withstand being projected and read from the back of a room.
- **PDF** — distribution / leave-behind. Tighter typography, denser annotations OK.
- **HTML** — embed back into the docs site under `docs/architecture/`. Web-native, supports interactivity (hover states, expandable details).

Recommended primary: **PPTX with PDF export**, then HTML version for the docs site.

---

## The master prompt

Paste this into the project's main chat after the design-system onboarding is done. It's conversational by design — Claude Design responds best to "brief the designer" framing.

```
I'd like to build a 12-slide executive architecture deck for "medkb" — our
new central RAG-as-a-Service platform. The full design narrative is in
the attached document MEDKB_ARCHITECTURE.md; please read it first, then
work with me on the deck.

The audience is technical executives — CTOs, VP-Engineering, board
technical advisors. They want to understand the SHAPE of the system in
under 10 minutes: what it is, why it exists, how it works, how it stays
safe, and how it rolls out. They are not implementers; they will not
read code on slides.

The full deck is 12 slides:

  1.  Title slide                     — "medkb · Central RAG-as-a-Service"
                                         + DHG mark + tagline
  2.  Why medkb                       — single retrieval plane,
                                         tunable per query, multi-tenant,
                                         LLM-agnostic, HIPAA-aware,
                                         observable. Five short value
                                         props as cards.
  3.  System Context                  — panoramic landscape: DHG consumers
                                         on the left, medkb in the middle
                                         (hero), external dependencies and
                                         observability on the right.
  4.  Layered Architecture            — vertical 4-layer stack (API,
                                         Tunable RAG Graph, Retriever
                                         Abstraction, Storage). Layer 3
                                         is the hero.
  5.  The Tunable Graph               — flowchart with conditional edges,
                                         strategy table on the side
                                         (regular / crag / srag / agentic /
                                         auto). Highlight the redact and
                                         emit_feedback nodes specially —
                                         redact in DHG Orange (safety
                                         gate), emit_feedback in a soft
                                         purple wash (learning loop).
  6.  Retriever Abstraction           — Protocol at the top with the
                                         retrieve() signature, six
                                         concrete retrievers fanning
                                         out below, four wrappers that
                                         compose. Plus a dark code card
                                         showing a real composition.
  7.  Data Model                      — six entity cards arranged with
                                         "corpora" as the central hub
                                         (Orange header — tenancy
                                         primitive). Highlight the
                                         dual-embedding columns on
                                         "chunks" and the sha256-only
                                         policy on "query_audit".
  8.  Model Routing                   — central "get_llm factory"
                                         hexagon (Orange — single point
                                         of model control) with
                                         five RAGConfig slots feeding
                                         in and four backend lanes
                                         fanning out (Anthropic, Ollama
                                         8B, Ollama 14B, Ollama 70B-
                                         future). End with the ~90%
                                         cost reduction callout.
  9.  Resilience & Safety             — five concentric defenses left
                                         to right (auth → rate limit →
                                         redaction → token budget →
                                         circuit breaker). Orange =
                                         degraded paths. End with the
                                         "four concentric defenses"
                                         summary strip.
  10. Observability Correlation       — hub-and-spoke: run_id at center
                                         (Orange hero hex), Loki / Tempo
                                         / Prometheus / LangSmith in
                                         four quadrants. Below LangSmith,
                                         show the feedback cascade into
                                         golden datasets and eval-gated
                                         CI.
  11. Phased Delivery                 — horizontal timeline / gantt with
                                         four lanes (Foundation,
                                         Retrieval, Quality, Adoption).
                                         Adoption lane in Orange — that
                                         lane is the prize.
  12. Design Decisions                — 12-row table summarising the
                                         design decisions from the source
                                         doc. Two columns: decision
                                         and reasoning. Compact, dense,
                                         executive-readable.

For all slides, follow the DHG design system in the project. The 60-30-10
color discipline matters: 60% neutral and graphite for structure, 30%
DHG Purple for primary accent and the medkb brand, and ONLY 10% DHG
Orange — reserve it for the hero element on each slide and for safety /
retry / fail-safe paths. Do not break this ratio.

Each slide should have:
  - A short bold heading (Graphite, 28pt, left-aligned at top)
  - A one-sentence subhead in #71717A (the "story this slide tells")
  - The diagram or content occupying the central 1600×800 area
  - A small footer band: slide number, "medkb Architecture · v1 · April 2026",
    and the DHG mark in the bottom-right
  - Speaker notes pulled from the relevant section of MEDKB_ARCHITECTURE.md

Style direction:
  - Modern enterprise infographic — McKinsey / Deloitte polish.
  - Flat 2D vector with subtle 2-4px soft shadow depth.
  - Monoline 1.5px icons inside 48×48 chips. Lucide-style.
  - No emoji, no clipart, no 3D, no isometric figures, no photographs.
  - Generous whitespace. Density only where the source narrative is
    inherently dense (slide 5, the graph, and slide 12, the decisions
    table).

Please start by drafting slides 1, 2, and 3 only. Show me the layouts
and we'll iterate before you produce the rest. I will refine using the
adjustment knobs and inline comments rather than re-prompting.

Output target: PPTX as the primary export, with a PDF and an HTML
version generated alongside. Light theme for the deck; we'll generate
a dark theme variant after the light version is locked.
```

---

## Iteration playbook

Once Claude Design returns slides 1–3, drive refinement through its native controls instead of re-prompting:

### Use inline comments for slide-level changes
Click the element (a card, a chip, an arrow) → leave a comment. Examples:
- *"This card needs a small Orange edge — it's the hero of this slide."*
- *"Move the legend to the lower-right; it's competing with the title."*
- *"The Anthropic chip should reference 'claude-sonnet-4-6' not the version we discussed last week."*

### Use the adjustment knobs for systemic changes
Claude Design generates per-element sliders for spacing, color intensity, layout density. Reach for these when something is *almost* right:
- Color intensity slider on the purple tint → dial back from 12% to 6%.
- Spacing knob → increase to give the L4 layer more breathing room.
- Layout density → loosen the System Context slide if it feels packed.

### Use "apply across deck" for global changes
When something works on one slide and should propagate:
- *"Apply this caption style to every slide footer."*
- *"Use this chip treatment for every external dependency in the deck."*
- *"Make every Orange hero element use this exact accent edge."*

### Hard requests where prompting *is* the right tool
A few things you'll need to write out, not click:
- **Replacing the icon set wholesale**: *"Swap all icons for Phosphor regular weight."*
- **Changing the strategy table** if the source doc has been updated.
- **Adding a 13th slide** — *"Insert a new slide after slide 5 showing the Strategy → Active Nodes mapping as a swimlane."*

### Get unstuck when a slide isn't landing
If a slide goes through 3 iterations without converging:
1. Ask Claude Design *"What three layouts could this slide take? Show me thumbnail variants."* — it will produce 3 mini-options to choose between.
2. Pick one, then refine.
3. If still stuck, drop back to MEDKB_ARCHITECTURE.md's Mermaid for that diagram and ask *"Use this Mermaid as the structural source of truth for this slide. Layout it in our design system."*

---

## Export checklist

Once the deck locks, export in this order:

| Artifact | Path | Use |
|----------|------|-----|
| PPTX (light) | `docs/architecture/decks/MEDKB_Architecture_v1.pptx` | Executive presentation, board readout |
| PDF (light) | `docs/architecture/decks/MEDKB_Architecture_v1.pdf` | Distribution / leave-behind |
| HTML | `docs/architecture/decks/medkb-architecture/` | Embed in docs site, deep-link individual slides |
| PPTX (dark) | `docs/architecture/decks/MEDKB_Architecture_v1_dark.pptx` | For dark-room demos / late-evening reviews |
| Canva URL | shared link | If marketing / events team wants to derive collateral |
| Claude Code handoff bundle | `frontend/src/components/deck/medkb/` | Optional — turn the slides into actual interactive React components for a docs-site embed |

The Claude Code handoff bundle is the interesting one — it produces JSX components that respect the DHG token system. If we're embedding the architecture story into the frontend (a `/about/medkb` route), that's the path.

---

## Maintenance rule

This deck has a v1 stamp because medkb is in design. As phases land:

- **After Phase 0 (skeleton)** → update slides 3, 4, 11 with what's actually deployed.
- **After Phase 4 (external retrievers)** → refresh slide 6 with the real retriever instances in the registry.
- **After Phase 7 (agentic + auto)** → refresh slide 5 with the actual classifier rules.

Each refresh is a new minor version (v1.1, v1.2, …). Don't let the deck drift — an out-of-date architecture deck is worse than no deck.

---

## Where to go next

| Need | Read |
|------|------|
| Source narrative this deck visualizes | `docs/architecture/MEDKB_ARCHITECTURE.md` |
| One-off image prompts (Gemini Nano Banana) | `docs/architecture/MEDKB_DIAGRAM_PROMPTS.md` |
| Full design spec with every decision | `docs/superpowers/specs/2026-04-17-medkb-rag-as-a-service-design.md` |
| DHG brand tokens (canonical) | `CLAUDE.md` § "DHG Brand" + `frontend/src/styles/tokens.css` |
| Claude Design product page | https://www.anthropic.com/news/claude-design-anthropic-labs |

---

*Claude Design launched 2026-04-17. This brief assumes the research-preview feature set; revise as the product evolves.*
