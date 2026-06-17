/**
 * 自唤醒机制：防止 Render 免费层 15 分钟无活动休眠
 * 每 13 分钟 ping 一次 /api/health，留 2 分钟缓冲
 *
 * 使用方式：在 App.vue 中调用 useWakeLock()
 */
import { onMounted, onUnmounted, ref } from 'vue'

const WAKE_INTERVAL = 13 * 60 * 1000 // 13 分钟
const HEALTH_URL = '/api/health'

export function useWakeLock() {
  let timer = null
  let visible = true
  const active = ref(false)

  async function ping() {
    try {
      const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        active.value = true
      }
    } catch {
      // 静默失败 — 服务器可能正在冷启动或网络不稳
      active.value = false
    }
  }

  function onVisibilityChange() {
    visible = document.visibilityState === 'visible'
    if (visible) {
      ping() // 切回标签页时立即 ping 一次
    }
  }

  function start() {
    ping() // 首次立即 ping
    timer = setInterval(() => {
      if (visible) ping()
    }, WAKE_INTERVAL)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    start()
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    stop()
  })

  return { active }
}
