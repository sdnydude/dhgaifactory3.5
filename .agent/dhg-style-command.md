# DHG Style Guide Slash Command

## Add to LibreChat Prompt Library

**Name:** DHG Style Guide
**Command:** `/dhg-style`

### Prompt Text:

```
Apply the Digital Harmony Group (DHG) official style guide to this work.

## DHG Color Variables

### Light Mode
```css
--dhg-background:       #FAF9F7;  /* Warm off-white */
--dhg-surface:          #FFFFFF;  /* Pure white */
--dhg-surface-elevated: #FFFFFF;  /* Elevated panels */
--dhg-text-primary:     #32374A;  /* Dark blue-gray text */
--dhg-text-secondary:   #71717A;  /* Medium gray */
--dhg-text-placeholder: #A1A1AA;  /* Light gray */
--dhg-border:           #E4E4E7;  /* Border color */
--dhg-border-focus:     #663399;  /* Purple accent */
```

### Dark Mode
```css
--dhg-background:       #1A1D24;  /* Dark blue-black */
--dhg-surface:          #27272A;  /* Dark gray */
--dhg-surface-elevated: #32374A;  /* Elevated panels */
--dhg-text-primary:     #FAF9F7;  /* Warm white text */
--dhg-text-secondary:   #A1A1AA;  /* Light gray */
--dhg-text-placeholder: #71717A;  /* Medium gray */
--dhg-border:           #3F3F46;  /* Border color */
--dhg-border-focus:     #A78BFA;  /* Light purple accent */
```

## Key Principles
1. Use warm off-white (#FAF9F7) not pure white for backgrounds
2. Purple (#663399) is the primary accent color
3. All UIs must support both light and dark modes
4. Use CSS variables, not hardcoded colors

## Logo
Tagline: "AI Agents In Tune With You"

When generating CSS, HTML, or UI designs, use these exact color values and variable names.
```

---

## How to Add in LibreChat

1. Open LibreChat
2. Click the **Prompts** icon in sidebar
3. Click **Create Prompt**
4. Set Name: `DHG Style Guide`
5. Set Command: `/dhg-style`
6. Paste the prompt text above
7. Save

---

## Usage Examples

### When designing UI:
```
/dhg-style Create a login page with dark mode support
```

### When writing CSS:
```
/dhg-style Generate CSS for a card component
```

### When reviewing colors:
```
/dhg-style Check if this code follows DHG style guide
```
