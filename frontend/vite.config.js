import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/auth':     'http://backend:8000',
      '/users':    'http://backend:8000',
      '/projects': 'http://backend:8000',
      '/stats':    'http://backend:8000',
    },
  },
})