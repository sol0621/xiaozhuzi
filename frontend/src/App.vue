<template>
  <ProgressBar />
  <router-view />
  <MobileNav />
</template>

<script setup>
import ProgressBar from './components/ProgressBar.vue'
import MobileNav from './components/MobileNav.vue'
import { useWakeLock } from './composables/useWakeLock'

useWakeLock()
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #F5F6FA; color: #333; }
#app { max-width: 480px; margin: 0 auto; min-height: 100vh; background: #F5F6FA; padding-bottom: 60px; }
@media (max-width: 480px) { #app { max-width: 100%; padding-bottom: 70px; } }
@media (min-width: 768px) { #app { max-width: 720px; } }
/* Touch-friendly: ensure all interactive elements are at least 44px tall */
button, select, .nav-item, input[type="file"] { min-height: 44px; }
@media (min-width: 769px) { button, select { min-height: auto; } }
</style>
