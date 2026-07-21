import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    build: {
      // Bundles go to /static/, NOT vite's default /assets/ — the app has real
      // routes at /assets (Asset Hub), and in the nginx prod build the directory
      // was shadowing the route (refresh/deep-link on /assets returned 403).
      assetsDir: 'static',
    },
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
