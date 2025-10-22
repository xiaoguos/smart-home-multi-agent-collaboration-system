import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

// https://vite.dev/config/
export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // 后端地址：默认本地，可通过环境变量配置局域网地址
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:2100';
  
  return {
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
      "@component": "/src/components",
      "@pages": "/src/pages",
    },
  },
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
    // API 代理配置
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path, // 保持路径不变
      }
    },
  },
}});

