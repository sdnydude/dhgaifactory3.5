# Digital Harmony Group AI Factory - UI Transformation & Agent SOPs

## Overview
This document outlines the plan to transform the DHG AI Factory Web UI into a premium, feature-rich interface and establishes Standard Operating Procedures (SOPs) for the Antigravity agents responsible for its development and maintenance.

---

## Part 1: Agent SOPs (Antigravity Roles)
To ensure high-quality, systematic development, we define the following agent roles (simulated by Antigravity) and their SOPs.

### 1. The Architect Agent (UI/UX Strategy)
**Goal:** Maintain structural integrity, design patterns, and user flow.
**SOP:**
1.  **Requirement Analysis:** Before any code is written, review the request against the "Premium Design" mandate.
2.  **Component Definition:** Define the component hierarchy and state management strategy.
3.  **Design Review:** Verify that colors, typography, and spacing align with `design-system.css`.
4.  **Documentation:** Update `WARP.md` or architecture docs when major flows change.

### 2. The Frontend Builder (Implementation)
**Goal:** Execute the Architect's plan with clean, performant React & Vanilla CSS code.
**SOP:**
1.  **Atomic Development:** Build small, reusable components first (e.g., `Button`, `Panel`, `Icon`).
2.  **Style Segregation:** Use `components.css` or scoped styles, referencing CSS variables from `design-system.css`.
3.  **Responsiveness:** Always implement mobile-responsive layouts using Flexbox/Grid and media queries.
4.  **Animation:** Apply `framer-motion` for transitions to ensure a "live" feel.

### 3. The Integration Specialist (API & Backend)
**Goal:** Connect the UI to the AI Factory backend and external LLM APIs.
**SOP:**
1.  **API Abstraction:** Create hook-based abstractions (e.g., `useLLM`, `useVision`) for API interactions.
2.  **Error Handling:** Implement graceful degradation and user notifications (Toast) for network failures.
3.  **Security:** Ensure API keys are managed securely (never hardcoded, use env vars/backend proxy).
4.  **Data Flow:** Manage WebSocket connections for real-time streaming responses.

### 4. The QA & Refiner (Polishing)
**Goal:** Ensure the "Wow" factor.
**SOP:**
1.  **Visual Inspection:** Check for alignment, contrast ratios, and "premium" feel (glassmorphism consistency).
2.  **Interaction Testing:** Verify hover states, loading states, and error states.
3.  **Performance Check:** Ensure 60fps animations and fast interactions.

---

## Part 2: UI Implementation Plan

### 1. Core Layout & Navigation
*   **Goal:** Create a "cockpit" feel with panels.
*   **Features:**
    *   **Sidebar:** Navigation for Chat, History, Settings, Admin.
    *   **Right Panel (Collapsible):** "Prompt Refiner" & "Checker".
    *   **Main Stage:** Chat interface / Work surface.
    *   **Top Bar:** Model Selector & Status.

### 2. Functional Modules
*   **Prompt Checker & Refiner:**
    *   Dedicated panel to analyze prompt quality (length, specificity).
    *   "Refine" button to auto-improve prompts using an internal LLM call.
*   **LLM Selector:**
    *   Dropdown with categories: Local (Ollama/LM Studio), Cloud (Gemini, Claude, GPT), Specialized (Nano Banana Pro, Sora).
    *   Visual indicators for "Active" and "Ready".
*   **Gemini Vision Integration:**
    *   Drag-and-drop zone in the chat input.
    *   Image preview with "Analyze" capabilities.

### 3. Admin & Settings Pages
*   **Admin Dashboard:**
    *   System Health (Service uptime).
    *   API Key Management (Secure input fields).
    *   User Management (if applicable).
*   **User Settings:**
    *   Theme toggle (Light/Dark/DHG Premium).
    *   Default Model preferences.
    *   Notification settings.

### 4. Iconography & Aesthetics
*   **Strategy:** Use `lucide-react` with custom SVG filters/gradients for an "Original" look.
*   **Theme:** "Deep Space Harmony" – Dark blues (`#0F172A`), vibrant accents (`#8B5CF6`, `#FF6B35`), glassmorphism overlays.

---

## Part 3: Action Plan
1.  **Foundation:** Update `design-system.css` for new panel layouts and "premium" gradients.
2.  **Components:** Build `Panel`, `ModelSelector`, `PromptRefiner`.
3.  **Pages:** Flesh out `AdminPage` and `SettingsPage`.
4.  **Integration:** Wire up the Model Selector to the backend/WebSocket.
