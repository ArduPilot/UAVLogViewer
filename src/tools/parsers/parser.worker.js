// Worker.js
// import MavlinkParser from 'mavlinkParser'
let mavparser = require('./mavlinkParser')

self.addEventListener('message', function (event) {
  let parser = new mavparser.MavlinkParser()
  let data = event.data.file
  parser.processData(data)
})
