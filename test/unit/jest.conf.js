const path = require('path')

// The top-level babel-jest (28.x) is incompatible with jest 24, so use the
// babel-jest that jest-config itself depends on.
const babelJest = require.resolve('babel-jest', { paths: [require.resolve('jest-config')] })

module.exports = {
    rootDir: path.resolve(__dirname, '../../'),
    moduleFileExtensions: [
        'js',
        'json',
        'vue'
    ],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1'
    },
    transform: {
        '^.+\\.js$': babelJest,
        '.*\\.(vue)$': '<rootDir>/node_modules/vue-jest'
    },
    testPathIgnorePatterns: [
        '<rootDir>/test/e2e'
    ],
    snapshotSerializers: ['<rootDir>/node_modules/jest-serializer-vue'],
    setupFiles: ['<rootDir>/test/unit/setup'],
    mapCoverage: true,
    coverageDirectory: '<rootDir>/test/unit/coverage',
    collectCoverageFrom: [
        'src/**/*.{js,vue}',
        '!src/main.js',
        '!src/router/index.js',
        '!**/node_modules/**'
    ],
    setupTestFrameworkScriptFile: '<rootDir>/test/unit/jest.setup.js'
}
