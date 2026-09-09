import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,   // fail loudly instead of silently picking 5174+
    proxy: {
      // Proxy REST API calls → FastAPI backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections → FastAPI backend
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
