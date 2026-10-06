import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 43187,
    strictPort: true,
    proxy: {
      "/login": "http://127.0.0.1:5001",
      "/turnos": "http://127.0.0.1:5001",
      "/trabajadores": "http://127.0.0.1:5001",
      "/usuarios": "http://127.0.0.1:5001",
      "/departamentos": "http://127.0.0.1:5001",
      "/fichajes": "http://127.0.0.1:5001",
      "/ajustes": "http://127.0.0.1:5001",
      "/festivos": "http://127.0.0.1:5001",
      "/health": "http://127.0.0.1:5001",
    },
  },
});
