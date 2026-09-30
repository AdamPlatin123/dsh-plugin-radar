import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base = 仓库名路径（GitHub Pages 项目页）；数据大表走独立 chunk（进 /browse 才拉）
export default defineConfig({
  base: '/dsh-plugin-radar/',
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          datarows: ['./src/data/plugins.ts'],
        },
      },
    },
  },
})
