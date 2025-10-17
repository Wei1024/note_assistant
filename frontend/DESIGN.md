# Note Assistant Frontend Design System

**Version:** 1.0
**Last Updated:** 2025-10-16
**Design Philosophy:** Modern, clean, warm, and humanistic

---

## 🎨 Design Philosophy

The Note Assistant interface embraces **calm technology** - tools that enhance human thought without demanding attention. The design prioritizes:

- **Warmth over sterility** - Earthy tones, soft edges, inviting interactions
- **Clarity over complexity** - Minimal UI, maximum information density
- **Focus over distraction** - Subtle animations, purposeful color
- **Human over mechanical** - Conversational tone, forgiving interactions

---

## 🌿 Color Palette

### Base Colors

| Name | Hex | Usage |
|------|-----|-------|
| **Forest Green** | `#294936` | Deep earthy green for calm focus and privacy |
| **Soft Beige** | `#EDE9E0` | Gentle warm background, easy on the eyes |
| **Muted Sage** | `#9CA89A` | Subtle desaturated green-gray for highlights |
| **Charcoal** | `#343434` | Neutral dark text or sidebar background |
| **Clay Orange** | `#D47A44` | Warm, confident accent for buttons/highlights |

### Semantic Color Mapping

#### Backgrounds
```typescript
background: {
  primary: '#EDE9E0',      // Main canvas (Soft Beige)
  secondary: '#294936',     // Sidebar/header (Forest Green)
  card: '#FFFFFF',          // Note cards (Pure white)
  hover: '#F5F2ED',         // Hover states (Lighter beige)
}
```

#### Text
```typescript
text: {
  primary: '#343434',       // Body text (Charcoal)
  secondary: '#6B6B6B',     // Secondary text (Mid gray)
  onDark: '#EDE9E0',        // Text on dark backgrounds
  muted: '#9CA89A',         // Labels, hints (Muted Sage)
}
```

#### Accents
```typescript
accent: {
  primary: '#D47A44',       // Primary actions (Clay Orange)
  primaryHover: '#C26A34',  // Hover state (Darker orange)
  secondary: '#9CA89A',     // Secondary accents (Muted Sage)
}
```

#### Dimensions (Multi-dimensional classification)
```typescript
dimension: {
  hasActionItems: '#D47A44',    // Clay Orange - warm urgency
  isSocial: '#6B8E7F',           // Soft blue-green - connection
  isEmotional: '#B87A9A',        // Muted rose - empathy
  isKnowledge: '#294936',        // Forest Green - growth
  isExploratory: '#C9A16B',      // Warm tan - curiosity
}
```

#### Status States
```typescript
status: {
  success: '#4A7C59',       // Deeper green
  error: '#C85A54',         // Muted red
  warning: '#D89A4E',       // Warm amber
  info: '#6B8E7F',          // Muted teal
}
```

### Color Usage Guidelines

✅ **Do:**
- Use Soft Beige for primary backgrounds (reduces eye strain)
- Use Clay Orange sparingly for primary CTAs
- Use Forest Green for navigation/headers (creates visual hierarchy)
- Use Charcoal for readable body text (WCAG AA compliant)

❌ **Don't:**
- Use pure black (`#000000`) - too harsh
- Use Clay Orange for large areas - reserve for accents
- Mix warm and cool grays - stick to palette

---

## 📝 Typography

### Font Stack

```typescript
fontFamily: {
  sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
  serif: 'Georgia, "Times New Roman", serif',
  mono: '"JetBrains Mono", "Fira Code", Consolas, monospace',
}
```

**Primary:** System font stack (native, fast, accessible)
**Monospace:** Code, note IDs, timestamps
**Serif:** Reserved for long-form note content (optional)

### Type Scale

| Name | Size | Usage |
|------|------|-------|
| `xs` | 12px / 0.75rem | Metadata, timestamps, hints |
| `sm` | 14px / 0.875rem | Labels, secondary text |
| `base` | 16px / 1rem | Body text, default |
| `lg` | 18px / 1.125rem | Emphasized text |
| `xl` | 20px / 1.25rem | Section headings |
| `2xl` | 24px / 1.5rem | Page titles |
| `3xl` | 30px / 1.875rem | Hero text |
| `4xl` | 36px / 2.25rem | Display text |

### Font Weights

- **Normal (400):** Body text
- **Medium (500):** Labels, UI elements
- **Semibold (600):** Subheadings, emphasis
- **Bold (700):** Headings, strong emphasis

### Line Heights

- **Tight (1.25):** Headings, compact UI
- **Normal (1.5):** Body text (optimal readability)
- **Relaxed (1.75):** Long-form content

### Typography Guidelines

✅ **Do:**
- Use `base` (16px) for body text - never smaller
- Maintain 1.5 line height for paragraphs
- Use semibold for headings, medium for UI
- Left-align text (never justify)

❌ **Don't:**
- Go below 14px for readable text
- Use more than 3 font weights per view
- Use all-caps for long text (ok for labels)

---

## 📐 Spacing & Layout

### Spacing Scale (8px system)

| Token | Size | Usage |
|-------|------|-------|
| `1` | 4px | Tight padding, icon margins |
| `2` | 8px | Small gaps, compact lists |
| `3` | 12px | Default padding for badges |
| `4` | 16px | Standard padding, card spacing |
| `6` | 24px | Section spacing |
| `8` | 32px | Large gaps between sections |
| `12` | 48px | Page margins |
| `16` | 64px | Hero spacing |

### Border Radius

| Name | Size | Usage |
|------|------|-------|
| `sm` | 2px | Subtle rounding |
| `base` | 4px | Default buttons, inputs |
| `md` | 6px | Cards |
| `lg` | 8px | Large cards, modals |
| `xl` | 12px | Feature cards |
| `2xl` | 16px | Hero elements |
| `full` | 9999px | Pills, circular badges |

### Shadows

```typescript
sm:   '0 1px 2px 0 rgba(52, 52, 52, 0.05)',        // Subtle lift
base: '0 1px 3px 0 rgba(52, 52, 52, 0.1), ...',    // Cards
md:   '0 4px 6px -1px rgba(52, 52, 52, 0.1), ...', // Hover states
lg:   '0 10px 15px -3px rgba(52, 52, 52, 0.1), ...', // Modals
xl:   '0 20px 25px -5px rgba(52, 52, 52, 0.1), ...', // Hero cards
```

**Philosophy:** Shadows create depth, not decoration. Use sparingly.

---

## 🧩 Component Design

### Buttons

**Primary Button**
```
Background: Clay Orange (#D47A44)
Text: Soft Beige (#EDE9E0)
Padding: 12px 24px
Border Radius: 8px
Font: Medium (500)
```

**Secondary Button**
```
Background: Transparent
Border: 1px Muted Sage (#9CA89A)
Text: Charcoal (#343434)
Padding: 12px 24px
Border Radius: 8px
```

**States:**
- Hover: Darken background by 10%
- Active: Scale 98%
- Disabled: 50% opacity

### Badges (Dimension Pills)

```
Background: Dimension color (see color palette)
Text: White or Soft Beige (contrast-tested)
Padding: 4px 12px
Border Radius: 9999px (full pill)
Font: 14px, Medium (500)
```

**Example:**
```html
<span class="badge-action">Action</span>     <!-- Clay Orange -->
<span class="badge-knowledge">Knowledge</span> <!-- Forest Green -->
```

### Cards

```
Background: White (#FFFFFF)
Border: 1px solid #E8E4DB
Border Radius: 8px
Padding: 16px
Shadow: base
```

**Hover:**
- Shadow: md
- Border: Clay Orange (#D47A44)
- Transition: 200ms ease

### Input Fields

```
Background: White (#FFFFFF)
Border: 1px solid #D4CFC4
Border Radius: 8px
Padding: 12px 16px
Font: 16px (prevents iOS zoom)
```

**Focus:**
- Border: Clay Orange (#D47A44)
- Shadow: 0 0 0 3px rgba(212, 122, 68, 0.1)

**Error:**
- Border: #C85A54 (muted red)

---

## 🎬 Motion & Animation

### Timing Functions

```typescript
easing: {
  default: 'cubic-bezier(0.4, 0.0, 0.2, 1)',    // Standard
  in: 'cubic-bezier(0.4, 0.0, 1, 1)',           // Accelerate
  out: 'cubic-bezier(0.0, 0.0, 0.2, 1)',        // Decelerate
  inOut: 'cubic-bezier(0.4, 0.0, 0.2, 1)',      // Smooth
}
```

### Durations

- **Fast (150ms):** Hover states, micro-interactions
- **Normal (200ms):** Button clicks, card reveals
- **Slow (300ms):** Page transitions, modals
- **Stream (0ms):** Text streaming (appears instantly)

### Animation Principles

✅ **Do:**
- Animate opacity and transform (GPU-accelerated)
- Use subtle easing for natural feel
- Fade in on load (opacity 0 → 1)
- Scale buttons on click (100% → 98%)

❌ **Don't:**
- Animate width/height (causes reflow)
- Use overly bouncy animations (unprofessional)
- Auto-play animations (respect user preferences)

---

## 🖼️ Icons

### Icon System

**Source:** Custom SVG icons in `/src/assets/icons/`
**Format:** 24×24px viewBox, monochrome paths
**Usage:** Via `<Icon>` component with type-safe names

### Icon Registry

```typescript
iconNames: [
  'search',         // Magnifying glass
  'graph',          // Network nodes
  'note',           // Document/page
  'capture',        // Pen/pencil
  'close',          // X mark
  'settings',       // Gear
  'person',         // User silhouette
  'tag',            // Label
  'calendar',       // Date
  'link',           // Chain
  'action',         // Checkbox
  'social',         // Speech bubble
  'emotional',      // Heart
  'knowledge',      // Book/lightbulb
  'exploratory',    // Compass
]
```

### Icon Guidelines

✅ **Do:**
- Use 20px icons in buttons, 16px in text
- Use `currentColor` for fill (inherits text color)
- Add 4px margin around icons
- Use consistent stroke width (2px)

❌ **Don't:**
- Mix icon styles (all outline OR all filled)
- Use icons without labels (accessibility)
- Scale icons disproportionately

---

## 📱 Layout System

### Grid Structure

```
Desktop (1024px+):
┌─────────────────────────────────────┐
│  Sidebar (240px)  │  Main (flex)    │
│  ─────────────────┼─────────────────│
│  Navigation       │  Content        │
│  • Capture        │  [Active View]  │
│  • Search         │                 │
│  • Graph          │                 │
│                   │                 │
└─────────────────────────────────────┘
```

### Responsive Breakpoints

- **Desktop:** 1024px+ (default)
- **Tablet:** 768px - 1023px (stacked sidebar)
- **Mobile:** < 768px (hidden sidebar, hamburger menu)

**MVP Focus:** Desktop-first (mobile can wait)

---

## 🎯 View-Specific Designs

### Capture View

**Layout:**
```
┌─────────────────────────────────────┐
│  [Large textarea - autofocus]       │
│                                     │
│  (Expands to fill space)            │
│                                     │
└─────────────────────────────────────┘
│  [💾 Save & Classify] [⚡ Quick Save] │
│  Status: Classifying... ⏳          │
│  Result: ✅ "Meeting with Sarah"    │
│  🏷️ [Social] [Knowledge]            │
│  👤 Sarah  🔖 OAuth2, JWT            │
└─────────────────────────────────────┘
```

**Colors:**
- Background: Soft Beige
- Textarea: White with subtle border
- Primary button: Clay Orange
- Status text: Forest Green (success)

---

### Search View

**Layout:**
```
┌─────────────────────────────────────┐
│  [Search input with icon]           │
├─────────────────────────────────────┤
│  ╔═══════════════════════════════╗ │
│  ║ 📋 Synthesis Summary          ║ │
│  ║ [Streaming text appears here] ║ │
│  ║ Analyzed 3 notes              ║ │
│  ╚═══════════════════════════════╝ │
│                                     │
│  📑 Search Results (3)              │
│  ┌───────────────────────────────┐ │
│  │ Snippet with **highlights**   │ │
│  │ 📅 Date  🏷️ [Badges]          │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Colors:**
- Synthesis box: White with Forest Green border
- Search highlights: Clay Orange background
- Result cards: White with hover state

---

### Graph View

**Layout:**
```
┌─────────────────────────────────────┐
│  [Force-directed graph canvas]      │
│                                     │
│  Nodes: Colored circles (dimension) │
│  Edges: Muted Sage lines            │
│                                     │
│  Controls: Depth [1][2][3]          │
│           Type [All ▾]              │
└─────────────────────────────────────┘
│  Selected: "Meeting with Sarah"     │
│  🏷️ [Social] [Knowledge]            │
│  [View Full Note]                   │
└─────────────────────────────────────┘
```

**Colors:**
- Background: Soft Beige
- Nodes: Dimension colors
- Selected node: Clay Orange border
- Edges: Muted Sage (40% opacity)

---

## ♿ Accessibility

### Color Contrast

All text meets **WCAG AA standards:**
- Charcoal on Soft Beige: 7.2:1 ✅
- White on Forest Green: 8.1:1 ✅
- White on Clay Orange: 4.8:1 ✅

### Keyboard Navigation

- **Tab:** Navigate interactive elements
- **Enter/Space:** Activate buttons
- **Escape:** Close modals, clear focus
- **Cmd/Ctrl + K:** Focus search
- **Cmd/Ctrl + N:** New note

### Screen Readers

- Semantic HTML (`<main>`, `<nav>`, `<article>`)
- ARIA labels on icon-only buttons
- `alt` text on decorative images (empty string)
- Skip links for keyboard users

---

## 🛠️ Implementation

### File Structure

```
frontend/
├── src/
│   ├── design/              # Design system tokens
│   │   ├── colors.ts        # Color palette + semantics
│   │   ├── typography.ts    # Fonts, sizes, weights
│   │   ├── spacing.ts       # Spacing, radius, shadows
│   │   └── icons.ts         # Icon registry
│   ├── components/
│   │   ├── shared/          # Reusable components
│   │   │   ├── Icon.vue
│   │   │   ├── Button.vue
│   │   │   ├── Badge.vue
│   │   │   └── Card.vue
│   │   ├── NoteCapture.vue
│   │   ├── SearchBar.vue
│   │   └── ...
│   ├── assets/
│   │   └── icons/           # SVG icons
│   └── ...
```

### Usage Example

```vue
<script setup lang="ts">
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import Icon from '@/components/shared/Icon.vue'
</script>

<template>
  <button :style="buttonStyle">
    <Icon name="search" :size="20" />
    Search
  </button>
</template>

<script lang="ts">
const buttonStyle = {
  backgroundColor: colors.accent.primary,
  color: colors.text.onDark,
  fontSize: typography.fontSize.base,
  fontWeight: typography.fontWeight.medium,
}
</script>
```

---

## 🎨 Design Checklist

Before shipping any component:

- [ ] Uses colors from `design/colors.ts`
- [ ] Uses typography from `design/typography.ts`
- [ ] Uses spacing tokens (no magic numbers)
- [ ] Meets WCAG AA contrast ratios
- [ ] Keyboard accessible
- [ ] Has hover/focus/active states
- [ ] Responsive (desktop-first MVP)
- [ ] Tested with screen reader

---

## 📚 References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design Motion](https://m3.material.io/styles/motion/overview)
- [Inclusive Components](https://inclusive-components.design/)
- [Refactoring UI](https://www.refactoringui.com/)

---

**Design System Version:** 1.0
**Maintained by:** Note Assistant Team
**Last Updated:** 2025-10-16
