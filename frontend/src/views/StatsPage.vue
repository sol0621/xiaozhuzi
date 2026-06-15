<template>
  <div class="stats-page">
    <div class="nav-bar">
      <span class="back" @click="router.push('/')">← 返回首页</span>
      <span class="title">易错点统计</span>
      <span class="placeholder"></span>
    </div>
    <div class="content" v-if="stats">
      <div class="summary">
        <div class="sum-item">
          <div class="sum-num">{{ stats.totalProblems || 0 }}</div>
          <div class="sum-label">总做题数</div>
        </div>
        <div class="sum-item">
          <div class="sum-num">{{ stats.totalErrors || 0 }}</div>
          <div class="sum-label">总错题数</div>
        </div>
        <div class="sum-item">
          <div class="sum-num">{{ stats.accuracyRate || '0%' }}</div>
          <div class="sum-label">正确率</div>
        </div>
      </div>

      <div class="section-title">TOP 5 易错类型</div>
      <div class="rank-list">
        <div v-for="(item, idx) in stats.topErrors || []" :key="idx" class="rank-item">
          <div class="rank-left">
            <span class="rank-num">{{ idx + 1 }}</span>
            <span class="rank-name">{{ item.type }}</span>
          </div>
          <div class="rank-bar-wrap">
            <div class="rank-bar" :style="{width: (item.percent||0) + '%'}"></div>
            <span class="rank-count">{{ item.count }}次</span>
          </div>
        </div>
      </div>

      <div class="section-title">科目分布</div>
      <div class="subject-tags">
        <div v-for="(s, idx) in stats.subjectDist || []" :key="idx" class="tag">
          {{ s.name }} {{ s.count }}题
        </div>
      </div>
    </div>
    <div v-else class="empty">
      暂无统计数据，快去批改作业吧～
      <button class="btn-primary" @click="router.push('/')">去批改</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchStats } from '@/api'

const router = useRouter()
const stats = ref(null)

onMounted(async () => {
  try {
    const res = await fetchStats()
    stats.value = res.data || null
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.stats-page { min-height:100vh; }
.nav-bar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:#fff; border-bottom:1px solid #eee; position:sticky; top:0; z-index:10; }
.back { color:#4A90D9; font-size:14px; cursor:pointer; }
.title { font-size:16px; font-weight:600; }
.placeholder { width:70px; }
.content { padding:16px; }
.summary { display:flex; gap:12px; margin-bottom:20px; }
.sum-item { flex:1; background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.sum-num { font-size:22px; font-weight:700; color:#4A90D9; }
.sum-label { font-size:12px; color:#999; margin-top:4px; }
.section-title { font-size:14px; font-weight:600; color:#333; margin-bottom:12px; }
.rank-list { background:#fff; border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:12px; }
.rank-item { display:flex; align-items:center; gap:10px; }
.rank-left { display:flex; align-items:center; gap:8px; width:100px; }
.rank-num { width:20px; height:20px; background:#eee; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; color:#666; }
.rank-item:first-child .rank-num { background:#F5A623; color:#fff; }
.rank-name { font-size:13px; color:#333; }
.rank-bar-wrap { flex:1; display:flex; align-items:center; gap:8px; }
.rank-bar { height:8px; background:#4A90D9; border-radius:4px; min-width:4px; }
.rank-count { font-size:11px; color:#999; white-space:nowrap; }
.subject-tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.tag { background:#fff; padding:8px 12px; border-radius:20px; font-size:12px; color:#666; border:1px solid #eee; }
.empty { padding:80px 24px; text-align:center; color:#999; font-size:14px; }
.empty .btn-primary { margin-top:20px; width:100%; padding:12px; background:#4A90D9; color:#fff; border:none; border-radius:10px; font-size:14px; cursor:pointer; }
</style>
