<template>
  <div class="explain-page">
    <div class="nav-bar">
      <span class="back" @click="router.back()">← 返回</span>
      <span class="title">{{ navTitle }}</span>
      <span class="placeholder"></span>
    </div>

    <div v-if="loading" class="skeleton-area">
      <SkeletonBlock variant="card" width="100%" height="80px" />
      <SkeletonBlock variant="text" width="100%" height="12px" />
      <SkeletonBlock variant="card" width="100%" height="160px" />
      <SkeletonBlock variant="text" width="60%" height="12px" />
      <SkeletonBlock variant="card" width="100%" height="60px" />
    </div>

    <div v-else-if="question" class="content">
      <div class="question-card">
        <div class="q-title">题目</div>
        <div class="q-body">{{ question.content }}</div>
        <div v-if="question.studentAnswer" class="q-wrong">你的答案：{{ question.studentAnswer }} ❌</div>
        <div v-else-if="question.correctAnswer" class="q-wrong">答案：{{ question.correctAnswer }}</div>
      </div>

      <!-- 语音播报 -->
      <VoicePlayer
        :isPlaying="tts.isPlaying.value"
        :isPaused="tts.isPaused.value"
        :currentSegment="tts.currentSegmentIndex.value"
        :totalSegments="tts.totalSegments.value"
        :rate="tts.rate.value"
        :isSupported="tts.isSupported.value"
        :error="tts.error.value"
        @play="startTTS"
        @pause="tts.pause"
        @resume="tts.resume"
        @stop="tts.stop"
        @setRate="tts.setRate"
      />

      <!-- 数学多方法 Tab -->
      <div v-if="subject==='math' && explanation?.methods?.length" class="methods-tabs">
        <button
          v-for="(m, idx) in explanation.methods"
          :key="idx"
          :class="{active: activeMethod===idx}"
          @click="activeMethod=idx"
        >方法{{ idx+1 }}：{{ m.name }}</button>
      </div>

      <div class="explain-card">
        <div class="explain-title">💡 讲解</div>
        <div class="explain-body" v-html="formatText(currentExplanation)"></div>
      </div>

      <div v-if="explanation?.tip" class="tip-box">
        <div class="tip-title">⚠️ 易错点提醒</div>
        <div class="tip-body">{{ explanation.tip }}</div>
      </div>

      <div v-if="explanation?.finalAnswer" class="final-box">
        ✅ 正确答案是：<strong>{{ explanation.finalAnswer }}</strong>
      </div>

      <div class="grade-hint">本讲解依据{{ grade }}年级{{ subjectName }}课程标准</div>
    </div>

    <div v-else class="empty">没有需要讲解的题目</div>

    <div class="bottom-nav" v-if="totalWrong > 1">
      <button :disabled="currentIndex===0" @click="prev">← 上一题</button>
      <button :disabled="currentIndex===totalWrong-1" @click="next">下一题 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeworkStore } from '@/stores/homework'
import { explainError } from '@/api'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import VoicePlayer from '@/components/VoicePlayer.vue'
import { useTTS } from '@/composables/useTTS'

const router = useRouter()
const store = useHomeworkStore()

const question = computed(() => store.currentExplainQuestion)
const currentIndex = computed(() => store.currentExplainIndex)
const totalWrong = computed(() => store.allWrongQuestions.length)
const grade = computed(() => store.grade)
const subject = computed(() => store.subject)

const subjectName = computed(() => {
  const map = { math:'数学', chinese:'语文', english:'英语', science:'科学' }
  return map[subject.value] || subject.value
})

const navTitle = computed(() => totalWrong.value > 1 ? `第 ${currentIndex.value+1}/${totalWrong.value} 题讲解` : '错题讲解')

const activeMethod = ref(0)
const explanation = ref(null)
const loading = ref(false)

async function loadExplain() {
  if (!question.value) return
  loading.value = true
  try {
    const res = await explainError({
      grade: grade.value,
      subject: subject.value,
      question: question.value.content,
      studentAnswer: question.value.studentAnswer,
      correctAnswer: question.value.correctAnswer,
      wrongReason: question.value.wrongReason,
    })
    explanation.value = res.data || null
    activeMethod.value = 0
  } catch (err) {
    explanation.value = { explanation: '讲解加载失败，请返回重试。', methods: [], tip: '', finalAnswer: question.value.correctAnswer || '' }
  } finally {
    loading.value = false
  }
}

const currentExplanation = computed(() => {
  if (!explanation.value) return ''
  if (subject.value === 'math' && explanation.value.methods?.length) {
    return explanation.value.methods[activeMethod.value]?.content || explanation.value.explanation
  }
  return explanation.value.explanation
})

function formatText(t) { return (t || '').replace(/\n/g, '<br>') }

// TTS 语音播报
const tts = useTTS()

function stripHtml(html) {
  return (html || '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]*>/g, '').trim()
}

function startTTS() {
  const text = stripHtml(currentExplanation.value)
  // 拼接易错点提醒和正确答案，让播报更完整
  let full = text
  if (explanation.value?.tip) full += '\n\n易错点提醒：' + explanation.value.tip
  if (explanation.value?.finalAnswer) full += '\n\n正确答案是：' + explanation.value.finalAnswer
  tts.play(full)
}

// 数学多方法切换或上下题切换时停止播报
watch([activeMethod, question], () => {
  tts.stop()
})

function prev() {
  if (currentIndex.value > 0) {
    store.setExplainQuestion(store.allWrongQuestions[currentIndex.value - 1], currentIndex.value - 1)
    loadExplain()
  }
}
function next() {
  if (currentIndex.value < totalWrong.value - 1) {
    store.setExplainQuestion(store.allWrongQuestions[currentIndex.value + 1], currentIndex.value + 1)
    loadExplain()
  }
}

loadExplain()
</script>

<style scoped>
.explain-page { min-height:100vh; padding-bottom:80px; }
.nav-bar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:#fff; border-bottom:1px solid #eee; position:sticky; top:0; z-index:10; }
.back { color:#4A90D9; font-size:14px; cursor:pointer; }
.title { font-size:16px; font-weight:600; }
.placeholder { width:50px; }
.content { padding:16px; display:flex; flex-direction:column; gap:12px; }
.empty { padding:80px 24px; text-align:center; color:#999; font-size:14px; }
.skeleton-area { padding: 16px; display: flex; flex-direction: column; gap: 4px; }
.question-card { background:#fff; border-radius:10px; padding:14px; border-left:4px solid #F0AD4E; }
.q-title { font-size:12px; color:#999; margin-bottom:6px; }
.q-body { font-size:15px; font-weight:600; color:#333; line-height:1.5; }
.q-wrong { margin-top:8px; font-size:14px; color:#D93025; background:#FFF5F5; padding:8px; border-radius:6px; }
.methods-tabs { display:flex; gap:8px; overflow-x:auto; }
.methods-tabs button { padding:8px 12px; background:#fff; border:1px solid #ddd; border-radius:20px; font-size:12px; white-space:nowrap; cursor:pointer; }
.methods-tabs button.active { background:#4A90D9; color:#fff; border-color:#4A90D9; }
.explain-card { background:#fff; border-radius:10px; padding:14px; }
.explain-title { font-size:14px; font-weight:600; color:#4A90D9; margin-bottom:10px; }
.explain-body { font-size:14px; color:#333; line-height:1.8; }
.tip-box { background:#FFF8F0; border:1px solid #F5A623; border-radius:10px; padding:12px; }
.tip-title { font-size:13px; font-weight:600; color:#F5A623; margin-bottom:6px; }
.tip-body { font-size:13px; color:#856404; line-height:1.6; }
.final-box { background:#E6F4EA; color:#1E8E3E; padding:12px; border-radius:10px; font-size:15px; }
.grade-hint { font-size:11px; color:#999; text-align:center; margin-top:8px; }
.bottom-nav { display:flex; gap:12px; padding:12px 16px; background:#fff; border-top:1px solid #eee; margin-top: 16px; }
.bottom-nav button { flex:1; padding:12px; background:#4A90D9; color:#fff; border:none; border-radius:10px; font-size:14px; cursor:pointer; }
.bottom-nav button:disabled { background:#ccc; cursor:not-allowed; }

@media (max-width: 480px) {
  .content { padding: 12px; }
  .nav-bar { padding: 10px 12px; }
  .nav-bar .title { font-size: 15px; }
  .question-card, .explain-card, .tip-box { padding: 12px; }
  .q-body, .explain-body { font-size: 13px; }
  .bottom-nav { padding: 10px 12px; }
  .bottom-nav button { font-size: 13px; padding: 10px; }
  .methods-tabs { gap: 4px; }
  .methods-tabs button { font-size: 12px; padding: 8px 6px; }
}
</style>
