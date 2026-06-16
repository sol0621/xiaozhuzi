import { createRouter, createWebHashHistory } from 'vue-router'
import SubmitPage from '@/views/SubmitPage.vue'
import ResultPage from '@/views/ResultPage.vue'
import ExplainPage from '@/views/ExplainPage.vue'
import StatsPage from '@/views/StatsPage.vue'
import AnalyticsPage from '@/views/AnalyticsPage.vue'
import MistakeBook from '@/views/MistakeBook.vue'

const routes = [
  { path: '/', name: 'Submit', component: SubmitPage },
  { path: '/result', name: 'Result', component: ResultPage },
  { path: '/explain', name: 'Explain', component: ExplainPage },
  { path: '/stats', name: 'Stats', component: StatsPage },
  { path: '/analytics', name: 'Analytics', component: AnalyticsPage },
  { path: '/mistake-book', name: 'MistakeBook', component: MistakeBook },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
