<template>
  <nav class="mobile-nav">
    <router-link to="/" class="nav-item" exact-active-class="active">
      <span class="nav-icon">🏠</span>
      <span class="nav-label">批改</span>
    </router-link>
    <router-link to="/mistake-book" class="nav-item" active-class="active">
      <span class="nav-icon">📒</span>
      <span class="nav-label">错题本</span>
    </router-link>
    <router-link to="/analytics" class="nav-item" active-class="active">
      <span class="nav-icon">📊</span>
      <span class="nav-label">分析</span>
    </router-link>
  </nav>
</template>

<style scoped>
.mobile-nav {
  display: flex;
  justify-content: space-around;
  align-items: center;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-top: 1px solid #eee;
  padding: 6px 0 env(safe-area-inset-bottom, 6px) 0;
  z-index: 100;
  box-shadow: 0 -1px 6px rgba(0,0,0,0.06);
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  text-decoration: none;
  font-size: 11px;
  color: #999;
  padding: 4px 20px;
  border-radius: 8px;
  transition: color 0.2s;
  min-height: 44px;
  justify-content: center;
}
.nav-item.active,
.nav-item.router-link-exact-active {
  color: #4A90D9;
  font-weight: 600;
}
.nav-icon { font-size: 20px; line-height: 1; }
.nav-label { line-height: 1; }

@media (min-width: 769px) {
  .mobile-nav { display: none; }
}
</style>
