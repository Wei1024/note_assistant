<script setup lang="ts">
import { ref, watch } from 'vue'
import { MagnifyingGlassIcon, SparklesIcon } from '@heroicons/vue/24/outline'

// Props
interface Props {
  loading?: boolean
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  placeholder: 'Ask anything about your notes...'
})

// Emits
const emit = defineEmits<{
  search: [query: string, synthesize: boolean]
}>()

// State
const query = ref('')
const synthesizeEnabled = ref(true)

// Focus input on mount
const inputRef = ref<HTMLInputElement | null>(null)

// Methods
function handleSearch() {
  const trimmedQuery = query.value.trim()
  if (!trimmedQuery) return

  emit('search', trimmedQuery, synthesizeEnabled.value)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSearch()
  }
}

// Auto-focus on mount
watch(() => inputRef.value, (el) => {
  if (el) el.focus()
}, { immediate: true })
</script>

<template>
  <div class="search-bar">
    <!-- Search input -->
    <div class="search-input-container">
      <MagnifyingGlassIcon class="search-icon" />

      <input
        ref="inputRef"
        v-model="query"
        type="text"
        class="search-input"
        :placeholder="placeholder"
        :disabled="loading"
        @keydown="handleKeydown"
      />

      <!-- Search button -->
      <button
        class="search-button"
        :class="{ loading }"
        :disabled="loading || !query.trim()"
        @click="handleSearch"
      >
        <span v-if="!loading">Search</span>
        <span v-else class="loading-spinner"></span>
      </button>
    </div>

    <!-- Synthesis toggle -->
    <div class="synthesis-toggle">
      <label class="toggle-label">
        <input
          v-model="synthesizeEnabled"
          type="checkbox"
          class="toggle-checkbox"
          :disabled="loading"
        />
        <span class="toggle-switch"></span>
        <SparklesIcon class="toggle-icon" />
        <span class="toggle-text">
          {{ synthesizeEnabled ? 'AI Synthesis enabled' : 'Search only' }}
        </span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.search-bar {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.search-input-container {
  position: relative;
  display: flex;
  align-items: center;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 4px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.search-input-container:focus-within {
  border-color: #D47A44;
  box-shadow: 0 0 0 3px rgba(212, 122, 68, 0.1),
              0 4px 12px rgba(0, 0, 0, 0.08);
}

.search-icon {
  width: 20px;
  height: 20px;
  color: #9ca3af;
  margin-left: 12px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 12px 16px;
  font-size: 15px;
  background: transparent;
  color: #1f2937;
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-button {
  padding: 10px 24px;
  background: linear-gradient(135deg, #D47A44 0%, #C26A34 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 80px;
}

.search-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #C26A34 0%, #B25A24 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(212, 122, 68, 0.3);
}

.search-button:active:not(:disabled) {
  transform: translateY(0);
}

.search-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Synthesis toggle */
.synthesis-toggle {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  padding: 8px 16px;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.toggle-label:hover {
  background: rgba(212, 122, 68, 0.05);
}

.toggle-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
  background: #e5e7eb;
  border-radius: 12px;
  transition: background 0.3s ease;
}

.toggle-switch::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-checkbox:checked + .toggle-switch {
  background: linear-gradient(135deg, #D47A44 0%, #C26A34 100%);
}

.toggle-checkbox:checked + .toggle-switch::before {
  left: 22px;
}

.toggle-checkbox:disabled + .toggle-switch {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-icon {
  width: 18px;
  height: 18px;
  color: #D47A44;
  transition: color 0.2s ease;
}

.toggle-checkbox:checked ~ .toggle-icon {
  color: #C26A34;
}

.toggle-text {
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
  transition: color 0.2s ease;
}

.toggle-checkbox:checked ~ .toggle-text {
  color: #C26A34;
}

/* Responsive */
@media (max-width: 640px) {
  .search-input-container {
    padding: 2px;
  }

  .search-input {
    padding: 10px 12px;
    font-size: 14px;
  }

  .search-button {
    padding: 8px 16px;
    font-size: 13px;
    min-width: 70px;
  }

  .toggle-text {
    font-size: 13px;
  }
}
</style>
