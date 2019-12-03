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
        parser.processData(logfile.buffer)
        expect(Object.keys(parser.messageTypes)).toContain('MODE')
    })
})
