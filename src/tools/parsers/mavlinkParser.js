require('mavlink_common_v1.0/mavlink')

let instance

export class MavlinkParser {
  constructor () {
    this.messages = {}
    this.totalSize = undefined
    this.lastPercentage = 0
    this.sent = false
    this.lastTime = 0
    this.mavlinkParser = new MAVLink()
    this.mavlinkParser.on('message', this.onMessage)
    instance = this
  }

  onMessage (message) {
    if (instance.totalSize == null) { // for percentage calculation
      console.log(this)
      instance.totalSize = this.buf.byteLength
    }
    if (message.id !== -1) {
      if (message.name in instance.messages) {
        instance.messages[message.name].push(MavlinkParser.fixData(message))
      } else {
        instance.messages[message.name] = [MavlinkParser.fixData(message)]
      }
      let percentage = 100 * (instance.totalSize - this.buf.byteLength) / instance.totalSize
      if (percentage - instance.lastPercentage > 1 || percentage > 99.5) {
        self.postMessage({percentage: percentage})
        instance.lastPercentage = percentage
      }
      // TODO: FIX THIS!
      // This a hack to detect the end of the buffer and only them message the main thread
      if (this.buf.length < 100 && instance.sent === false) {
        self.postMessage({percentage: 100})
        self.postMessage({messages: instance.messages})
        instance.sent = true
      }
    }
  }

  // TODO: fix case of restarting flight controller
  static fixData (message) {
    if (message.name === 'GLOBAL_POSITION_INT') {
      message.lat = message.lat / 10000000
      message.lon = message.lon / 10000000
      message.relative_alt = message.relative_alt / 1000
      return message
    }
    return message
  }

  processData (data) {
    this.mavlinkParser.pushBuffer(Buffer.from(data))
    this.mavlinkParser.parseBuffer()
  }
}
