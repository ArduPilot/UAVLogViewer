import {ParamSeeker} from '../tools/paramseeker'

window.radians = function (a) {
    return 0.0174533 * a
}

export class DataflashDataExtractor {
    static extractAttitudes (messages) {
        let attitudes = {}
        if ('AHR2' in messages) {
            let attitudeMsgs = messages['AHR2']
            for (let i in attitudeMsgs.time_boot_ms) {
                attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                    [
                        window.radians(attitudeMsgs.Roll[i]),
                        window.radians(attitudeMsgs.Pitch[i]),
                        window.radians(attitudeMsgs.Yaw[i])
                    ]
            }
        } else if ('ATT' in messages) {
            let attitudeMsgs = messages['ATT']
            for (let i in attitudeMsgs.time_boot_ms) {
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

    static extractAttitudesQ (messages) {
        let attitudes = {}
        if ('XKQ1' in messages && messages['XKQ1'].length > 0) {
            console.log('QUATERNIOS1')
            let attitudeMsgs = messages['XKQ1']
            for (let att of attitudeMsgs) {
                attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
                // attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
            }
            return attitudes
        } else if ('NKQ1' in messages && messages['NKQ1'].length > 0) {
            console.log('QUATERNIOS2')
            let attitudeMsgs = messages['NKQ1']
            for (let att of attitudeMsgs) {
                // attitudes[att.time_boot_ms] = [att.Q2, att.Q3, att.Q4, att.Q1]
                attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
            }
            return attitudes
        }
        return []
    }

    static extractFlightModes (messages) {
        let modes = []
        if ('MODE' in messages) {
            let msgs = messages['MODE']
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
            for (let i in msgs.time_boot_ms) {
                if (i !== 0 && (msgs.asText[i] !== modes[modes.length - 1][1]) && msgs.asText[i] !== null) {
                    modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                }
            }
        }
        return modes
    }

    static extractArmedEvents (messages) {
        let armedState = []
        if ('STAT' in messages && messages['STAT'].length > 0) {
            let msgs = messages['STAT']
            armedState = [[msgs.time_boot_ms[0], msgs.Armed[0] === 1]]
            for (let i in msgs.time_boot_ms) {
                if ((msgs.Armed[i] === 1) !== armedState[armedState.length - 1][1]) {
                    armedState.push([msgs.time_boot_ms[i], msgs.Armed[i] === 1])
                }
            }
        } else if ('EV' in messages) {
            armedState = []
            let msgs = messages['EV']
            let armed = false
            for (let i in msgs.time_boot_ms) {
                if (armed) {
                    armed = (msgs.Id[i] !== 11) // 10 means armed
                } else {
                    armed = (msgs.Id[i] === 10) // 11 means disarmed
                }
                if (armedState.length === 0 || armed !== armedState[armedState.length - 1][1]) {
                    armedState.push([msgs.time_boot_ms[i], armed])
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
        if ('MSG' in messages) {
            let msgs = messages['MSG']
            for (let i in msgs.Message) {
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

    static extractParams (messages) {
        let params = []
        if ('PARM' in messages) {
            let paramData = messages['PARM']
            for (let i in paramData.time_boot_ms) {
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
        if ('MSG' in messages) {
            let textMsgs = messages['MSG']
            for (let i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], 0, textMsgs.Message[i]])
            }
        }
        return texts
    }

    static extractTrajectory (messages) {
        // returns a dict with the trajectories found
        let ret = {}
        if ('POS' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['POS']
            for (let i in gpsData.time_boot_ms) {
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
                ret['POS'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHR2' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['AHR2']
            for (let i in gpsData.time_boot_ms) {
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
                ret['AHR2'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('GPS' in messages) {
            let trajectory = []
            let timeTrajectory = {}
            let startAltitude = null
            let gpsData = messages['GPS']
            for (let i in gpsData.time_boot_ms) {
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
                ret['GPS'] = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        return ret
    }
}
