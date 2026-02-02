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

2.  **Visuals by "Nano Banana Pro" (Image Generation)**: 
    - You must use **Nano Banana Pro** (Google's advanced image model) to generate the 11 visual assets defined in the Appendix.
    - **Do not** code simple SVGs. Use the full power of the image generator.
    - **Text Rendering**: Leverage Nano Banana Pro's superior text capability for the Dashboards, Org Charts, and Swimlanes. The text in the images must be legible and match the copy provided.
    - **Character Consistency**: Ensure the characters (Sarah, Marcus) and Agent Avatars (Doc, Sage, Ace) remain consistent across all visuals (Visual 1, 3, and 6).
    - **Style**: High-fidelity, 4K-ready, photorealistic-meets-illustrative style (premium corporate aesthetic).
    - **Integration**: Generate the images, then embed them into the HTML layout (or provide specific placeholders if generation happens in a separate step).

**Input Data**:
[PASTE THE FULL MARKDOWN CONTENT OF DHG_AI_FACTORY_WHITE_PAPER.MD HERE]
