import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Detect if running inside Docker (backend service is reachable at "backend:8001")
const isDocker = process.env.CHOKIDAR_USEPOLLING === 'true'
const backendHost = isDocker ? 'http://backend:8001' : 'http://localhost:8001'
const backendWs   = isDocker ? 'ws://backend:8001'   : 'ws://localhost:8001'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Listen on all interfaces so Docker can forward traffic
    host: '0.0.0.0',
    port: 5173,
    // Allow connections from any origin (Docker host, etc.)
    allowedHosts: true,
    // HMR configuration for Docker on macOS
    hmr: {
      // Let the browser connect to HMR on the same host it loaded the page from
      clientPort: 5173,
    },
    // File watching — use polling for macOS Docker Desktop
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api': backendHost,
      '/ws': {
        target: backendWs,
        ws: true,
      }
    }
  }
})