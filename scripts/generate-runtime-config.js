const fs = require('fs')
const path = require('path')

const token = process.env.VUE_APP_CESIUM_TOKEN || ''
const content = `window.__APP_CONFIG__ = Object.assign({}, window.__APP_CONFIG__, {\n  VUE_APP_CESIUM_TOKEN: ${JSON.stringify(token)}\n});\n`

const targets = [
    path.resolve(__dirname, '../runtime-config.js'),
    path.resolve(__dirname, '../dist/runtime-config.js')
]

for (const filePath of targets) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true })
    fs.writeFileSync(filePath, content)
}

console.log('Generated runtime config for Cesium token')
