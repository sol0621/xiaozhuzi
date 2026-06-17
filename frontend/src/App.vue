<template>
  <ProgressBar />
  <router-view />
</template>

<script setup>
import ProgressBar from './components/ProgressBar.vue'
import { useWakeLock } from './composables/useWakeLock'

useWakeLock()
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #F5F6FA; color: #333; }
#app { max-width: 480px; margin: 0 auto; min-height: 100vh; background: #F5F6FA; }
</style>
