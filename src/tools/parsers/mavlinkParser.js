import {
    mavlink20 as mavlink,
    MAVLink20Processor as MAVLink,
} from "../../libs/mavlink";
import {
    modeMappingAcm,
    modeMappingApm,
    modeMappingBlimp,
    modeMappingRover,
    modeMappingSub,
    modeMappingTracker,
} from "./modeMaps";
import { Buffer } from "buffer/";

const vehicles = {
    1: "airplane", // Fixed wing aircraft.
    2: "quadcopter", // Quadrotor
    3: "quadcopter", // Coaxial helicopter
    4: "quadcopter", // Normal helicopter with tail rotor.
    5: "tracker", // Ground installation
    10: "rover", // Ground rover
    11: "boat", // Surface vessel, boat, ship
    12: "submarine", // Submarine
    13: "quadcopter", // Hexarotor
    14: "quadcopter", // Octorotor
    15: "quadcopter", // Tricopter
    19: "airplane", // Two-rotor VTOL using control surfaces in vertical operation in addition. Tailsitter.
    20: "airplane", // Quad-rotor VTOL using a V-shaped quad config in vertical operation. Tailsitter.
    21: "quadcopter", // Tiltrotor VTOL
    22: "airplane",
    23: "airplane",
    24: "airplane",
    25: "airplane",
    29: "quadcopter", // Dodecarotor
    35: "quadcopter", // Decarotor
};

// The mode table for each vehicle type, as pymavlink's AP_MAV_TYPE_MODE_MAP:
// every ArduPilot VTOL (a QuadPlane reports its Q_MAV_TYPE) runs Plane's modes
const MODE_MAPS = new Map([
    [mavlink.MAV_TYPE_QUADROTOR, modeMappingAcm],
    [mavlink.MAV_TYPE_HELICOPTER, modeMappingAcm],
    [mavlink.MAV_TYPE_HEXAROTOR, modeMappingAcm],
    [mavlink.MAV_TYPE_OCTOROTOR, modeMappingAcm],
    [mavlink.MAV_TYPE_DECAROTOR, modeMappingAcm],
    [mavlink.MAV_TYPE_DODECAROTOR, modeMappingAcm],
    [mavlink.MAV_TYPE_COAXIAL, modeMappingAcm],
    [mavlink.MAV_TYPE_TRICOPTER, modeMappingAcm],
    [mavlink.MAV_TYPE_FIXED_WING, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_DUOROTOR, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_QUADROTOR, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_TILTROTOR, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_RESERVED2, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_RESERVED3, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_RESERVED4, modeMappingApm],
    [mavlink.MAV_TYPE_VTOL_RESERVED5, modeMappingApm],
    [mavlink.MAV_TYPE_GROUND_ROVER, modeMappingRover],
    [mavlink.MAV_TYPE_SURFACE_BOAT, modeMappingRover],
    [mavlink.MAV_TYPE_ANTENNA_TRACKER, modeMappingTracker],
    [mavlink.MAV_TYPE_SUBMARINE, modeMappingSub],
    [mavlink.MAV_TYPE_AIRSHIP, modeMappingBlimp],
]);

function getModeString(mavtype, cmode, basemode) {
    if (mavtype === mavlink.MAV_TYPE_GCS) {
        return "";
    }
    const map = MODE_MAPS.get(mavtype);
    if (map === undefined) {
        if ((basemode & 4) > 0) {
            return "Auto";
        }
        if ((basemode & 8) > 0) {
            return "Guided";
        }
        if ((basemode & 16) > 0) {
            return "Stabilize";
        }
        return "Unknown";
    }
    // a mode newer than this table: show its number, as pymavlink does
    return map[cmode] ?? `Mode(${cmode})`;
}

export class MavlinkParser {
    constructor() {
        this.messages = {};
        this.totalSize = undefined;
        this.lastPercentage = 0;

        this.mavlinkParser = new MAVLink();
        // the emitter calls its listeners with itself as `this`
        this.mavlinkParser.on("message", (messages) =>
            this.onMessage(messages),
        );
        this.maxPercentageInterval = 0.1;
    }

    static fixData(message) {
        if (message._name === "GLOBAL_POSITION_INT") {
            message.lat = message.lat / 10000000;
            message.lon = message.lon / 10000000;
            message.relative_alt = message.relative_alt / 1000;
            return message;
        } else if (message._name === "HEARTBEAT") {
            message.asText = getModeString(
                message.type,
                message.custom_mode,
                message.base_mode,
            );
            message.craft = vehicles[message.type];
            return message;
        }
        delete message.crc;
        delete message.crc_extra;
        delete message.format;
        delete message.header;
        delete message.msgbuf;
        delete message.id;
        delete message.payload;
        delete message.order_map;
        return message;
    }

    onMessage(messages) {
        // parseType() emits all messages of one type at once
        const name = messages[0]._name;
        // for percentage calculation
        this.totalSize ??= this.mavlinkParser.buf.byteLength;
        for (const message of messages) {
            if (message._id !== -1) {
                MavlinkParser.fixData(message);
            }
        }

        const fields = messages[0].fieldnames;
        if (!fields.includes("time_boot_ms")) {
            fields.push("time_boot_ms");
        }
        // fixData adds these; SYSTEM_TIME's time_unix_usec is one of its own fields already (adding
        // it again pushed every value twice)
        if (messages[0]._name === "HEARTBEAT") {
            fields.push("asText", "craft");
        }
        const mergedData = {};
        for (const field of fields) {
            mergedData[field] = [];
        }
        for (const message of messages) {
            for (const field of fields) {
                mergedData[field].push(message[field]);
            }
        }
        this.messages[name] = mergedData;
        self.postMessage({ messages: this.messages });
    }

    extractStartTime() {
        return new Date(this.mavlinkParser.startTime);
    }

    processData(data) {
        this.mavlinkParser.pushBuffer(Buffer.from(data));
        const availableMessages = this.mavlinkParser.preParse();
        const preparseList = [
            "SYSTEM_TIME",
            "GLOBAL_POSITION_INT",
            "GPS_RAW_INT",
            "HEARTBEAT",
            "ATTITUDE",
            "AHRS",
            "PARAM_VALUE",
            "STATUSTEXT",
            "AHRS2",
            "AHRS3",
            "NAMED_VALUE_FLOAT",
        ];
        for (const i in preparseList) {
            this.mavlinkParser.parseType(preparseList[i]);
            self.postMessage({ percentage: (i / preparseList.length) * 100 });
        }
        self.postMessage({ percentage: 100 });
        const messageTypes = {};
        for (const msg of availableMessages) {
            let fields = mavlink.messageFields[msg];
            fields = fields.filter(
                (e) => e !== "time_boot_ms" && e !== "time_usec",
            );
            const complexFields = {};
            for (const field in fields) {
                complexFields[fields[field]] = {
                    name: fields[field],
                    units: "?",
                    multiplier: 1,
                };
            }
            messageTypes[msg] = {
                expressions: fields,
                units: null,
                multipiers: null,
                complexFields,
            };
        }
        const metadata = {
            startTime: this.extractStartTime(),
        };

        self.postMessage({ metadata });
        self.postMessage({ availableMessages: messageTypes });
        self.postMessage({ messagesDoneLoading: true });
        // self.postMessage({done: true})
        return { types: messageTypes, messages: this.messages };
    }

    trimFile(time) {
        const start = time[0];
        const end = time[1];
        console.log("triming", start, end);
        self.postMessage({ url: this.mavlinkParser.trimFile(start, end) });
    }

    loadType(type) {
        this.mavlinkParser.parseType(type);
        console.log("done");
    }
}
