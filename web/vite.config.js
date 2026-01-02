/// <reference types="vitest" />
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import svgr from "vite-plugin-svgr"
import path from "path"

export default defineConfig({
  plugins: [
    react(),
    svgr({
      svgrOptions: {
        exportType: "named",
        ref: true,
        svgo: false,
        titleProp: true,
      },
      include: "**/*.svg?react",
    }),
  ],
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
    allowedHosts: ["dumontcloud.orb.local", "dumontcloud-local.orb.local", ".orb.local", "localhost"],
    // HMR config - let Vite auto-detect port
    hmr: {
      protocol: "ws",
      host: "localhost",
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
        target: "http://localhost:8081",
        changeOrigin: true,
      },
      "/api/docs": {
        target: "http://localhost:8081",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/docs/, "/api"),
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
  },
})
