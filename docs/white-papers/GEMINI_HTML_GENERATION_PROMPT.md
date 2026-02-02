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

2.  **Visuals Strategy (2-Step Process)**: 
    - **Step A (HTML)**: In the HTML code, use `<img>` tags with local filenames for the visuals (e.g., `<img src="visual1_hybrid_workforce.png" class="visual-img">`). **DO NOT** generate SVG code. Use clean placeholders.
    - **Step B (Image Prompts)**: After the HTML code block, provide a separate list of **11 Optimized Image Generation Prompts**. I will use these prompts with Nano Banana Pro to generate the actual assets.
    - **Style for Prompts**: Write the prompts to enforce the "Nano Banana Pro" aesthetic: High-fidelity, 4K, photorealistic-meets-illustrative, consistent text rendering.

3.  **Single File**: The output should comprise the `index.html` code block followed by the `Image Prompts` text block.

**Input Data**:
[PASTE THE FULL MARKDOWN CONTENT OF DHG_AI_FACTORY_WHITE_PAPER.MD HERE]
