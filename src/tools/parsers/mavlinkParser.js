require('mavlink_common_v1.0/mavlink')

let modeMappingApm = {
    0: 'MANUAL',
    1: 'CIRCLE',
    2: 'STABILIZE',
    3: 'TRAINING',
    4: 'ACRO',
    5: 'FBWA',
    6: 'FBWB',
    7: 'CRUISE',
    8: 'AUTOTUNE',
    10: 'AUTO',
    11: 'RTL',
    12: 'LOITER',
    14: 'LAND',
    15: 'GUIDED',
    16: 'INITIALISING',
    17: 'QSTABILIZE',
    18: 'QHOVER',
    19: 'QLOITER',
    20: 'QLAND',
    21: 'QRTL'
}
let modeMappingAcm = {
    0: 'STABILIZE',
    1: 'ACRO',
    2: 'ALT_HOLD',
    3: 'AUTO',
    4: 'GUIDED',
    5: 'LOITER',
    6: 'RTL',
    7: 'CIRCLE',
    8: 'POSITION',
    9: 'LAND',
    10: 'OF_LOITER',
    11: 'DRIFT',
    13: 'SPORT',
    14: 'FLIP',
    15: 'AUTOTUNE',
    16: 'POSHOLD',
    17: 'BRAKE',
    18: 'THROW',
    19: 'AVOID_ADSB',
    20: 'GUIDED_NOGPS',
    21: 'SMART_RTL'
}
let modeMappingRover = {
    0: 'MANUAL',
    2: 'LEARNING',
    3: 'STEERING',
    4: 'HOLD',
    10: 'AUTO',
    11: 'RTL',
    12: 'SMART_RTL',
    15: 'GUIDED',
    16: 'INITIALISING'
}

let modeMappingTracker = {
    0: 'MANUAL',
    1: 'STOP',
    2: 'SCAN',
    10: 'AUTO',
    16: 'INITIALISING'
}

let modeMappingSub = {
    0: 'STABILIZE',
    1: 'ACRO',
    2: 'ALT_HOLD',
    3: 'AUTO',
    4: 'GUIDED',
    7: 'CIRCLE',
    9: 'SURFACE',
    16: 'POSHOLD',
    19: 'MANUAL'
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
    if (mavType === mavlink.MAV_TYPE_GROUND_ROVER) {
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

function getModeString (mavtype, cmode) {
    return getModeMap(mavtype)[cmode]
}

let instance

export class MavlinkParser {
    constructor () {
        this.messages = {}
        this.totalSize = undefined
        this.lastPercentage = 0
        this.sent = false
        this.lastTime = 0
        this.mavlinkParser = new MAVLink()
        this.mavlinkParser.on('message', this.onMessage)
        this.maxPercentageInterval = 0.1
        instance = this
    }

    onMessage (message) {
        if (instance.totalSize == null) { // for percentage calculation
            instance.totalSize = this.buf.byteLength
        }
        if (message.id !== -1) {
            if (message.time_boot_ms === undefined) {
                message.time_boot_ms = this.lastTime
            } else {
                this.lastTime = message.time_boot_ms
            }
            if (message.name in instance.messages) {
                instance.messages[message.name].push(MavlinkParser.fixData(message))
            } else {
                instance.messages[message.name] = [MavlinkParser.fixData(message)]
            }
            let percentage = 100 * (instance.totalSize - this.buf.byteLength) / instance.totalSize
            if ((percentage - instance.lastPercentage) > instance.maxPercentageInterval) {
                self.postMessage({percentage: percentage})
                instance.lastPercentage = percentage
            }

            // TODO: FIX THIS!
            // This a hack to detect the end of the buffer and only them message the main thread
            if (this.buf.length < 100 && instance.sent === false) {
                self.postMessage({percentage: 100})
                self.postMessage({messages: instance.messages})
                instance.sent = true
            }
        }
    }

    static fixData (message) {
        if (message.name === 'GLOBAL_POSITION_INT') {
            message.lat = message.lat / 10000000
            message.lon = message.lon / 10000000
            message.relative_alt = message.relative_alt / 1000
            return message
        } else if (message.name === 'HEARTBEAT') {
            message.asText = getModeString(message.type, message.custom_mode)
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

    processData (data) {
        this.mavlinkParser.pushBuffer(Buffer.from(data))
        this.mavlinkParser.parseBuffer()
        this.postMessage({done: true})
    }
}
