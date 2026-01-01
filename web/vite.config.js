/// <reference types="vitest" />
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.js"],
    include: ["**/*.{test,spec}.{js,jsx,ts,tsx}"],
    css: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 4890,
    strictPort: false,
    allowedHosts: ["dumontcloud-local.orb.local", ".orb.local", "localhost"],
    // HMR config - automatically use the same port as the server
    hmr: {
      protocol: "ws",
    },
    watch: {
      usePolling: false,
    },
    proxy: {
      "/admin/doc/live": {
        target: "http://192.168.139.80:8081",
        changeOrigin: true,
      },
      "/api/docs": {
        target: "http://192.168.139.80:8081",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/docs/, "/api"),
      },
      "/api": {
        target: "http://192.168.139.80:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://192.168.139.80:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
  },
})
