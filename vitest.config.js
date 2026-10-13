import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue2";

export default defineConfig({
    plugins: [vue()],
    // what webpack's DefinePlugin gives the app (see Globals.js)
    define: {
        _COMMIT_: JSON.stringify("test"),
        _BUILDDATE_: JSON.stringify("test"),
    },
    resolve: {
        alias: { "@": fileURLToPath(new URL("src", import.meta.url)) },
    },
    test: {
        environment: "jsdom",
        // describe, test, expect and vi without imports, as with Jest
        globals: true,
        include: ["test/unit/specs/**/*.spec.js"],
        setupFiles: ["test/unit/setup.js"],
        // the parser specs read whole flight logs
        testTimeout: 30000,
        coverage: {
            provider: "v8",
            reportsDirectory: "test/unit/coverage",
            include: ["src/**/*.{js,vue}"],
            exclude: ["src/main.js", "src/router/index.js"],
        },
    },
});
