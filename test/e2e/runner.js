// 1. start the dev server using production config
import { exec } from "node:child_process";
import spawn from "cross-spawn";
import devConfigPromise from "../../build/webpack.dev.conf.js";

process.env.NODE_ENV = "testing";

devConfigPromise
    .then((devConfig) => {
        exec(
            "cd $(pwd)/dist && python3 -m http.server 8080",
            function callback(error, stdout, stderr) {
                console.log(error);
                console.log(stdout);
                console.log(stderr);
            },
        );
    })
    .then(() => {
        // 2. run the nightwatch test suite against it
        // to run in additional browsers:
        //    1. add an entry in test/e2e/nightwatch.conf.cjs under "test_settings"
        //    2. add it to the --env flag below
        // or override the environment flag, for example: `npm run e2e -- --env chrome,firefox`
        // For more information on Nightwatch's config file, see
        // http://nightwatchjs.org/guide#settings-file
        let opts = process.argv.slice(2);
        if (!opts.includes("--config")) {
            opts = opts.concat(["--config", "test/e2e/nightwatch.conf.cjs"]);
        }
        if (!opts.includes("--env")) {
            opts = opts.concat(["--env", "chromeHeadless"]);
        }

        const runner = spawn("./node_modules/.bin/nightwatch", opts, {
            stdio: "inherit",
        });
        runner.on("exit", function (code) {
            exec("pkill -9 -f http.server");
            process.exit(code);
        });

        runner.on("error", function (err) {
            exec("pkill -9 -f http.server");
            throw err;
        });
    });
