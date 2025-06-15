/* eslint-disable no-undef */
import { mavlink20 as mavlink, MAVLink20Processor as MAVLink } from '../../libs/mavlink'
import { modeMappingAcm, modeMappingApm, modeMappingRover, modeMappingSub, modeMappingTracker } from './modeMaps'

const Buffer = require('buffer/').Buffer

const vehicles = {
    1: 'airplane', // Fixed wing aircraft.
    2: 'quadcopter', // Quadrotor
    3: 'quadcopter', // Coaxial helicopter
    4: 'quadcopter', // Normal helicopter with tail rotor.
    5: 'tracker', // Ground installation
    10: 'rover', // Ground rover
    11: 'boat', // Surface vessel, boat, ship
    12: 'submarine', // Submarine
    13: 'quadcopter', // Hexarotor
    14: 'quadcopter', // Octorotor
    15: 'quadcopter', // Tricopter
    19: 'airplane', // Two-rotor VTOL using control surfaces in vertical operation in addition. Tailsitter.
    20: 'airplane', // Quad-rotor VTOL using a V-shaped quad config in vertical operation. Tailsitter.
    21: 'quadcopter', // Tiltrotor VTOL
    22: 'airplane',
    23: 'airplane',
    24: 'airplane',
    29: 'quadcopter' // Dodecarotor
}

function getModeMap (mavType) {
    let map
    if ([mavlink.MAV_TYPE_QUADROTOR,
        mavlink.MAV_TYPE_HELICOPTER,
        mavlink.MAV_TYPE_HEXAROTOR,
        mavlink.MAV_TYPE_OCTOROTOR,
        mavlink.MAV_TYPE_COAXIAL,
        mavlink.MAV_TYPE_TRICOPTER].includes(mavType)) {
        map = modeMappingAcm
    }
    if (mavType === mavlink.MAV_TYPE_FIXED_WING) {
        map = modeMappingApm
    }
    if ([mavlink.MAV_TYPE_GROUND_ROVER,
        mavlink.MAV_TYPE_SURFACE_BOAT].includes(mavType)) {
        map = modeMappingRover
    }
    if (mavType === mavlink.MAV_TYPE_ANTENNA_TRACKER) {
        map = modeMappingTracker
    }
    if (mavType === mavlink.MAV_TYPE_SUBMARINE) {
        map = modeMappingSub
    }
    if (map == null) {
        return null
    }
    return map
}

function getModeString (mavtype, cmode, basemode) {
    if (mavtype === mavlink.MAV_TYPE_GCS) {
        return ''
    }
    const map = getModeMap(mavtype)
    if (map === null) {
        if ((basemode & 4) > 0) {
            return 'Auto'
        }
        if ((basemode & 8) > 0) {
            return 'Guided'
        }
        if ((basemode & 16) > 0) {
            return 'Stabilize'
        }
        return 'Unknown'
    }
    try {
        return map[cmode]
    } catch {

    }
}

let instance

export class MavlinkParser {
    constructor () {
        this.messages = {}
        this.totalSize = undefined
        this.lastPercentage = 0
        this.sent = false

        this.mavlinkParser = new MAVLink()
        this.mavlinkParser.on('message', this.onMessage)
        this.maxPercentageInterval = 0.1
        instance = this
        instance.forcedTimeOffset = 0
        instance.lastTime = 0
    }

    static fixData (message) {
        if (message._name === 'GLOBAL_POSITION_INT') {
            message.lat = message.lat / 10000000
            message.lon = message.lon / 10000000
            // eslint-disable-next-line
            message.relative_alt = message.relative_alt / 1000
            return message
        } else if (message._name === 'HEARTBEAT') {
            message.asText = getModeString(message.type, message.custom_mode, message.base_mode)
            message.craft = vehicles[message.type]
            return message
        }
        delete message.crc
        delete message.crc_extra
        delete message.format
        delete message.header
        delete message.msgbuf
        delete message.id
        delete message.payload
        delete message.order_map
        return message
    }

    onMessage (messages) {
        const name = messages[0]._name
        for (const message of messages) {
            if (instance.totalSize == null) { // for percentage calculation
                instance.totalSize = this.buf.byteLength
            }
            if (message._id !== -1) {
                // if (message.time_boot_ms === undefined) {
                //     message.time_boot_ms = instance.lastTime
                // }
                //
                // // TODO: Fix this logic, it is probably wrong.
                // if ((+message.time_boot_ms + instance.forcedTimeOffset) < instance.lastTime) {
                //     console.log(
                //     'Time going backwards detected, adding an offset.This means SYSTEM_TIME is now out of sync!')
                //     instance.forcedTimeOffset = +instance.lastTime - message.time_boot_ms + 100000
                // }

                if (+message.time_boot_ms < instance.lastTime) {
                    // eslint-disable-next-line
                    message.time_boot_ms = +message.time_boot_ms + instance.forcedTimeOffset
                }
                instance.lastTime = +message.time_boot_ms

                if (message.name in instance.messages) {
                    MavlinkParser.fixData(message)
                } else {
                    instance.messages[message._name] = [MavlinkParser.fixData(message)]
                }
                // TODO: FIX THIS!
                // This a hack to detect the end of the buffer and only them message the main thread
                if (this.buf.length < 100 && instance.sent === false) {
                    instance.sent = true
                }
            }
        }

        const fields = messages[0].fieldnames
        if (fields.indexOf('time_boot_ms') === -1) {
            fields.push('time_boot_ms')
        }
        if (messages[0]._name === 'HEARTBEAT') {
            fields.push('asText')
            fields.push('craft')
        } else if (messages[0]._name === 'SYSTEM_TIME') {
            fields.push('time_unix_usec')
        }
        const mergedData = {}
        for (const field of fields) {
            mergedData[field] = []
        }
        for (const message of messages) {
            for (let i = 0; i < fields.length; i++) {
                const fieldname = fields[i]
                mergedData[fieldname].push(message[fieldname])
            }
        }
        instance.messages[name] = mergedData
        self.postMessage({ messages: instance.messages })
    }

    extractStartTime () {
        return new Date(this.mavlinkParser.startTime)
    }

    processData (data) {
        this.mavlinkParser.pushBuffer(Buffer.from(data))
        const availableMessages = this.mavlinkParser.preParse()
        const preparseList = [
            'SYSTEM_TIME',
            'GLOBAL_POSITION_INT',
            'GPS_RAW_INT',
            'HEARTBEAT',
            'ATTITUDE',
            'AHRS',
            'PARAM_VALUE',
            'STATUSTEXT',
            'AHRS2',
            'AHRS3',
            'NAMED_VALUE_FLOAT',]
        for (const i in preparseList) {
            this.mavlinkParser.parseType(preparseList[i])
            self.postMessage({ percentage: (i / preparseList.length) * 100 })
        }
        self.postMessage({ percentage: 100 })
        const messageTypes = {}
        for (const msg of availableMessages) {
            let fields = mavlink.messageFields[msg]
            fields = fields.filter(e => e !== 'time_boot_ms' && e !== 'time_usec')
            const complexFields = {}
            for (const field in fields) {
                complexFields[fields[field]] = {
                    name: fields[field],
                    units: '?',
                    multiplier: 1
                }
            }
            messageTypes[msg] = {
                expressions: fields,
                units: null,
                multipiers: null,
                complexFields: complexFields
            }
        }
        const metadata = {
            startTime: this.extractStartTime()
        }

        self.postMessage({ metadata: metadata })
        self.postMessage({ availableMessages: messageTypes })
        self.postMessage({ messagesDoneLoading: true })
        // self.postMessage({done: true})
        return { types: messageTypes, messages: instance.messages }
    }

    trimFile (time) {
        const start = time[0]
        const end = time[1]
        console.log('triming', start, end)
        self.postMessage({ url: this.mavlinkParser.trimFile(start, end) })
    }

    loadType (type) {
        this.mavlinkParser.parseType(type)
        console.log('done')
    }
}
