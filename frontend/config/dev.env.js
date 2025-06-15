'use strict'
const { merge } = require('webpack-merge')
const prodEnv = require('./prod.env')
const dotenv = require('dotenv')

// Load environment variables from .env file
dotenv.config()


module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
  VUE_APP_CESIUM_TOKEN: JSON.stringify(process.env.VUE_APP_CESIUM_TOKEN || '')
})
