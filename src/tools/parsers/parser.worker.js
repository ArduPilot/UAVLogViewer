// Worker.js
// import MavlinkParser from 'mavlinkParser'
let mavparser = require('./mavlinkParser')
let dataflashparser = require('./dataflashParser')

self.addEventListener('message', function (event) {
  let parser
  if (event.data.isTlog) {
    parser = new mavparser.MavlinkParser()
  }
  else {
    parser = new dataflashparser.DataflashParser()
  }
  let data = event.data.file
  parser.processData(data)
})
