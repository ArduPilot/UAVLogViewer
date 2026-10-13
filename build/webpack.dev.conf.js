"use strict";

process.env.NODE_ENV = "development";

import { styleLoaders } from "./utils.js";
import webpack from "webpack";
import { dev } from "../config/index.js";
import devEnv from "../config/dev.env.js";
import { merge } from "webpack-merge";
import { posix, resolve as _resolve } from "node:path";
import baseWebpackConfig from "./webpack.base.conf.js";
import CopyWebpackPlugin from "copy-webpack-plugin";
import HtmlWebpackPlugin from "html-webpack-plugin";
import { getPort } from "portfinder";
import { VueLoaderPlugin } from "vue-loader";
// Cesium loads its web workers, decoders (ThirdParty: Draco, KTX2), images and widget files at
// runtime from CESIUM_BASE_URL: copy its built folders next to the app
const cesiumBuild = "node_modules/cesium/Build/Cesium";
const cesiumFolders = ["Workers", "ThirdParty", "Assets", "Widgets"];
import GitRevisionPlugin from "git-revision-webpack-plugin";
const gitRevisionPlugin = new GitRevisionPlugin();
import ESLintPlugin from "eslint-webpack-plugin";

const HOST = "0.0.0.0";
const PORT = process.env.PORT && Number(process.env.PORT);

const devWebpackConfig = merge(baseWebpackConfig, {
    mode: "development",
    module: {
        rules: styleLoaders({
            sourceMap: dev.cssSourceMap,
            usePostCSS: true,
        }),
    },
    // cheap-module-eval-source-map is faster for development
    devtool: dev.devtool,

    stats: {
        children: true,
    },
    // these devServer options should be customized in /config/index.js
    devServer: {
        client: {
            overlay: dev.errorOverlay
                ? { warnings: false, errors: true }
                : false,
            logging: "warn",
        },
        historyApiFallback: {
            rewrites: [
                {
                    from: /.*/,
                    to: posix.join(dev.assetsPublicPath, "index.html"),
                },
            ],
        },
        hot: true,
        // Serve only the build output. "./" also served the repo itself (sources, .git) to the
        // network, since the dev server listens on 0.0.0.0.
        static: false,
        compress: true,
        host: HOST || dev.host,
        port: PORT || dev.port,
        open: dev.autoOpenBrowser,
        // publicPath: config.dev.assetsPublicPath,
        proxy: dev.proxyTable,
    },
    plugins: [
        // lint the app sources while developing (fixes what ESLint can fix automatically)
        new ESLintPlugin({
            files: "src",
            extensions: ["js", "vue"],
            fix: true,
        }),
        new webpack.DefinePlugin({
            "process.env": devEnv,
            _COMMIT_: JSON.stringify(gitRevisionPlugin.commithash()),
            _BUILDDATE_: JSON.stringify(new Date().toString()),
        }),
        new webpack.HotModuleReplacementPlugin(),
        new webpack.NoEmitOnErrorsPlugin(),
        // https://github.com/ampedandwired/html-webpack-plugin
        new HtmlWebpackPlugin({
            filename: "index.html",
            template: "index.html",
            inject: true,
        }),
        // copy custom static assets
        new CopyWebpackPlugin({
            patterns: cesiumFolders.map((dir) => ({
                from: _resolve(cesiumBuild, dir),
                to: dir,
            })),
            options: {
                concurrency: 100,
            },
        }),
        new webpack.DefinePlugin({
            // Define relative base path in cesium for loading assets
            CESIUM_BASE_URL: JSON.stringify(""),
        }),
        new VueLoaderPlugin(),
    ],
});

export default new Promise((resolve, reject) => {
    getPort({ port: PORT || dev.port }, (err, port) => {
        if (err) {
            reject(err);
        } else {
            // publish the new Port, necessary for e2e tests
            process.env.PORT = port;
            // add port to devServer config
            devWebpackConfig.devServer.port = port;
            resolve(devWebpackConfig);
        }
    });
});
