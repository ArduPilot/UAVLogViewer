// ESLint checks code quality only; prettier owns formatting (eslint-config-prettier comes last).
// https://eslint.org/docs/latest/use/configure/configuration-files
import js from "@eslint/js";
import prettier from "eslint-config-prettier/flat";
import sonarjs from "eslint-plugin-sonarjs";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";
import neostandard from "neostandard";

export default [
    {
        ignores: [
            "dist/",
            "static/",
            "test/unit/coverage/",
            "test/e2e/reports/",
            // generated MAVLink binding and the DataFlash parser submodule
            "src/libs/",
            "src/tools/parsers/JsDataflashParser/",
        ],
    },
    js.configs.recommended,
    ...neostandard({ noStyle: true }),
    ...pluginVue.configs["flat/vue2-recommended"],
    sonarjs.configs.recommended,
    {
        languageOptions: {
            ecmaVersion: 2024,
            sourceType: "module",
            globals: {
                ...globals.browser,
                // defined by webpack's DefinePlugin
                _COMMIT_: "readonly",
                _BUILDDATE_: "readonly",
            },
        },
        rules: {
            // Property names come from MAVLink, DataFlash, Plotly and Nightwatch (snake_case);
            // our own identifiers are still checked
            camelcase: ["error", { properties: "never", ignoreGlobals: true }],
            // Math.random only drives MagFit's optimiser; nothing security-related uses it
            "sonarjs/pseudo-random": "off",
            "vue/multi-word-component-names": "off",
            "vue/no-reserved-component-names": "off",
            "vue/no-v-html": "error",
        },
    },
    {
        // Plot expressions are user-entered JavaScript by design (see src/mavextra/)
        files: ["src/components/Plotly.vue"],
        rules: { "sonarjs/code-eval": "off" },
    },
    {
        // the log parsers run in a web worker
        files: ["src/tools/parsers/**/*.js"],
        languageOptions: { globals: globals.worker },
    },
    {
        files: [
            "build/**/*.js",
            "config/**/*.js",
            "scripts/**/*.js",
            "*.js",
            "*.cjs",
            "test/e2e/*.js",
        ],
        languageOptions: { globals: globals.node },
    },
    {
        files: ["**/*.cjs"],
        languageOptions: { sourceType: "commonjs" },
    },
    {
        files: ["test/unit/**/*.js"],
        languageOptions: { globals: { ...globals.jest, ...globals.node } },
    },
    {
        files: ["test/e2e/**/*.js"],
        languageOptions: { globals: globals.nightwatch },
    },
    prettier,
];
