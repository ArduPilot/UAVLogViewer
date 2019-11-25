require('mavlink_common_v1.0/mavlink')
let mavlinkparser = require('../../../src/tools/parsers/mavlinkParser.js')

describe('MavlinkParser', () => {
    it('should be able to pre-parse the file', () => {
        const fs = require('fs')
        const logfile = fs.readFileSync(require('path').join(__dirname,'../../testlogfiles/vtol.tlog'))
        const parser = new mavlinkparser.MavlinkParser()

        // Hide these two
        parser.mavlinkParser.on = () => {}
        self.postMessage = function (a) {}
        const messageTypes = parser.processData(logfile)
        expect(Object.keys(messageTypes)).toContain('HEARTBEAT')
    })
})
