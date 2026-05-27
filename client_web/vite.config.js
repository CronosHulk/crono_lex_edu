import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const sharedAlias = resolve(__dirname, "../frontend_shared/src");
const dependencyAliases = {
  "@mui/material": resolve(__dirname, "node_modules/@mui/material"),
  "lucide-react": resolve(__dirname, "node_modules/lucide-react"),
  react: resolve(__dirname, "node_modules/react"),
  "react-dom": resolve(__dirname, "node_modules/react-dom"),
};

export default defineConfig({
  base: "/",
  plugins: [react()],
  resolve: {
    alias: {
      "@cronolex/shared": sharedAlias,
      ...dependencyAliases,
    },
    dedupe: ["@mui/material", "lucide-react", "react", "react-dom"],
  },
  server: {
    port: 5175,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 0,
  },
});
