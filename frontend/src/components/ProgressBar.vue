<template>
  <div v-if="visible" class="progress-bar-wrap">
    <div class="progress-bar" :class="{ done: progress >= 90, error: hasError }" :style="{ width: progress + '%' }"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const progress = ref(0)
const hasError = ref(false)
let timer = null
let pending = 0

function start() {
  pending++
  if (pending === 1) {
    visible.value = true
    hasError.value = false
    progress.value = 0
    // 模拟渐进度 0-80% (冷启动约30-60秒)
    timer = setInterval(() => {
      if (progress.value < 80) {
        progress.value += Math.random() * 8 + 2
        if (progress.value > 80) progress.value = 80
      }
    }, 800)
  }
}

function done() {
  pending = Math.max(0, pending - 1)
  if (pending === 0) {
    if (timer) clearInterval(timer)
    progress.value = 100
    // 完成后 500ms 隐藏
    setTimeout(() => {
      visible.value = false
      progress.value = 0
    }, 500)
  }
}

function error() {
  pending = Math.max(0, pending - 1)
  if (pending === 0) {
    if (timer) clearInterval(timer)
    hasError.value = true
    progress.value = 100
    setTimeout(() => {
      visible.value = false
      progress.value = 0
      hasError.value = false
    }, 1500)
  }
}

onMounted(() => {
  window._progressBar = { start, done, error }
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  delete window._progressBar
})
</script>

<style scoped>
.progress-bar-wrap {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  height: 3px;
  background: transparent;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4A90D9, #667EEA, #764BA2);
  background-size: 200% 100%;
  transition: width 0.3s ease;
  border-radius: 0 2px 2px 0;
  animation: barShimmer 2s linear infinite;
}

.progress-bar.done {
  background: #27ae60;
  animation: none;
}

.progress-bar.error {
  background: #e74c3c;
  animation: none;
}

@keyframes barShimmer {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
</style>
