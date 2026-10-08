"use strict";
const utils = require("./utils");
const config = require("../config");
const isProduction = process.env.NODE_ENV === "production";
const sourceMapEnabled = isProduction
    ? config.build.productionSourceMap
    : config.dev.cssSourceMap;

module.exports = {
    loaders: utils.cssLoaders({
        sourceMap: sourceMapEnabled,
        extract: isProduction,
    }),
    cssSourceMap: sourceMapEnabled,
    cacheBusting: config.dev.cacheBusting,
    // Vue 2.7's template compiler calls prettier.format() synchronously to beautify
    // dev render functions; with prettier 3 that returns a Promise and breaks the build
    prettify: false,
    transformToRequire: {
        video: ["src", "poster"],
        source: "src",
        img: "src",
        image: "xlink:href",
    },
    module: {
        rules: [
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"],
            },
        ],
    },
};
