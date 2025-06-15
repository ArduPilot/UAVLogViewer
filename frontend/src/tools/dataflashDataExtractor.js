import { ParamSeeker } from '../tools/paramseeker'
import extractStartTime from './datetools'

window.radians = function (a) {
    return 0.0174533 * a
}

const events = {
    7: 'AP_STATE',
    9: 'INIT_SIMPLE_BEARING',
    10: 'ARMED',
    11: 'DISARMED',
    15: 'AUTO_ARMED',
    17: 'LAND_COMPLETE_MAYBE',
    18: 'LAND_COMPLETE',
    28: 'NOT_LANDED',
    19: 'LOST_GPS',
    21: 'FLIP_START',
    22: 'FLIP_END',
    25: 'SET_HOME',
    26: 'SET_SIMPLE_ON',
    27: 'SET_SIMPLE_OFF',
    29: 'SET_SUPERSIMPLE_ON',
    30: 'AUTOTUNE_INITIALISED',
    31: 'AUTOTUNE_OFF',
    32: 'AUTOTUNE_RESTART',
    33: 'AUTOTUNE_SUCCESS',
    34: 'AUTOTUNE_FAILED',
    35: 'AUTOTUNE_REACHED_LIMIT',
    36: 'AUTOTUNE_PILOT_TESTING',
    37: 'AUTOTUNE_SAVEDGAINS',
    38: 'SAVE_TRIM',
    39: 'SAVEWP_ADD_WP',
    41: 'FENCE_ENABLE',
    42: 'FENCE_DISABLE',
    43: 'ACRO_TRAINER_DISABLED',
    44: 'ACRO_TRAINER_LEVELING',
    45: 'ACRO_TRAINER_LIMITED',
    46: 'GRIPPER_GRAB',
    47: 'GRIPPER_RELEASE',
    49: 'PARACHUTE_DISABLED',
    50: 'PARACHUTE_ENABLED',
    51: 'PARACHUTE_RELEASED',
    52: 'LANDING_GEAR_DEPLOYED',
    53: 'LANDING_GEAR_RETRACTED',
    54: 'MOTORS_EMERGENCY_STOPPED',
    55: 'MOTORS_EMERGENCY_STOP_CLEARED',
    56: 'MOTORS_INTERLOCK_DISABLED',
    57: 'MOTORS_INTERLOCK_ENABLED',
    58: 'ROTOR_RUNUP_COMPLETE', // Heli only
    59: 'ROTOR_SPEED_BELOW_CRITICAL', // Heli only
    60: 'EKF_ALT_RESET',
    61: 'LAND_CANCELLED_BY_PILOT',
    62: 'EKF_YAW_RESET',
    63: 'AVOIDANCE_ADSB_ENABLE',
    64: 'AVOIDANCE_ADSB_DISABLE',
    65: 'AVOIDANCE_PROXIMITY_ENABLE',
    66: 'AVOIDANCE_PROXIMITY_DISABLE',
    67: 'GPS_PRIMARY_CHANGED',
    68: 'WINCH_RELAXED',
    69: 'WINCH_LENGTH_CONTROL',
    70: 'WINCH_RATE_CONTROL',
    71: 'ZIGZAG_STORE_A',
    72: 'ZIGZAG_STORE_B',
    73: 'LAND_REPO_ACTIVE',
    163: 'SURFACED',
    164: 'NOT_SURFACED',
    165: 'BOTTOMED',
    166: 'NOT_BOTTOMED'
}
export class DataflashDataExtractor {
    static extractAttitude (messages, source) {
        const attitudes = {}
        if (source in messages) {
            const attitudeMsgs = messages[source]
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                    [
                        window.radians(attitudeMsgs.Roll[i]),
                        window.radians(attitudeMsgs.Pitch[i]),
                        window.radians(attitudeMsgs.Yaw[i])
                    ]
            }
        }
        return attitudes
    }

    static extractAttitudeSources (messages) {
        const result = {
            quaternions: [],
            eulers: []
        }
        // Quaternions
        const baseMsgTypes = ['XKF1', 'XKQ1', 'NKQ1', 'XKQ']
        const expandedMsgTypes = []
        for (const baseMsgType of baseMsgTypes) {
            for (let i = 0; i < 10; i++) {
                expandedMsgTypes.push(`${baseMsgType}[${i}]`)
            }
        }
        for (const msgType of expandedMsgTypes) {
            if (msgType in messages && Object.keys(messages[msgType]).length > 0) {
                result.quaternions.push(msgType)
            }
        }
        // Eulers
        const attTypes = ['ATT', 'AHR2']
        for (const msgType of attTypes) {
            if (msgType in messages && Object.keys(messages[msgType]).length > 0) {
                result.eulers.push(msgType)
            }
        }
        return result
    }

    static extractAttitudeQ (messages, source) {
        const attitudes = {}
        if (source in messages && Object.keys(messages[source]).length > 0) {
            console.log(`QUATERNION1: ${source}`)
            const attitudeMsgs = messages[source]
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                    [
                        attitudeMsgs.Q1[i],
                        attitudeMsgs.Q2[i],
                        attitudeMsgs.Q3[i],
                        attitudeMsgs.Q4[i]
                    ]
            }
            return attitudes
        }
        return []
    }

    static extractFlightModes (messages) {
        let modes = []
        if ('MODE' in messages) {
            const msgs = messages.MODE
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
            for (const i in msgs.time_boot_ms) {
                if (i !== 0 && (msgs.asText[i] !== modes[modes.length - 1][1]) && msgs.asText[i] !== null) {
                    modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                }
            }
        }
        return modes
    }

    static extractEvents (messages) {
        let armedState = []
        if ('STAT' in messages && messages.STAT.length > 0) {
            const msgs = messages.STAT
            armedState = [[msgs.time_boot_ms[0], msgs.Armed[0] === 1]]
            for (const i in msgs.time_boot_ms) {
                if ((msgs.Armed[i] === 1) !== armedState[armedState.length - 1][1]) {
                    armedState.push([msgs.time_boot_ms[i], msgs.Armed[i] === 1])
                }
            }
        } else if ('EV' in messages) {
            armedState = []
            const msgs = messages.EV
            for (const i in msgs.time_boot_ms) {
                const event = events[msgs.Id[i]]
                if (event === undefined) {
                    armedState.push([msgs.time_boot_ms[i], 'Unk: ' + msgs.Id[i]])
                } else {
                    armedState.push([msgs.time_boot_ms[i], event])
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
                    const tot = cmdMsgs.CTot[i]
                    const id = cmdMsgs.CId[i]
                    const num = cmdMsgs.CNum[i]
                    const frame = cmdMsgs.Frame[i]
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6
                        lon = lon / 10e6
                    }
                    wps.push([lon, lat, cmdMsgs.Alt[i], tot, id, num, frame])
                }
            }
        }
        return wps
    }

    static extractFences (messages) {
        const fences = []
        let tempFences = []
        let lastCount = -1
        if ('FNCE' in messages) {
            console.log(messages.FNCE)
            const cmdMsgs = messages.FNCE
            for (const i in cmdMsgs.time_boot_ms) {
                if (cmdMsgs.Lat[i] !== 0) {
                    let lat = cmdMsgs.Lat[i]
                    let lon = cmdMsgs.Lng[i]
                    if (lastCount !== cmdMsgs.Count[i] || cmdMsgs.Radius[i] > 0) {
                        if (tempFences.length > 0) {
                            fences.push(tempFences)
                        }
                        tempFences = []
                        lastCount = cmdMsgs.Count[i]
                    }
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6
                        lon = lon / 10e6
                    }
                    tempFences.push([lon, lat, cmdMsgs.Radius[i]])
                }
            }
            fences.push(tempFences)
        }
        return fences
    }

    static extractVehicleType (messages) {
        if ('MSG' in messages) {
            const msgs = messages.MSG
            for (const i in msgs.Message) {
                if (msgs.Message[i].toLowerCase().indexOf('arduplane') > -1) {
                    return 'airplane'
                }
                if (msgs.Message[i].toLowerCase().indexOf('ardusub') > -1) {
                    return 'submarine'
                }
                if (msgs.Message[i].toLowerCase().toLowerCase().indexOf('rover') > -1) {
                    return 'boat'
                }
                if (msgs.Message[i].toLowerCase().indexOf('tracker') > -1) {
                    return 'tracker'
                }
            }
            return 'quadcopter'
        }
    }

    static extractDefaultParams (messages) {
        const params = {}
        if ('PARM' in messages) {
            const paramData = messages.PARM
            const range = [...Array(paramData.Name.length).keys()]
            if (paramData.Default === undefined) {
                return {}
            }
            for (const i of range) {
                params[paramData.Name[i]] = paramData.Default[i]
            }
        }
        return params
    }

    static extractParams (messages) {
        const params = []
        if ('PARM' in messages) {
            const paramData = messages.PARM
            for (const i in paramData.time_boot_ms) {
                params.push(
                    [
                        paramData.time_boot_ms[i],
                        paramData.Name[i],
                        paramData.Value[i]
                    ]
                )
            }
        }
        if ('PARAM_VALUE' in messages) {
            const paramData = messages.PARAM_VALUE
            for (const i in paramData.time_boot_ms) {
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
        const texts = []
        if ('STATUSTEXT' in messages) {
            const textMsgs = messages.STATUSTEXT
            for (const i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], textMsgs.severity[i], textMsgs.text[i]])
            }
        }
        if ('MSG' in messages) {
            const textMsgs = messages.MSG
            for (const i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], 0, textMsgs.Message[i]])
            }
        }
        return texts
    }

    static extractTrajectorySources (messages) {
        const candidates = []
        if ('POS' in messages) {
            candidates.push('POS')
        }
        if ('AHR2' in messages) {
            candidates.push('AHR2')
        }
        if ('GPS' in messages) {
            candidates.push('GPS')
        }
        if ('GPS[0]' in messages) {
            candidates.push('GPS[0]')
        }
        if ('GPS[1]' in messages) {
            candidates.push('GPS[1]')
        }
        return candidates
    }

    static extractTrajectory (messages, source) {
        // returns a dict with the trajectories found
        const ret = {}
        if ('POS' in messages && source === 'POS') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.POS
            let start = 0
            for (const i in gpsData.time_boot_ms) {
                const delta = gpsData.time_boot_ms[i] - start
                if (delta < 200) {
                    continue
                }
                start = gpsData.time_boot_ms[i]
                if (gpsData.Lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.Alt[i]
                    }
                    trajectory.push(
                        [
                            gpsData.Lng[i] / 1e7,
                            gpsData.Lat[i] / 1e7,
                            gpsData.Alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.Lng[i] / 1e7,
                        gpsData.Lat[i] / 1e7,
                        (gpsData.Alt[i] - startAltitude) / 1000,
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.POS = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHR2' in messages && source === 'AHR2') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.AHR2
            let start = 0
            for (const i in gpsData.time_boot_ms) {
                const delta = gpsData.time_boot_ms[i] - start
                if (delta < 200) {
                    continue
                }
                start = gpsData.time_boot_ms[i]
                if (gpsData.Lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.Alt[i]
                    }
                    trajectory.push(
                        [
                            gpsData.Lng[i] * 1e-7,
                            gpsData.Lat[i] * 1e-7,
                            gpsData.Alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.Lng[i] * 1e-7,
                        gpsData.Lat[i] * 1e-7,
                        (gpsData.Alt[i] - startAltitude) / 1000,
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.AHR2 = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        for (const gpsSource of ['GPS', 'GPS[0]', 'GPS[1]']) {
            if (gpsSource in messages && source === gpsSource) {
                const trajectory = []
                const timeTrajectory = {}
                let startAltitude = null
                const gpsData = messages[gpsSource]
                let start = 0
                for (const i in gpsData.time_boot_ms) {
                    const delta = gpsData.time_boot_ms[i] - start
                    if (delta < 200) {
                        continue
                    }
                    start = gpsData.time_boot_ms[i]
                    if (gpsData.Lat[i] !== 0) {
                        if (startAltitude === null) {
                            startAltitude = gpsData.Alt[i]
                        }
                        trajectory.push(
                            [
                                gpsData.Lng[i] / 1e7,
                                gpsData.Lat[i] / 1e7,
                                gpsData.Alt[i] - startAltitude,
                                gpsData.time_boot_ms[i]
                            ]
                        )
                        timeTrajectory[gpsData.time_boot_ms[i]] = [
                            gpsData.Lng[i] / 1e7,
                            gpsData.Lat[i] / 1e7,
                            gpsData.Alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]]
                    }
                }
                if (trajectory.length) {
                    ret[gpsSource] = {
                        startAltitude: startAltitude,
                        trajectory: trajectory,
                        timeTrajectory: timeTrajectory
                    }
                }
            }
        }
        return ret
    }

    static extractNamedValueFloatNames (_messages) {
        // this mechanism is not used for dataflash logs
        return []
    }

    static extractStartTime (messages) {
        return extractStartTime(messages)
    }
}
