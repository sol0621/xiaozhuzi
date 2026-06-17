import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 210000,  // 3.5分钟，覆盖Render冷启动(~60s)+OCR(~15s)+LLM(~30s)
})

// 全局请求拦截器：显示进度条
api.interceptors.request.use(
  (config) => {
    if (window._progressBar) window._progressBar.start()
    return config
  },
  (error) => {
    if (window._progressBar) window._progressBar.error()
    return Promise.reject(error)
  }
)

// 全局响应拦截器：隐藏进度条
api.interceptors.response.use(
  (response) => {
    if (window._progressBar) window._progressBar.done()
    return response
  },
  (error) => {
    if (window._progressBar) window._progressBar.error()
    return Promise.reject(error)
  }
)

export async function correctHomework(formData) {
  const res = await api.post('/correct', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

export async function explainError(payload) {
  const res = await api.post('/explain', payload)
  return res.data
}

export async function fetchStats(params) {
  const res = await api.get('/stats', { params })
  return res.data
}

export async function fetchAnalytics(subject) {
  const params = subject ? { subject } : {}
  const res = await api.get('/analytics', { params })
  return res.data
}

export async function fetchMistakeBook(params) {
  const res = await api.get('/mistake-book', { params })
  return res.data
}

export async function recordError(payload) {
  const res = await api.post('/record-error', payload)
  return res.data
}
