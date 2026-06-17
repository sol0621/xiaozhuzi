<template>
  <div class="voice-player" v-if="isSupported">
    <div class="vp-controls">
      <!-- 播放/暂停 -->
      <button
        v-if="!isPlaying"
        class="vp-btn vp-btn-play"
        @click="$emit('play')"
        title="朗读讲解"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        <span>{{ label || '朗读讲解' }}</span>
      </button>
      <template v-else>
        <button class="vp-btn vp-btn-icon" @click="isPaused ? $emit('resume') : $emit('pause')" :title="isPaused ? '继续' : '暂停'">
          <svg v-if="isPaused" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
        </button>
        <button class="vp-btn vp-btn-icon" @click="$emit('stop')" title="停止">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12"/></svg>
        </button>
      </template>

      <!-- 语速选择 -->
      <div class="vp-rate">
        <button
          v-for="r in rates"
          :key="r"
          :class="{ active: rate === r }"
          @click="$emit('setRate', r)"
        >{{ r }}x</button>
      </div>
    </div>

    <!-- 进度指示 -->
    <div v-if="isPlaying && totalSegments > 0" class="vp-progress">
      <div
        v-for="i in totalSegments"
        :key="i"
        :class="['vp-dot', {
          active: i - 1 === currentSegment,
          done: i - 1 < currentSegment,
        }]"
      ></div>
      <span class="vp-info">{{ currentSegment + 1 }}/{{ totalSegments }}</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="vp-error">{{ error }}</div>
  </div>

  <!-- 不支持时的降级提示 -->
  <div v-else class="voice-player vp-unsupported">
    <span class="vp-unsupported-text">⚠️ 您的浏览器不支持语音播报</span>
    <span class="vp-unsupported-hint">建议使用 Chrome 或 Edge 浏览器打开</span>
  </div>
</template>

<script setup>
defineProps({
  isPlaying: { type: Boolean, default: false },
  isPaused: { type: Boolean, default: false },
  currentSegment: { type: Number, default: -1 },
  totalSegments: { type: Number, default: 0 },
  rate: { type: Number, default: 1 },
  isSupported: { type: Boolean, default: true },
  error: { type: String, default: null },
  label: { type: String, default: '' },
})

defineEmits(['play', 'pause', 'resume', 'stop', 'setRate'])

const rates = [0.75, 1, 1.5]
</script>

<style scoped>
.voice-player {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #F0F5FF;
  border: 1px solid #D4E2FC;
  border-radius: 10px;
  padding: 10px 14px;
}

.vp-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vp-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  padding: 8px 14px;
  transition: background 0.2s;
}

.vp-btn-play {
  background: #4A90D9;
  color: #fff;
}

.vp-btn-play:hover { background: #357ABD; }

.vp-btn-icon {
  background: #fff;
  color: #4A90D9;
  border: 1px solid #D4E2FC;
  padding: 8px 10px;
}

.vp-btn-icon:hover { background: #E8F2FC; }

.vp-rate {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.vp-rate button {
  padding: 4px 10px;
  border: 1px solid #D4E2FC;
  border-radius: 6px;
  background: #fff;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.vp-rate button.active {
  background: #4A90D9;
  color: #fff;
  border-color: #4A90D9;
}

.vp-rate button:hover:not(.active) {
  background: #E8F2FC;
}

/* 进度点 */
.vp-progress {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.vp-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #D4E2FC;
  transition: all 0.3s;
}

.vp-dot.done { background: #90CAF9; }
.vp-dot.active { background: #4A90D9; transform: scale(1.3); }

.vp-info {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

/* 错误 */
.vp-error {
  font-size: 12px;
  color: #D93025;
  background: #FFF5F5;
  padding: 6px 10px;
  border-radius: 6px;
}

/* 不支持的降级 */
.vp-unsupported {
  background: #FFF8F0;
  border-color: #F5A623;
  flex-direction: column;
  align-items: flex-start;
}

.vp-unsupported-text { font-size: 13px; color: #856404; }
.vp-unsupported-hint { font-size: 12px; color: #999; }
</style>
