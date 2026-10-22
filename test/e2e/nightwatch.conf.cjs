// https://nightwatchjs.org/guide/reference/settings.html
// Nightwatch 3 starts the browser driver itself (Selenium Manager downloads a matching one).
const appUrl = process.env.E2E_URL || "http://localhost:8089";
const headless = ["--headless=new", "--disable-gpu", "--no-sandbox"];

module.exports = {
    src_folders: ["test/e2e/specs"],
    output_folder: "test/e2e/reports",
    custom_assertions_path: ["test/e2e/custom-assertions"],
    // no anonymous usage reporting from test runs
    usage_analytics: { enabled: false },

    webdriver: {
        start_process: true,
    },

    test_settings: {
        default: {
            launch_url: appUrl,
            globals: {
                devServerURL: appUrl,
            },
        },
        chromeHeadless: {
            desiredCapabilities: {
                browserName: "chrome",
                "goog:chromeOptions": { args: headless },
            },
        },
        edgeHeadless: {
            desiredCapabilities: {
                browserName: "MicrosoftEdge",
                "ms:edgeOptions": { args: headless },
            },
        },
    },
};
