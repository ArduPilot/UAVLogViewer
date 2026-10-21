import { ParamSeeker } from "@/shared/lib/paramseeker.js";
import extractStartTime from "@/shared/lib/datetools.js";

globalThis.radians = function (a) {
    return 0.0174533 * a;
};

const events = {
    7: "AP_STATE",
    9: "INIT_SIMPLE_BEARING",
    10: "ARMED",
    11: "DISARMED",
    15: "AUTO_ARMED",
    17: "LAND_COMPLETE_MAYBE",
    18: "LAND_COMPLETE",
    28: "NOT_LANDED",
    19: "LOST_GPS",
    21: "FLIP_START",
    22: "FLIP_END",
    25: "SET_HOME",
    26: "SET_SIMPLE_ON",
    27: "SET_SIMPLE_OFF",
    29: "SET_SUPERSIMPLE_ON",
    30: "AUTOTUNE_INITIALISED",
    31: "AUTOTUNE_OFF",
    32: "AUTOTUNE_RESTART",
    33: "AUTOTUNE_SUCCESS",
    34: "AUTOTUNE_FAILED",
    35: "AUTOTUNE_REACHED_LIMIT",
    36: "AUTOTUNE_PILOT_TESTING",
    37: "AUTOTUNE_SAVEDGAINS",
    38: "SAVE_TRIM",
    39: "SAVEWP_ADD_WP",
    41: "FENCE_ENABLE",
    42: "FENCE_DISABLE",
    43: "ACRO_TRAINER_DISABLED",
    44: "ACRO_TRAINER_LEVELING",
    45: "ACRO_TRAINER_LIMITED",
    46: "GRIPPER_GRAB",
    47: "GRIPPER_RELEASE",
    49: "PARACHUTE_DISABLED",
    50: "PARACHUTE_ENABLED",
    51: "PARACHUTE_RELEASED",
    52: "LANDING_GEAR_DEPLOYED",
    53: "LANDING_GEAR_RETRACTED",
    54: "MOTORS_EMERGENCY_STOPPED",
    55: "MOTORS_EMERGENCY_STOP_CLEARED",
    56: "MOTORS_INTERLOCK_DISABLED",
    57: "MOTORS_INTERLOCK_ENABLED",
    58: "ROTOR_RUNUP_COMPLETE", // Heli only
    59: "ROTOR_SPEED_BELOW_CRITICAL", // Heli only
    60: "EKF_ALT_RESET",
    61: "LAND_CANCELLED_BY_PILOT",
    62: "EKF_YAW_RESET",
    63: "AVOIDANCE_ADSB_ENABLE",
    64: "AVOIDANCE_ADSB_DISABLE",
    65: "AVOIDANCE_PROXIMITY_ENABLE",
    66: "AVOIDANCE_PROXIMITY_DISABLE",
    67: "GPS_PRIMARY_CHANGED",
    68: "WINCH_RELAXED",
    69: "WINCH_LENGTH_CONTROL",
    70: "WINCH_RATE_CONTROL",
    71: "ZIGZAG_STORE_A",
    72: "ZIGZAG_STORE_B",
    73: "LAND_REPO_ACTIVE",
    163: "SURFACED",
    164: "NOT_SURFACED",
    165: "BOTTOMED",
    166: "NOT_BOTTOMED",
};
// FNCE.Type values (ArduPilot's AC_PolyFenceType) of exclusion fences:
// 97 POLYGON_EXCLUSION, 96 CIRCLE_EXCLUSION_INT, 93 CIRCLE_EXCLUSION
// (the others: 98 POLYGON_INCLUSION, 95 RETURN_POINT, 94 CIRCLE_INCLUSION_INT, 92 CIRCLE_INCLUSION)
const EXCLUSION_FENCE_TYPES = new Set([97, 96, 93]);

// Lat/Lng in degrees * 1e7 to degrees; each source keeps the operation it always used
// (dividing and multiplying round differently)
const divideBy1e7 = (value) => value / 1e7;
const times1e7 = (value) => value * 1e-7;
const TRAJECTORY_SCALES = new Map([
    ["POS", divideBy1e7],
    ["AHR2", times1e7],
    ["SIM", times1e7],
    ["GPS", divideBy1e7],
    ["GPS[0]", divideBy1e7],
    ["GPS[1]", divideBy1e7],
]);

// Points at least 200 ms apart, skipping samples without a position (Lat 0)
function trajectoryFrom(gpsData, toDegrees) {
    const trajectory = [];
    const timeTrajectory = {};
    let startAltitude = null;
    let start = 0;
    for (const i in gpsData.time_boot_ms) {
        const time = gpsData.time_boot_ms[i];
        if (time - start < 200) {
            continue;
        }
        start = time;
        if (gpsData.Lat[i] === 0) {
            continue;
        }
        if (startAltitude === null) {
            startAltitude = gpsData.Alt[i];
        }
        const point = () => [
            toDegrees(gpsData.Lng[i]),
            toDegrees(gpsData.Lat[i]),
            gpsData.Alt[i],
            time,
        ];
        trajectory.push(point());
        timeTrajectory[time] = point();
    }
    return trajectory.length
        ? { startAltitude, trajectory, timeTrajectory }
        : null;
}

// Lat/Lng in degrees, or in degrees * 1e7
function fenceVertex(fnce, i) {
    const scale = Math.abs(fnce.Lat[i]) > 180 ? 10e6 : 1;
    return [fnce.Lng[i] / scale, fnce.Lat[i] / scale, fnce.Radius[i]];
}

export class DataflashDataExtractor {
    static extractAttitude(messages, source) {
        const attitudes = {};
        if (source in messages) {
            const attitudeMsgs = messages[source];
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[Number.parseInt(attitudeMsgs.time_boot_ms[i])] = [
                    globalThis.radians(attitudeMsgs.Roll[i]),
                    globalThis.radians(attitudeMsgs.Pitch[i]),
                    globalThis.radians(attitudeMsgs.Yaw[i]),
                ];
            }
        }
        return attitudes;
    }

    static extractAttitudeSources(messages) {
        const result = {
            quaternions: [],
            eulers: [],
        };
        // Quaternions
        const baseMsgTypes = ["XKF1", "XKQ1", "NKQ1", "XKQ"];
        const expandedMsgTypes = [];
        for (const baseMsgType of baseMsgTypes) {
            for (let i = 0; i < 10; i++) {
                expandedMsgTypes.push(`${baseMsgType}[${i}]`);
            }
        }
        for (const msgType of expandedMsgTypes) {
            if (
                msgType in messages &&
                Object.keys(messages[msgType]).length > 0
            ) {
                result.quaternions.push(msgType);
            }
        }
        // Eulers
        const attTypes = ["ATT", "AHR2"];
        for (const msgType of attTypes) {
            if (
                msgType in messages &&
                Object.keys(messages[msgType]).length > 0
            ) {
                result.eulers.push(msgType);
            }
        }
        return result;
    }

    static extractAttitudeQ(messages, source) {
        const attitudes = {};
        if (source in messages && Object.keys(messages[source]).length > 0) {
            console.log(`QUATERNION1: ${source}`);
            const attitudeMsgs = messages[source];
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[Number.parseInt(attitudeMsgs.time_boot_ms[i])] = [
                    attitudeMsgs.Q1[i],
                    attitudeMsgs.Q2[i],
                    attitudeMsgs.Q3[i],
                    attitudeMsgs.Q4[i],
                ];
            }
            return attitudes;
        }
        return [];
    }

    static extractFlightModes(messages) {
        let modes = [];
        if ("MODE" in messages) {
            const msgs = messages.MODE;
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]];
            for (const i in msgs.time_boot_ms) {
                if (
                    i !== "0" &&
                    msgs.asText[i] !== modes.at(-1)[1] &&
                    msgs.asText[i] !== null
                ) {
                    modes.push([msgs.time_boot_ms[i], msgs.asText[i]]);
                }
            }
        }
        return modes;
    }

    static extractEvents(messages) {
        let armedState = [];
        if ("STAT" in messages && messages.STAT.length > 0) {
            const msgs = messages.STAT;
            armedState = [[msgs.time_boot_ms[0], msgs.Armed[0] === 1]];
            for (const i in msgs.time_boot_ms) {
                if ((msgs.Armed[i] === 1) !== armedState.at(-1)[1]) {
                    armedState.push([
                        msgs.time_boot_ms[i],
                        msgs.Armed[i] === 1,
                    ]);
                }
            }
        } else if ("EV" in messages) {
            armedState = [];
            const msgs = messages.EV;
            for (const i in msgs.time_boot_ms) {
                const event = events[msgs.Id[i]];
                if (event === undefined) {
                    armedState.push([
                        msgs.time_boot_ms[i],
                        "Unk: " + msgs.Id[i],
                    ]);
                } else {
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
                    const tot = cmdMsgs.CTot[i];
                    const id = cmdMsgs.CId[i];
                    const num = cmdMsgs.CNum[i];
                    const frame = cmdMsgs.Frame[i];
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6;
                        lon = lon / 10e6;
                    }
                    wps.push([lon, lat, cmdMsgs.Alt[i], tot, id, num, frame]);
                }
            }
        }
        return wps;
    }

    static extractFences(messages) {
        const fences = [];
        if (!("FNCE" in messages)) {
            return fences;
        }
        console.log(messages.FNCE);
        const cmdMsgs = messages.FNCE;
        const hasType = cmdMsgs.Type !== undefined;
        let tempFences = [];
        let lastCount = -1;
        let lastType = -1;
        for (const i in cmdMsgs.time_boot_ms) {
            if (cmdMsgs.Lat[i] === 0) {
                continue;
            }
            const type = hasType ? cmdMsgs.Type[i] : -1;
            // Start a new fence group when the polygon vertex count changes,
            // when a circle (Radius > 0) is encountered, or when the fence
            // Type changes (e.g. an inclusion polygon followed by an exclusion
            // polygon with the same vertex count).
            const newGroup =
                lastCount !== cmdMsgs.Count[i] ||
                cmdMsgs.Radius[i] > 0 ||
                (hasType && lastType !== type);
            if (newGroup) {
                if (tempFences.length > 0) {
                    fences.push(tempFences);
                }
                tempFences = [];
                lastCount = cmdMsgs.Count[i];
                lastType = type;
            }
            // Tag the fence group with its type so the viewer can colour
            // inclusion vs exclusion fences
            if (hasType) {
                tempFences.exclusion = EXCLUSION_FENCE_TYPES.has(type);
            }
            tempFences.push(fenceVertex(cmdMsgs, i));
        }
        fences.push(tempFences);
        return fences;
    }

    static extractVehicleType(messages) {
        if ("MSG" in messages) {
            const msgs = messages.MSG;
            for (const i in msgs.Message) {
                if (msgs.Message[i].toLowerCase().includes("arduplane")) {
                    return "airplane";
                }
                if (msgs.Message[i].toLowerCase().includes("ardusub")) {
                    return "submarine";
                }
                if (
                    msgs.Message[i]
                        .toLowerCase()
                        .toLowerCase()
                        .includes("rover")
                ) {
                    return "boat";
                }
                if (msgs.Message[i].toLowerCase().includes("tracker")) {
                    return "tracker";
                }
            }
            return "quadcopter";
        }
    }

    static extractDefaultParams(messages) {
        const params = {};
        if ("PARM" in messages) {
            const paramData = messages.PARM;
            const range = [...new Array(paramData.Name.length).keys()];
            if (paramData.Default === undefined) {
                return {};
            }
            for (const i of range) {
                params[paramData.Name[i]] = paramData.Default[i];
            }
        }
        return params;
    }

    static extractParams(messages) {
        const params = [];
        if ("PARM" in messages) {
            const paramData = messages.PARM;
            for (const i in paramData.time_boot_ms) {
                params.push([
                    paramData.time_boot_ms[i],
                    paramData.Name[i],
                    paramData.Value[i],
                ]);
            }
        }
        if ("PARAM_VALUE" in messages) {
            const paramData = messages.PARAM_VALUE;
            for (const i in paramData.time_boot_ms) {
                params.push([
                    paramData.time_boot_ms[i],
                    paramData.param_id[i].replace(/\W/g, ""),
                    paramData.param_value[i],
                ]);
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
        if ("MSG" in messages) {
            const textMsgs = messages.MSG;
            for (const i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], 0, textMsgs.Message[i]]);
            }
        }
        return texts;
    }

    static extractTrajectorySources(messages) {
        const candidates = [];
        if ("POS" in messages) {
            candidates.push("POS");
        }
        if ("AHR2" in messages) {
            candidates.push("AHR2");
        }
        if ("SIM" in messages) {
            candidates.push("SIM");
        }
        if ("GPS" in messages) {
            candidates.push("GPS");
        }
        if ("GPS[0]" in messages) {
            candidates.push("GPS[0]");
        }
        if ("GPS[1]" in messages) {
            candidates.push("GPS[1]");
        }
        return candidates;
    }

    static extractTrajectory(messages, source) {
        // returns a dict with the trajectories found
        const ret = {};
        const toDegrees = TRAJECTORY_SCALES.get(source);
        if (toDegrees && source in messages) {
            const trajectory = trajectoryFrom(messages[source], toDegrees);
            if (trajectory) {
                ret[source] = trajectory;
            }
        }
        return ret;
    }

    static extractNamedValueFloatNames(_messages) {
        // this mechanism is not used for dataflash logs
        return [];
    }

    static extractStartTime(messages) {
        return extractStartTime(messages);
    }
}
