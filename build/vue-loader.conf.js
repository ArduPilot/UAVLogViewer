"use strict";
import { cssLoaders } from "./utils.js";
import { build, dev } from "../config/index.js";
const isProduction = process.env.NODE_ENV === "production";
const sourceMapEnabled = isProduction
    ? build.productionSourceMap
    : dev.cssSourceMap;

export default {
    loaders: cssLoaders({
        sourceMap: sourceMapEnabled,
        extract: isProduction,
    }),
    cssSourceMap: sourceMapEnabled,
    cacheBusting: dev.cacheBusting,
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
