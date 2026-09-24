import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  build: {
    outDir: "dist/client",
    rollupOptions: {
      // The desktop app shows splash.html while its local service starts.
      input: {
        main: fileURLToPath(new URL("index.html", import.meta.url)),
        splash: fileURLToPath(new URL("splash.html", import.meta.url)),
      },
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  server: {
    host: "127.0.0.1",
    allowedHosts: ["terminal.local"],
    proxy: {
      "/api": process.env.DAYWRIGHT_API_TARGET || "http://127.0.0.1:8421",
    },
    warmup: {
      clientFiles: ["./src/main.jsx"],
    },
  },
  plugins: [react()],
});
