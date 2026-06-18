const CACHE = 'hw-v2-2'
const ASSETS = ['/manifest.json']

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS).catch(() => {}))
  )
  self.skipWaiting()
})

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return

  const url = new URL(e.request.url)
  const isNavigation = e.request.mode === 'navigate'
  const isSameOrigin = url.origin === self.location.origin

  if (isNavigation && isSameOrigin) {
    // 页面 HTML：始终网络优先，网络失败才用缓存
    e.respondWith(
      fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone()
          caches.open(CACHE).then(c => c.put(e.request, clone))
        }
        return res
      }).catch(() => caches.match(e.request))
    )
  } else if (isSameOrigin) {
    // JS/CSS/图片等静态资源：缓存优先，后台更新
    e.respondWith(
      caches.match(e.request).then(cached => {
        const fetchPromise = fetch(e.request).then(res => {
          if (res.ok) {
            const clone = res.clone()
            caches.open(CACHE).then(c => c.put(e.request, clone))
          }
          return res
        })
        return cached || fetchPromise
      })
    )
  }
  // 跨域请求不拦截，直接放行
})
