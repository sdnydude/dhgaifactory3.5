# DHG AI Factory — Documentation & Product Marketing Site
## Complete Manus Prompt

---

Here are the URLs for this project:

- **GitHub Repository:** [REPO URL]
- **Live Prototype:** [PROTOTYPE URL]

**Review the entire repository and live prototype, then build a Fortune 500-quality interactive documentation and product marketing website. Follow all instructions below precisely.**

---

## 1. Repository Analysis

- Clone and analyze the full repo — all code, docs, configs, README files, and any existing diagrams or visual assets
- Map the complete architecture: modules, services, orchestration flows, data models, integrations
- Identify documentation gaps where supplemental visuals or narrative are needed

---

## 2. Prototype Exploration

- Browse the full live prototype — every page, modal, and interactive state
- Capture full-page screenshots of all key screens, workflows, and UI states
- For interactive elements (modals, dropdowns, expanded states, hover effects), capture each state separately as individual screenshots
- Annotate screenshots where needed (callouts, numbered highlights, flow arrows) to support the non-technical narrative
- Save all raw screenshots as standalone assets alongside the annotated versions

### Authentication

- The prototype URL requires Google OAuth login
- When you reach the login screen, **pause and wait for me to authenticate manually** before proceeding
- Do not attempt to bypass, auto-fill, or interact with the login form
- Once I confirm authentication is complete, continue browsing and capturing the full site

---

## 3. Design System — DHG Apple Glassmorphism

### DHG Color Guide

| Token | Hex | Usage |
|---|---|---|
| `--dhg-graphite` | #32374A | Primary / dominant (60%) — backgrounds, headings, body text |
| `--dhg-purple` | #663399 | Secondary (30%) — subheadings, glows, gradient accents, highlights |
| `--dhg-orange` | #F77E2D | Accent (10%) — CTAs, buttons, alert highlights, hover states only |
| `--dhg-white` | #FFFFFF | Card backgrounds (with alpha), body text on dark |
| `--dhg-light-gray` | #F5F5F5 | Subtle section dividers, table alternating rows |
| `--dhg-dark` | #2E3243 | Deep backgrounds, footer, gradient endpoints |
| `--dhg-green-bg` | #E8F5E9 | Success/performance indicators |
| `--dhg-green-txt` | #2E7D32 | Success/performance text |
| `--dhg-orange-bg` | #FFF3E0 | Warning/competence indicators |
| `--dhg-orange-txt` | #E65100 | Warning/competence text |

**Rules:**
- Apply 60-30-10 rule strictly: Graphite (dominant), Purple (secondary), Orange (accent/CTAs only)
- Use CSS custom properties (semantic tokens) — never raw hex values in components
- Orange is ONLY for interactive elements, CTAs, and small accent highlights — never large color blocks

### Glassmorphism Specifications

```css
/* Glass Card Base */
.glass-card {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  padding: 2rem;
}

/* Glass Card Hover */
.glass-card:hover {
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  transform: translateY(-2px);
  transition: all 0.3s ease;
}

/* Background Gradient */
body {
  background: linear-gradient(135deg, var(--dhg-graphite) 0%, var(--dhg-dark) 100%);
}

/* Purple Glow Accent */
.accent-glow {
  box-shadow: 0 0 30px rgba(102, 51, 153, 0.15);
}

/* Orange CTA Button */
.cta-button {
  background: linear-gradient(135deg, var(--dhg-orange), #e06820);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.cta-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(247, 126, 45, 0.35);
}
```

### Typography

- **Font:** Inter throughout (import from Google Fonts)
- **Body:** 300/400 weight, 16-18px, generous line-height (1.6-1.8)
- **Headings:** 600 weight
- **Hero/Display:** 200-300 weight at large sizes for elegance
- **Letter spacing:** Slight tracking on uppercase labels (+0.05em)

### Overall Aesthetic

Apple.com meets Bloomberg Terminal — premium, clean, modern, data-rich but visually calm. Every element should feel intentional. Generous whitespace. No visual clutter. Content breathes.

---

## 4. Site Content & Narrative

### Existing Content
- All existing documentation compiled and organized by topic
- All existing diagrams, illustrations, and Nano Banana Pro graphics integrated in context

### New Supplemental Visuals
- Architecture diagrams, workflow illustrations, system maps, and infographics created where gaps exist
- All new visuals styled to match the glassmorphism aesthetic
- Use SVG preferred, PNG fallback
- Diagrams should use DHG color palette with glass panel styling

### Non-Technical Narrative
Write a complete non-technical narrative woven throughout the entire site that:

- Explains what the project does, why it matters, and how it works in **plain language**
- Uses **real-world analogies, visual storytelling, and progressive disclosure** — concept first, then detail
- Treats illustrations and diagrams as **primary explanation tools**, not decoration
- Is written for **executive, investor, and non-technical business audiences**
- Reads like a product story, not a technical manual
- Builds understanding progressively: "What is this?" → "Why does it matter?" → "How does it work?" → "What can I do with it?"

---

## 5. Interactive Elements

### Interactive Architecture Explorer
- Clickable system diagram — click a module and a glass panel expands with details, narrative explanation, and animated data flow
- Modules should light up and show connections on hover

### Animated Scroll Narrative
- As the user scrolls, the story unfolds progressively — animated transitions between concept layers, modules lighting up, data flowing through the system
- Smooth entrance animations on scroll (fade-in, slide-up) — subtle, not distracting

### Before/After Workflow Comparisons
- Interactive sliders showing "manual process" vs "AI Factory automated process"
- Show quantified impact: time, cost, error rate reductions

### Agent Demo Placeholders
- Reserve clearly marked sections for 4 embedded live agent demos:
  1. **Platform Q&A Agent** — answers any question about the AI Factory (replaces FAQ)
  2. **ROI Calculator Agent** — takes inputs (team size, manual hours, error rates), outputs projected savings
  3. **Workflow Design Agent** — user describes a business process, agent suggests modularization approach
  4. **Use Case Match Agent** — short interview → recommends which AI Factory modules fit their business
- Each placeholder should include: styled container, title, description, and a "Coming Soon" or "Launch Demo" button
- Design these so a chat interface or iframe can be dropped in seamlessly later

---

## 6. Lead Capture & White Paper System

### Tiered Content Access Model

**Tier 1 — Ungated (builds trust):**
- Full site narrative, interactive architecture explorer, animated walkthroughs
- Use case summaries and capability overviews
- Enough value that visitors respect the brand before you ask for anything

**Tier 2 — Gated with Registration (captures leads):**
- White paper download: "The Modular AI Factory: Enterprise Architecture for Adaptive Intelligence"
- Technical deep-dive PDFs and case study documents
- Registration form fields (minimal): Name, Email, Company, Role
- Form styled as a glassmorphism card — clean, premium, not salesy

**Tier 3 — Request Access (qualifies leads):**
- Live platform demo scheduling (Calendly embed or styled booking form)
- Custom agent building consultation request
- API access / pilot program application

### White Paper Download Flow

**Registration Page:**
- Glassmorphism-styled landing section with white paper cover preview
- Compelling copy: what they'll learn, who it's for, page count/read time
- Clean registration form (Name, Email, Company, Role)
- Submit button (Orange CTA): "Get the White Paper"

**Confirmation Page (post-submit):**
- "Check your email — your white paper is on its way."
- Secondary CTA: "While you wait — explore the interactive architecture" (links back to site)

**Automated Email Template:**
- Build a branded HTML email template matching the glassmorphism aesthetic
- Contents:
  - DHG logo header
  - Personal greeting: "Hi [Name],"
  - Brief message from the CEO (2-3 sentences)
  - Download button (Orange CTA) — time-limited link (72 hours)
  - PDF attached directly as backup
  - Footer CTA: "Want to see it live? Book 15 minutes with our team →"
  - Unsubscribe link and company details footer
- Design this as a standalone HTML file ready for Resend/SendGrid

**Follow-Up Email (3-day delay):**
- Build a second branded HTML email template
- Contents: "Found the white paper useful?" + link to a related asset or case study + demo booking CTA

---

## 7. Site Structure

Suggested information architecture (adapt based on repo content):

```
Home (Hero + narrative scroll)
├── What is the AI Factory? (concept + analogies)
├── How It Works (interactive architecture explorer)
├── Capabilities (module deep-dives in glass cards)
├── Use Cases (before/after comparisons)
├── Live Demos (agent placeholders)
├── Resources
│   ├── White Paper (gated download)
│   ├── Technical Documentation (compiled from repo)
│   └── Case Studies
├── About DHG (company + divisions overview)
└── Contact / Book a Demo
```

---

## 8. Deliverables

1. **Complete website source files** — HTML/CSS/JS, self-contained, no external build tools required, deployable as a static site
2. **CSS custom properties file** with all DHG semantic design tokens
3. **All generated graphics** as standalone assets (SVG preferred, PNG fallback)
4. **All captured prototype screenshots** — raw and annotated versions
5. **HTML email templates** — white paper delivery email + 3-day follow-up email
6. **White paper cover/placeholder PDF** — styled, ready for content insertion
7. **README** with deployment instructions and file manifest

---

## Quality Standard

**This should look and read like it came from a Fortune 500 product team.**

Premium glassmorphism aesthetic. DHG branded throughout. Narrative-driven. Visually rich. Interactive where it counts. Every pixel intentional. Every word purposeful.

The site serves three audiences simultaneously:
- **Executives** see the business value and credibility
- **Technical evaluators** find the depth and documentation they need
- **Investors** see a polished, market-ready product with clear differentiation

---
