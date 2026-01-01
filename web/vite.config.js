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
    port: 4892,
    strictPort: false,
    allowedHosts: ["dumontcloud.orb.local", "dumontcloud-local.orb.local", ".orb.local"],
    // HMR config - automatically use the same port as the server
    hmr: {
      protocol: "ws",
      host: "dumontcloud.orb.local",
      clientPort: 4892,
    },
    watch: {
      usePolling: false,
    },
    // Disable cache completely
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
      "Pragma": "no-cache",
      "Expires": "0",
    },
    proxy: {
      "/admin/doc/live": {
        target: "http://dumontcloud.orb.local:8081",
        changeOrigin: true,
      },
      "/api/docs": {
        target: "http://dumontcloud.orb.local:8081",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/docs/, "/api"),
      },
      "/api": {
        target: "http://dumontcloud.orb.local:8767",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://dumontcloud.orb.local:8767",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
  },
})
