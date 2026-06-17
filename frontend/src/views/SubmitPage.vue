<template>
  <div class="submit-page">
    <div class="header"><img src="/avatar.jpg" class="app-avatar" /> 小学作业辅导助手</div>

    <div class="section">
      <div class="label">年级</div>
      <div class="segment">
        <button v-for="g in [4,5,6]" :key="g" :class="{active: grade===g}" @click="grade=g">{{g}}年级</button>
      </div>
    </div>

    <div class="section">
      <div class="label">科目</div>
      <div class="segment">
        <button v-for="s in subjects" :key="s.value" :class="{active: subject===s.value}" @click="subject=s.value">{{s.label}}</button>
      </div>
    </div>

    <div class="section">
      <div class="tabs">
        <button :class="{active: inputMode==='text'}" @click="inputMode='text'">文字输入</button>
        <button :class="{active: inputMode==='photo'}" @click="inputMode='photo'">拍照上传</button>
      </div>

      <div v-if="inputMode==='text'" class="input-area">
        <textarea v-model="textContent" rows="8" placeholder="请把作业内容粘贴在这里，每道题换一行即可"></textarea>
        <div class="hint">支持一次性粘贴多道题，换行即可自动分题</div>
      </div>

      <div v-else class="input-area photo-area">
        <div class="upload-box" @click="triggerUpload">
          <div class="camera-icon">📷</div>
          <div>点击选择图片（最多10张，每张≤10MB）</div>
        </div>
        <input ref="fileInput" type="file" accept="image/*" multiple @change="onFilesChange" style="display:none;">
        <div v-if="uploadedImages.length" class="thumbnails">
          <div v-for="(img, idx) in uploadedImages" :key="idx" class="thumb">
            <img :src="img.preview" />
            <span class="del" @click.stop="removeImage(idx)">×</span>
            <span class="num">{{idx+1}}</span>
          </div>
        </div>
        <div v-if="uploadedImages.length" class="count">已选 {{uploadedImages.length}} 张 / 最多 10 张</div>
      </div>
    </div>

    <div class="section">
      <button class="btn-primary" :disabled="!canSubmit || loading" @click="submit">
        <span v-if="loading">正在识别和批改…</span>
        <span v-else>开始批改</span>
      </button>
    </div>

    <div v-if="loading" class="loading-mask">
      <div class="spinner"></div>
      <div class="loading-text">{{ loadingText }}</div>
    </div>

    <!-- Bottom Nav -->
    <nav class="bottom-nav">
      <router-link to="/" class="nav-item active">🏠 批改</router-link>
      <router-link to="/mistake-book" class="nav-item">📒 错题本</router-link>
      <router-link to="/analytics" class="nav-item">📊 分析</router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeworkStore } from '@/stores/homework'
import { correctHomework } from '@/api'

const router = useRouter()
const store = useHomeworkStore()

const grade = ref(store.grade || 4)
const subject = ref(store.subject || 'math')
const inputMode = ref(store.inputMode || 'text')
const textContent = ref(store.textContent || '')
const uploadedImages = ref([])
const fileInput = ref(null)
const loading = ref(false)
const loadingText = ref('AI正在读取作业，请稍候…')
let timer = null

const subjects = [
  {value:'math', label:'数学'},
  {value:'chinese', label:'语文'},
  {value:'english', label:'英语'},
  {value:'science', label:'科学'},
]

const canSubmit = computed(() => {
  if (inputMode.value === 'text') return textContent.value.trim().length >= 3
  return uploadedImages.value.length > 0
})

function triggerUpload() { fileInput.value?.click() }

function onFilesChange(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  if (uploadedImages.value.length + files.length > 10) {
    alert('最多上传10张图片')
    return
  }
  files.forEach(file => {
    if (file.size > 10 * 1024 * 1024) { alert(`图片 ${file.name} 超过10MB，已跳过`); return }
    const reader = new FileReader()
    reader.onload = ev => uploadedImages.value.push({ file, preview: ev.target.result })
    reader.readAsDataURL(file)
  })
  e.target.value = ''
}
function removeImage(idx) { uploadedImages.value.splice(idx, 1) }

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  const hints = ['AI正在读取作业，请稍候…','正在逐题判断对错…','正在整理结果…']
  let i = 0
  loadingText.value = hints[0]
  timer = setInterval(() => { i = (i+1)%hints.length; loadingText.value = hints[i] }, 3000)

  try {
    const fd = new FormData()
    fd.append('grade', grade.value)
    fd.append('subject', subject.value)
    fd.append('inputMode', inputMode.value)
    if (inputMode.value === 'text') fd.append('textContent', textContent.value)
    else uploadedImages.value.forEach(img => fd.append('images', img.file))

    const res = await correctHomework(fd)
    store.grade = grade.value
    store.subject = subject.value
    store.inputMode = inputMode.value
    store.textContent = textContent.value
    store.uploadedImages = uploadedImages.value
    store.setResult(res.data)
    router.push('/result')
  } catch (err) {
    const msg = err.response?.data?.message || err.message || ''
    if (err.code === 'ECONNABORTED' || msg.includes('timeout')) {
      alert('请求超时，服务器可能正在冷启动（约需30-60秒），请稍后重试。')
    } else if (err.code === 'ERR_NETWORK' || msg.includes('Network Error')) {
      alert('网络连接失败。可能是服务器正在启动中，请等待1分钟后重试。\n\n若持续失败，请检查网络或联系技术支持。')
    } else {
      alert('提交失败：' + (msg || '未知错误'))
    }
  } finally {
    loading.value = false
    clearInterval(timer)
  }
}
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.submit-page { padding: 16px 16px 70px 16px; }
.header { font-size: 20px; font-weight: 700; color: #4A90D9; text-align: center; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 8px; }
.app-avatar { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid #4A90D9; }
.section { margin-bottom: 20px; }
.label { font-size: 14px; color: #666; margin-bottom: 8px; }
.segment { display: flex; gap: 8px; }
.segment button { flex:1; padding:10px 0; border:1px solid #ddd; background:#fff; border-radius:8px; font-size:14px; cursor:pointer; }
.segment button.active { background:#4A90D9; color:#fff; border-color:#4A90D9; }
.tabs { display:flex; margin-bottom:12px; }
.tabs button { flex:1; padding:10px 0; border:none; background:#eee; font-size:14px; cursor:pointer; border-radius:0; }
.tabs button:first-child { border-radius:8px 0 0 8px; }
.tabs button:last-child { border-radius:0 8px 8px 0; }
.tabs button.active { background:#4A90D9; color:#fff; }
textarea { width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; font-size:14px; resize:vertical; }
.hint { font-size:12px; color:#999; margin-top:6px; }
.photo-area .upload-box { border:2px dashed #ccc; border-radius:8px; padding:30px; text-align:center; color:#999; cursor:pointer; }
.camera-icon { font-size:32px; margin-bottom:8px; }
.thumbnails { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }
.thumb { position:relative; aspect-ratio:1; border-radius:6px; overflow:hidden; background:#eee; }
.thumb img { width:100%; height:100%; object-fit:cover; }
.thumb .del { position:absolute; top:4px; right:4px; width:20px; height:20px; background:rgba(0,0,0,0.5); color:#fff; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; cursor:pointer; }
.thumb .num { position:absolute; top:4px; left:4px; background:rgba(0,0,0,0.5); color:#fff; font-size:10px; padding:2px 6px; border-radius:4px; }
.count { font-size:12px; color:#666; margin-top:8px; }
.btn-primary { width:100%; padding:14px; background:#4A90D9; color:#fff; border:none; border-radius:12px; font-size:16px; font-weight:600; cursor:pointer; }
.btn-primary:disabled { background:#ccc; cursor:not-allowed; }
.loading-mask { position:fixed; inset:0; background:rgba(255,255,255,0.85); display:flex; flex-direction:column; align-items:center; justify-content:center; z-index:100; }
.spinner { width:40px; height:40px; border:4px solid #eee; border-top-color:#4A90D9; border-radius:50%; animation:spin 1s linear infinite; margin-bottom:16px; }
@keyframes spin { to { transform:rotate(360deg); } }
.loading-text { color:#4A90D9; font-size:14px; }

/* Bottom Navigation */
.bottom-nav { display: flex; justify-content: space-around; align-items: center; position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 480px; background: #fff; border-top: 1px solid #eee; padding: 8px 0; z-index: 50; box-shadow: 0 -1px 4px rgba(0,0,0,0.04); }
.nav-item { display: flex; flex-direction: column; align-items: center; gap: 2px; text-decoration: none; font-size: 11px; color: #999; padding: 4px 16px; }
.nav-item.active { color: #4A90D9; font-weight: 600; }
</style>
