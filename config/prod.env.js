'use strict'
module.exports = {
  NODE_ENV: '"production"',
  VUE_APP_CESIUM_TOKEN: JSON.stringify(process.env.VUE_APP_CESIUM_TOKEN || ''),
  VUE_APP_CESIUM_RESOURCE_ID: JSON.stringify(process.env.VUE_APP_CESIUM_RESOUR_ID || 3),
  VUE_APP_MAPTILER_KEY: JSON.stringify(process.env.VUE_APP_MAPTILER_KEY || 'o3JREHNnXex8WSPPm2BU')
}
