import { ParamSeeker } from './paramseeker'
import { modeMappingPX4 } from './parsers/modeMaps'

window.radians = window.radians || function (a) {
    return 0.0174533 * a
}

export class PX4DataExtractor {
    static extractFlightModes (messages) {
        const modes = []
        if ('vehicle_status' in messages) {
            const msgs = messages.vehicle_status
            if (msgs.nav_state) {
                let lastMode = null
                for (const i in msgs.time_boot_ms) {
                    const modeNum = msgs.nav_state[i]
                    const modeName = modeMappingPX4[modeNum] || `Unknown(${modeNum})`
                    if (modeName !== lastMode) {
                        modes.push([msgs.time_boot_ms[i], modeName])
                        lastMode = modeName
                    }
                }
            }
        }
        return modes
    }

    static extractEvents (messages) {
        const armedState = []
        if ('vehicle_status' in messages) {
            const msgs = messages.vehicle_status
            if (msgs.arming_state) {
                let lastArmed = null
                for (const i in msgs.time_boot_ms) {
                    const armed = msgs.arming_state[i] === 2
                    if (armed !== lastArmed) {
                        armedState.push([msgs.time_boot_ms[i], armed])
                        lastArmed = armed
                    }
                }
            }
        }
        return armedState
    }

    static extractMission (messages) {
        return []
    }

    static extractVehicleType (messages) {
        if ('vehicle_status' in messages && messages.vehicle_status.vehicle_type) {
            const types = messages.vehicle_status.vehicle_type
            const lastType = types[types.length - 1]
            // PX4 MAV_TYPE values
            if (lastType === 1) return 'airplane'
            if (lastType === 2) return 'quadcopter'
            if (lastType === 10) return 'boat'
        }
        return 'quadcopter'
    }

    static extractAttitude (messages, source) {
        const attitudes = {}
        if (source in messages) {
            const attMsgs = messages[source]
            // PX4 vehicle_attitude uses quaternions; compute Euler angles
            if (attMsgs.q_0) {
                for (const i in attMsgs.time_boot_ms) {
                    const w = attMsgs.q_0[i]
                    const x = attMsgs.q_1[i]
                    const y = attMsgs.q_2[i]
                    const z = attMsgs.q_3[i]
                    // Quaternion to Euler (roll, pitch, yaw)
                    const sinrCosp = 2.0 * (w * x + y * z)
                    const cosrCosp = 1.0 - 2.0 * (x * x + y * y)
                    const roll = Math.atan2(sinrCosp, cosrCosp)

                    const sinp = 2.0 * (w * y - z * x)
                    const pitch = Math.abs(sinp) >= 1.0
                        ? Math.sign(sinp) * Math.PI / 2.0
                        : Math.asin(sinp)

                    const sinyCosp = 2.0 * (w * z + x * y)
                    const cosyCosp = 1.0 - 2.0 * (y * y + z * z)
                    const yaw = Math.atan2(sinyCosp, cosyCosp)

                    attitudes[parseInt(attMsgs.time_boot_ms[i])] = [roll, pitch, yaw]
                }
            }
        }
        return attitudes
    }

    static extractAttitudeQ (messages, source) {
        const attitudes = {}
        if (source in messages && messages[source].q_0) {
            const attMsgs = messages[source]
            for (const i in attMsgs.time_boot_ms) {
                attitudes[parseInt(attMsgs.time_boot_ms[i])] = [
                    attMsgs.q_0[i],
                    attMsgs.q_1[i],
                    attMsgs.q_2[i],
                    attMsgs.q_3[i]
                ]
            }
            return attitudes
        }
        return []
    }

    static extractAttitudeSources (messages) {
        const result = {
            quaternions: [],
            eulers: []
        }
        if ('vehicle_attitude' in messages) {
            result.quaternions.push('vehicle_attitude')
        }
        return result
    }

    static extractTrajectory (messages, source) {
        const ret = {}
        if (!(source in messages)) return ret

        const gpsData = messages[source]
        const trajectory = []
        const timeTrajectory = {}
        let startAltitude = null
        let start = 0

        // Determine field names and scaling based on topic
        let latField, lonField, altField
        let latScale = 1
        let lonScale = 1
        let altScale = 1

        if (source === 'vehicle_global_position' || source.startsWith('vehicle_global_position[')) {
            latField = 'lat'
            lonField = 'lon'
            altField = 'alt'
            // vehicle_global_position: lat/lon in degrees, alt in meters
        } else if (source === 'vehicle_gps_position' || source.startsWith('vehicle_gps_position[') ||
                   source === 'sensor_gps' || source.startsWith('sensor_gps[')) {
            latField = 'lat'
            lonField = 'lon'
            altField = 'alt'
            // vehicle_gps_position / sensor_gps: lat/lon in 1e-7 degrees, alt in mm
            latScale = 1e-7
            lonScale = 1e-7
            altScale = 0.001
        } else {
            return ret
        }

        if (!gpsData[latField] || !gpsData[lonField]) return ret

        for (const i in gpsData.time_boot_ms) {
            const delta = gpsData.time_boot_ms[i] - start
            if (delta < 200) continue
            start = gpsData.time_boot_ms[i]

            const lat = gpsData[latField][i] * latScale
            const lon = gpsData[lonField][i] * lonScale
            const alt = gpsData[altField] ? gpsData[altField][i] * altScale : 0

            if (lat !== 0) {
                if (startAltitude === null) {
                    startAltitude = alt
                }
                trajectory.push([lon, lat, alt - startAltitude, gpsData.time_boot_ms[i]])
                timeTrajectory[gpsData.time_boot_ms[i]] = [
                    lon, lat, (alt - startAltitude) / 1000, gpsData.time_boot_ms[i]
                ]
            }
        }

        if (trajectory.length) {
            ret[source] = {
                startAltitude: startAltitude,
                trajectory: trajectory,
                timeTrajectory: timeTrajectory
            }
        }
        return ret
    }

    static extractTrajectorySources (messages) {
        const candidates = []
        if ('vehicle_global_position' in messages) {
            candidates.push('vehicle_global_position')
        }
        if ('vehicle_gps_position' in messages) {
            candidates.push('vehicle_gps_position')
        }
        if ('sensor_gps' in messages) {
            candidates.push('sensor_gps')
        }
        return candidates
    }

    static extractParams (messages) {
        const params = []
        if ('PARM' in messages) {
            const paramData = messages.PARM
            for (const i in paramData.time_boot_ms) {
                params.push([
                    paramData.time_boot_ms[i],
                    paramData.Name[i],
                    paramData.Value[i]
                ])
            }
        }
        if (params.length > 0) {
            return new ParamSeeker(params)
        }
        return undefined
    }

    static extractDefaultParams (messages) {
        return {}
    }

    static extractTextMessages (messages) {
        const texts = []
        if ('log_message' in messages) {
            const logMsgs = messages.log_message
            for (const i in logMsgs.time_boot_ms) {
                texts.push([logMsgs.time_boot_ms[i], logMsgs.level[i], logMsgs.message[i]])
            }
        }
        return texts
    }

    static extractStartTime (messages) {
        return 0
    }

    static extractFences (messages) {
        return []
    }

    static extractNamedValueFloatNames (messages) {
        return []
    }
}
