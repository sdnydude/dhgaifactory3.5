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
1.  **Content**: Use the full text provided below. Do not summarize.
2.  **Visuals**: You MUST generate the graphics described in the "Appendix: Visual Specifications" section using SVG code directly embedded in the HTML.
    - Do not use placeholders like `[Insert Image Here]`.
    - Actually code the SVG visuals (Org charts, Swimlanes, Bar charts).
    - Make them look professional (gradients, rounded corners, clear labels).
3.  **Single File**: The output must be one `index.html` file containing all HTML, CSS, and JS. No external image dependencies (use embedded SVGs or Data URIs).

**Input Data**:
[PASTE THE FULL MARKDOWN CONTENT OF DHG_AI_FACTORY_WHITE_PAPER.MD HERE]
