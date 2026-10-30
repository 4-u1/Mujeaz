import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

// The API is served by the FastAPI backend (backend/). In development, Vite
// proxies /api and /.well-known to it so the browser sees a single origin.
const API_TARGET = process.env.MUJEAZ_API_URL || 'http://localhost:8000';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': { target: API_TARGET, changeOrigin: true },
        '/.well-known': { target: API_TARGET, changeOrigin: true },
      },
    },
  };
});
