import { ref, onUnmounted, readonly } from 'vue'

/**
 * 讲解语音播报组合式函数
 * 封装 Web Speech API speechSynthesis，支持分段朗读、播放控制、语速调节
 */
export function useTTS() {
  const isSupported = ref(typeof window !== 'undefined' && 'speechSynthesis' in window)
  const isPlaying = ref(false)
  const isPaused = ref(false)
  const currentSegmentIndex = ref(-1)
  const rate = ref(1)
  const totalSegments = ref(0)
  const error = ref(null)

  let segments = []
  let utterance = null

  /**
   * 获取中文语音（优先普通话，否则取第一个匹配中文的）
   */
  function getVoice() {
    const voices = speechSynthesis.getVoices()
    // 优先选择简体中文普通话
    let voice = voices.find(
      v => v.lang === 'zh-CN' && (v.name.includes('Tingting') || v.name.includes('Xiaoxiao') || v.name.includes('Google'))
    )
    if (!voice) voice = voices.find(v => v.lang.startsWith('zh'))
    if (!voice) voice = voices[0]
    return voice
  }

  /**
   * 智能分段：按段落拆分，过长则再按句子拆分
   */
  function splitText(text) {
    if (!text) return []
    // 先按换行拆段落
    const paragraphs = text.split(/\n+/).filter(s => s.trim())
    const result = []
    const MAX_LEN = 250 // 单段最大字符数，避免 TTS 卡顿

    for (const p of paragraphs) {
      const trimmed = p.trim()
      if (trimmed.length <= MAX_LEN) {
        result.push(trimmed)
      } else {
        // 按中文标点拆分
        const sentences = trimmed.split(/(?<=[。！？；\n])/g)
        let chunk = ''
        for (const s of sentences) {
          const candidate = chunk + s
          if (candidate.length <= MAX_LEN) {
            chunk = candidate
          } else {
            if (chunk.trim()) result.push(chunk.trim())
            chunk = s
          }
        }
        if (chunk.trim()) result.push(chunk.trim())
      }
    }
    return result.filter(s => s.length > 0)
  }

  /**
   * 朗读指定索引的段落
   */
  function speak(index) {
    if (!isSupported.value || index >= segments.length) {
      finish()
      return
    }

    // 朗读前先取消当前朗读（避免残留）
    speechSynthesis.cancel()

    currentSegmentIndex.value = index

    utterance = new SpeechSynthesisUtterance(segments[index])
    utterance.rate = rate.value
    utterance.lang = 'zh-CN'
    utterance.volume = 1
    utterance.pitch = 1

    const voice = getVoice()
    if (voice) utterance.voice = voice

    utterance.onend = () => {
      // 自动播放下一段
      if (index + 1 < segments.length && isPlaying.value && !isPaused.value) {
        speak(index + 1)
      } else {
        finish()
      }
    }

    utterance.onerror = (e) => {
      // canceled/interrupted 是用户主动操作，不算错误
      if (e.error !== 'canceled' && e.error !== 'interrupted') {
        error.value = `语音播放失败: ${e.error}`
      }
      isPlaying.value = false
      isPaused.value = false
    }

    speechSynthesis.speak(utterance)
  }

  function finish() {
    isPlaying.value = false
    isPaused.value = false
    currentSegmentIndex.value = -1
  }

  /**
   * 开始播放
   */
  function play(text) {
    if (!isSupported.value) {
      error.value = '您的浏览器不支持语音播报，请使用 Chrome/Edge 浏览器'
      return false
    }

    if (!text) return false

    // 先停止当前播放
    speechSynthesis.cancel()

    error.value = null
    segments = splitText(text)
    totalSegments.value = segments.length

    if (segments.length === 0) {
      error.value = '没有可朗读的内容'
      return false
    }

    isPlaying.value = true
    isPaused.value = false
    speak(0)
    return true
  }

  function pause() {
    if (isSupported.value && isPlaying.value) {
      speechSynthesis.pause()
      isPaused.value = true
    }
  }

  function resume() {
    if (isSupported.value && isPaused.value) {
      speechSynthesis.resume()
      isPaused.value = false
    }
  }

  function stop() {
    if (isSupported.value) {
      speechSynthesis.cancel()
    }
    finish()
  }

  function setRate(r) {
    rate.value = r
  }

  // 组件卸载时自动停止
  onUnmounted(() => {
    if (isSupported.value) {
      speechSynthesis.cancel()
    }
  })

  return {
    isSupported: readonly(isSupported),
    isPlaying,
    isPaused,
    currentSegmentIndex,
    rate,
    totalSegments,
    error,
    play,
    pause,
    resume,
    stop,
    setRate,
  }
}
