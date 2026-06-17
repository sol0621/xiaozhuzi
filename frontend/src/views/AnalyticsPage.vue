<template>
  <div class="analytics-page">
    <nav class="top-bar">
      <h1>📊 学习分析</h1>
      <router-link to="/submit" class="nav-link">← 返回</router-link>
    </nav>

    <div v-if="loading" class="skeleton-area">
      <!-- 总览卡片骨架 -->
      <div class="skeleton-row">
        <SkeletonBlock variant="card" width="22%" height="70px" />
        <SkeletonBlock variant="card" width="22%" height="70px" />
        <SkeletonBlock variant="card" width="22%" height="70px" />
        <SkeletonBlock variant="card" width="22%" height="70px" />
      </div>
      <!-- 双栏 -->
      <div class="skeleton-two-col">
        <SkeletonBlock variant="card" width="100%" height="200px" />
        <SkeletonBlock variant="card" width="100%" height="200px" />
      </div>
      <!-- 趋势 -->
      <SkeletonBlock variant="card" width="100%" height="180px" />
      <!-- 学科 -->
      <SkeletonBlock variant="card" width="100%" height="120px" />
    </div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="!data" class="empty">暂无数据，请先批改作业</div>

    <div v-else class="content">
      <!-- 总览卡片 -->
      <section class="overview-cards">
        <div class="card">
          <div class="card-num">{{ data.overview.totalProblems }}</div>
          <div class="card-label">累计批改题数</div>
        </div>
        <div class="card">
          <div class="card-num">{{ data.overview.totalHomeworks }}</div>
          <div class="card-label">提交次数</div>
        </div>
        <div class="card highlight">
          <div class="card-num">{{ data.overview.averageAccuracy }}%</div>
          <div class="card-label">平均正确率</div>
        </div>
        <div class="card warn">
          <div class="card-num">{{ data.overview.totalWrong }}</div>
          <div class="card-label">错题总数</div>
        </div>
      </section>

      <!-- 两栏布局 -->
      <div class="two-col">
        <!-- 错误模式 -->
        <section class="panel">
          <h2>🔍 错误模式分布</h2>
          <div v-if="data.errorPatterns.length === 0" class="empty">暂无错误记录</div>
          <div v-else class="bar-list">
            <div v-for="(p, i) in data.errorPatterns.slice(0, 10)" :key="i" class="bar-row">
              <span class="bar-label">{{ p.type }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: p.percent + '%' }"></div>
              </div>
              <span class="bar-value">{{ p.count }}次 ({{ p.percent }}%)</span>
            </div>
          </div>
        </section>

        <!-- 薄弱知识点 -->
        <section class="panel">
          <h2>⚠️ 薄弱知识点</h2>
          <div v-if="data.weakPoints.length === 0" class="empty">暂无诊断结果</div>
          <div v-else class="weak-list">
            <div v-for="(wp, i) in data.weakPoints" :key="i" class="weak-item">
              <span class="severity" :class="severityClass(wp.severity)">{{ wp.severity }}</span>
              <span class="wp-text">{{ wp.point }}</span>
              <span class="wp-count">{{ wp.error_count }}次</span>
            </div>
          </div>
        </section>
      </div>

      <!-- 趋势图 -->
      <section class="panel full-width">
        <h2>📈 学习趋势（按周）</h2>
        <div v-if="data.trends.length === 0" class="empty">暂无趋势数据</div>
        <div v-else class="trend-chart">
          <div class="trend-rows">
            <div v-for="(t, i) in data.trends" :key="i" class="trend-row">
              <span class="trend-week">{{ t.week }}</span>
              <div class="trend-bar-wrap">
                <div class="trend-bar" :style="{ width: Math.max(t.accuracy, 5) + '%' }">
                  <span class="trend-val">{{ t.accuracy }}%</span>
                </div>
              </div>
              <span class="trend-detail">{{ t.correct }}/{{ t.correct + t.wrong }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 学科对比 -->
      <section class="panel full-width">
        <h2>📚 学科对比</h2>
        <div v-if="data.subjects.length === 0" class="empty">暂无学科数据</div>
        <div v-else class="subject-grid">
          <div v-for="s in data.subjects" :key="s.subject" class="subject-card">
            <h3>{{ s.subject }}</h3>
            <div class="sub-stat">题目数：{{ s.total }}</div>
            <div class="sub-stat">错误数：{{ s.wrong }}</div>
            <div class="sub-acc" :class="{ good: s.accuracy >= 80, mid: s.accuracy >= 60, bad: s.accuracy < 60 }">
              正确率：{{ s.accuracy }}%
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchAnalytics } from '../api'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const data = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetchAnalytics()
    if (res.success) {
      data.value = res.data
    } else {
      error.value = res.message || '获取分析失败'
    }
  } catch (e) {
    error.value = '请求失败：' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
})

function severityClass(level) {
  if (level === '高危') return 'high'
  if (level === '中危') return 'mid'
  if (level === '关注') return 'low'
  return 'none'
}
</script>

<style scoped>
.analytics-page { max-width: 900px; margin: 0 auto; padding: 16px; font-family: sans-serif; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top-bar h1 { margin: 0; font-size: 1.4em; }
.nav-link { color: #667eea; text-decoration: none; font-size: 0.9em; }
.loading, .error-msg, .empty { text-align: center; padding: 40px; color: #888; font-size: 1em; }
.error-msg { color: #e74c3c; }

/* 骨架屏 */
.skeleton-area { padding: 16px; }
.skeleton-row { display: flex; gap: 12px; margin-bottom: 16px; }
.skeleton-row .skeleton-block { margin-bottom: 0; }
.skeleton-two-col { display: flex; gap: 16px; margin-bottom: 16px; }
.skeleton-two-col .skeleton-block { flex: 1; margin-bottom: 0; }
@media (max-width: 640px) {
  .skeleton-two-col { flex-direction: column; }
}

/* 总览卡片 */
.overview-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.card { background: #fff; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.card-num { font-size: 1.8em; font-weight: bold; color: #333; }
.card.highlight .card-num { color: #27ae60; }
.card.warn .card-num { color: #e67e22; }
.card-label { font-size: 0.8em; color: #999; margin-top: 4px; }

/* 双栏 */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.panel { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.panel h2 { font-size: 1em; margin: 0 0 12px; color: #333; }
.full-width { margin-bottom: 20px; }

/* 条形图 */
.bar-list { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 0.82em; }
.bar-label { width: 90px; text-align: right; color: #555; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { flex: 1; height: 18px; background: #f0f0f0; border-radius: 9px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 9px; min-width: 2px; transition: width 0.5s; }
.bar-value { width: 85px; color: #888; font-size: 0.75em; flex-shrink: 0; }

/* 薄弱知识点 */
.weak-list { display: flex; flex-direction: column; gap: 6px; }
.weak-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: #fafafa; border-radius: 8px; font-size: 0.82em; }
.severity { padding: 2px 8px; border-radius: 10px; font-size: 0.75em; font-weight: bold; color: #fff; }
.severity.high { background: #e74c3c; }
.severity.mid { background: #e67e22; }
.severity.low { background: #3498db; }
.severity.none { background: #95a5a6; }
.wp-text { flex: 1; color: #333; }
.wp-count { color: #888; font-size: 0.8em; white-space: nowrap; }

/* 趋势图 */
.trend-rows { display: flex; flex-direction: column; gap: 6px; }
.trend-row { display: flex; align-items: center; gap: 8px; font-size: 0.82em; }
.trend-week { width: 45px; text-align: right; color: #555; flex-shrink: 0; }
.trend-bar-wrap { flex: 1; height: 22px; background: #f0f0f0; border-radius: 11px; overflow: hidden; }
.trend-bar { height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); border-radius: 11px; min-width: 40px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; }
.trend-val { color: #fff; font-size: 0.75em; font-weight: bold; }
.trend-detail { width: 50px; color: #888; font-size: 0.75em; text-align: left; flex-shrink: 0; }

/* 学科对比 */
.subject-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
.subject-card { background: #fafafa; border-radius: 10px; padding: 12px; text-align: center; }
.subject-card h3 { margin: 0 0 8px; font-size: 0.95em; color: #333; }
.sub-stat { font-size: 0.78em; color: #777; margin: 2px 0; }
.sub-acc { font-size: 0.85em; font-weight: bold; margin-top: 6px; }
.sub-acc.good { color: #27ae60; }
.sub-acc.mid { color: #e67e22; }
.sub-acc.bad { color: #e74c3c; }

@media (max-width: 640px) {
  .overview-cards { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .bar-label { width: 60px; font-size: 0.72em; }
  .analytics-page { padding: 12px; }
  .subject-grid { grid-template-columns: repeat(2, 1fr); }
  .card { padding: 12px; }
  .card-num { font-size: 1.4em; }
}
@media (max-width: 480px) {
  .overview-cards { grid-template-columns: 1fr 1fr; gap: 8px; }
  .bar-label { width: 50px; }
  .top-bar h1 { font-size: 1.1em; }
}
</style>
