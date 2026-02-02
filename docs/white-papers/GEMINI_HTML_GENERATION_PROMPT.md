# Prompt for Gemini: White Paper HTML Production

**Role**: You are an expert Web Designer and Data Visualization Specialist.

**Task**: take the provided Markdown white paper content and transform it into a single, self-contained, interactive HTML file.

**Design Aesthetic**:
- **Style**: Premium "Harvard Business Review" or "McKinsey Insights" aesthetic. Clean, modern, authoritative.
- **Layout**: Two-column responsive magazine layout for the main text. Single-column spanning for major headings and large visuals.
- **Typography**: Serif for headings (e.g., Merriweather or Playfair Display), Sans-serif for body (e.g., Inter or Roboto).
- **Color Palette**:
    - **Primary**: Deep Navy Blue (#0A192F)
    - **Secondary**: DHG Green (#4CAF50) for CME elements
    - **Accent**: Electric Blue (#2196F3) for Studio elements
    - **Background**: White / Off-white (#F5F7FA)

**Interactive Features**:
- **Interactive Graphics**: Using SVG and simple CSS/JS animations.
    - *Example*: Hovering over an agent's name in the Org Chart should show a tooltip with their role description.
    - *Example*: The Timeline should scroll or reveal phases on click.
- **Sticky Table of Contents**: A sidebar that highlights the current section.
- **Responsive implementation**: Collapses to single column on mobile.

**Specific Instructions**:
1.  **Strict Text Fidelity (CRITICAL)**: You are acting as a Typesetter and Developer, NOT an Editor.
    - You must preserve the input text word-for-word.
    - Do not summarize, shorten, or "improve" the copy.
    - Do not fix what you perceive as typos unless they are obvious code errors.
    - Your job is POSITIONAL only (layout), not EDITORIAL.

2.  **Visuals by "Nano Banana Pro"**: 
    - You must generate the SVG graphics yourself, but style them according to the "Nano Banana Pro" aesthetic:
    - **Style Definition**: High-contrast, vibrant, slightly playful but professional (think "Stripe" or "Duolingo" business tier).
    - Use clean lines, distinct geometry, and the DHG color palette.
    - Do not use generic corporate stock art styles.
    - Code these graphics as inline SVGs.

3.  **Single File**: The output must be one `index.html` file containing all HTML, CSS, and JS. No external image dependencies.

**Input Data**:
[PASTE THE FULL MARKDOWN CONTENT OF DHG_AI_FACTORY_WHITE_PAPER.MD HERE]
