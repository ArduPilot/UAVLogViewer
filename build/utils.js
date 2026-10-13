"use strict";
import { posix } from "node:path";
import { build, dev } from "../config/index.js";

export function assetsPath(_path) {
    const assetsSubDirectory =
        process.env.NODE_ENV === "production"
            ? build.assetsSubDirectory
            : dev.assetsSubDirectory;

    return posix.join(assetsSubDirectory, _path);
}

export function cssLoaders(options) {
    options = options || {};

    const cssLoader = {
        loader: "css-loader",
        options: {
            sourceMap: options.sourceMap,
        },
    };

    const postcssLoader = {
        loader: "postcss-loader",
        options: {
            sourceMap: options.sourceMap,
        },
    };

    // generate loader string to be used with extract text plugin
    function generateLoaders(loader, loaderOptions) {
        const loaders = options.usePostCSS
            ? [cssLoader, postcssLoader]
            : [cssLoader];

        if (loader) {
            loaders.push({
                loader: loader + "-loader",
                options: Object.assign({}, loaderOptions, {
                    sourceMap: options.sourceMap,
                }),
            });
        }

        // Extract CSS when that option is specified
        // (which is the case during production build)

        return ["vue-style-loader"].concat(loaders);
    }

    // https://vue-loader.vuejs.org/en/configurations/extract-css.html
    return {
        css: generateLoaders(),
        postcss: generateLoaders(),
    };
}

// Generate loaders for standalone style files (outside of .vue)
export function styleLoaders(options) {
    const output = [];
    const loaders = cssLoaders(options);

    for (const extension in loaders) {
        const loader = loaders[extension];
        output.push({
            test: new RegExp(String.raw`\.` + extension + "$"),
            use: loader,
        });
    }

    return output;
}
