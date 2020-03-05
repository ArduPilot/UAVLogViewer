require('mavlink_common_v1.0/mavlink')
let mavlinkparser = require('../../../src/tools/parsers/mavlinkParser.js')
import {MavlinkDataExtractor} from '../../../src/tools/mavlinkDataExtractor'
var glob = require('glob')

// options is optional
let files = glob.sync('/tmp/testlogs/*.tlog')
console.log('Testing MAVLink files:')
console.log(files)
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
        const result = parser.processData(logfile)
        const messageTypes = result.types
        const messages = result.messages
        expect(Object.keys(messageTypes)).toContain('HEARTBEAT')
        expect(MavlinkDataExtractor.extractArmedEvents(messages).length).toBeGreaterThan(0)
        expect(Object.keys(MavlinkDataExtractor.extractAttitudes(messages)).length).toBeGreaterThan(100)
        expect(MavlinkDataExtractor.extractFlightModes(messages).length).toBeGreaterThan(0)

        expect(MavlinkDataExtractor.extractParams(messages)).toBeDefined()

        expect(MavlinkDataExtractor.extractTextMessages(messages).length).toBeGreaterThan(0)
        let trajectory = MavlinkDataExtractor.extractTrajectory(messages)
        expect(Object.keys(trajectory).length).toBeGreaterThan(1)
        let firstItem = Object.keys(trajectory)[0]
        expect(trajectory[firstItem].trajectory.length).toBeGreaterThan(100)
    })
})
