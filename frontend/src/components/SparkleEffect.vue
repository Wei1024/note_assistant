<script setup lang="ts">
interface Props {
  show?: boolean
  duration?: number  // How long sparkles show (ms)
}

// Duration prop is defined but not currently used in component logic
// It's here for future enhancement to dynamically control animation timing
withDefaults(defineProps<Props>(), {
  show: false,
  duration: 2000
})
</script>

<template>
  <Transition name="sparkle-fade">
    <div v-if="show" class="sparkle-container">
      <!-- Multiple sparkles at different positions -->
      <div class="sparkle sparkle--1">✨</div>
      <div class="sparkle sparkle--2">⭐</div>
      <div class="sparkle sparkle--3">✨</div>
      <div class="sparkle sparkle--4">⭐</div>
      <div class="sparkle sparkle--5">✨</div>
      <div class="sparkle sparkle--6">💫</div>
    </div>
  </Transition>
</template>

<style scoped>
.sparkle-container {
  position: absolute;
  top: -30px;
  left: -30px;
  right: -30px;
  bottom: -30px;
  pointer-events: none;
  z-index: 10;
}

.sparkle {
  position: absolute;
  font-size: 1.5rem;
  animation: sparkle-float 1.5s ease-out forwards;
}

/* Position each sparkle differently */
.sparkle--1 {
  top: 10%;
  left: 20%;
  animation-delay: 0s;
}

.sparkle--2 {
  top: 5%;
  right: 25%;
  animation-delay: 0.1s;
}

.sparkle--3 {
  top: 30%;
  left: 10%;
  animation-delay: 0.2s;
}

.sparkle--4 {
  top: 25%;
  right: 15%;
  animation-delay: 0.15s;
}

.sparkle--5 {
  bottom: 30%;
  left: 15%;
  animation-delay: 0.3s;
}

.sparkle--6 {
  top: 50%;
  right: 10%;
  animation-delay: 0.25s;
}

/* Sparkle float animation */
@keyframes sparkle-float {
  0% {
    opacity: 0;
    transform: translateY(0) scale(0.5) rotate(0deg);
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translateY(-30px) scale(1.2) rotate(180deg);
  }
}

/* Fade transition */
.sparkle-fade-enter-active,
.sparkle-fade-leave-active {
  transition: opacity 0.3s ease;
}

.sparkle-fade-enter-from,
.sparkle-fade-leave-to {
  opacity: 0;
}
</style>
