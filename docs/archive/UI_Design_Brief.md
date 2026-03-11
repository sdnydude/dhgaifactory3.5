# DHG AI Factory - UI/UX Design Brief

**Project**: CME Pipeline Multi-Agent System Interface  
**Type**: Progressive Web Application (PWA)  
**Date**: November 30, 2025  
**Version**: 1.0

---

## 📋 Executive Summary

Design a modern, professional Progressive Web Application (PWA) for the DHG AI Factory CME generation system. The interface must support real-time agent communication, document generation, and compliance validation with a clean, medical-professional aesthetic.

---

## 🎯 Design Goals

1. **Professional Medical Aesthetic** - Trust, credibility, clinical precision
2. **Real-Time Transparency** - Show agent activity during content generation
3. **Dual-Context Workflow** - Chat interface + live results simultaneously
4. **Progressive Enhancement** - Works offline, installable, responsive
5. **Accessibility First** - WCAG 2.1 AA compliant minimum

---

## 🎨 Color Palette

### Primary Colors

```
DHG Blue (Primary)
- Main: #0066CC
- Light: #3385DB
- Dark: #004D99
- Usage: Primary actions, headers, active states

DHG Navy (Secondary)
- Main: #1A365D
- Light: #2D4A7C
- Dark: #0F2540
- Usage: Navigation, secondary elements, text
```

### Accent Colors

```
Success Green
- Main: #059669
- Light: #10B981
- Dark: #047857
- Usage: Completed tasks, validated content

Warning Amber
- Main: #D97706
- Light: #F59E0B
- Dark: #B45309
- Usage: Warnings, pending validation

Error Red
- Main: #DC2626
- Light: #EF4444
- Dark: #B91C1C
- Usage: Errors, violations, critical issues

Info Cyan
- Main: #0891B2
- Light: #06B6D4
- Dark: #0E7490
- Usage: Information, tips, agent status
```

### Neutral Palette

```
Background
- White: #FFFFFF
- Light Gray: #F9FAFB
- Gray 100: #F3F4F6
- Gray 200: #E5E7EB

Text
- Primary: #111827
- Secondary: #6B7280
- Tertiary: #9CA3AF
- Disabled: #D1D5DB

Borders
- Light: #E5E7EB
- Default: #D1D5DB
- Dark: #9CA3AF
```

### Agent-Specific Colors

```
Orchestrator: #0066CC (Blue)
Medical LLM: #7C3AED (Purple)
Research: #059669 (Green)
Curriculum: #EA580C (Orange)
Outcomes: #DB2777 (Pink)
Competitor Intel: #0891B2 (Cyan)
QA/Compliance: #DC2626 (Red - for validation)
```

---

## 🔤 Typography

### Font Stack

```css
/* Primary (Interface) */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 
             Helvetica, Arial, sans-serif;

/* Monospace (Code/Technical) */
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 
             'Monaco', monospace;

/* Medical/Formal (Generated Content) */
font-family: 'Crimson Text', 'Georgia', 'Times New Roman', serif;
```

### Type Scale

```
Display: 48px / 56px line-height / Bold / -0.02em
H1: 36px / 44px / Bold / -0.01em
H2: 30px / 38px / Semibold / -0.01em
H3: 24px / 32px / Semibold / 0em
H4: 20px / 28px / Semibold / 0em
H5: 16px / 24px / Semibold / 0em
H6: 14px / 20px / Semibold / 0em

Body Large: 18px / 28px / Regular / 0em
Body: 16px / 24px / Regular / 0em
Body Small: 14px / 20px / Regular / 0em

Caption: 12px / 16px / Medium / 0.01em
Overline: 12px / 16px / Semibold / 0.05em / UPPERCASE

Code: 14px / 20px / Monospace / Regular
```

---

## 📐 Layout Architecture

### Main Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  Header (64px fixed)                                    │
│  [Logo] [Nav] [Mode Badge] [User] [Settings]          │
├─────────┬───────────────────────────────┬───────────────┤
│         │                               │               │
│  Left   │    Main Content Area         │    Right      │
│  Panel  │    (Flex/Scrollable)         │    Panel      │
│  (0-400)│                               │    (0-400)    │
│         │                               │               │
│  Chat   │    • Dashboard               │   Results     │
│  Agent  │    • Request Form            │   Output      │
│  Status │    • History                 │   Preview     │
│         │    • Settings                │   Validation  │
│         │                               │               │
│         │                               │               │
│         │                               │               │
│         │                               │               │
└─────────┴───────────────────────────────┴───────────────┘
│  Footer (48px) - Status Bar                            │
│  [Connection] [Agent Status] [Progress] [Credits]      │
└─────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

```
Mobile: 320px - 767px   (Panels become bottom sheets)
Tablet: 768px - 1023px  (Single panel at a time)
Desktop: 1024px - 1439px (Both panels available)
Large: 1440px+          (Both panels + wide content)
```

### Panel Behavior

```
Desktop (1440px+):
- Both panels can be open simultaneously
- Resizable with drag handles (280px - 400px)
- Collapsible to icons-only (64px)

Tablet (768px - 1023px):
- One panel at a time
- Slide in from side
- Backdrop overlay on main content

Mobile (320px - 767px):
- Bottom sheet for chat
- Full screen for results
- Swipe gestures to switch
```

---

## 🎭 Component Specifications

### 1. Header Component

**Dimensions**: Full width × 64px  
**Position**: Fixed top  
**Background**: White with bottom border (#E5E7EB)  
**Shadow**: 0 1px 3px rgba(0,0,0,0.1)

```
Elements:
├─ Logo (32px height)
├─ Navigation Menu
│   ├─ Dashboard
│   ├─ Generate
│   ├─ History
│   └─ Settings
├─ Mode Badge (CME / NON-CME)
│   ├─ Pill shape, 8px padding
│   └─ Success green (CME) / Info cyan (NON-CME)
├─ User Avatar (32px circle)
└─ Settings Icon (24px)
```

### 2. Left Panel - Chat & Agent Status

**Width**: 320px - 400px (resizable)  
**Background**: #F9FAFB  
**Border**: Right 1px #E5E7EB

#### Chat Interface

```
Components:
├─ Chat Header
│   ├─ "Chat with Orchestrator" (H6)
│   └─ Status indicator (dot + text)
│
├─ Message List (Scrollable)
│   ├─ User Messages
│   │   ├─ Align: Right
│   │   ├─ Background: #0066CC
│   │   ├─ Text: White
│   │   └─ Border radius: 16px 16px 4px 16px
│   │
│   └─ Agent Messages
│       ├─ Align: Left
│       ├─ Background: White
│       ├─ Text: #111827
│       ├─ Border: 1px #E5E7EB
│       └─ Border radius: 16px 16px 16px 4px
│
├─ Agent Activity Feed
│   ├─ Compact list view
│   ├─ Color-coded by agent
│   ├─ Real-time updates
│   └─ Expandable details
│
└─ Input Area (Fixed bottom)
    ├─ Textarea (auto-expand to 5 lines)
    ├─ Attachment button
    ├─ Send button (Primary)
    └─ Voice input (optional)
```

**Message Metadata**:
- Timestamp (12px, #6B7280)
- Agent avatar (24px circle with agent color)
- Status icons (16px)

#### Agent Status Panel

```
Live Agent Activity:
┌─────────────────────────────┐
│ 🟢 Orchestrator  Active     │
│ ⏳ Research      Working... │
│ ✅ Medical LLM   Complete   │
│ ⏸️  Curriculum   Waiting    │
│ 🔴 QA/Compliance Error      │
└─────────────────────────────┘

Each agent row:
- Status dot (12px)
- Agent name (14px, Semibold)
- Status text (12px, Secondary)
- Progress bar (if working)
- Expand button for logs
```

### 3. Main Content Area

**Background**: White  
**Padding**: 32px  
**Max width**: 1200px (centered)

#### Dashboard View

```
┌─────────────────────────────────────┐
│  Welcome Header                     │
│  Quick Stats Cards (4 columns)      │
├─────────────────────────────────────┤
│  Recent Requests (Table)            │
├─────────────────────────────────────┤
│  Quick Actions (Cards)              │
│  • Generate CME Needs Assessment    │
│  • Create Curriculum                │
│  • Run Competitor Analysis          │
└─────────────────────────────────────┘
```

**Stat Cards**:
- Size: 260px × 120px
- Background: White
- Border: 1px #E5E7EB
- Border radius: 12px
- Hover: Shadow 0 4px 12px rgba(0,0,0,0.1)
- Icon: 32px agent color
- Value: 32px Bold
- Label: 14px Secondary

#### Request Form View

```
Form Structure:
├─ Page Header (H2)
├─ Breadcrumb Navigation
├─ Form Sections (Cards)
│   ├─ Basic Information
│   │   ├─ Task Type (Dropdown)
│   │   ├─ Topic (Text input)
│   │   └─ Compliance Mode (Toggle)
│   │
│   ├─ Audience & Context
│   │   ├─ Target Audience
│   │   ├─ Funder (optional)
│   │   └─ Moore Levels (Multi-select)
│   │
│   ├─ Advanced Options (Expandable)
│   │   ├─ Word Count Target
│   │   ├─ Reference Count
│   │   └─ Additional Context (JSON)
│   │
│   └─ Action Buttons
│       ├─ Generate (Primary, large)
│       ├─ Save Draft (Secondary)
│       └─ Cancel (Tertiary)
│
└─ Preview Panel (Sticky right)
    └─ Live request preview (JSON)
```

**Form Inputs**:
- Height: 40px
- Border: 1px #D1D5DB
- Border radius: 8px
- Focus: Border #0066CC, Shadow 0 0 0 3px rgba(0,102,204,0.1)
- Label: 14px Semibold, margin-bottom 8px
- Helper text: 12px #6B7280

### 4. Right Panel - Results & Output

**Width**: 320px - 400px (resizable)  
**Background**: White  
**Border**: Left 1px #E5E7EB

#### Content Preview

```
Components:
├─ Header
│   ├─ "Generated Content" (H6)
│   ├─ Download button
│   └─ Copy button
│
├─ Tabs
│   ├─ Preview
│   ├─ Markdown
│   ├─ JSON
│   └─ References
│
├─ Content Area (Scrollable)
│   ├─ Formatted preview
│   ├─ Syntax highlighting (for code)
│   └─ Line numbers (optional)
│
├─ Metadata Section
│   ├─ Word count
│   ├─ Reference count
│   ├─ Compliance mode
│   └─ Generation time
│
└─ Validation Results
    ├─ Status badge
    ├─ Violations list (if any)
    ├─ Warnings list
    └─ Recommendations
```

**Validation Badge**:
```
Pass: 
- Background: #ECFDF5 (light green)
- Border: #10B981
- Text: #047857
- Icon: ✓

Fail:
- Background: #FEF2F2 (light red)
- Border: #EF4444
- Text: #B91C1C
- Icon: ✗

Warning:
- Background: #FFFBEB (light amber)
- Border: #F59E0B
- Text: #B45309
- Icon: ⚠
```

### 5. Progress Indicator

**During Generation**:

```
┌─────────────────────────────────────┐
│  Generating CME Needs Assessment... │
│  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  45%       │
│                                     │
│  ✅ Research complete               │
│  ⏳ Medical LLM generating...       │
│  ⏸  QA validation pending           │
└─────────────────────────────────────┘
```

**Styles**:
- Progress bar height: 8px
- Border radius: 4px
- Background: #E5E7EB
- Fill: Linear gradient #0066CC → #3385DB
- Animation: Smooth transition 0.3s

### 6. Compliance Mode Toggle

**Design**: Segmented control

```
┌─────────────────────────────┐
│  AUTO  │  CME  │  NON-CME  │
└─────────────────────────────┘
```

**States**:
- Default: Background #F3F4F6, Text #6B7280
- Active: Background #0066CC, Text White
- Height: 40px
- Border radius: 8px
- Transition: 0.2s ease

**Mode Indicators**:
- CME: Green dot + "ACCME Compliant"
- NON-CME: Cyan dot + "Business Content"
- AUTO: Blue dot + "Auto-Detect"

---

## 🎬 Interactions & Animations

### Micro-Interactions

**Button Hover**:
```css
transition: all 0.2s ease;
transform: translateY(-1px);
box-shadow: 0 4px 12px rgba(0,0,0,0.15);
```

**Panel Slide In**:
```css
transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
backdrop-filter: blur(4px);
```

**Message Send**:
```css
/* Send animation */
opacity: 0 → 1 (0.2s)
transform: translateY(10px) → translateY(0)
```

**Agent Status Update**:
```css
/* Pulse effect on status change */
animation: pulse 0.5s ease-in-out;
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
```

### Loading States

**Skeleton Screens**:
- Use for table rows, cards
- Background: Linear gradient shimmer
- Animation: 1.5s infinite

**Spinner**:
- Size: 24px
- Border: 3px
- Color: #0066CC
- Speed: 0.8s linear infinite

---

## 📱 Mobile Adaptations

### Mobile Layout (320px - 767px)

```
┌─────────────────────────┐
│  Header (56px)          │
│  [☰] [Logo] [User]     │
├─────────────────────────┤
│                         │
│  Main Content           │
│  (Full width)           │
│                         │
│                         │
│                         │
├─────────────────────────┤
│  Tab Bar (64px)         │
│  [Home][Chat][Results]  │
└─────────────────────────┘
```

**Chat Bottom Sheet**:
- Swipe up to expand
- Height: 60% of screen
- Backdrop: rgba(0,0,0,0.5)
- Border radius: 16px 16px 0 0

**Results Full Screen**:
- Slide from right
- Header with back button
- Full screen overlay

---

## ♿ Accessibility Requirements

### WCAG 2.1 AA Compliance

**Color Contrast**:
- Normal text: 4.5:1 minimum
- Large text (18px+): 3:1 minimum
- Interactive elements: 3:1 minimum

**Keyboard Navigation**:
- Tab order follows visual flow
- Focus indicators: 2px solid #0066CC
- Skip links for main content
- All actions keyboard accessible

**Screen Reader Support**:
- ARIA labels on all icons
- ARIA live regions for status updates
- Semantic HTML (nav, main, aside, etc.)
- Alt text for all images

**Motion**:
- Respect `prefers-reduced-motion`
- Option to disable animations
- No auto-playing content

---

## 🎯 Interactive States

### Button States

**Primary Button**:
```
Default:
- Background: #0066CC
- Text: White
- Height: 40px
- Padding: 12px 24px
- Border radius: 8px

Hover:
- Background: #004D99
- Transform: translateY(-1px)
- Shadow: 0 4px 12px rgba(0,102,204,0.3)

Active:
- Background: #003D7A
- Transform: translateY(0)

Disabled:
- Background: #D1D5DB
- Text: #9CA3AF
- Cursor: not-allowed
```

**Secondary Button**:
```
Default:
- Background: White
- Border: 1px #D1D5DB
- Text: #0066CC

Hover:
- Border: #0066CC
- Background: #F0F9FF
```

### Input States

```
Default:
- Border: 1px #D1D5DB
- Background: White

Focus:
- Border: 1px #0066CC
- Shadow: 0 0 0 3px rgba(0,102,204,0.1)

Error:
- Border: 1px #DC2626
- Shadow: 0 0 0 3px rgba(220,38,38,0.1)

Success:
- Border: 1px #059669
- Icon: ✓ right side
```

---

## 🖼️ Component Examples

### Request Card (History)

```
┌────────────────────────────────────────────┐
│ 🟢 CME  Type 2 Diabetes Management        │
│                                            │
│ Primary Care Physicians                    │
│ Generated: Nov 30, 2025 10:45 AM         │
│                                            │
│ ✓ 1,247 words  ✓ 10 references           │
│ ✓ Validation passed                       │
│                                            │
│ [View] [Download] [•••]                   │
└────────────────────────────────────────────┘

Card:
- Padding: 20px
- Border radius: 12px
- Border: 1px #E5E7EB
- Hover: Shadow + transform
- Max width: 400px
```

### Agent Activity Item

```
┌─────────────────────────────────────┐
│ ⚡ Research Agent                   │
│ Querying PubMed...                  │
│ ▓▓▓▓▓▓▓▓░░░░  65%                  │
│ 15 results found                    │
│ [View Details ▼]                    │
└─────────────────────────────────────┘

Compact view:
- Height: 60px
- Padding: 12px
- Agent color accent (left border 3px)
```

### Validation Result

```
┌────────────────────────────────────┐
│ ✓ Compliance Check Passed          │
│                                    │
│ ✅ No hallucinated sources         │
│ ✅ References validated (10/10)    │
│ ✅ Word count within range         │
│ ✅ ACCME rules applied             │
│ ✅ Fair balance confirmed          │
│                                    │
│ ⚠️  1 Warning                      │
│ Consider adding SDOH context       │
└────────────────────────────────────┘

Success card:
- Background: #ECFDF5
- Border: 1px #10B981
- Icon: 24px
```

---

## 🎨 Dark Mode (Optional Phase 2)

### Dark Palette

```
Background: #0F172A
Surface: #1E293B
Surface Variant: #334155

Text Primary: #F1F5F9
Text Secondary: #CBD5E1
Text Tertiary: #94A3B8

Borders: #334155
```

**Toggle**: Top right header, moon/sun icon

---

## 📦 Asset Requirements

### Icons
- **Style**: Outlined (2px stroke)
- **Size**: 16px, 24px, 32px
- **Format**: SVG
- **Library**: Heroicons or Lucide Icons

### Logos
- **Full logo**: 240px × 48px (horizontal)
- **Icon**: 48px × 48px (square)
- **Favicon**: 32px × 32px
- **PWA Icons**: 192px, 512px

### Illustrations
- **Empty states**: 240px × 180px
- **Error states**: 240px × 180px
- **Onboarding**: 360px × 270px
- **Style**: Flat, 2-color (Blue + Navy)

---

## 🚀 PWA Specifications

### Manifest.json

```json
{
  "name": "DHG AI Factory",
  "short_name": "DHG CME",
  "description": "CME Content Generation System",
  "theme_color": "#0066CC",
  "background_color": "#FFFFFF",
  "display": "standalone",
  "start_url": "/",
  "scope": "/",
  "icons": [...]
}
```

### Offline Support
- Cache shell (HTML, CSS, JS)
- Cache recent requests
- Show offline indicator
- Queue actions when offline

### Install Prompt
- Show after 2nd visit
- Position: Bottom banner
- Dismissible
- "Add to Home Screen" CTA

---

## 📋 Deliverables Checklist

### Phase 1 - Core Interface
- [ ] High-fidelity mockups (Figma/Sketch)
- [ ] Desktop views (1440px)
- [ ] Tablet views (768px)
- [ ] Mobile views (375px)
- [ ] Component library
- [ ] Style guide document
- [ ] Interactive prototype

### Phase 2 - Assets
- [ ] Icon set (SVG)
- [ ] Logo variations
- [ ] PWA icons
- [ ] Illustrations
- [ ] Loading animations

### Phase 3 - Documentation
- [ ] Component specifications
- [ ] Responsive behavior guide
- [ ] Animation timing guide
- [ ] Accessibility checklist
- [ ] Developer handoff notes

---

## 🎓 Reference Materials

### Design Inspiration
- **Medical**: UpToDate, Medscape interfaces
- **Chat**: Linear, Slack, Discord
- **Professional**: Notion, Airtable
- **PWA**: Twitter Lite, Google Keep

### Color Psychology
- **Blue**: Trust, medical, professional
- **Green**: Success, validation, health
- **Red**: Critical, errors, compliance issues
- **Purple**: Medical specialty, expertise

---

## 📞 Design Questions to Address

1. **Branding**: Existing DHG brand guidelines?
2. **Illustrations**: Custom or stock (unDraw, Storyset)?
3. **Animation**: Level of motion (minimal, standard, rich)?
4. **Data Viz**: Charts for analytics (Chart.js, D3)?
5. **Templates**: Pre-built request templates?
6. **Collaboration**: Multi-user support needed?
7. **Export**: PDF generation styling requirements?
8. **Localization**: Multiple languages planned?

---

## ✅ Success Criteria

### User Experience
- [ ] Task completion in < 3 clicks
- [ ] Form submission < 2 minutes
- [ ] Real-time feedback < 500ms
- [ ] Mobile usable one-handed

### Performance
- [ ] First paint < 1.5s
- [ ] Time to interactive < 3s
- [ ] Lighthouse score > 90

### Accessibility
- [ ] WCAG 2.1 AA compliant
- [ ] Keyboard navigable
- [ ] Screen reader tested

---

## 🎯 Design Priorities

**Must Have (P0)**:
1. Request form with validation
2. Chat interface with agents
3. Results preview panel
4. Compliance mode toggle
5. Mobile responsive layout

**Should Have (P1)**:
1. Request history/dashboard
2. Agent activity real-time
3. Download/export options
4. Dark mode support
5. Offline capability

**Nice to Have (P2)**:
1. Advanced search/filter
2. Collaborative features
3. Custom themes
4. Data visualization
5. Admin dashboard

---

## 📅 Timeline Estimate

**Week 1-2**: Research, wireframes, style guide  
**Week 3-4**: High-fidelity mockups (desktop)  
**Week 5**: Responsive designs (tablet/mobile)  
**Week 6**: Interactive prototype  
**Week 7**: Asset creation  
**Week 8**: Documentation & handoff

---

## 📎 Appendix

### Tools Recommended
- **Design**: Figma (with Ant Design System plugin)
- **Icons**: Heroicons, Lucide Icons
- **Prototyping**: Figma, ProtoPie
- **Handoff**: Zeplin, Figma Dev Mode
- **Accessibility**: Stark plugin

### Frameworks for Development
- **Frontend**: React + TypeScript
- **UI Library**: Tailwind CSS + Headless UI
- **PWA**: Workbox
- **State**: Zustand or Redux Toolkit
- **Forms**: React Hook Form + Zod

---

**Contact**: DHG AI Factory Team  
**Version**: 1.0  
**Last Updated**: November 30, 2025

---

**Status**: ✅ Ready for Design Team

This brief provides complete specifications for building a professional, accessible, and user-friendly interface for the DHG AI Factory CME system.
