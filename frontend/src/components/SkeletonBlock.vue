<template>
  <div class="skeleton-block" :class="variant" :style="{ width, height }">
    <div class="shimmer"></div>
  </div>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'text' },  // text | card | circle | rect
  width: { type: String, default: '100%' },
  height: { type: String, default: '16px' },
})
</script>

<style scoped>
.skeleton-block {
  position: relative;
  overflow: hidden;
  background: #e8eaed;
  border-radius: 4px;
  margin-bottom: 8px;
}
.skeleton-block.card {
  border-radius: 10px;
  min-height: 80px;
}
.skeleton-block.circle {
  border-radius: 50%;
}
.skeleton-block.text {
  border-radius: 4px;
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg,
    transparent 25%,
    rgba(255,255,255,0.6) 50%,
    transparent 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
