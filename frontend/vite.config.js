import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
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
