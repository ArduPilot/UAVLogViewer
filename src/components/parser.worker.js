// Worker.js
require('mavlink_common_v1.0')

const mavlinkParser = new MAVLink()

let messages = {}
let totalSize
let lastPercentage = 0
let sent = false
let lastTime = 0
let offset = 0

// TODO: fix case of restarting flight controller
function fixData (message) {
  if (message.name === 'GLOBAL_POSITION_INT') {
    message.lat = message.lat / 10000000
    message.lon = message.lon / 10000000
    message.relative_alt = message.relative_alt / 1000
    if (message.time_boot_ms < lastTime - 1000) {
      console.long('time_boot_ms: ' + message.time_boot_ms + ' last: ' + lastTime)
    }
    message.time_boot_ms = message.time_boot_ms + offset
  }
  lastTime = message.time_boot_ms
  return message
}

mavlinkParser.on('message', function (message) {
  if (totalSize == null) { // for percentage calculation
    totalSize = mavlinkParser.buf.byteLength
  }
  if (message.id !== -1) {
    if (message.name in messages) {
      messages[message.name].push(fixData(message))
    } else {
      messages[message.name] = [fixData(message)]
    }
    let percentage = 100 * (totalSize - mavlinkParser.buf.byteLength) / totalSize
    if (percentage - lastPercentage > 1 || percentage > 99.5) {
      self.postMessage({percentage: percentage})
      lastPercentage = percentage
    }
    // TODO: FIX THIS!
    // This a hack to detect the end of the buffer and only them message the main thread
    if (mavlinkParser.buf.length < 100 && sent === false) {
      self.postMessage({percentage: 100})
      self.postMessage({messages: messages})
      sent = true
    }
  }
})

self.addEventListener('message', function (event) {
  console.log(event)
  let data = event.data.file
  mavlinkParser.pushBuffer(Buffer.from(data))
  mavlinkParser.parseBuffer()
})
