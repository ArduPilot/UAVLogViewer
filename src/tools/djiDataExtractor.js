globalThis.radians = function (a) {
    return 0.0174533 * a;
};

// OSD points at least 200 ms apart, skipping samples without a position (latitude 0)
function osdTrajectory(gpsData) {
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
        if (gpsData.latitude[i] === 0) {
            continue;
        }
        if (startAltitude === null) {
            startAltitude = gpsData.altitude[i];
        }
        const point = () => [
            gpsData.longitude[i],
            gpsData.latitude[i],
            gpsData.altitude[i],
            time,
        ];
        trajectory.push(point());
        timeTrajectory[time] = point();
    }
    return trajectory.length
        ? { startAltitude, trajectory, timeTrajectory }
        : null;
}

export class DjiDataExtractor {
    static extractAttitude(messages, source) {
        const attitudes = {};
        // console.log('extractAttitude', messages, source)
        if (source in messages) {
            // console.log('extractAttitude', messages[source])
            const attitudeMsgs = messages[source];
            // console.log('attitudeMsgs', attitudeMsgs)
            for (const i in attitudeMsgs.time_boot_ms) {
                // console.log('attitudeMsgs.time_boot_ms[i]', attitudeMsgs.time_boot_ms[i])
                // console.log(attitudeMsgs)
                attitudes[Number.parseInt(attitudeMsgs.time_boot_ms[i])] = [
                    globalThis.radians(attitudeMsgs.roll[i]),
                    globalThis.radians(attitudeMsgs.pitch[i]),
                    globalThis.radians(attitudeMsgs.yaw[i]),
                ];
            }
        }
        return attitudes;
    }

    static extractAttitudeSources(messages) {
        const result = {
            quaternions: [],
            eulers: ["OSD"],
        };
        return result;
    }

    static extractEvents(messages) {
        return [];
    }

    static extractFlightModes(messages) {
        return [[0, "Normal"]];
    }

    static extractMission(messages) {
        return [];
    }

    static extractParams(messages) {
        return undefined;
    }

    static extractFences(messages) {
        return [];
    }

    static extractDefaultParams(messages) {
        return [];
    }

    static extractVehicleType(messages) {
        return "quadcopter";
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
        return ["OSD"];
    }

    static extractTrajectory(messages, source) {
        // returns a dict with the trajectories found
        console.log("extractTrajectory", messages, source);
        const ret = {};
        if ("OSD" in messages && source === "OSD") {
            const trajectory = osdTrajectory(messages.OSD);
            if (trajectory) {
                ret.OSD = trajectory;
            }
        }
        console.log("extractTrajectory", ret);
        return ret;
    }

    static extractNamedValueFloatNames(_messages) {
        // this mechanism is not used for dataflash logs
        return [];
    }

    static extractStartTime(messages) {
        return 0;
    }
}
