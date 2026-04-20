/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import tailwindcss from "@tailwindcss/vite";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (/[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/.test(id)) {
              return "react-core";
            }
            if (/[\\/]node_modules[\\/]framer-motion[\\/]/.test(id)) {
              return "motion-core";
            }
            if (/[\\/]node_modules[\\/]country-flag-icons[\\/]/.test(id)) {
              return "desktop-flags";
            }
            if (/[\\/]node_modules[\\/]lucide-react[\\/]/.test(id)) {
              return "desktop-icons";
            }
            if (/[\\/]node_modules[\\/]recharts[\\/]/.test(id)) {
              return "desktop-charts";
            }
            if (/[\\/]node_modules[\\/](@hookform|react-hook-form|zod)[\\/]/.test(id)) {
              return "desktop-forms";
            }
            if (/[\\/]node_modules[\\/]@tauri-apps[\\/]/.test(id)) {
              return "desktop-tauri";
            }
            if (/[\\/]node_modules[\\/](i18next|react-i18next|luxon)[\\/]/.test(id)) {
              return "desktop-i18n";
            }
          }

          if (id.includes("/src/pages/Dashboard/")) {
            return "dashboard-route";
          }

          if (
            id.includes("/src/pages/Settings/") ||
            id.includes("/src/components/settings/")
          ) {
            return "settings-route";
          }

          if (
            (id.includes("/src/widgets/") &&
              !id.endsWith("/src/widgets/TrafficGraph.tsx")) ||
            id.includes("/src/app/") ||
            id.includes("/src/components/ui/") ||
            id.endsWith("/src/main.tsx") ||
            id.endsWith("/src/shared/lib/motion.ts")
          ) {
            return "desktop-shell";
          }
        },
      },
    },
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
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
  },
  test: {
    environment: "happy-dom",
    pool: "threads",
    setupFiles: "./vitest.setup.ts",
  },
}));
