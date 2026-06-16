import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
})

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

export async function recordError(payload) {
  const res = await api.post('/record-error', payload)
  return res.data
}

export async function correctProblem(payload) {
  const res = await api.post('/correct-problem', payload)
  return res.data
}

export async function fetchMistakeBook(params) {
  const res = await api.get('/mistake-book', { params })
  return res.data
}
