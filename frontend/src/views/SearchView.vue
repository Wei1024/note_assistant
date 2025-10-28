<script setup lang="ts">
import { ref } from 'vue'
import SearchBar from '@/components/SearchBar.vue'
import SynthesisDisplay from '@/components/SynthesisDisplay.vue'
import SearchResults from '@/components/SearchResults.vue'
import { useSearch } from '@/composables/useSearch'
import { useToast } from '@/composables/useToast'

// Composables
const {
  isSearching,
  isSynthesizing,
  error,
  primaryResults,
  expandedResults,
  clusterSummaries,
  synthesisText,
  notesAnalyzed,
  hasClusterContext,
  hasExpandedContext,
  synthesizeStream,
  search
} = useSearch()

const { showToast } = useToast()

// State
const currentQuery = ref('')
const lastSearchWasSynthesis = ref(false)

// Methods
async function handleSearch(query: string, synthesize: boolean) {
  currentQuery.value = query
  lastSearchWasSynthesis.value = synthesize

  try {
    if (synthesize) {
      // Execute streaming synthesis
      await synthesizeStream(query, 10, true, 1)
    } else {
      // Execute hybrid search only
      await search(query, 10, true, 1)
    }

    // Show success toast if results found
    if (primaryResults.value.length > 0) {
      showToast({
        type: 'success',
        message: synthesize
          ? `Synthesized ${notesAnalyzed.value} notes`
          : `Found ${primaryResults.value.length} results`
      })
    } else {
      showToast({
        type: 'info',
        message: 'No notes found matching your query'
      })
    }
  } catch (err) {
    showToast({
      type: 'error',
      message: error.value || 'Search failed'
    })
  }
}
</script>

<template>
  <div class="search-view">
    <!-- Header -->
    <div class="header">
      <h1 class="title">Search & Synthesis</h1>
      <p class="subtitle">
        Ask questions about your notes using hybrid search + AI synthesis
      </p>
    </div>

    <!-- Search Bar -->
    <div class="search-section">
      <SearchBar
        :loading="isSearching || isSynthesizing"
        @search="handleSearch"
      />
    </div>

    <!-- Synthesis Display (when enabled) -->
    <div v-if="lastSearchWasSynthesis" class="synthesis-section">
      <SynthesisDisplay
        :text="synthesisText"
        :notes-analyzed="notesAnalyzed"
        :is-loading="isSynthesizing"
        :has-cluster-context="hasClusterContext"
        :has-expanded-context="hasExpandedContext"
      />
    </div>

    <!-- Search Results -->
    <div v-if="primaryResults.length > 0" class="results-section">
      <SearchResults
        :primary-results="primaryResults"
        :expanded-results="expandedResults"
        :cluster-summaries="clusterSummaries"
      />
    </div>

    <!-- Empty state (when not searching and no results) -->
    <div
      v-if="!isSearching && !isSynthesizing && primaryResults.length === 0 && !currentQuery"
      class="empty-state"
    >
      <div class="empty-content">
        <svg
          class="empty-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <h3 class="empty-title">Search your knowledge</h3>
        <p class="empty-description">
          Enter a query above to search your notes with hybrid FTS + vector similarity.<br />
          Enable AI synthesis to get coherent answers across multiple notes.
        </p>

        <div class="features">
          <div class="feature">
            <div class="feature-icon">🔍</div>
            <div class="feature-content">
              <h4>Hybrid Search</h4>
              <p>Combines keyword matching (FTS5) with semantic similarity (embeddings)</p>
            </div>
          </div>

          <div class="feature">
            <div class="feature-icon">🕸️</div>
            <div class="feature-content">
              <h4>Graph Expansion</h4>
              <p>Includes contextually connected notes via knowledge graph edges</p>
            </div>
          </div>

          <div class="feature">
            <div class="feature-icon">✨</div>
            <div class="feature-content">
              <h4>AI Synthesis</h4>
              <p>LLM generates coherent summaries across your notes in real-time</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-view {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  min-height: 100vh;
}

/* Header */
.header {
  text-align: center;
  margin-bottom: 48px;
}

.title {
  font-size: 32px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  color: #6b7280;
  max-width: 600px;
  margin: 0 auto;
}

/* Search Section */
.search-section {
  margin-bottom: 48px;
}

/* Synthesis Section */
.synthesis-section {
  margin-bottom: 48px;
}

/* Results Section */
.results-section {
  margin-bottom: 48px;
}

/* Empty State */
.empty-state {
  margin-top: 64px;
}

.empty-content {
  text-align: center;
  max-width: 600px;
  margin: 0 auto;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: #d1d5db;
  margin: 0 auto 24px;
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
}

.empty-description {
  font-size: 15px;
  line-height: 1.6;
  color: #6b7280;
  margin-bottom: 48px;
}

/* Features */
.features {
  display: flex;
  flex-direction: column;
  gap: 24px;
  text-align: left;
}

.feature {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.feature:hover {
  border-color: #D47A44;
  box-shadow: 0 4px 12px rgba(212, 122, 68, 0.1);
}

.feature-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.feature-content h4 {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.feature-content p {
  font-size: 14px;
  line-height: 1.5;
  color: #6b7280;
}

/* Responsive */
@media (max-width: 768px) {
  .search-view {
    padding: 24px 16px;
  }

  .header {
    margin-bottom: 32px;
  }

  .title {
    font-size: 28px;
  }

  .subtitle {
    font-size: 14px;
  }

  .search-section,
  .synthesis-section,
  .results-section {
    margin-bottom: 32px;
  }

  .empty-state {
    margin-top: 48px;
  }

  .empty-icon {
    width: 48px;
    height: 48px;
  }

  .empty-title {
    font-size: 20px;
  }

  .empty-description {
    font-size: 14px;
  }

  .features {
    gap: 16px;
  }

  .feature {
    padding: 16px;
  }

  .feature-icon {
    font-size: 28px;
  }

  .feature-content h4 {
    font-size: 15px;
  }

  .feature-content p {
    font-size: 13px;
  }
}

@media (max-width: 640px) {
  .title {
    font-size: 24px;
  }

  .feature {
    flex-direction: column;
    text-align: center;
  }

  .feature-content {
    text-align: center;
  }
}
</style>
