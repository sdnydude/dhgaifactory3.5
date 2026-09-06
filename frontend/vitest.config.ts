import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    // tdd-guard reads test results from <repo>/.claude/tdd-guard/data/test.json;
    // the reporter must point at the repo root, not frontend/.
    reporters: ["default", ["tdd-guard-vitest", { projectRoot: path.resolve(__dirname, "..") }]],
  },
});
