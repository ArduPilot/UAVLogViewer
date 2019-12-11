import {DataflashDataExtractor} from '../../../src/tools/dataflashDataExtractor'

let dfparser = require('../../../src/tools/parsers/dataflashParser.js')
var glob = require('glob')

// options is optional
let files = glob.sync('/tmp/testlogs/*.bin')
console.log(files)
describe('parse binary logs', () => {
    test.each(files)('parse %s', (a) => {
        const fs = require('fs')
        const logfile = fs.readFileSync(a)
        const parser = new dfparser.DataflashParser()
        // Hide these two
        self.postMessage = function (a) {
        }
        const result = parser.processData(logfile.buffer)
        const messageTypes = result.types
        const messages = result.messages
        expect(Object.keys(messageTypes)).toContain('MODE')
        console.log(a)
        if (a.indexOf('Plane') !== -1 && a.indexOf('rover') !== -1) {
            expect(DataflashDataExtractor.extractArmedEvents(messages).length).toBeGreaterThan(0)
        }
        expect(Object.keys(DataflashDataExtractor.extractAttitudes(messages)).length).toBeGreaterThan(100)
        expect(DataflashDataExtractor.extractFlightModes(messages).length).toBeGreaterThan(0)

        expect(DataflashDataExtractor.extractParams(messages)).toBeDefined()

        expect(DataflashDataExtractor.extractTextMessages(messages).length).toBeGreaterThan(0)
        let trajectory = DataflashDataExtractor.extractTrajectory(messages)
        expect(Object.keys(trajectory).length).toBeGreaterThan(1)
        expect(trajectory.trajectory.length).toBeGreaterThan(100)
    })
})
