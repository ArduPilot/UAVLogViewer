require('mavlink_common_v1.0/mavlink')
let mavlinkparser = require('../../../src/tools/parsers/mavlinkParser.js')
var glob = require('glob')

// options is optional
let files = glob.sync('/tmp/testlogs/*.tlog')

describe('parse tlogs', () => {
    test.each(files)('parse %s', (a) => {
        const fs = require('fs')
        const logfile = fs.readFileSync(a)
        const parser = new mavlinkparser.MavlinkParser()
        // Hide these two
        parser.mavlinkParser.on = () => {
        }
        self.postMessage = function (a) {
        }
        const messageTypes = parser.processData(logfile)
        expect(Object.keys(messageTypes)).toContain('HEARTBEAT')
    })
})
