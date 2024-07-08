import { mavlink20 as mavlink } from '../libs/mavlink'
import { ParamSeeker } from '../tools/paramseeker'

const validGCSs = [
    mavlink.MAV_TYPE_FIXED_WING,
    mavlink.MAV_TYPE_QUADROTOR,
    mavlink.MAV_TYPE_COAXIAL,
    mavlink.MAV_TYPE_HELICOPTER,
    mavlink.MAV_TYPE_ANTENNA_TRACKER,
    mavlink.MAV_TYPE_AIRSHIP,
    mavlink.MAV_TYPE_FREE_BALLOON,
    mavlink.MAV_TYPE_ROCKET,
    mavlink.MAV_TYPE_GROUND_ROVER,
    mavlink.MAV_TYPE_SURFACE_BOAT,
    mavlink.MAV_TYPE_SUBMARINE,
    mavlink.MAV_TYPE_HEXAROTOR,
    mavlink.MAV_TYPE_OCTOROTOR,
    mavlink.MAV_TYPE_TRICOPTER,
    mavlink.MAV_TYPE_FLAPPING_WING,
    mavlink.MAV_TYPE_KITE
]

export class MavlinkDataExtractor {
    static extractAttitude (messages, source) {
        const attitudes = {}
        if ('ATTITUDE' in messages) {
            const attitudeMsgs = messages.ATTITUDE
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                    [
                        attitudeMsgs.roll[i],
                        attitudeMsgs.pitch[i],
                        attitudeMsgs.yaw[i]
                    ]
            }
        }
        return attitudes
    }

    static extractAttitudeQ (messages, source) {
        return {}
    }

    static extractFlightModes (messages) {
        let modes = []
        if ('HEARTBEAT' in messages) {
            const msgs = messages.HEARTBEAT
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
            for (const i in msgs.time_boot_ms) {
                if (validGCSs.includes(msgs.type[i])) {
                    if (msgs.asText[i] === undefined) {
                        msgs.asText[i] = 'Unknown'
                    }
                    if (msgs.asText[i] !== null && msgs.asText[i] !== modes[modes.length - 1][1]) {
                        modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                    }
                }
            }
        }
        return modes
    }

    static extractEvents (messages) {
        let armedState = []
        if ('HEARTBEAT' in messages) {
            const msgs = messages.HEARTBEAT
            const event = (msgs.base_mode[0] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
            armedState = [[msgs.time_boot_ms[0], event]]
            for (const i in msgs.time_boot_ms) {
                if (msgs.type[i] !== mavlink.MAV_TYPE_GCS) {
                    const newEvent = (msgs.base_mode[i] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
                    if (newEvent !== armedState[armedState.length - 1][1]) {
                        const event = (msgs.base_mode[i] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
                        armedState.push([msgs.time_boot_ms[i], event])
                    }
                }
            }
        }
        return armedState
    }

    static extractMission (messages) {
        const wps = []
        if ('CMD' in messages) {
            const cmdMsgs = messages.CMD
            for (const i in cmdMsgs.time_boot_ms) {
                if (cmdMsgs.Lat[i] !== 0) {
                    let lat = cmdMsgs.Lat[i]
                    let lon = cmdMsgs.Lng[[i]]
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6
                        lon = lon / 10e6
                    }
                    wps.push([lon, lat, cmdMsgs.Alt[i]])
                }
            }
        }
        return wps
    }

    static extractFences (messages) {
        return []
    }

    static extractVehicleType (messages) {
        if ('HEARTBEAT' in messages) {
            for (const i in messages.HEARTBEAT.craft) {
                if (messages.HEARTBEAT.craft[i] !== undefined) {
                    return messages.HEARTBEAT.craft[i]
                }
            }
        }
    }

    static extractAttitudeSources (messages) {
        return {
            quaternions: [],
            eulers: ['ATTITUDE']
        }
    }

    static extractTrajectorySources (messages) {
        const sources = []
        if ('GLOBAL_POSITION_INT' in messages) {
            sources.push('GLOBAL_POSITION_INT')
        }
        if ('GPS_RAW_INT' in messages) {
            sources.push('GPS_RAW_INT')
        }
        if ('AHRS2' in messages) {
            sources.push('AHRS2')
        }
        if ('AHRS3' in messages) {
            sources.push('AHRS3')
        }
        return sources
    }

    static extractTrajectory (messages, source) {
        const ret = {}
        if (('GLOBAL_POSITION_INT' in messages) && source === 'GLOBAL_POSITION_INT') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.GLOBAL_POSITION_INT
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.relative_alt[i]
                    }
                    trajectory.push(
                        [
                            gpsData.lon[i],
                            gpsData.lat[i],
                            gpsData.relative_alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lon[i],
                        gpsData.lat[i],
                        gpsData.relative_alt[i],
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.GLOBAL_POSITION_INT = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('GPS_RAW_INT' in messages && source === 'GPS_RAW_INT') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.GPS_RAW_INT
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.alt[0] / 1000
                    }
                    trajectory.push(
                        [
                            gpsData.lon[i] * 1e-7,
                            gpsData.lat[i] * 1e-7,
                            gpsData.alt[i] / 1000 - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lon[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.alt[i] / 1000,
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.GPS_RAW_INT = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS2' in messages && source === 'AHRS2') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.AHRS2
            for (const i in gpsData.time_boot_ms) {
                if (startAltitude === null) {
                    startAltitude = gpsData.altitude[0]
                }
                trajectory.push(
                    [
                        gpsData.lng[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.altitude[i] - startAltitude,
                        gpsData.time_boot_ms[i]
                    ]
                )
                timeTrajectory[gpsData.time_boot_ms[i]] = [
                    gpsData.lng[i] * 1e-7,
                    gpsData.lat[i] * 1e-7,
                    gpsData.altitude[i],
                    gpsData.time_boot_ms[i]]
            }
            if (trajectory.length) {
                ret.AHRS2 = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS3' in messages && source === 'AHRS3') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.AHRS3
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.altitude[0]
                    }
                    trajectory.push(
                        [
                            gpsData.lng[i] * 1e-7,
                            gpsData.lat[i] * 1e-7,
                            gpsData.altitude[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lng[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.altitude[i],
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.AHRS3 = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        return ret
    }

    static extractDefaultParams (messages) {
        return {}
    }

    static extractParams (messages) {
        const params = []
        const lastValue = {}
        if ('PARAM_VALUE' in messages) {
            const paramData = messages.PARAM_VALUE
            for (const i in paramData.time_boot_ms) {
                const paramName = paramData.param_id[i].replace(/[^a-z0-9A-Z_]/ig, '')
                const paramValue = paramData.param_value[i]
                if (lastValue.paramName && lastValue[paramName] === paramValue) {
                    continue
                }
                params.push(
                    [
                        paramData.time_boot_ms[i],
                        paramName,
                        paramValue
                    ]
                )
                lastValue[paramName] = paramValue
            }
        }
        if (params.length > 0) {
            return new ParamSeeker(params)
        } else {
            return undefined
        }
    }

    static extractTextMessages (messages) {
        const texts = []
        if ('STATUSTEXT' in messages) {
            const textMsgs = messages.STATUSTEXT
            for (const i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], textMsgs.severity[i], textMsgs.text[i]])
            }
        }
        return texts
    }

    static extractNamedValueFloatNames (messages) {
        if ('NAMED_VALUE_FLOAT' in messages) {
            return Array.from(new Set(messages.NAMED_VALUE_FLOAT.name))
        }
        return []
    }

    static extractStartTime (messages) {
        return undefined
    }
}
