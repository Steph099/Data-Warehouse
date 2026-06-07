import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API calls to the FastAPI backend, so the app uses relative
// URLs with no CORS dance during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
