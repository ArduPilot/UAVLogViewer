"use strict";
import { posix, join } from "node:path";
import { build, dev } from "../config/index.js";
import { createRequire } from "node:module";
import notifier from "node-notifier";

const { name } = createRequire(import.meta.url)("../package.json");

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
        less: generateLoaders("less"),
        sass: generateLoaders("sass", { indentedSyntax: true }),
        scss: generateLoaders("sass"),
        stylus: generateLoaders("stylus"),
        styl: generateLoaders("stylus"),
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

export function createNotifierCallback() {
    return (severity, errors) => {
        if (severity !== "error") return;

        const error = errors[0];
        const filename = error.file?.split("!").pop();

        notifier.notify({
            title: name,
            message: severity + ": " + error.name,
            subtitle: filename || "",
            icon: join(import.meta.dirname, "logo.png"),
        });
    };
}
