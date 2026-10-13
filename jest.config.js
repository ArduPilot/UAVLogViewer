// At the repo root so plain `jest` (and editor integrations such as vscode-jest) use it
export default {
    testEnvironment: "jsdom",
    moduleFileExtensions: ["js", "json", "vue"],
    moduleNameMapper: {
        "^@/(.*)$": "<rootDir>/src/$1",
        "^(.+\\.xml)\\?raw$": "$1",
    },
    transform: {
        "^.+\\.js$": "babel-jest",
        ".*\\.(vue)$": "@vue/vue2-jest",
    },
    globals: {
        // Vue 2.7's template compiler calls prettier synchronously, which prettier 3 can't do
        // (same as build/vue-loader.conf.js)
        "vue-jest": { templateCompiler: { prettify: false } },
        // defined by webpack's DefinePlugin in the app
        _COMMIT_: "test",
        _BUILDDATE_: "test",
    },
    testPathIgnorePatterns: ["<rootDir>/test/e2e"],
    setupFiles: ["<rootDir>/test/unit/setup"],
    setupFilesAfterEnv: ["<rootDir>/test/unit/jest.setup.js"],
    coverageDirectory: "<rootDir>/test/unit/coverage",
    collectCoverageFrom: [
        "src/**/*.{js,vue}",
        "!src/main.js",
        "!src/router/index.js",
        "!**/node_modules/**",
    ],
};
