# DHG AI Factory - Master Implementation Plan & SOPs
## 1. User Interface Strategy (Studio Metaphor)
**Goal:** Create an "Apple-elegant" PWA that feels like a premium native app on iPad/iOS.

### UI/UX Specifications
- **Design System:** Vanilla CSS with "Glassmorphism" (already started). Generous whitespace, frosted glass panels.
- **Structure:**
  - **Left Panel:** Navigation & History (Collapsible on mobile).
  - **Center:** Main Composition Canvas (Chat/Interaction).
  - **Right Panel (Contextual):** 
    - *Prompt Checker:* Real-time analysis of prompt quality.
    - *Refiner:* Suggestions to improve prompts.
    - *Model Settings:* Selector for active models.
- **PWA Features:**
  - Full `manifest.json` for installability.
  - Apple touch icons and splash screens.
  - `viewport-fit=cover` for edge-to-edge design.
  - Offline capability strategy.

## 2. Model Integration Strategy
**Primary Selector:** Dropdown in Header or Right Panel.
**Supported Models (via API/Local):**
1.  **Local LLMs:** Ollama/LocalAI connection.
2.  **Cloud Leaders:**
    -   **Google:** Gemini 1.5 Pro (Latest), Gemini Vision.
    -   **Anthropic:** Claude 3.5 Sonnet (Latest).
    -   **OpenAI:** GPT-4o / Latest.
    -   **Specialized:** Nano Banana Pro (Specific use case), Sora (Video generation).

## 3. Agent Standard Operating Procedures (SOPs)
We will implement these agents in Antigravity/Backend.

### A. The Director (Orchestrator)
*Role:* Primary interface handler.
*SOP:* 
1.  Receive user input.
2.  Route to specific specialist if needed (e.g., "Make a video" -> Visuals Agent).
3.  Aggregate responses and format for UI.

### B. The Visualist (Visuals Agent)
*Role:* Image & Video generation.
*SOP:*
1.  **Input:** Text prompt or image reference.
2.  **Processing:** 
    -   If video: Call Sora API.
    -   If image analysis: Call Gemini Vision.
3.  **Output:** Return media URL or analysis text.

### C. The Wordsmith (Text Agent)
*Role:* Heavy text lifting, reasoning, medical/CME analysis.
*SOP:*
1.  **Context:** Maintain session history.
2.  **Model Selection:** Route to Claude for reasoning, GPT for creative, Local for privacy.

## 4. Implementation Phase Plan
- **Phase 1 (Current):** Perfect the PWA Shell & Glass UI.
- **Phase 2:** Build Settings & Admin Pages.
- **Phase 3:** Implement Model Selector & API Routes.
- **Phase 4:** Build "Prompt Tools" (Checker/Refiner).
