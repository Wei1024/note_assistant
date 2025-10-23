<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing } from '@/design/spacing'

interface Tag {
  id: string
  name: string
  level: number
  use_count: number
}

const props = defineProps<{
  query: string
  position: { top: number; left: number }
}>()

const emit = defineEmits<{
  select: [tag: string]
  close: []
}>()

const tags = ref<Tag[]>([])
const loading = ref(false)
const selectedIndex = ref(0)

// Debounced search
let searchTimeout: number | null = null

watch(() => props.query, async (newQuery) => {
  if (!newQuery) {
    tags.value = []
    return
  }

  // Debounce API calls (300ms)
  if (searchTimeout) clearTimeout(searchTimeout)

  searchTimeout = window.setTimeout(async () => {
    loading.value = true
    try {
      const res = await fetch(`http://localhost:8000/tags/search?q=${encodeURIComponent(newQuery)}&limit=10`)
      const data = await res.json()
      tags.value = data.tags || []
      selectedIndex.value = 0
    } catch (error) {
      console.error('Tag search failed:', error)
      tags.value = []
    } finally {
      loading.value = false
    }
  }, 300)
}, { immediate: true })

function selectTag(tagName: string) {
  emit('select', tagName)
}

function selectCurrent() {
  if (tags.value.length > 0) {
    selectTag(tags.value[selectedIndex.value].name)
  } else if (props.query) {
    // Create new tag
    selectTag(props.query)
  }
}

// Keyboard navigation
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, tags.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    selectCurrent()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (searchTimeout) clearTimeout(searchTimeout)
})

// Styling
const dropdownStyle = {
  position: 'fixed',
  zIndex: 1000,
  background: colors.background.primary,
  border: `1px solid ${colors.border.default}`,
  borderRadius: '8px',
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
  maxHeight: '300px',
  overflowY: 'auto',
  minWidth: '250px',
  maxWidth: '400px',
}

const optionStyle = (isSelected: boolean) => ({
  padding: `${spacing[2]} ${spacing[3]}`,
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  backgroundColor: isSelected ? colors.background.hover : 'transparent',
  borderBottom: `1px solid ${colors.border.subtle}`,
})

const tagNameStyle = (level: number) => ({
  fontFamily: 'monospace',
  color: colors.accent.primary,
  fontSize: typography.fontSize.sm,
  paddingLeft: level > 0 ? `${level * 12}px` : '0',
})

const tagCountStyle = {
  fontSize: typography.fontSize.xs,
  color: colors.text.muted,
  marginLeft: spacing[2],
}

const loadingStyle = {
  padding: spacing[3],
  color: colors.text.muted,
  fontSize: typography.fontSize.sm,
  textAlign: 'center',
}

const noResultsStyle = {
  padding: spacing[3],
  color: colors.text.secondary,
  fontSize: typography.fontSize.sm,
  fontStyle: 'italic',
}
</script>

<template>
  <div
    class="tag-autocomplete"
    :style="{
      ...dropdownStyle,
      top: position.top + 'px',
      left: position.left + 'px',
    } as any"
  >
    <div v-if="loading" :style="loadingStyle as any">
      Searching...
    </div>

    <template v-else>
      <div
        v-for="(tag, index) in tags"
        :key="tag.id"
        :style="optionStyle(index === selectedIndex) as any"
        @click="selectTag(tag.name)"
        @mouseenter="selectedIndex = index"
        class="tag-option"
      >
        <span :style="tagNameStyle(tag.level) as any">
          #{{ tag.name }}
        </span>
        <span :style="tagCountStyle as any">
          {{ tag.use_count }}
        </span>
      </div>

      <div
        v-if="tags.length === 0 && query"
        :style="noResultsStyle as any"
        @click="selectTag(query)"
        class="tag-option"
      >
        Create "#{{ query }}"
      </div>
    </template>
  </div>
</template>

<style scoped>
.tag-autocomplete {
  animation: fadeIn 0.15s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tag-option {
  transition: background-color 0.1s ease;
}

.tag-option:last-child {
  border-bottom: none;
}

.tag-autocomplete::-webkit-scrollbar {
  width: 8px;
}

.tag-autocomplete::-webkit-scrollbar-track {
  background: transparent;
}

.tag-autocomplete::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 4px;
}

.tag-autocomplete::-webkit-scrollbar-thumb:hover {
  background: #bbb;
}
</style>
