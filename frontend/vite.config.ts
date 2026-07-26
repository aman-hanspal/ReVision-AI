import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react({ jsxRuntime: "automatic" })],
  esbuild: { jsx: "automatic" },
  server: {
    port: 5173,
    proxy: {
      "/chat": { target: "http://localhost:8000", changeOrigin: true },
      "/upload": { target: "http://localhost:8000", changeOrigin: true },
      "/telegram": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});