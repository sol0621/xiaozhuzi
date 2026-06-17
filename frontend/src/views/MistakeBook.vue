<template>
  <div class="mistake-page">
    <!-- 导航栏 -->
    <div class="nav-bar">
      <span class="back" @click="$router.push('/')">← 返回</span>
      <span class="title">📖 错题本</span>
      <span class="placeholder"></span>
    </div>

    <!-- 概览卡片 -->
    <div class="overview" v-if="overview.total > 0">
      <div class="ov-item">
        <div class="ov-num">{{ overview.total }}</div>
        <div class="ov-label">总错题</div>
      </div>
      <div class="ov-item">
        <div class="ov-num">{{ overview.thisMonth }}</div>
        <div class="ov-label">本月新增</div>
      </div>
      <div class="ov-item">
        <div class="ov-num">{{ overview.corrected }}</div>
        <div class="ov-label">已纠正</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filters">
      <select v-model="filterSubject" @change="loadData">
        <option value="">全部学科</option>
        <option value="math">数学</option>
        <option value="chinese">语文</option>
        <option value="english">英语</option>
        <option value="science">科学</option>
      </select>
      <select v-model="filterErrorType" @change="loadData">
        <option value="">全部类型</option>
        <option v-for="et in errorTypes" :key="et.type" :value="et.type">
          {{ et.type }}（{{ et.count }}）
        </option>
      </select>
      <select v-model="filterPeriod" @change="loadData">
        <option value="">全部时间</option>
        <option value="week">本周</option>
        <option value="month">本月</option>
        <option value="quarter">近三月</option>
      </select>
    </div>

    <!-- 加载中 - 骨架屏 -->
    <div v-if="loading" class="skeleton-area">
      <!-- 概览骨架 -->
      <div class="skeleton-row">
        <SkeletonBlock variant="card" width="30%" height="60px" />
        <SkeletonBlock variant="card" width="30%" height="60px" />
        <SkeletonBlock variant="card" width="30%" height="60px" />
      </div>
      <!-- 筛选栏骨架 -->
      <SkeletonBlock variant="text" width="100%" height="40px" />
      <!-- 错题卡片骨架 -->
      <SkeletonBlock variant="card" width="100%" height="120px" />
      <SkeletonBlock variant="card" width="100%" height="120px" />
      <SkeletonBlock variant="card" width="100%" height="120px" />
    </div>

    <!-- 讲解全部按钮 -->
    <div v-if="problems.length > 0" class="explain-all-bar">
      <button class="btn-explain-all" @click="explainAll">📖 逐题讲解（共 {{ problems.length }} 题）</button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="problems.length === 0" class="empty">
      <div class="empty-emoji">📭</div>
      <div class="empty-text">还没有错题记录</div>
      <div class="empty-sub">提交作业批改后，错题会自动收录到这里</div>
      <button class="btn-primary" @click="$router.push('/')">去提交作业</button>
    </div>

    <!-- 错题列表 -->
    <div v-else class="problem-list">
      <div v-for="p in problems" :key="p.id" :class="['problem-card', p.parent_correction ? 'corrected' : '']">
        <div class="pc-header">
          <span class="pc-tag">{{ p.subject }}</span>
          <span class="pc-tag error-tag">{{ p.error_type || '未分类' }}</span>
          <span class="pc-tag" v-if="p.parent_correction">🔧 已纠正</span>
          <span class="pc-date">{{ formatDate(p.created_at) }}</span>
        </div>
        <div class="pc-question">{{ p.question_content }}</div>
        <div class="pc-row">
          <div class="pc-answer wrong-answer">
            <span class="label">孩子答案：</span>
            <span class="strike">{{ p.student_answer }}</span>
          </div>
          <div class="pc-answer correct-answer">
            <span class="label">正确答案：</span>
            <span>{{ p.correct_answer }}</span>
          </div>
        </div>
        <div v-if="p.wrong_reason" class="pc-reason">
          💡 错误原因：{{ p.wrong_reason }}
        </div>
        <div class="pc-actions">
          <button class="btn-explain" @click="goExplain(p, idx)">💡 讲解此题</button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
    </div>

    <!-- 导出打印按钮 -->
    <div v-if="problems.length > 0" class="export-bar">
      <button class="btn-outline" @click="printMistakes">🖨️ 打印错题</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeworkStore } from '@/stores/homework'
import { fetchMistakeBook } from '@/api'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const router = useRouter()
const store = useHomeworkStore()

const loading = ref(true)
const problems = ref([])
const errorTypes = ref([])
const page = ref(1)
const total = ref(0)
const pageSize = 20
const filterSubject = ref('')
const filterErrorType = ref('')
const filterPeriod = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

const now = new Date()
const thisMonthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`

const overview = reactive({
  total: 0,
  thisMonth: 0,
  corrected: 0,
})

function getDateRange() {
  let start = '', end = ''
  if (filterPeriod.value === 'week') {
    const d = new Date()
    d.setDate(d.getDate() - 7)
    start = d.toISOString().slice(0, 10)
  } else if (filterPeriod.value === 'month') {
    start = thisMonthStart
  } else if (filterPeriod.value === 'quarter') {
    const d = new Date()
    d.setMonth(d.getMonth() - 3)
    start = d.toISOString().slice(0, 10)
  }
  return { start, end }
}

async function loadData() {
  loading.value = true
  try {
    const { start, end } = getDateRange()
    const params = {
      page: page.value,
      page_size: pageSize,
    }
    if (filterSubject.value) params.subject = filterSubject.value
    if (filterErrorType.value) params.error_type = filterErrorType.value
    if (start) params.start_date = start
    if (end) params.end_date = end

    const res = await fetchMistakeBook(params)
    if (res.success) {
      problems.value = res.data.problems
      errorTypes.value = res.data.errorTypes
      total.value = res.data.total
    } else {
      problems.value = []
      errorTypes.value = []
      total.value = 0
    }
  } catch (e) {
    console.error(e)
    problems.value = []
  } finally {
    loading.value = false
  }

  // 同时加载概览数据（全部错题不分页）
  try {
    const resAll = await fetchMistakeBook({ page: 1, page_size: 1 })
    if (resAll.success) overview.total = resAll.data.total
    const resMonth = await fetchMistakeBook({ page: 1, page_size: 1, start_date: thisMonthStart })
    if (resMonth.success) overview.thisMonth = resMonth.data.total
    // 粗略统计已纠正（查全部数据取前1000条中数parent_correction不为空的）
    const resCorrected = await fetchMistakeBook({ page: 1, page_size: 1000 })
    if (resCorrected.success) {
      overview.corrected = resCorrected.data.problems.filter(p => p.parent_correction).length
    }
  } catch(e) {
    // ignore
  }
}

function changePage(p) {
  page.value = p
  loadData()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function formatDate(d) {
  if (!d) return ''
  return d.slice(0, 10)
}

// 从错题本跳转到讲解页
function mapToExplain(p) {
  return {
    content: p.question_content,
    studentAnswer: p.student_answer,
    correctAnswer: p.correct_answer,
    wrongReason: p.wrong_reason,
  }
}

function goExplain(p, idx) {
  // 设置当前页所有错题为可翻页列表（统一格式映射）
  store.allWrongQuestions = problems.value.map(mapToExplain)
  store.grade = parseInt(p.grade) || 4
  store.subject = p.subject === '数学' ? 'math' : p.subject === '语文' ? 'chinese' : p.subject === '英语' ? 'english' : 'science'
  store.setExplainQuestion(mapToExplain(p), idx)
  router.push('/explain')
}

function explainAll() {
  if (!problems.value.length) return
  goExplain(problems.value[0], 0)
}

function printMistakes() {
  const w = window.open('', '_blank')
  const subjectLabel = filterSubject.value || '全部'
  const periodLabel = filterPeriod.value === 'week' ? '本周' :
    filterPeriod.value === 'month' ? '本月' :
    filterPeriod.value === 'quarter' ? '近三月' : '全部时间'
  
  let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>错题集 - ${subjectLabel}</title>
<style>
body { font-family: 'Microsoft YaHei', sans-serif; padding: 30px; max-width: 800px; margin: auto; }
h1 { text-align: center; color: #333; border-bottom: 2px solid #4A90D9; padding-bottom: 10px; }
.meta { text-align: center; color: #999; font-size: 13px; margin-bottom: 24px; }
.card { border: 1px solid #eee; border-radius: 8px; padding: 16px; margin-bottom: 16px; page-break-inside: avoid; }
.card .tag { display: inline-block; background: #FFF3CD; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 6px; }
.card .cat { background: #FCE8E6; color: #D93025; }
.card .q { font-size: 15px; font-weight: 600; margin: 10px 0; }
.card .row { display: flex; gap: 24px; font-size: 13px; }
.card .wrong { color: #D93025; text-decoration: line-through; }
.card .correct { color: #1E8E3E; }
.card .reason { margin-top: 8px; font-size: 13px; color: #666; background: #F5F5F5; padding: 8px; border-radius: 6px; }
</style></head><body>
<h1>📖 错题集</h1>
<p class="meta">学科：${subjectLabel} | 时间：${periodLabel} | 共 ${problems.value.length} 题 | 生成日期：${formatDate(new Date().toISOString())}</p>`

  problems.value.forEach((p, i) => {
    html += `<div class="card">
<div><span class="tag">${p.subject}</span><span class="tag cat">${p.error_type || '未分类'}</span></div>
<div class="q">${i + 1}. ${p.question_content}</div>
<div class="row">
  <span class="wrong">✗ ${p.student_answer || '（无）'}</span>
  <span class="correct">✓ ${p.correct_answer || ''}</span>
</div>
${p.wrong_reason ? `<div class="reason">💡 ${p.wrong_reason}</div>` : ''}
</div>`
  })

  html += '</body></html>'
  w.document.write(html)
  w.document.close()
  setTimeout(() => w.print(), 500)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.mistake-page { min-height: 100vh; background: #f8f9fa; }
.nav-bar { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #fff; border-bottom: 1px solid #eee; position: sticky; top: 0; z-index: 10; }
.back { color: #4A90D9; font-size: 14px; cursor: pointer; }
.title { font-size: 16px; font-weight: 600; }
.placeholder { width: 50px; }

/* 概览 */
.overview { display: flex; gap: 12px; padding: 16px; }
.ov-item { flex: 1; background: #fff; border-radius: 10px; padding: 14px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.ov-num { font-size: 24px; font-weight: 700; color: #4A90D9; }
.ov-label { font-size: 12px; color: #999; margin-top: 4px; }

/* 筛选 */
.filters { display: flex; gap: 8px; padding: 0 16px 12px; }
.filters select { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; background: #fff; color: #333; }

/* 加载/空 */
.skeleton-area { padding: 16px; }
.skeleton-row { display: flex; gap: 12px; margin-bottom: 8px; }
.skeleton-row .skeleton-block { margin-bottom: 0; }
.loading { text-align: center; padding: 60px 16px; color: #999; font-size: 14px; }
.empty { text-align: center; padding: 60px 16px; }
.empty-emoji { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 16px; color: #666; margin-bottom: 8px; }
.empty-sub { font-size: 13px; color: #999; margin-bottom: 20px; }

/* 错题卡片 */
.problem-list { padding: 0 16px; display: flex; flex-direction: column; gap: 12px; }
.problem-card { background: #fff; border-radius: 10px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #F0AD4E; }
.problem-card.corrected { border-left-color: #5CB85C; opacity: 0.85; }
.pc-header { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.pc-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #E8F2FC; color: #4A90D9; }
.pc-tag.error-tag { background: #FCE8E6; color: #D93025; }
.pc-date { margin-left: auto; font-size: 11px; color: #bbb; }
.pc-question { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 8px; line-height: 1.5; }
.pc-row { display: flex; gap: 16px; font-size: 13px; flex-wrap: wrap; }
.pc-answer .label { color: #999; }
.pc-answer.wrong-answer .strike { color: #D93025; text-decoration: line-through; }
.pc-answer.correct-answer span:last-child { color: #1E8E3E; font-weight: 600; }
.pc-reason { margin-top: 8px; font-size: 12px; color: #666; background: #F5F5F5; padding: 8px; border-radius: 6px; }

/* 分页 */
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 20px 16px; }
.pagination button { padding: 8px 16px; background: #fff; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; cursor: pointer; color: #333; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.pagination span { font-size: 13px; color: #666; }

/* 导出 */
.export-bar { text-align: center; padding: 12px 16px; }
.btn-outline { padding: 10px 20px; background: #fff; border: 1px solid #4A90D9; color: #4A90D9; border-radius: 8px; font-size: 14px; cursor: pointer; }
.btn-primary { padding: 10px 20px; background: #4A90D9; color: #fff; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }

/* 讲解按钮 */
.explain-all-bar { padding: 0 16px 12px; }
.btn-explain-all { width: 100%; padding: 12px; background: linear-gradient(135deg, #667EEA, #764BA2); color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 8px rgba(102,126,234,0.3); }
.pc-actions { margin-top: 10px; display: flex; gap: 8px; }
.btn-explain { padding: 6px 14px; background: #E8F2FC; color: #4A90D9; border: 1px solid #B8D4F0; border-radius: 6px; font-size: 12px; cursor: pointer; }

@media (max-width: 480px) {
  .overview { padding: 12px; gap: 8px; }
  .ov-item { padding: 10px; }
  .ov-num { font-size: 20px; }
  .filters { padding: 0 12px 8px; flex-direction: column; }
  .problem-list { padding: 0 12px; gap: 8px; }
  .problem-card { padding: 12px; }
  .pc-question { font-size: 13px; }
  .pc-row { gap: 8px; font-size: 12px; }
  .nav-bar { padding: 10px 12px; }
}
</style>
