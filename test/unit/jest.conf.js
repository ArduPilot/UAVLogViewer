import { fileURLToPath } from "node:url";

export default {
    rootDir: fileURLToPath(new URL("../../", import.meta.url)),
    testEnvironment: "jsdom",
    moduleFileExtensions: ["js", "json", "vue"],
    moduleNameMapper: {
        "^@/(.*)$": "<rootDir>/src/$1",
    },
    transform: {
        "^.+\\.js$": "babel-jest",
        ".*\\.(vue)$": "@vue/vue2-jest",
    },
    testPathIgnorePatterns: ["<rootDir>/test/e2e"],
    snapshotSerializers: ["jest-serializer-vue"],
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
