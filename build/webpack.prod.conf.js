'use strict'

process.env.NODE_ENV = 'production'

const path = require('path')
const utils = require('./utils')
const webpack = require('webpack')
const config = require('../config')
const { merge } = require('webpack-merge');
const baseWebpackConfig = require('./webpack.base.conf')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const cesiumSource =  'node_modules/cesium/Source'
const cesiumWorkers = 'node_modules/cesium/Build/Cesium/Workers'
const TerserPlugin = require('terser-webpack-plugin')
const { VueLoaderPlugin }  = require('vue-loader')
const CompressionPlugin = require('compression-webpack-plugin');
const GitRevisionPlugin = require('git-revision-webpack-plugin')
const gitRevisionPlugin = new GitRevisionPlugin()

const env = process.env.NODE_ENV === 'testing'
  ? require('../config/test.env')
  : require('../config/prod.env')

const webpackConfig = merge(baseWebpackConfig, {
    mode: 'production',
  module: {
    rules: utils.styleLoaders({
      sourceMap: config.build.productionSourceMap,
      extract: true,
      usePostCSS: true
    })
  },
  devtool: config.build.productionSourceMap ? config.build.devtool : false,
  output: {
    path: config.build.assetsRoot,
    filename: utils.assetsPath('js/[name].[chunkhash].js'),
    chunkFilename: utils.assetsPath('js/[id].[chunkhash].js')
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
      CESIUM_BASE_URL: JSON.stringify(''),
      '_COMMIT_': JSON.stringify(gitRevisionPlugin.commithash()),
      '_BUILDDATE_': JSON.stringify((new Date().toString()))
    }),
    // http://vuejs.github.io/vue-loader/en/workflow/production.html
    new webpack.DefinePlugin({
      'process.env': env
    }),
      new VueLoaderPlugin(),
    // extract css into its own file
      new MiniCssExtractPlugin({
      filename: utils.assetsPath('css/[name].[contenthash].css'),
    }),
    new webpack.ProvidePlugin({
      Buffer: ['buffer', 'Buffer'],
    }),
    // generate dist index.html with correct asset hash for caching.
    // you can customize output by editing /index.html
    // see https://github.com/ampedandwired/html-webpack-plugin
    new HtmlWebpackPlugin({
      filename: process.env.NODE_ENV === 'testing'
        ? 'index.html'
        : config.build.index,
      template: 'index.html',
      inject: true,
      minify: {
        removeComments: true,
        collapseWhitespace: true,
        removeAttributeQuotes: true
        // more options:
        // https://github.com/kangax/html-minifier#options-quick-reference
      },
    }),
    // enable scope hoisting
    new webpack.optimize.ModuleConcatenationPlugin(),
    new CopyWebpackPlugin({
      patterns: [
        {from: path.join(cesiumSource, 'Assets'), to: 'Assets'},
        {from: path.join(cesiumSource, 'Widgets'), to: 'Widgets'},
        {from: cesiumWorkers, to: 'Workers'},
        // {from: path.join(cesiumSource, 'ThirdParty'), to: 'ThirdParty'},
        // {from: path.join(cesiumSource, '../Build/Cesium/ThirdParty/Workers'), to: 'ThirdParty/Workers', force: true},
        // {from: path.join(cesiumSource, '../Build/Cesium/Workers'), to: 'Workers', force: true}
      ]
    })
  ]
})

if (config.build.productionGzip) {
  const CompressionWebpackPlugin = require('compression-webpack-plugin')

  webpackConfig.plugins.push(
    new CompressionWebpackPlugin({
      asset: '[path].gz[query]',
      algorithm: 'gzip',
      test: new RegExp(
        '\\.(' +
        config.build.productionGzipExtensions.join('|') +
        ')$'
      ),
      threshold: 10240,
      minRatio: 0.8
    })
  )
}

if (config.build.bundleAnalyzerReport) {
  const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin
  webpackConfig.plugins.push(new BundleAnalyzerPlugin())
}

module.exports = webpackConfig
