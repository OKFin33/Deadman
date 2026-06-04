import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const repoRootPath = new URL("..", import.meta.url).pathname;
const deadmanApiProxyTarget = process.env.VITE_DEADMAN_API_PROXY_TARGET || "http://127.0.0.1:7860";

export default defineConfig({
  plugins: [react()],
  publicDir: "../assets/public",
  server: {
    port: 5175,
    proxy: {
      "/api/deadman": deadmanApiProxyTarget,
    },
    fs: {
      allow: [repoRootPath],
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
