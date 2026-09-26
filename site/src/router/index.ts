import { createRouter, createWebHistory } from 'vue-router'

// 全部视图路由级懒加载（大表 chunk 只在 /browse 拉）
export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/browse', name: 'browse', component: () => import('../views/BrowseView.vue') },
    {
      path: '/plugin/:owner/:name',
      name: 'plugin',
      component: () => import('../views/PluginDetailView.vue'),
      props: true,
    },
    { path: '/featured', name: 'featured', component: () => import('../views/FeaturedView.vue') },
    { path: '/bundles', name: 'bundles', component: () => import('../views/BundlesView.vue') },
    { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
