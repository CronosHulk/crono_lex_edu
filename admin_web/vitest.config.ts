import { defineConfig } from "vitest/config";

const sharedPath = new URL("../frontend_shared/src", import.meta.url).pathname;
const dependencyPath = (dependency: string) => new URL(`./node_modules/${dependency}`, import.meta.url).pathname;

export default defineConfig({
  resolve: {
    alias: {
      "@cronolex/shared": sharedPath,
      "@mui/material": dependencyPath("@mui/material"),
      "lucide-react": dependencyPath("lucide-react"),
      react: dependencyPath("react"),
      "react-dom": dependencyPath("react-dom")
    },
    dedupe: ["@mui/material", "lucide-react", "react", "react-dom"]
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    testTimeout: 15_000,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: [
        "src/api/**/*.{ts,tsx}",
        "src/app/**/*.{ts,tsx}",
        "src/features/**/*.{ts,tsx}",
        "src/i18n/**/*.{ts,tsx}",
        "src/shared/**/*.{ts,tsx}",
        "src/theme/**/*.{ts,tsx}"
      ],
      exclude: [
        "**/*.test.{ts,tsx}",
        "**/*.spec.{ts,tsx}",
        "**/*.d.ts",
        "src/test/**"
      ],
      thresholds: {
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100
      }
    }
  }
});
