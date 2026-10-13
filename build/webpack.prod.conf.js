"use strict";

process.env.NODE_ENV = "production";

import { join } from "node:path";
import { styleLoaders, assetsPath } from "./utils.js";
import webpack from "webpack";
import { build } from "../config/index.js";
import { merge } from "webpack-merge";
import baseWebpackConfig, { vueFeatureFlags } from "./webpack.base.conf.js";
import CopyWebpackPlugin from "copy-webpack-plugin";
import HtmlWebpackPlugin from "html-webpack-plugin";
import MiniCssExtractPlugin from "mini-css-extract-plugin";
// Cesium loads its web workers, decoders (ThirdParty: Draco, KTX2), images and widget files at
// runtime from CESIUM_BASE_URL: copy its built folders next to the app
const cesiumBuild = "node_modules/cesium/Build/Cesium";
const cesiumFolders = ["Workers", "ThirdParty", "Assets", "Widgets"];
import TerserPlugin from "terser-webpack-plugin";
import { VueLoaderPlugin } from "vue-loader";
import CompressionPlugin from "compression-webpack-plugin";
import { BundleAnalyzerPlugin } from "webpack-bundle-analyzer";
import GitRevisionPlugin from "git-revision-webpack-plugin";
import prodEnv from "../config/prod.env.js";
import testEnv from "../config/test.env.js";
const gitRevisionPlugin = new GitRevisionPlugin();

const env = process.env.NODE_ENV === "testing" ? testEnv : prodEnv;

const webpackConfig = merge(baseWebpackConfig, {
    mode: "production",
    module: {
        rules: styleLoaders({
            sourceMap: build.productionSourceMap,
            extract: true,
            usePostCSS: true,
        }),
    },
    devtool: build.productionSourceMap ? build.devtool : false,
    output: {
        path: build.assetsRoot,
        filename: assetsPath("js/[name].[chunkhash].js"),
        chunkFilename: assetsPath("js/[id].[chunkhash].js"),
    },
    plugins: [
        new CompressionPlugin(),
        new TerserPlugin({
            parallel: true,
            terserOptions: {
                ecma: 6,
            },
        }),
        new webpack.DefinePlugin({
            // Define relative base path in cesium for loading assets
            CESIUM_BASE_URL: JSON.stringify(""),
            ...vueFeatureFlags,
            _COMMIT_: JSON.stringify(gitRevisionPlugin.commithash()),
            _BUILDDATE_: JSON.stringify(new Date().toString()),
        }),
        // http://vuejs.github.io/vue-loader/en/workflow/production.html
        new webpack.DefinePlugin({
            "process.env": env,
        }),
        new VueLoaderPlugin(),
        // extract css into its own file
        new MiniCssExtractPlugin({
            filename: assetsPath("css/[name].[contenthash].css"),
        }),
        new webpack.ProvidePlugin({
            Buffer: ["buffer", "Buffer"],
        }),
        // generate dist index.html with correct asset hash for caching.
        // you can customize output by editing /index.html
        // see https://github.com/ampedandwired/html-webpack-plugin
        new HtmlWebpackPlugin({
            filename:
                process.env.NODE_ENV === "testing" ? "index.html" : build.index,
            template: "index.html",
            inject: true,
            minify: {
                removeComments: true,
                collapseWhitespace: true,
                removeAttributeQuotes: true,
                // more options:
                // https://github.com/kangax/html-minifier#options-quick-reference
            },
        }),
        // enable scope hoisting
        new webpack.optimize.ModuleConcatenationPlugin(),
        new CopyWebpackPlugin({
            patterns: cesiumFolders.map((dir) => ({
                from: join(cesiumBuild, dir),
                to: dir,
            })),
        }),
    ],
});

if (build.productionGzip) {
    webpackConfig.plugins.push(
        new CompressionPlugin({
            asset: "[path].gz[query]",
            algorithm: "gzip",
            test: new RegExp(
                String.raw`\.(` +
                    build.productionGzipExtensions.join("|") +
                    ")$",
            ),
            threshold: 10240,
            minRatio: 0.8,
        }),
    );
}

if (build.bundleAnalyzerReport) {
    webpackConfig.plugins.push(new BundleAnalyzerPlugin());
}

export default webpackConfig;
