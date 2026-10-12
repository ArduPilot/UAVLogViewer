// Serve the production build (npm run build) and run the Nightwatch suite against it.
// Extra arguments go to Nightwatch, e.g. `npm run e2e -- --env edgeHeadless`.
import { existsSync } from "node:fs";
import spawn from "cross-spawn";

const port = process.env.E2E_PORT || "8089";
process.env.E2E_URL = `http://localhost:${port}`;

if (!existsSync("dist/index.html")) {
    console.error("dist/ not found: run `npm run build` first");
    process.exit(1);
}

const server = spawn(
    "node",
    [
        "node_modules/serve/build/main.js",
        "-s",
        "dist",
        "-l",
        port,
        "-c",
        "../serve.json",
    ],
    { stdio: "ignore" },
);

let opts = process.argv.slice(2);
if (!opts.includes("--config")) {
    opts = opts.concat(["--config", "test/e2e/nightwatch.conf.cjs"]);
}
if (!opts.includes("--env")) {
    opts = opts.concat(["--env", "chromeHeadless"]);
}

const runner = spawn(
    "node",
    ["node_modules/nightwatch/bin/nightwatch", ...opts],
    {
        stdio: "inherit",
    },
);
runner.on("exit", (code) => {
    server.kill();
    process.exit(code);
});
runner.on("error", (err) => {
    server.kill();
    throw err;
});
