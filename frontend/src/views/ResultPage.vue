<template>
  <div class="result-page">
    <div class="nav-bar">
      <span class="back" @click="goBack">← 返回</span>
      <span class="title">{{ pageTitle }}</span>
      <span class="placeholder"></span>
    </div>

    <!-- B5 整页失败 -->
    <div v-if="mode==='error'" class="center-state">
      <div class="big-emoji">😅</div>
      <div class="big-text">这张作业看起来有点模糊</div>
      <div class="sub-text">AI没能识别出任何题目<br>建议检查光线、文字清晰度、是否有遮挡</div>
      <div class="actions">
        <button class="btn-secondary" @click="switchMode('photo')">📷 重新拍照</button>
        <button class="btn-secondary" @click="switchMode('text')">⌨️ 文字输入</button>
      </div>
    </div>

    <!-- B6 AI异常 -->
    <div v-else-if="mode==='ai_error'" class="center-state">
      <div class="big-emoji">⚠️</div>
      <div class="big-text">批改服务暂时开小差了</div>
      <div class="sub-text">错误类型：{{ errorMessage }}</div>
      <div class="actions">
        <button class="btn-primary" @click="retry">🔄 重新尝试</button>
        <button class="btn-secondary" @click="goBack">← 返回修改</button>
      </div>
    </div>

    <!-- B3 全对庆祝 -->
    <div v-else-if="mode==='all_correct'" class="celebrate">
      <div class="celebrate-emoji">🎉</div>
      <div class="celebrate-title">全对！共 {{ totalCount }} 题，全部正确</div>
      <div class="cards">
        <div v-for="q in questions" :key="q.id" class="card correct-card">
          <div class="card-header">第 {{ q.id }} 题</div>
          <div class="question-content">{{ q.content }}</div>
          <div v-if="q.studentAnswer" class="answer-line">孩子答案：{{ q.studentAnswer }}</div>
          <div class="badge correct">✅ 正确</div>
        </div>
      </div>
      <div class="bottom-tip">太棒了！继续保持～</div>
    </div>

    <!-- B2 直接解答 -->
    <div v-else-if="mode==='direct-answer'" class="direct-mode">
      <div class="tip-bar">✨ 这些孩子没有写答案，AI直接给出了讲解，建议以后先自己完成哦～</div>
      <div class="cards">
        <div v-for="q in questions" :key="q.id" class="card direct-card">
          <div class="card-header">第 {{ q.id }} 题 【🚀 直接解答】</div>
          <div class="question-content">{{ q.content }}</div>
          <div class="answer-section">
            <div class="section-title">解答：</div>
            <div class="explanation-text" v-html="formatText(q.explanation)"></div>
            <div class="final-answer">答案：{{ q.finalAnswer }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- B1/B4 批改混合态 -->
    <div v-else class="normal-mode">
      <div v-if="pendingCount > 0" class="yellow-bar">⚠️ 有 {{ pendingCount }} 道题需要确认</div>
      <div class="stats-bar">
        <span v-if="pendingCount===0 && notAttemptedCount===0">📊 共 {{ totalCount }} 题 | ✅ {{ correctCount }} 对 | ❌ {{ wrongCount }} 错</span>
        <span v-else-if="pendingCount===0">📊 共 {{ totalCount }} 题 | ✅ {{ correctCount }} 对 | ❌ {{ wrongCount }} 错 | 📝 {{ notAttemptedCount }} 未答</span>
        <span v-else>已识别 {{ recognizedCount }} 题 | ✅ {{ correctCount }} 对 | ❌ {{ wrongCount }} 错 | 📝 {{ notAttemptedCount }} 未答 | ⏳ {{ pendingCount }} 待确认</span>
      </div>

      <div class="cards">
        <div v-for="q in displayQuestions" :key="q.id" :class="['card', cardClass(q)]">
          <template v-if="q.status==='normal'">
            <div class="card-header">第 {{ q.id }} 题</div>
            <div class="question-content">{{ q.content }}</div>
            <div v-if="q.studentAnswer" class="answer-line">孩子答案：{{ q.studentAnswer }}</div>
            <div :class="['badge', q.isCorrect?'correct':'wrong']">{{ q.isCorrect ? '✅ 正确' : '❌ 错误' }}</div>
            <div v-if="!q.isCorrect && q.wrongReason" class="reason">{{ q.wrongReason }}</div>
            <button v-if="!q.isCorrect" class="explain-btn" @click="goExplain(q)">📖 查看讲解</button>
            <div class="correct-link" @click="openCorrect(q)">
              {{ q._corrected ? '✓ 已纠正' : '不对？点此纠正' }}
            </div>
          </template>

          <template v-else-if="q.status==='answer_unclear'">
            <div class="card-header warn">第 {{ q.id }} 题 ⚠️ 答案待确认</div>
            <div class="question-content">{{ q.content }}</div>
            <div class="input-line">
              <label>请输入孩子的答案：</label>
              <input v-model="q.tempAnswer" class="small-input" />
            </div>
            <div class="actions-row">
              <button class="btn-small" @click="confirmAnswer(q)">✅ 确认答案</button>
              <button class="btn-small ghost" @click="skipQuestion(q)">⏭️ 跳过此题</button>
            </div>
          </template>

          <template v-else-if="q.status==='not_attempted'">
            <div class="card-header warn">第 {{ q.id }} 题 📝 未答题</div>
            <div class="question-content">{{ q.content }}</div>
            <div class="answer-section">
              <div class="section-title">参考答案：</div>
              <div class="explanation-text" v-html="formatText(q.explanation)"></div>
              <div class="final-answer">答案：{{ q.finalAnswer }}</div>
            </div>
          </template>

          <template v-else-if="q.status==='partial_recognition'">
            <div class="card-header warn">第 {{ q.id }} 题 ⚠️ 题目不完整</div>
            <div class="sub-hint">已识别片段：{{ q.content }}</div>
            <div class="input-line">
              <label>补全题目：</label>
              <input v-model="q.tempContent" class="small-input" />
            </div>
            <div class="actions-row">
              <button class="btn-small" @click="confirmComplete(q)">✅ 确认补全</button>
              <button class="btn-small ghost" @click="removeQuestion(q)">🗑️ 删除此题</button>
            </div>
          </template>

          <template v-else-if="q.status==='unrecognizable'">
            <div class="card-header muted">第 {{ q.id }} 题 ❓ 无法识别</div>
            <div class="sub-hint">此区域无法识别为题目</div>
            <div class="actions-row">
              <button class="btn-small" @click="inputTextFor(q)">⌨️ 文字输入</button>
              <button class="btn-small ghost" @click="ignoreQuestion(q)">⏭️ 忽略</button>
            </div>
          </template>

          <template v-else-if="q.status==='skipped' || q.status==='ignored'">
            <div class="card-header muted">第 {{ q.id }} 题 {{ q.status==='skipped' ? '（已跳过）' : '（已忽略）' }}</div>
          </template>
        </div>
      </div>

      <!-- 纠错弹窗 -->
    <div v-if="correctModal.visible" class="modal-overlay" @click.self="closeCorrect">
      <div class="modal-card">
        <div class="modal-title">纠正 AI 判断</div>
        <div class="modal-body">
          <p class="modal-q">第 {{ correctModal.q?.id }} 题：{{ correctModal.q?.content }}</p>
          <p class="modal-a">AI 当前判断：<b :style="{color: correctModal.q?.isCorrect ? '#5CB85C' : '#D93025'}">{{ correctModal.q?.isCorrect ? '正确' : '错误' }}</b></p>
          <div class="modal-options">
            <button class="corr-btn should-correct" @click="doCorrect('should_be_correct')">✅ 应该判为正确</button>
            <button class="corr-btn should-wrong" @click="doCorrect('should_be_wrong')">❌ 应该判为错误</button>
          </div>
          <div class="modal-input-row">
            <label>或输入正确答案：</label>
            <input v-model="correctModal.customAnswer" class="modal-input" placeholder="输入正确答案..." />
            <button class="corr-btn custom" @click="doCorrect('custom_answer')">确认</button>
          </div>
        </div>
        <button class="modal-close" @click="closeCorrect">取消</button>
      </div>
    </div>

    <div v-if="wrongCount > 0 && pendingCount===0" class="footer-action">
        <button class="btn-primary" @click="explainAll">📖 一键讲解 {{ wrongCount }} 道错题</button>
      </div>
      <div v-else-if="wrongCount > 0 && pendingCount > 0" class="footer-action">
        <button class="btn-primary" disabled>请先处理待确认的题目</button>
      </div>

      <div class="footer-links">
        <button class="text-btn" @click="$router.push('/mistake-book')">📖 错题本</button>
        <button class="text-btn" @click="goStats">📊 查看易错点统计</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeworkStore } from '@/stores/homework'
import { correctProblem } from '@/api'

const router = useRouter()
const store = useHomeworkStore()

const res = store.correctionResult || {}
const rawMode = computed(() => res.mode || 'correction')
const questions = computed(() => res.questions || [])
const totalCount = computed(() => res.totalCount || 0)
const correctCount = computed(() => res.correctCount || 0)
const wrongCount = computed(() => res.wrongCount || 0)
const notAttemptedCount = computed(() => res.notAttemptedCount || 0)
const errorMessage = computed(() => res.errorType || res.rawText?.slice(0,200) || '未知错误')

const mode = computed(() => {
  if (rawMode.value === 'ai_error') return 'ai_error'
  if (rawMode.value === 'error') return 'error'
  if (rawMode.value === 'direct-answer') return 'direct-answer'
  if (rawMode.value === 'all_correct' && wrongCount.value === 0) return 'all_correct'
  return 'correction'
})

const pageTitle = computed(() => {
  if (mode.value === 'direct-answer') return '作业解答'
  if (mode.value === 'all_correct') return '批改结果'
  return '批改结果'
})

const displayQuestions = computed(() => questions.value)
const recognizedCount = computed(() => questions.value.filter(q => q.status==='normal' || q.status==='not_attempted').length)
const pendingCount = computed(() => questions.value.filter(q => ['answer_unclear','partial_recognition'].includes(q.status)).length)

function cardClass(q) {
  if (q.status==='normal') return q.isCorrect ? 'correct-card' : 'wrong-card'
  if (q.status==='not_attempted') return 'not-attempted-card'
  if (q.status==='answer_unclear' || q.status==='partial_recognition') return 'warn-card'
  if (q.status==='unrecognizable') return 'muted-card'
  return 'ghost-card'
}

function goBack() { router.push('/') }
function goExplain(q) { store.setExplainQuestion(q); router.push('/explain') }
function explainAll() {
  const wrongs = questions.value.filter(q => !q.isCorrect && q.status==='normal')
  if (wrongs.length) { store.allWrongQuestions = wrongs; store.setExplainQuestion(wrongs[0],0); router.push('/explain') }
}
function goStats() { router.push('/stats') }
function switchMode(m) { store.inputMode = m; router.push('/') }
function retry() { router.push('/') }

function confirmAnswer(q) { if(!q.tempAnswer) return; q.studentAnswer=q.tempAnswer; q.status='normal' }
function skipQuestion(q) { q.status='skipped' }
function confirmComplete(q) { if(!q.tempContent) return; q.content=q.tempContent; q.status='normal' }
function removeQuestion(q) { const idx=questions.value.indexOf(q); if(idx>-1) questions.value.splice(idx,1) }
function ignoreQuestion(q) { q.status='ignored' }
function inputTextFor(q) { const t=prompt('请输入该题文字内容：'); if(t){ q.content=t; q.status='normal'; } }
function formatText(t) { return (t||'').replace(/\n/g,'<br>') }

// 纠错弹窗
const correctModal = computed(() => store.correctModal)
function openCorrect(q) {
  store.correctModal = {
    visible: true,
    q: q,
    customAnswer: '',
  }
}
function closeCorrect() {
  store.correctModal = { visible: false, q: null, customAnswer: '' }
}
async function doCorrect(type) {
  const q = correctModal.value.q
  if (!q) return
  const payload = { problem_id: q._problemId || q.id, correction_type: type }
  if (type === 'custom_answer' && correctModal.value.customAnswer) {
    payload.custom_answer = correctModal.value.customAnswer
  }
  try {
    const res = await correctProblem(payload)
    if (res.success) {
      if (type === 'should_be_correct') {
        q.isCorrect = true
        q._corrected = true
      } else if (type === 'should_be_wrong') {
        q.isCorrect = false
        q._corrected = true
      }
      // 更新 store 中的统计数据
      store.refreshCounts()
    }
  } catch(e) {
    console.error(e)
  }
  closeCorrect()
}
</script>

<style scoped>
.result-page { min-height:100vh; padding-bottom:100px; }
.nav-bar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:#fff; border-bottom:1px solid #eee; position:sticky; top:0; z-index:10; }
.back { color:#4A90D9; font-size:14px; cursor:pointer; }
.title { font-size:16px; font-weight:600; }
.placeholder { width:50px; }
.yellow-bar { background:#FFF3CD; color:#856404; padding:10px 16px; font-size:13px; }
.stats-bar { background:#fff; padding:12px 16px; font-size:14px; color:#333; border-bottom:1px solid #eee; }
.cards { padding:12px 16px; display:flex; flex-direction:column; gap:12px; }
.card { background:#fff; border-radius:10px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.correct-card { border-left:4px solid #5CB85C; }
.wrong-card { border-left:4px solid #F0AD4E; }
.direct-card { border-left:4px solid #4A90D9; }
.not-attempted-card { border-left:4px solid #9B59B6; background:#FAF5FF; }
.warn-card { border-left:4px solid #F5A623; background:#FFFBF2; }
.muted-card { border-left:4px solid #ccc; background:#f5f5f5; }
.ghost-card { background:#eee; opacity:0.7; }
.card-header { font-size:13px; color:#666; margin-bottom:6px; }
.card-header.warn { color:#F5A623; font-weight:600; }
.card-header.muted { color:#999; }
.question-content { font-size:15px; font-weight:600; color:#333; margin-bottom:8px; line-height:1.5; }
.answer-line { font-size:13px; color:#666; margin-bottom:6px; }
.badge { display:inline-block; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:600; margin-top:4px; }
.badge.correct { background:#E6F4EA; color:#1E8E3E; }
.badge.wrong { background:#FCE8E6; color:#D93025; }
.reason { font-size:13px; color:#D93025; margin-top:8px; background:#FFF5F5; padding:8px; border-radius:6px; }
.explain-btn { margin-top:10px; width:100%; padding:10px; background:#4A90D9; color:#fff; border:none; border-radius:8px; font-size:14px; cursor:pointer; }
.answer-section { margin-top:10px; padding-top:10px; border-top:1px dashed #eee; }
.section-title { font-size:13px; color:#666; margin-bottom:6px; }
.explanation-text { font-size:14px; color:#333; line-height:1.6; }
.final-answer { margin-top:10px; font-size:15px; font-weight:700; color:#4A90D9; }
.input-line { display:flex; align-items:center; gap:8px; margin:10px 0; font-size:13px; }
.small-input { flex:1; padding:8px; border:1px solid #ddd; border-radius:6px; font-size:13px; }
.actions-row { display:flex; gap:8px; margin-top:8px; }
.btn-small { flex:1; padding:8px; background:#4A90D9; color:#fff; border:none; border-radius:6px; font-size:13px; cursor:pointer; }
.btn-small.ghost { background:#fff; color:#666; border:1px solid #ddd; }
.footer-action { position:fixed; bottom:0; left:0; right:0; max-width:480px; margin:0 auto; padding:12px 16px; background:#fff; border-top:1px solid #eee; }
.footer-action .btn-primary { width:100%; padding:14px; background:#4A90D9; color:#fff; border:none; border-radius:12px; font-size:16px; font-weight:600; cursor:pointer; }
.footer-action .btn-primary:disabled { background:#ccc; cursor:not-allowed; }
.footer-links { text-align:center; padding:16px; display:flex; gap:16px; justify-content:center; }
.text-btn { background:none; border:none; color:#4A90D9; font-size:14px; cursor:pointer; }
.celebrate { padding:24px 16px; text-align:center; }
.celebrate-emoji { font-size:48px; margin-bottom:12px; }
.celebrate-title { font-size:18px; font-weight:700; color:#5CB85C; margin-bottom:20px; }
.bottom-tip { margin-top:20px; color:#666; font-size:14px; }
.center-state { padding:60px 24px; text-align:center; }
.big-emoji { font-size:48px; margin-bottom:16px; }
.big-text { font-size:18px; font-weight:600; color:#333; margin-bottom:12px; }
.sub-text { font-size:14px; color:#666; line-height:1.6; margin-bottom:24px; }
.actions { display:flex; gap:12px; justify-content:center; }
.btn-secondary { padding:10px 16px; background:#fff; border:1px solid #ddd; border-radius:8px; font-size:14px; cursor:pointer; color:#333; }
.btn-primary { padding:10px 20px; background:#4A90D9; color:#fff; border:none; border-radius:8px; font-size:14px; cursor:pointer; }
.direct-mode .tip-bar { background:#E8F2FC; color:#4A90D9; padding:10px 16px; font-size:13px; margin-bottom:8px; }
.sub-hint { font-size:12px; color:#999; margin-bottom:8px; }
.correct-link { text-align: right; font-size: 12px; color: #999; margin-top: 8px; cursor: pointer; }
.correct-link:hover { color: #4A90D9; }

/* 纠错弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 24px; }
.modal-card { background: #fff; border-radius: 14px; padding: 24px; width: 100%; max-width: 360px; }
.modal-title { font-size: 17px; font-weight: 700; margin-bottom: 16px; text-align: center; }
.modal-q { font-size: 14px; color: #333; margin-bottom: 8px; }
.modal-a { font-size: 13px; color: #666; margin-bottom: 16px; }
.modal-options { display: flex; gap: 10px; margin-bottom: 16px; }
.corr-btn { flex: 1; padding: 12px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; }
.corr-btn.should-correct { background: #E6F4EA; color: #1E8E3E; }
.corr-btn.should-wrong { background: #FCE8E6; color: #D93025; }
.corr-btn.custom { flex: none; padding: 8px 16px; background: #4A90D9; color: #fff; border-radius: 8px; }
.modal-input-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; font-size: 13px; }
.modal-input { flex: 1; min-width: 120px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; }
.modal-close { display: block; margin: 0 auto; padding: 8px 24px; background: #fff; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; color: #999; cursor: pointer; }
</style>
