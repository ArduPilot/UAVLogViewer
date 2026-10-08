import { mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";

const token = process.env.VUE_APP_CESIUM_TOKEN || "";
const content = `window.__APP_CONFIG__ = Object.assign({}, window.__APP_CONFIG__, {\n  VUE_APP_CESIUM_TOKEN: ${JSON.stringify(
    token,
)}\n});\n`;

const targets = [
    resolve(import.meta.dirname, "../runtime-config.js"),
    resolve(import.meta.dirname, "../dist/runtime-config.js"),
];

for (const filePath of targets) {
    mkdirSync(dirname(filePath), { recursive: true });
    writeFileSync(filePath, content);
}

console.log("Generated runtime config for Cesium token");
