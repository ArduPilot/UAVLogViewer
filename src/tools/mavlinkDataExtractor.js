import {mavlink} from 'mavlink_common_v1.0/mavlink'
import {ParamSeeker} from '../tools/paramseeker'

export class MavlinkDataExtractor {
    static extractAttitudes (messages) {
        let attitudes = {}
        if ('ATTITUDE' in messages) {
            let attitudeMsgs = messages['ATTITUDE']
            for (let i in attitudeMsgs.time_boot_ms) {
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

    static extractAttitudesQ (messages) {
        return {}
    }

    static extractFlightModes (messages) {
        let modes = []
        if ('HEARTBEAT' in messages) {
            let msgs = messages['HEARTBEAT']
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
            for (let i in msgs.time_boot_ms) {
                // TODO: fix this properly
                // eslint-disable-next-line
                if (msgs.type[i] !== mavlink.MAV_TYPE_GCS) {
                    if (msgs.asText[i] === undefined) {
                        msgs.asText[i] = 'Unknown'
                    }
                    if (msgs.asText[i] !== modes[modes.length - 1][1]) {
                        modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                    }
                }
            }
        }
        return modes
    }

    static extractArmedEvents (messages) {
        let armedState = []
        if ('HEARTBEAT' in messages) {
            let msgs = messages['HEARTBEAT']
            armedState = [[msgs.time_boot_ms[0], (msgs.base_mode[0] & 0b10000000) === 128]]
            for (let i in msgs.time_boot_ms) {
                if (msgs.type[i] !== mavlink.MAV_TYPE_GCS) {
                    if (((msgs.base_mode[i] & 0b10000000) === 128) !== armedState[armedState.length - 1][1]) {
                        armedState.push([msgs.time_boot_ms[i], (msgs.base_mode[i] & 0b10000000) === 128])
                    }
                }
            }
        }
        return armedState
    }

    static extractMission (messages) {
        let wps = []
        if ('CMD' in messages) {
            let cmdMsgs = messages['CMD']
            for (let i in cmdMsgs.time_boot_ms) {
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

    static extractVehicleType (messages) {
        if ('HEARTBEAT' in messages) {
            for (let i in messages['HEARTBEAT'].craft) {
                if (messages['HEARTBEAT'].craft[i] !== undefined) {
                    return messages['HEARTBEAT'].craft[i]
                }
            }
        }
    }

    static extractTrajectory (messages) {
        let ret = {}
        if ('GLOBAL_POSITION_INT' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['GLOBAL_POSITION_INT']
            for (let i in gpsData.time_boot_ms) {
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
                ret['GLOBAL_POSITION_INT'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('GPS_RAW_INT' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['GPS_RAW_INT']
            for (let i in gpsData.time_boot_ms) {
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
                ret['GPS_RAW_INT'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS2' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['AHRS2']
            for (let i in gpsData.time_boot_ms) {
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
                ret['AHRS2'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS3' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['AHRS3']
            for (let i in gpsData.time_boot_ms) {
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
                ret['AHRS3'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        return ret
    }

    static extractParams (messages) {
        let params = []
        if ('PARAM_VALUE' in messages) {
            let paramData = messages['PARAM_VALUE']
            for (let i in paramData.time_boot_ms) {
                params.push(
                    [
                        paramData.time_boot_ms[i],
                        paramData.param_id[i].replace(/[^a-z0-9A-Z_]/ig, ''),
                        paramData.param_value[i]
                    ]
                )
            }
        }
        if (params.length > 0) {
            return new ParamSeeker(params)
        } else {
            return undefined
        }
    }

    static extractTextMessages (messages) {
        let texts = []
        if ('STATUSTEXT' in messages) {
            let textMsgs = messages['STATUSTEXT']
            for (let i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], textMsgs.severity[i], textMsgs.text[i]])
            }
        }
        return texts
    }
}
