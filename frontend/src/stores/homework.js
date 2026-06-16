import { ref } from 'vue'
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

  function setResult(result) {
    correctionResult.value = result
    if (result?.questions) {
      allWrongQuestions.value = result.questions.filter(q => !q.isCorrect && q.status === 'normal')
    } else {
      allWrongQuestions.value = []
    }
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
  }

  return {
    grade, subject, inputMode, textContent, uploadedImages,
    correctionResult, currentExplainQuestion, allWrongQuestions, currentExplainIndex, stats,
    setResult, setExplainQuestion, reset
  }
})
