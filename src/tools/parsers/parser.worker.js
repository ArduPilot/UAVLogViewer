// Worker.js
// import MavlinkParser from 'mavlinkParser'
let mavparser = require('./mavlinkParser')
let dataflashparser = require('./dataflashParser')

let parser

self.addEventListener('message', function (event) {
    if (event.data === null) {
        console.log('got bad file message!')
    } else if (event.data.action === 'parse') {
        if (event.data.isTlog) {
            parser = new mavparser.MavlinkParser()
        } else {
            parser = new dataflashparser.DataflashParser()
        }
        let data = event.data.file
        parser.processData(data)
    } else if (event.data.action === 'loadType') {
        parser.loadType(event.data.type)
    }
})
