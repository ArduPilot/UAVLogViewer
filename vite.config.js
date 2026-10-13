import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import eslint from "vite-plugin-eslint2";
import { viteStaticCopy } from "vite-plugin-static-copy";

// The commit the app is built from, shown in the sidebar. Read from .git instead of running git;
// in a worktree .git is a file naming its git directory. "unknown" without a repository.
function gitCommit() {
    try {
        const gitDir = statSync(".git").isFile()
            ? readFileSync(".git", "utf8")
                  .replace(/^gitdir:\s*/, "")
                  .trim()
            : ".git";
        const head = readFileSync(join(gitDir, "HEAD"), "utf8").trim();
        if (!head.startsWith("ref: ")) {
            return head; // a detached HEAD is the commit itself
        }
        const ref = head.slice("ref: ".length);
        // a worktree's branches live in the main repository's git directory
        const commonFile = join(gitDir, "commondir");
        const commonDir = existsSync(commonFile)
            ? resolve(gitDir, readFileSync(commonFile, "utf8").trim())
            : gitDir;
        const loose = join(commonDir, ref);
        if (existsSync(loose)) {
            return readFileSync(loose, "utf8").trim();
        }
        const packed = readFileSync(join(commonDir, "packed-refs"), "utf8");
        return packed
            .split("\n")
            .find((line) => line.endsWith(` ${ref}`))
            .slice(0, 40);
    } catch {
        return "unknown";
    }
}

// Cesium loads its web workers, decoders (ThirdParty: Draco, KTX2), images and widget files at
// runtime from CESIUM_BASE_URL: its built folders go next to index.html
const CESIUM_FOLDERS = ["Workers", "ThirdParty", "Assets", "Widgets"];

export default defineConfig(({ command, mode }) => ({
    // relative URLs: dist/ works wherever it is served from
    base: "./",
    plugins: [
        vue(),
        viteStaticCopy({
            targets: CESIUM_FOLDERS.map((dir) => ({
                src: `node_modules/cesium/Build/Cesium/${dir}`,
                dest: ".",
                // dist/Workers, not dist/node_modules/cesium/Build/Cesium/Workers
                rename: { stripBase: 4 },
            })),
        }),
        // lint the sources while developing, fixing what ESLint can fix (it rewrites them)
        command === "serve" && mode !== "test" && eslint({ fix: true }),
    ],
    define: {
        _COMMIT_: JSON.stringify(gitCommit()),
        _BUILDDATE_: JSON.stringify(new Date().toString()),
        CESIUM_BASE_URL: JSON.stringify(""),
        // Node's name for it, which Plotly's has-hover uses (webpack 5 mapped it by itself)
        global: "globalThis",
    },
    resolve: {
        alias: { "@": fileURLToPath(new URL("src", import.meta.url)) },
    },
    // the vehicle models and the sample log are imported as file URLs
    assetsInclude: ["**/*.glb", "**/*.tlog"],
    build: {
        outDir: "dist",
        // the URLs plot.ardupilot.org has always had (static/...)
        assetsDir: "static",
        // files under 10 kB become data URLs, as with webpack
        assetsInlineLimit: 10000,
        rolldownOptions: {
            output: {
                // the libraries apart from the app, so that a new version of the app does not
                // download them again
                codeSplitting: {
                    // module ids use forward slashes, also on Windows
                    groups: [
                        { name: "cesium", test: /node_modules\/@?cesium\// },
                        { name: "plotly", test: /node_modules\/plotly\.js\// },
                        {
                            name: "vue",
                            test: /node_modules\/(@vue|vue|vue-router)\//,
                        },
                        { name: "vendor", test: /node_modules\// },
                    ],
                },
            },
        },
    },
    // the parser worker is a module worker (new Worker(..., { type: "module" }))
    worker: { format: "es" },
    // the app's page only, not every .html in the project (e.g. the Nightwatch report)
    optimizeDeps: { entries: ["index.html"] },
    server: {
        host: "0.0.0.0",
        port: 8080,
        proxy: {
            // the terrain tiles of plot.ardupilot.org (see CesiumViewer.vue)
            "/quantized": {
                target: "https://plot.ardupilot.org",
                changeOrigin: true,
            },
            // the upload and Eniro map backend plot.ardupilot.org runs next to the app
            "/upload": "http://localhost:8001",
            "/uploaded": "http://localhost:8001",
            "/eniro": "http://localhost:8001",
        },
    },
}));
