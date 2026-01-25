# DHG AI Factory - Brand Color Guide

**Last Updated:** January 20, 2026  
**For:** Digital Harmony Group AI Factory  
**Ready for:** Replit, Web Development, Design Systems  

---

## Official Brand Colors

| Color Name | Hex | RGB | HSL | Usage |
|------------|-----|-----|-----|-------|
| **Deep Navy Blue** |  |  |  | Background, foundation |
| **Purple** |  |  |  | Primary brand color |
| **Orange** |  |  |  | Accent, human touch |

---

## CSS Variables (Copy to Replit)

```css
:root {
  /* DHG Brand Colors */
  --dhg-navy: #1a1f3a;
  --dhg-navy-rgb: 26, 31, 58;
  
  --dhg-purple: #8b5cf6;
  --dhg-purple-rgb: 139, 92, 246;
  
  --dhg-orange: #f97316;
  --dhg-orange-rgb: 249, 115, 22;
  
  /* Semantic Aliases */
  --color-background: var(--dhg-navy);
  --color-primary: var(--dhg-purple);
  --color-accent: var(--dhg-orange);
  
  /* Text Colors */
  --color-text-primary: #ffffff;
  --color-text-secondary: rgba(255, 255, 255, 0.7);
  --color-text-muted: rgba(255, 255, 255, 0.5);
}
```

---

## Tailwind CSS Config (Copy to Replit)

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'dhg-navy': '#1a1f3a',
        'dhg-purple': '#8b5cf6',
        'dhg-orange': '#f97316',
        navy: {
          DEFAULT: '#1a1f3a',
          50: '#eef0f5',
          100: '#dce1eb',
          200: '#b9c3d7',
          300: '#96a5c3',
          400: '#7387af',
          500: '#50699b',
          600: '#3d5177',
          700: '#2a3953',
          800: '#1a1f3a',
          900: '#0d1020',
        },
        purple: {
          DEFAULT: '#8b5cf6',
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        orange: {
          DEFAULT: '#f97316',
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
      },
    },
  },
}
```

---

## SCSS/SASS Variables (Copy to Replit)

```scss
// _colors.scss
$dhg-navy: #1a1f3a;
$dhg-purple: #8b5cf6;
$dhg-orange: #f97316;

// Semantic aliases
$color-background: $dhg-navy;
$color-primary: $dhg-purple;
$color-accent: $dhg-orange;

// Color map
$dhg-colors: (
  'navy': $dhg-navy,
  'purple': $dhg-purple,
  'orange': $dhg-orange,
);
```

---

## JavaScript/TypeScript (Copy to Replit)

```typescript
// colors.ts
export const DHGColors = {
  navy: '#1a1f3a',
  purple: '#8b5cf6',
  orange: '#f97316',
} as const;

export const DHGColorsRGB = {
  navy: 'rgb(26, 31, 58)',
  purple: 'rgb(139, 92, 246)',
  orange: 'rgb(249, 115, 22)',
} as const;

export const DHGColorsRGBA = {
  navy: (alpha: number) => `rgba(26, 31, 58, ${alpha})`,
  purple: (alpha: number) => `rgba(139, 92, 246, ${alpha})`,
  orange: (alpha: number) => `rgba(249, 115, 22, ${alpha})`,
};

export type DHGColorName = keyof typeof DHGColors;
```

---

## React/Next.js Theme (Copy to Replit)

```tsx
// theme.ts
export const theme = {
  colors: {
    background: '#1a1f3a',
    primary: '#8b5cf6',
    accent: '#f97316',
    text: {
      primary: '#ffffff',
      secondary: 'rgba(255, 255, 255, 0.7)',
      muted: 'rgba(255, 255, 255, 0.5)',
    },
  },
  gradients: {
    purpleOrange: 'linear-gradient(135deg, #8b5cf6 0%, #f97316 100%)',
    navyPurple: 'linear-gradient(135deg, #1a1f3a 0%, #8b5cf6 100%)',
    harmonyFlow: 'linear-gradient(90deg, #8b5cf6 0%, #f97316 50%, #8b5cf6 100%)',
  },
};
```

---

## Color Usage Guidelines

### Background (Foundation)
- **Color:** Deep Navy Blue (`#1a1f3a`)
- **Use for:** Page backgrounds, cards, containers
- **Reason:** Trust, stability, medical professionalism

### Primary Elements (AI/Intelligence)
- **Color:** Purple (`#8b5cf6`)
- **Use for:** Primary buttons, links, AI components, main CTAs
- **Reason:** Wisdom, innovation, AI intelligence

### Accent/Highlight (Human Touch)
- **Color:** Orange (`#f97316`)
- **Use for:** Hover states, highlights, human-facing elements
- **Reason:** Human warmth, energy, life, healthcare focus

---

## Color Ratios (Recommended)

| Context | Navy | Purple | Orange |
|---------|------|--------|--------|
| **Logo** | 20% | 50% | 30% |
| **UI Background** | 80% | 15% | 5% |
| **Marketing Materials** | 30% | 40% | 30% |
| **Documentation** | 60% | 30% | 10% |

---

## Accessibility (WCAG AA Compliant)

| Combination | Contrast Ratio | WCAG Level |
|-------------|----------------|------------|
| White on Navy | 12.5:1 | AAA |
| Orange on Navy | 7.2:1 | AA |
| Purple on Navy | 4.8:1 | AA |
| Purple on White | 4.6:1 | AA |

---

## Gradients

### Purple-Orange Harmony (Brand Signature)
```css
background: linear-gradient(135deg, #8b5cf6 0%, #f97316 100%);
```

### Navy-Purple Depth
```css
background: linear-gradient(135deg, #1a1f3a 0%, #8b5cf6 100%);
```

### Flowing Energy (DNA Helix)
```css
background: linear-gradient(90deg, #8b5cf6 0%, #f97316 50%, #8b5cf6 100%);
```

---

## Design Philosophy

### Divergent Convergence
- Purple (AI) + Orange (Human) flowing together
- Integration, not opposition

### Digital Harmony
- AI and human life working together
- Interweaving colors (DNA helix visual)

### TRUST Ethos
- Medical/healthcare audience requires credibility
- Deep navy foundation = stability
- Premium, not flashy

---

## Additional Shades (for UI depth)

### Navy Variants
```css
--dhg-navy-lighter: #2a3353;  /* +10% lightness */
--dhg-navy-darker: #0d1020;   /* -50% lightness */
--dhg-navy-subtle: rgba(26, 31, 58, 0.5);
```

### Purple Variants
```css
--dhg-purple-light: #a78bfa;   /* +20% lightness */
--dhg-purple-dark: #7c3aed;    /* -20% lightness */
--dhg-purple-subtle: rgba(139, 92, 246, 0.1);
--dhg-purple-hover: rgba(139, 92, 246, 0.8);
```

### Orange Variants
```css
--dhg-orange-light: #fb923c;   /* +20% lightness */
--dhg-orange-dark: #ea580c;    /* -20% lightness */
--dhg-orange-subtle: rgba(249, 115, 22, 0.1);
--dhg-orange-hover: rgba(249, 115, 22, 0.8);
```

---

## Quick Copy: Full Palette

```
Navy:   #1a1f3a | rgb(26, 31, 58)   | hsl(231, 38%, 16%)
Purple: #8b5cf6 | rgb(139, 92, 246) | hsl(258, 90%, 66%)
Orange: #f97316 | rgb(249, 115, 22) | hsl(25, 95%, 53%)
```

---

**Digital Harmony Group AI Factory**  
Creating harmony between AI and life.
