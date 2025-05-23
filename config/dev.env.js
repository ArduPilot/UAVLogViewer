'use strict'
const { merge } = require('webpack-merge')
const prodEnv = require('./prod.env')

module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
    VUE_APP_CESIUM_TOKEN: JSON.stringify(process.env.VUE_APP_CESIUM_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmMDc4ZTk0Yy04MDE1LTQwMDYtYjIzOS03NTczYTA3ZTdkYmYiLCJpZCI6MzA1MDE4LCJpYXQiOjE3NDc4NzI0NTN9.MRFEeyTpq3S6WOa8Yf7ZXQJ_DTBgBR_k_rEmhuySlwY')
})
