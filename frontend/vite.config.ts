import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        rewrite: (path) => path,
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/snapshots": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
