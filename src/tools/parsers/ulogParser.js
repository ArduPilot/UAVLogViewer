import { ULog, DataReader } from '@foxglove/ulog'

// Monkey-patch parseMessage to fix an offset bug in @foxglove/ulog.
// The library passes data.byteOffset (absolute in ArrayBuffer) to parseMessage,
// but the DataView may have a non-zero byteOffset, causing a double-offset.
// We correct by subtracting the view's byteOffset.
const parseModule = require('@foxglove/ulog/dist/parse')
const originalParseMessage = parseModule.parseMessage
parseModule.parseMessage = function (definition, definitions, view, offset) {
    try {
        const correctedOffset = offset - view.byteOffset
        return originalParseMessage(definition, definitions, view, correctedOffset)
    } catch (e) {
        return { timestamp: 0n, _parseError: true }
    }
}

class UlogParser {
    loadType () {
        console.warn('UlogParser.loadType() is not implemented — all data loaded at once')
    }

    async processData (data) {
        const reader = new DataReader(data)
        const ulog = new ULog(reader)
        await ulog.open()

        const header = ulog.header
        const subscriptions = ulog.subscriptions

        // Build a map of msgId -> topic name (with multi-instance suffix)
        const topicNames = new Map()
        for (const [msgId, sub] of subscriptions) {
            const name = sub.multiId > 0 ? `${sub.name}[${sub.multiId}]` : sub.name
            topicNames.set(msgId, name)
        }

        // Initialize columnar storage per topic
        const messages = {}
        const availableMessages = {}

        // Read all data messages
        let messageCount = 0
        const totalMessages = ulog.messageCount() || 0
        let lastProgressUpdate = 0

        for await (const msg of ulog.readMessages()) {

            // Handle log messages
            if (msg.type === 76) { // MessageType.Log
                if (!messages.log_message) {
                    messages.log_message = {
                        time_boot_ms: [],
                        level: [],
                        message: []
                    }
                }
                messages.log_message.time_boot_ms.push(Number(msg.timestamp) / 1000)
                messages.log_message.level.push(msg.logLevel)
                messages.log_message.message.push(msg.message)
                continue
            }

            // Handle data messages
            if (msg.type !== 68) continue // MessageType.Data
            const topicName = topicNames.get(msg.msgId)
            if (!topicName || !msg.value || msg.value._parseError) continue

            if (!messages[topicName]) {
                messages[topicName] = { time_boot_ms: [] }
            }

            const topicData = messages[topicName]
            // Convert timestamp from microseconds to milliseconds
            topicData.time_boot_ms.push(Number(msg.value.timestamp) / 1000)

            // Flatten and store each field
            this._flattenFields(msg.value, topicData, '')

            messageCount++
            if (totalMessages > 0) {
                const progress = Math.round(100 * messageCount / totalMessages)
                if (progress > lastProgressUpdate) {
                    lastProgressUpdate = progress
                    self.postMessage({ percentage: progress })
                }
            }
        }

        // Build available message definitions for the sidebar
        for (const topicName of Object.keys(messages)) {
            const topicData = messages[topicName]
            const fields = Object.keys(topicData).filter(k => k !== 'time_boot_ms')
            availableMessages[topicName] = {
                expressions: fields,
                complexFields: fields.map(f => ({
                    name: f,
                    units: '?',
                    multiplier: 1
                }))
            }
        }

        // Extract parameters from ULog header into a synthetic PARM message
        if (header && header.parameters && header.parameters.size > 0) {
            const paramNames = []
            const paramValues = []
            const timestamps = []
            for (const [name, entry] of header.parameters) {
                paramNames.push(name)
                paramValues.push(entry.value)
                timestamps.push(0)
            }
            messages.PARM = {
                time_boot_ms: timestamps,
                Name: paramNames,
                Value: paramValues
            }
            availableMessages.PARM = {
                expressions: ['Name', 'Value'],
                complexFields: [
                    { name: 'Name', units: '?', multiplier: 1 },
                    { name: 'Value', units: '?', multiplier: 1 }
                ]
            }
        }

        // Post results
        const startTimestamp = header ? Number(header.timestamp) / 1000 : 0
        self.postMessage({ metadata: { startTime: startTimestamp } })
        self.postMessage({ availableMessages: availableMessages })
        self.postMessage({ messages: messages })
        self.postMessage({ messagesDoneLoading: true })
    }

    _flattenFields (value, topicData, prefix) {
        for (const [key, val] of Object.entries(value)) {
            if (key === 'timestamp') continue // already handled as time_boot_ms

            const fieldName = prefix ? `${prefix}_${key}` : key

            if (typeof val === 'bigint') {
                // Convert BigInt to Number
                if (!topicData[fieldName]) topicData[fieldName] = []
                topicData[fieldName].push(Number(val))
            } else if (Array.isArray(val)) {
                // Flatten arrays: q[4] -> q_0, q_1, q_2, q_3
                for (let i = 0; i < val.length; i++) {
                    const arrayFieldName = `${fieldName}_${i}`
                    if (!topicData[arrayFieldName]) topicData[arrayFieldName] = []
                    if (typeof val[i] === 'bigint') {
                        topicData[arrayFieldName].push(Number(val[i]))
                    } else if (typeof val[i] === 'object' && val[i] !== null) {
                        this._flattenFields(val[i], topicData, arrayFieldName)
                    } else {
                        topicData[arrayFieldName].push(val[i])
                    }
                }
            } else if (typeof val === 'object' && val !== null) {
                // Flatten nested structs
                this._flattenFields(val, topicData, fieldName)
            } else {
                if (!topicData[fieldName]) topicData[fieldName] = []
                topicData[fieldName].push(val)
            }
        }
    }
}

export default UlogParser
