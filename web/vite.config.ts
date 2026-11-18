/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server forwards API calls to `libarrei serve`, so the app always uses
// same-origin relative URLs, exactly as it will when FastAPI serves the build.
// LIBARREI_API overrides the target when port 8000 is taken.
const api = process.env.LIBARREI_API ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/v1': api, '/health': api } },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'] },
})
