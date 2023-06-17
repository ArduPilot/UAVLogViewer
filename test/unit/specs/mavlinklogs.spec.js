import { MavlinkDataExtractor } from '../../../src/tools/mavlinkDataExtractor'
const mavlinkparser = require('../../../src/tools/parsers/mavlinkParser.js')
const glob = require('glob')

// options is optional
let files = glob.sync('/tmp/testlogs/*.tlog')
files = files.length > 0 ? files : glob.sync('test/testlogfiles/*.tlog')
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
        expect(MavlinkDataExtractor.extractEvents(messages).length).toBeGreaterThan(0)
        expect(Object.keys(MavlinkDataExtractor.extractAttitudes(messages)).length).toBeGreaterThan(50)
        expect(MavlinkDataExtractor.extractFlightModes(messages).length).toBeGreaterThan(0)

        expect(MavlinkDataExtractor.extractParams(messages)).toBeDefined()

        expect(MavlinkDataExtractor.extractTextMessages(messages).length).toBeGreaterThan(0)
        const trajectory = MavlinkDataExtractor.extractTrajectory(messages)
        expect(Object.keys(trajectory).length).toBeGreaterThan(1)
        const firstItem = Object.keys(trajectory)[0]
        expect(trajectory[firstItem].trajectory.length).toBeGreaterThan(10)
    })
})
