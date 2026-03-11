# DHG Brand System

- Graphite: #32374A
- Purple: #663399
- Orange: #F77E2D
- Font: Inter
- Layout: 60-30-10 rule
- Use semantic CSS tokens, not raw hex values
- Tagline: "AI Agents In Tune With You"

## CSS Variables (use these in all UI work)

### Light Mode
| Variable | Value | Usage |
|----------|-------|-------|
| `--dhg-background` | #FAF9F7 | Page background (warm off-white, NOT pure white) |
| `--dhg-surface` | #FFFFFF | Cards, panels |
| `--dhg-surface-elevated` | #FFFFFF | Modals, dropdowns |
| `--dhg-text-primary` | #32374A | Main text |
| `--dhg-text-secondary` | #71717A | Secondary text |
| `--dhg-text-placeholder` | #A1A1AA | Placeholder text |
| `--dhg-border` | #E4E4E7 | Borders |
| `--dhg-border-focus` | #663399 | Focus state (purple) |

### Dark Mode
| Variable | Value | Usage |
|----------|-------|-------|
| `--dhg-background` | #1A1D24 | Page background |
| `--dhg-surface` | #27272A | Cards, panels |
| `--dhg-surface-elevated` | #32374A | Modals, dropdowns |
| `--dhg-text-primary` | #FAF9F7 | Main text |
| `--dhg-text-secondary` | #A1A1AA | Secondary text |
| `--dhg-text-placeholder` | #71717A | Placeholder text |
| `--dhg-border` | #3F3F46 | Borders |
| `--dhg-border-focus` | #A78BFA | Focus state (light purple) |

## Rules
- All UIs must support both light and dark modes
- Use warm off-white (#FAF9F7), never pure white, for light backgrounds
- Purple (#663399) is the primary accent color
