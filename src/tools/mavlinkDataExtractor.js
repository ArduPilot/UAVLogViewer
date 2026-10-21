import { mavlink20 as mavlink } from "@/shared/lib/mavlink.js";
import { ParamSeeker } from "../tools/paramseeker.js";

// Vehicle types: their heartbeats carry the flight mode and the armed state. A GCS, gimbal,
// camera or companion computer sends heartbeats of its own, which must not count.
const VEHICLE_TYPES = new Set([
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
    mavlink.MAV_TYPE_KITE,
    mavlink.MAV_TYPE_VTOL_DUOROTOR,
    mavlink.MAV_TYPE_VTOL_QUADROTOR,
    mavlink.MAV_TYPE_VTOL_TILTROTOR,
    mavlink.MAV_TYPE_VTOL_RESERVED2,
    mavlink.MAV_TYPE_VTOL_RESERVED3,
    mavlink.MAV_TYPE_VTOL_RESERVED4,
    mavlink.MAV_TYPE_VTOL_RESERVED5,
    mavlink.MAV_TYPE_PARAFOIL,
    mavlink.MAV_TYPE_DODECAROTOR,
    mavlink.MAV_TYPE_DECAROTOR,
]);

// Indexes of the vehicle's heartbeats; without any, the first heartbeat (as before)
function vehicleHeartbeats(msgs) {
    const indexes = [];
    for (let i = 0; i < msgs.time_boot_ms.length; i++) {
        if (VEHICLE_TYPES.has(msgs.type[i])) {
            indexes.push(i);
        }
    }
    return indexes.length > 0 || msgs.time_boot_ms.length === 0 ? indexes : [0];
}

const armedText = (baseMode) =>
    (baseMode & 0b10000000) === 128 ? "Armed" : "Disarmed";

// How each source gives [lon, lat, alt] points: which samples have a position, and the
// start altitude, read at the first of them (or at the first sample, for some sources)
const TRAJECTORY_SOURCES = new Map([
    [
        "GLOBAL_POSITION_INT",
        {
            hasPosition: (d, i) => d.lat[i] !== 0,
            startAltitude: (d, i) => d.relative_alt[i],
            point: (d, i) => [d.lon[i], d.lat[i], d.alt[i] / 1000],
        },
    ],
    [
        "GPS_RAW_INT",
        {
            hasPosition: (d, i) => d.lat[i] !== 0,
            startAltitude: (d) => d.alt[0] / 1000,
            point: (d, i) => [
                d.lon[i] * 1e-7,
                d.lat[i] * 1e-7,
                d.alt[i] / 1000,
            ],
        },
    ],
    [
        "AHRS2",
        {
            hasPosition: (d, i) => d.lat[i] !== 0 || d.lng[i] !== 0,
            startAltitude: (d) => d.altitude[0],
            point: (d, i) => [d.lng[i] * 1e-7, d.lat[i] * 1e-7, d.altitude[i]],
        },
    ],
    [
        "AHRS3",
        {
            hasPosition: (d, i) => d.lat[i] !== 0,
            startAltitude: (d) => d.altitude[0],
            point: (d, i) => [d.lng[i] * 1e-7, d.lat[i] * 1e-7, d.altitude[i]],
        },
    ],
]);

export class MavlinkDataExtractor {
    static extractAttitude(messages, source) {
        const attitudes = {};
        if ("ATTITUDE" in messages) {
            const attitudeMsgs = messages.ATTITUDE;
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[Number.parseInt(attitudeMsgs.time_boot_ms[i])] = [
                    attitudeMsgs.roll[i],
                    attitudeMsgs.pitch[i],
                    attitudeMsgs.yaw[i],
                ];
            }
        }
        return attitudes;
    }

    static extractAttitudeQ(messages, source) {
        return {};
    }

    static extractFlightModes(messages) {
        const modes = [];
        if ("HEARTBEAT" in messages) {
            const msgs = messages.HEARTBEAT;
            for (const i of vehicleHeartbeats(msgs)) {
                const mode = msgs.asText[i] ?? "Unknown";
                if (mode !== modes.at(-1)?.[1]) {
                    modes.push([msgs.time_boot_ms[i], mode]);
                }
            }
        }
        return modes;
    }

    static extractEvents(messages) {
        const armedState = [];
        if ("HEARTBEAT" in messages) {
            const msgs = messages.HEARTBEAT;
            for (const i of vehicleHeartbeats(msgs)) {
                const event = armedText(msgs.base_mode[i]);
                if (event !== armedState.at(-1)?.[1]) {
                    armedState.push([msgs.time_boot_ms[i], event]);
                }
            }
        }
        return armedState;
    }

    static extractMission(messages) {
        const wps = [];
        if ("CMD" in messages) {
            const cmdMsgs = messages.CMD;
            for (const i in cmdMsgs.time_boot_ms) {
                if (cmdMsgs.Lat[i] !== 0) {
                    let lat = cmdMsgs.Lat[i];
                    let lon = cmdMsgs.Lng[[i]];
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6;
                        lon = lon / 10e6;
                    }
                    wps.push([lon, lat, cmdMsgs.Alt[i]]);
                }
            }
        }
        return wps;
    }

    static extractFences(messages) {
        return [];
    }

    static extractVehicleType(messages) {
        if ("HEARTBEAT" in messages) {
            for (const i in messages.HEARTBEAT.craft) {
                if (messages.HEARTBEAT.craft[i] !== undefined) {
                    return messages.HEARTBEAT.craft[i];
                }
            }
        }
    }

    static extractAttitudeSources(messages) {
        return {
            quaternions: [],
            eulers: ["ATTITUDE"],
        };
    }

    static extractTrajectorySources(messages) {
        const sources = [];
        if ("GLOBAL_POSITION_INT" in messages) {
            sources.push("GLOBAL_POSITION_INT");
        }
        if ("GPS_RAW_INT" in messages) {
            sources.push("GPS_RAW_INT");
        }
        if ("AHRS2" in messages) {
            sources.push("AHRS2");
        }
        if ("AHRS3" in messages) {
            sources.push("AHRS3");
        }
        return sources;
    }

    static extractTrajectory(messages, source) {
        const ret = {};
        const reader = TRAJECTORY_SOURCES.get(source);
        if (!reader || !(source in messages)) {
            return ret;
        }
        const gpsData = messages[source];
        const trajectory = [];
        const timeTrajectory = {};
        let startAltitude = null;
        for (const i in gpsData.time_boot_ms) {
            if (!reader.hasPosition(gpsData, i)) {
                continue;
            }
            if (startAltitude === null) {
                startAltitude = reader.startAltitude(gpsData, i);
            }
            const time = gpsData.time_boot_ms[i];
            trajectory.push([...reader.point(gpsData, i), time]);
            timeTrajectory[time] = [...reader.point(gpsData, i), time];
        }
        if (trajectory.length) {
            ret[source] = { startAltitude, trajectory, timeTrajectory };
        }
        return ret;
    }

    static extractDefaultParams(messages) {
        return {};
    }

    static extractParams(messages) {
        const params = [];
        const lastValue = {};
        if ("PARAM_VALUE" in messages) {
            const paramData = messages.PARAM_VALUE;
            for (const i in paramData.time_boot_ms) {
                const paramName = paramData.param_id[i].replace(/\W/gi, "");
                const paramValue = paramData.param_value[i];
                if (
                    lastValue[paramName] !== undefined &&
                    lastValue[paramName] === paramValue
                ) {
                    continue;
                }
                params.push([paramData.time_boot_ms[i], paramName, paramValue]);
                lastValue[paramName] = paramValue;
            }
        }
        if (params.length > 0) {
            return new ParamSeeker(params);
        } else {
            return undefined;
        }
    }

    static extractTextMessages(messages) {
        const texts = [];
        if ("STATUSTEXT" in messages) {
            const textMsgs = messages.STATUSTEXT;
            for (const i in textMsgs.time_boot_ms) {
                texts.push([
                    textMsgs.time_boot_ms[i],
                    textMsgs.severity[i],
                    textMsgs.text[i],
                ]);
            }
        }
        return texts;
    }

    static extractNamedValueFloatNames(messages) {
        if ("NAMED_VALUE_FLOAT" in messages) {
            return Array.from(new Set(messages.NAMED_VALUE_FLOAT.name));
        }
        return [];
    }

    static extractStartTime(messages) {
        return undefined;
    }
}
