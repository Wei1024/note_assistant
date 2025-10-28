<script setup lang="ts">
import { ref } from 'vue'
import type { SearchResultModel, ExpandedNodeModel, ClusterSummaryModel } from '../types/api'
import {
  ChevronDownIcon,
  ChevronUpIcon,
  UserIcon,
  LightBulbIcon,
  MapPinIcon,
  TagIcon,
  LinkIcon
} from '@heroicons/vue/24/outline'

// Props
interface Props {
  primaryResults: SearchResultModel[]
  expandedResults?: ExpandedNodeModel[]
  clusterSummaries?: ClusterSummaryModel[]
}

const props = withDefaults(defineProps<Props>(), {
  expandedResults: () => [],
  clusterSummaries: () => []
})

// State
const expandedSections = ref({
  expanded: false,
  clusters: false
})

// Methods
function toggleSection(section: 'expanded' | 'clusters') {
  expandedSections.value[section] = !expandedSections.value[section]
}

function getRelationBadgeColor(relation: string): string {
  switch (relation) {
    case 'semantic':
      return 'bg-blue-100 text-blue-700'
    case 'entity_link':
      return 'bg-purple-100 text-purple-700'
    case 'tag_link':
      return 'bg-green-100 text-green-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

function formatScore(score: number): string {
  return (score * 100).toFixed(0) + '%'
}
</script>

<template>
  <div class="search-results">
    <!-- Primary Results -->
    <div v-if="primaryResults.length > 0" class="results-section">
      <h3 class="section-title">
        Top Results
        <span class="result-count">{{ primaryResults.length }}</span>
      </h3>

      <div class="results-list">
        <article
          v-for="result in primaryResults"
          :key="result.note_id"
          class="result-card"
        >
          <!-- Title -->
          <h4 class="result-title">{{ result.title }}</h4>

          <!-- Score indicators -->
          <div class="score-indicators">
            <span class="score-badge primary">
              Match: {{ formatScore(result.score) }}
            </span>
            <span class="score-badge">
              Text: {{ formatScore(result.fts_score) }}
            </span>
            <span class="score-badge">
              Semantic: {{ formatScore(result.vector_score) }}
            </span>
          </div>

          <!-- Snippet -->
          <p class="result-snippet" v-html="result.snippet"></p>

          <!-- Episodic metadata -->
          <div class="metadata-tags">
            <!-- WHO -->
            <div v-if="result.episodic.who.length > 0" class="tag-group">
              <UserIcon class="tag-icon" />
              <span
                v-for="person in result.episodic.who.slice(0, 3)"
                :key="person"
                class="tag"
              >
                {{ person }}
              </span>
            </div>

            <!-- WHAT -->
            <div v-if="result.episodic.what.length > 0" class="tag-group">
              <LightBulbIcon class="tag-icon" />
              <span
                v-for="topic in result.episodic.what.slice(0, 3)"
                :key="topic"
                class="tag"
              >
                {{ topic }}
              </span>
            </div>

            <!-- WHERE -->
            <div v-if="result.episodic.where.length > 0" class="tag-group">
              <MapPinIcon class="tag-icon" />
              <span
                v-for="location in result.episodic.where"
                :key="location"
                class="tag"
              >
                {{ location }}
              </span>
            </div>

            <!-- TAGS -->
            <div v-if="result.episodic.tags.length > 0" class="tag-group">
              <TagIcon class="tag-icon" />
              <span
                v-for="tag in result.episodic.tags.slice(0, 3)"
                :key="tag"
                class="tag"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </article>
      </div>
    </div>

    <!-- Expanded Results (Graph Neighbors) -->
    <div v-if="expandedResults && expandedResults.length > 0" class="results-section expandable">
      <button
        class="section-header"
        @click="toggleSection('expanded')"
      >
        <h3 class="section-title">
          Related Notes (via Graph)
          <span class="result-count">{{ expandedResults.length }}</span>
        </h3>
        <ChevronDownIcon v-if="!expandedSections.expanded" class="chevron-icon" />
        <ChevronUpIcon v-else class="chevron-icon" />
      </button>

      <div v-show="expandedSections.expanded" class="results-list">
        <article
          v-for="node in expandedResults"
          :key="node.note_id"
          class="result-card expanded"
        >
          <!-- Title with relation badge -->
          <div class="expanded-header">
            <h4 class="result-title">{{ node.title }}</h4>
            <span :class="['relation-badge', getRelationBadgeColor(node.relation)]">
              {{ node.relation }}
            </span>
          </div>

          <!-- Connection info -->
          <div class="connection-info">
            <LinkIcon class="connection-icon" />
            <span>
              {{ node.hop_distance }} hop{{ node.hop_distance > 1 ? 's' : '' }} away
              • {{ formatScore(node.relevance_score) }} relevance
            </span>
          </div>

          <!-- Text preview -->
          <p class="result-snippet">{{ node.text_preview }}</p>
        </article>
      </div>
    </div>

    <!-- Cluster Summaries -->
    <div v-if="clusterSummaries && clusterSummaries.length > 0" class="results-section expandable">
      <button
        class="section-header"
        @click="toggleSection('clusters')"
      >
        <h3 class="section-title">
          Cluster Context
          <span class="result-count">{{ clusterSummaries.length }}</span>
        </h3>
        <ChevronDownIcon v-if="!expandedSections.clusters" class="chevron-icon" />
        <ChevronUpIcon v-else class="chevron-icon" />
      </button>

      <div v-show="expandedSections.clusters" class="cluster-list">
        <div
          v-for="cluster in clusterSummaries"
          :key="cluster.cluster_id"
          class="cluster-card"
        >
          <div class="cluster-header">
            <h4 class="cluster-title">{{ cluster.title }}</h4>
            <span class="cluster-size">{{ cluster.size }} notes</span>
          </div>
          <p class="cluster-summary">{{ cluster.summary }}</p>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="primaryResults.length === 0" class="empty-state">
      <p>No results found. Try different keywords or check if your notes are indexed.</p>
    </div>
  </div>
</template>

<style scoped>
.search-results {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.results-section {
  margin-bottom: 32px;
}

.results-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  background: linear-gradient(135deg, #D47A44 0%, #C26A34 100%);
  color: white;
  font-size: 13px;
  font-weight: 600;
  border-radius: 12px;
}

/* Expandable sections */
.expandable .section-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-bottom: 16px;
  transition: opacity 0.2s ease;
}

.expandable .section-header:hover {
  opacity: 0.7;
}

.chevron-icon {
  width: 20px;
  height: 20px;
  color: #6b7280;
  transition: transform 0.2s ease;
}

/* Results list */
.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.result-card:hover {
  border-color: #D47A44;
  box-shadow: 0 4px 12px rgba(212, 122, 68, 0.15);
  transform: translateY(-2px);
}

.result-card.expanded {
  background: #fafafa;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
  line-height: 1.4;
}

/* Score indicators */
.score-indicators {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.score-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
}

.score-badge.primary {
  background: linear-gradient(135deg, #FFF4ED 0%, #FFE9DC 100%);
  color: #C26A34;
}

/* Snippet */
.result-snippet {
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
  margin-bottom: 12px;
}

.result-snippet :deep(b) {
  background: #fef3c7;
  font-weight: 600;
  padding: 2px 4px;
  border-radius: 3px;
}

/* Metadata tags */
.metadata-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tag-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-icon {
  width: 14px;
  height: 14px;
  color: #9ca3af;
  flex-shrink: 0;
}

.tag {
  padding: 3px 8px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
}

/* Expanded results */
.expanded-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.relation-badge {
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.connection-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #6b7280;
}

.connection-icon {
  width: 14px;
  height: 14px;
  color: #9ca3af;
}

/* Cluster cards */
.cluster-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cluster-card {
  background: linear-gradient(135deg, #FFF4ED 0%, #FFE9DC 100%);
  border: 1px solid #FFD9C3;
  border-radius: 12px;
  padding: 16px;
}

.cluster-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.cluster-title {
  font-size: 15px;
  font-weight: 600;
  color: #A85A2C;
}

.cluster-size {
  font-size: 12px;
  font-weight: 600;
  color: #C26A34;
  background: white;
  padding: 4px 8px;
  border-radius: 6px;
}

.cluster-summary {
  font-size: 13px;
  line-height: 1.6;
  color: #B25A24;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: #6b7280;
  font-size: 14px;
}

/* Responsive */
@media (max-width: 640px) {
  .result-card {
    padding: 16px;
  }

  .score-indicators {
    gap: 6px;
  }

  .score-badge {
    font-size: 11px;
    padding: 3px 8px;
  }

  .metadata-tags {
    gap: 8px;
  }

  .tag {
    font-size: 11px;
  }
}
</style>
