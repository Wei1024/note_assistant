<script setup lang="ts">
import { colors } from '@/design/colors'
import { spacing } from '@/design/spacing'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import Icon from '@/components/shared/Icon.vue'
import ToastContainer from '@/components/shared/ToastContainer.vue'

const route = useRoute()
</script>

<template>
  <div class="app">
    <!-- Sidebar Navigation -->
    <nav class="sidebar" :style="sidebarStyle">
      <div class="sidebar__header">
        <h1 :style="{ fontSize: '1.5rem', fontWeight: '600', color: colors.text.onDark }">
          Note Assistant
        </h1>
      </div>

      <div class="sidebar__nav">
        <RouterLink
          to="/"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === 'capture' }"
        >
          <Icon name="capture" size="sm" />
          <span>Capture</span>
        </RouterLink>

        <RouterLink
          to="/search"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === 'search' }"
        >
          <Icon name="search" size="sm" />
          <span>Search</span>
        </RouterLink>

        <RouterLink
          to="/graph"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === 'graph' }"
        >
          <Icon name="graph" size="sm" />
          <span>Graph</span>
        </RouterLink>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="main" :style="mainStyle">
      <RouterView />
    </main>

    <!-- Global Toast Notifications -->
    <ToastContainer />
  </div>
</template>

<script lang="ts">
const sidebarStyle = {
  backgroundColor: colors.background.secondary,
  color: colors.text.onDark,
  padding: spacing[6],
}

const mainStyle = {
  backgroundColor: colors.background.primary,
  padding: spacing[8],
}
</script>

<style scoped>
.app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: v-bind('spacing[8]');
}

.sidebar__header {
  padding-bottom: v-bind('spacing[6]');
  border-bottom: 1px solid rgba(237, 233, 224, 0.2);
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: v-bind('spacing[2]');
}

.nav-item {
  display: flex;
  align-items: center;
  gap: v-bind('spacing[3]');
  padding: v-bind('spacing[3]') v-bind('spacing[4]');
  color: v-bind('colors.text.onDark');
  text-decoration: none;
  border-radius: 8px;
  transition: all 150ms ease;
  font-weight: 500;
}

.nav-item:hover {
  background-color: rgba(237, 233, 224, 0.1);
}

.nav-item--active {
  background-color: v-bind('colors.accent.primary');
  color: v-bind('colors.text.onDark');
}

.main {
  flex: 1;
  overflow-y: auto;
}
</style>
