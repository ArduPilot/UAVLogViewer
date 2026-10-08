"use strict";

process.env.NODE_ENV = "production";

import { join } from "node:path";
import { styleLoaders, assetsPath } from "./utils.js";
import webpack from "webpack";
import { build } from "../config/index.js";
import { merge } from "webpack-merge";
import baseWebpackConfig from "./webpack.base.conf.js";
import CopyWebpackPlugin from "copy-webpack-plugin";
import HtmlWebpackPlugin from "html-webpack-plugin";
import MiniCssExtractPlugin from "mini-css-extract-plugin";
const cesiumSource = "node_modules/cesium/Source";
const cesiumWorkers = "node_modules/cesium/Build/Cesium/Workers";
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
            patterns: [
                { from: "runtime-config.js", to: "runtime-config.js" },
                { from: join(cesiumSource, "Assets"), to: "Assets" },
                { from: join(cesiumSource, "Widgets"), to: "Widgets" },
                { from: cesiumWorkers, to: "Workers" },
                // {from: path.join(cesiumSource, 'ThirdParty'), to: 'ThirdParty'},
                // {from: path.join(cesiumSource, '../Build/Cesium/ThirdParty/Workers'), to: 'ThirdParty/Workers', force: true},
                // {from: path.join(cesiumSource, '../Build/Cesium/Workers'), to: 'Workers', force: true}
            ],
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
