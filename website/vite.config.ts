import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Single source of truth for the version shown in download links.
const versionFile = fileURLToPath(new URL('../VERSION', import.meta.url))
const appVersion = readFileSync(versionFile, 'utf-8').trim()

// https://vite.dev/config/
export default defineConfig({
  base: '/MediaGrab/',
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
