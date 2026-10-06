---
title: "DHG corporate-site launch prep (dhg-web)"
sidebar_label: "DHG corporate-site launch prep (dhg-web)"
sidebar_position: 142
slug: ship-5fc1795c
registry_id: 5fc1795c-7ce9-48dc-9da5-27d03da78525
generated: true
---

# DHG corporate-site launch prep (dhg-web)

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex |
| **TDD** | Yes |
| **PR** | no PR recorded |
| **Completed** | 2026-09-04 |
| **Model** | claude-fable-5-1 |

## Approach

Full corporate site (no coming-soon parking): Labs rewrite, GA4 both layouts, designed OG share cards, landing astro:assets webp pipeline, shared vitest runner (D0), blog stays draft with links removed

## Commits

- a4fd9f8 feat(web): corporate-site launch prep
- 0f0cb0f feat(portage): landing v3 + design-lead agent

## Decisions

- publish full corporate site not homepage-only
- Labs features Portage graduate + memreg + git-risk-gate, ADHD dropped
- blog stays draft, links removed until published

## Verification

- **lint:** builds clean both sites
- **tests:** 3 pass (shared runner)
- **typecheck:** n/a (astro)

**Tags:** `dhg-web`, `website`, `launch`, `astro`, `og-cards`, `ga4`
