import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.js";

// the app's Vite config (plugins, defines, aliases, ?raw imports) plus the test settings
export default defineConfig((env) =>
    mergeConfig(viteConfig(env), {
        define: {
            _COMMIT_: JSON.stringify("test"),
            _BUILDDATE_: JSON.stringify("test"),
        },
        test: {
            environment: "jsdom",
            // describe, test, expect and vi without imports, as with Jest
            globals: true,
            include: ["test/unit/specs/**/*.spec.js"],
            // the parser specs read whole flight logs
            testTimeout: 30000,
            coverage: {
                provider: "v8",
                reportsDirectory: "test/unit/coverage",
                include: ["src/**/*.{js,vue}"],
                exclude: ["src/main.js", "src/router/index.js"],
            },
        },
    }),
);
