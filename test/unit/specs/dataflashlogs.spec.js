import { DataflashDataExtractor } from '../../../src/tools/dataflashDataExtractor'

const dfparser = require('../../../src/tools/parsers/dataflashParser.js')
const glob = require('glob')

// options is optional
let files = glob.sync('/tmp/testlogs/*.bin')
files = files.length > 0 ? files : glob.sync('test/testlogfiles/*.bin')
console.log(files)
console.log('Testing datalash files:')
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
        if (a.indexOf('Plane') !== -1 && a.indexOf('rover') !== -1) {
            expect(DataflashDataExtractor.extractEvents(messages).length).toBeGreaterThan(0)
        }
        expect(Object.keys(DataflashDataExtractor.extractAttitudes(messages)).length).toBeGreaterThan(50)
        expect(DataflashDataExtractor.extractFlightModes(messages).length).toBeGreaterThan(0)

        expect(DataflashDataExtractor.extractParams(messages)).toBeDefined()

        expect(DataflashDataExtractor.extractTextMessages(messages).length).toBeGreaterThan(0)
        const trajectory = DataflashDataExtractor.extractTrajectory(messages)
        expect(Object.keys(trajectory).length).toBeGreaterThan(1)
        const firstItem = Object.keys(trajectory)[0]
        expect(trajectory[firstItem].trajectory.length).toBeGreaterThan(10)
    })
})
