import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'

export const useHomeworkStore = defineStore('homework', () => {
  const grade = ref(4)
  const subject = ref('math')
  const inputMode = ref('text')
  const textContent = ref('')
  const uploadedImages = ref([])

  const correctionResult = ref(null)
  const currentExplainQuestion = ref(null)
  const allWrongQuestions = ref([])
  const currentExplainIndex = ref(0)
  const stats = ref(null)
  const correctModal = reactive({ visible: false, q: null, customAnswer: '' })

  function setResult(result) {
    correctionResult.value = result
    if (result?.questions) {
      allWrongQuestions.value = result.questions.filter(q => !q.isCorrect && q.status === 'normal')
    } else {
      allWrongQuestions.value = []
    }
  }

  function refreshCounts() {
    const res = correctionResult.value
    if (!res || !res.questions) return
    res.correctCount = res.questions.filter(q => q.isCorrect && q.status === 'normal').length
    res.wrongCount = res.questions.filter(q => !q.isCorrect && q.status === 'normal').length
  }

  function setExplainQuestion(q, index = 0) {
    currentExplainQuestion.value = q
    currentExplainIndex.value = index
  }

  function reset() {
    textContent.value = ''
    uploadedImages.value = []
    correctionResult.value = null
    currentExplainQuestion.value = null
    allWrongQuestions.value = []
    currentExplainIndex.value = 0
    correctModal.visible = false
    correctModal.q = null
    correctModal.customAnswer = ''
  }

  return {
    grade, subject, inputMode, textContent, uploadedImages,
    correctionResult, currentExplainQuestion, allWrongQuestions, currentExplainIndex, stats,
    correctModal,
    setResult, refreshCounts, setExplainQuestion, reset
  }
})
