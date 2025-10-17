# Note Assistant Frontend

A warm, humanistic Vue 3 + TypeScript frontend for the Note Assistant multi-dimensional note-taking system.

## 🎨 Design Philosophy

**Modern, clean, warm, and humanistic**

- Earthy color palette (Forest Green, Soft Beige, Clay Orange)
- Centralized design system for consistency
- Type-safe components and API integration
- Calm technology principles - enhances thought without demanding attention

See [DESIGN.md](./DESIGN.md) for complete design system documentation.

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8734` (see [../api/README.md](../api/README.md))

### Installation

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
npm run preview
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── design/              # Design system tokens (colors, typography, spacing, icons)
│   │   ├── colors.ts        # Color palette + semantic mappings
│   │   ├── typography.ts    # Font scales, families, weights
│   │   ├── spacing.ts       # Spacing scale, border radius, shadows
│   │   └── icons.ts         # Icon registry
│   ├── components/
│   │   ├── shared/          # Reusable design system components
│   │   │   ├── Icon.vue
│   │   │   ├── Button.vue
│   │   │   ├── Badge.vue
│   │   │   └── Card.vue
│   │   └── ...              # Feature-specific components
│   ├── composables/         # Vue composables (API integrations)
│   │   └── useNoteCapture.ts
│   ├── views/               # Page-level components
│   │   ├── CaptureView.vue  # Note input & classification
│   │   ├── SearchView.vue   # Smart search + synthesis
│   │   └── GraphView.vue    # Knowledge graph visualization
│   ├── types/
│   │   └── api.ts           # TypeScript types for backend API
│   ├── assets/
│   │   └── icons/           # SVG icons (centralized)
│   ├── App.vue              # Root component with sidebar navigation
│   ├── main.ts              # App entry point + router
│   └── style.css            # Global styles
├── DESIGN.md                # Design system documentation
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 🎨 Design System

All visual design is centralized in `/src/design/` for consistency and easy theming.

### Color Palette

```typescript
import { colors } from '@/design/colors'

colors.forestGreen   // #294936 - Deep earthy green
colors.softBeige     // #EDE9E0 - Warm background
colors.mutedSage     // #9CA89A - Subtle highlights
colors.charcoal      // #343434 - Text
colors.clayOrange    // #D47A44 - Accent/CTAs
```

**Semantic tokens:**
```typescript
colors.background.primary    // Main canvas
colors.text.primary          // Body text
colors.accent.primary        // Primary actions
colors.dimension.hasActionItems  // Action dimension color
```

### Typography

```typescript
import { typography } from '@/design/typography'

typography.fontSize.base     // 16px body text
typography.fontWeight.medium // 500 for UI elements
```

### Spacing

```typescript
import { spacing } from '@/design/spacing'

spacing[4]  // 1rem (16px) - standard padding
spacing[8]  // 2rem (32px) - section gaps
```

### Components

All shared components use design tokens:

```vue
<Button variant="primary" size="lg" icon="search">
  Search
</Button>

<Badge dimension="hasActionItems" />

<Card padding="6" hoverable>
  <!-- content -->
</Card>
```

---

## 🔌 API Integration

### Backend Connection

Frontend connects to backend API at `http://localhost:8734` (configured in `vite.config.ts` proxy).

### Composables

API logic is centralized in composables for reusability:

```typescript
import { useNoteCapture } from '@/composables/useNoteCapture'

const { isLoading, error, result, capture } = useNoteCapture()

await capture('Meeting with Sarah about OAuth2')
// result.value => { title, dimensions, tags, path }
```

### Type Safety

All API types are defined in `src/types/api.ts` based on backend specification:

```typescript
import type { ClassifyResponse, Dimensions, SearchHit } from '@/types/api'
```

---

## 🎯 Development Status

### Phase 1: Core Capture ✅ (Completed)
- [x] Setup Vite + Vue 3 + TypeScript
- [x] Create design system (colors, typography, spacing)
- [x] Build shared components (Icon, Button, Badge, Card)
- [x] Implement CaptureView with textarea
- [x] Create useNoteCapture composable
- [x] Display dimension badges and metadata

### Phase 2: Smart Search (Next)
- [ ] Create SearchView with input
- [ ] Implement useSmartSearch composable
- [ ] Display search results with snippets
- [ ] Show dimension badges on results

### Phase 3: Streaming Synthesis
- [ ] Implement useStreamingSynthesis composable
- [ ] Create StreamingSummary component
- [ ] Integrate SSE (Server-Sent Events)
- [ ] Display real-time summary

### Phase 4: Knowledge Graph
- [ ] Choose graph library (D3.js or Vue Flow)
- [ ] Create GraphView component
- [ ] Implement useGraph composable
- [ ] Build interactive visualization

---

## 🛠️ Development Guidelines

### Adding New Components

1. Use design tokens (no magic values)
2. Define TypeScript interfaces for props
3. Add accessibility attributes (ARIA labels, keyboard nav)
4. Test hover/focus/active states

Example:
```vue
<script setup lang="ts">
import { colors } from '@/design/colors'
import { spacing } from '@/design/spacing'

interface Props {
  title: string
  active?: boolean
}

defineProps<Props>()
</script>
```

### Code Style

- Use Composition API (`<script setup>`)
- Prefer `const` over `let`
- Use TypeScript strict mode
- Keep components focused (single responsibility)

### Design Checklist

Before shipping any component:

- [ ] Uses colors from `design/colors.ts`
- [ ] Uses typography from `design/typography.ts`
- [ ] Uses spacing tokens (no px values)
- [ ] Meets WCAG AA contrast ratios
- [ ] Keyboard accessible
- [ ] Has hover/focus/active states

---

## 📚 Resources

- [Vue 3 Docs](https://vuejs.org/)
- [VueUse Composables](https://vueuse.org/)
- [Backend API Docs](../api/README.md)
- [Design System](./DESIGN.md)

---

## 🐛 Troubleshooting

**Backend connection errors:**
```bash
# Ensure backend is running
cd ../
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8734
```

**TypeScript errors:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

**Version:** 1.0
**Built with:** Vue 3 + TypeScript + Vite
**Last Updated:** 2025-10-16
