"use strict";
import { join, resolve as _resolve } from "node:path";
import { assetsPath } from "./utils.js";
import { dev, build } from "../config/index.js";
import vueLoaderConfig from "./vue-loader.conf.js";
import { createRequire } from "node:module";
import CssMinimizerPlugin from "css-minimizer-webpack-plugin";

const require = createRequire(import.meta.url);

// The path to the Cesium source code

function resolveDir(dir) {
    return join(import.meta.dirname, "..", dir);
}

export const context = _resolve(import.meta.dirname, "../");
export const entry = {
    app: "./src/main.js",
};
export const output = {
    path: build.assetsRoot,
    filename: "[name].js",
    publicPath:
        process.env.NODE_ENV === "production"
            ? build.assetsPublicPath
            : dev.assetsPublicPath,
    sourcePrefix: " ",
    globalObject: "self",
};
export const module = {
    rules: [
        // "type": "module" makes webpack require file extensions in imports;
        // keep resolving extensionless imports like "./foo" and "../libs/mavlink"
        {
            test: /.m?js$/,
            resolve: { fullySpecified: false },
        },
        {
            test: /\.worker\.js$/,
            use: { loader: "worker-loader" },
        },
        {
            test: /\.xml$/,
            use: { loader: "raw-loader" },
        },
        {
            test: /\.vue$/,
            loader: "vue-loader",
            options: vueLoaderConfig,
        },
        {
            test: /\.js$/,
            loader: "babel-loader",
            include: [
                resolveDir("src"),
                resolveDir("test"),
                resolveDir("node_modules/webpack-dev-server/client"),
                resolveDir("node_modules/mavlink_common_v1.0/parsers"),
            ],
        },
        // The asset rules below use url-loader/file-loader; "javascript/auto" stops webpack 5's
        // asset modules from emitting the loader's JS output a second time as the asset itself
        // (which broke url() references in CSS, e.g. the Font Awesome fonts).
        {
            test: /\.(png|jpe?g|gif)(\?.*)?$/,
            type: "javascript/auto",
            loader: "url-loader",
            options: {
                limit: 10000,
                name: assetsPath("img/[name].[hash:7].[ext]"),
            },
        },
        {
            test: /\.(svg)$/i,
            type: "javascript/auto",
            use: [
                {
                    loader: "file-loader",
                    options: {
                        esModule: false,
                    },
                },
            ],
        },
        {
            test: /\.(mp4|webm|ogg|mp3|wav|flac|aac|glb|tlog)(\?.*)?$/,
            type: "javascript/auto",
            loader: "url-loader",
            options: {
                limit: 10000,
                name: assetsPath("media/[name].[hash:7].[ext]"),
            },
        },
        {
            test: /\.(woff2?|eot|ttf|otf)(\?.*)?$/,
            type: "javascript/auto",
            loader: "url-loader",
            options: {
                limit: 10000,
                name: assetsPath("fonts/[name].[hash:7].[ext]"),
                // fonts are only referenced from CSS url(), which needs a plain string export
                esModule: false,
            },
        },
    ],
};
export const resolve = {
    fallback: {
        // the MAVLink binding and parser use Node's Buffer
        buffer: require.resolve("buffer/"),
    },
    alias: {
        vue$: "vue/dist/vue.esm.js",
        "@": resolveDir("src"),
    },
};
export const node = {};
export const optimization = {
    concatenateModules: false,
    splitChunks: {
        chunks: "all",
        minSize: 30000,
        maxSize: 300000,
        minChunks: 1,
        maxAsyncRequests: 6,
        maxInitialRequests: 4,
        automaticNameDelimiter: "~",
        cacheGroups: {
            vendors: {
                test: /[\\/]node_modules[\\/]/,
                priority: -10,
            },
            default: {
                minChunks: 2,
                priority: -20,
                reuseExistingChunk: true,
            },
        },
    },
    moduleIds: "deterministic", //Added this to retain hash of vendor chunks.
    runtimeChunk: "single",
    minimizer: [
        // For webpack@5 you can use the `...` syntax to extend existing minimizers (i.e. `terser-webpack-plugin`), uncomment the next line
        `...`,
        new CssMinimizerPlugin(),
    ],
};
export default {
    context,
    entry,
    output,
    module,
    resolve,
    node,
    optimization,
};
