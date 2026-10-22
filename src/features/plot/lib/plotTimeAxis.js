import { DateTime } from "luxon";

// The plots' x axis is a Plotly date axis. It shows the local time where the flight was (as the 3D
// clock does) when the log has its absolute time, otherwise the time since the log's time 0 from
// 00:00:00. The rest of the app keeps the log's own times (milliseconds since boot, or since the start
// of a tlog or DJI log); toAxis and fromAxis convert them for Plotly and back.

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const DAY = 24 * 60 * MINUTE;
// the clock of the elapsed time: time 0 at 2000-01-01 00:00:00, which is also Plotly's first tick
const ELAPSED_BASE = Date.UTC(2000, 0, 1);
// a position as Plotly reports it, e.g. "2000-01-01 00:01:40.5"
const DATE_RE =
    /^(-?\d+)-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d)(?::(\d\d(?:\.\d*)?))?)?$/;

// log times have microsecond resolution (DataFlash TimeUS, tlog timestamps); rounding to it drops
// the float error of converting them to and from the large clock numbers
function toMicroseconds(ms) {
    return Math.round(ms * 1000) / 1000;
}

// Plotly reads a number on a date axis as a time in the browser's time zone: it shows the number
// minus this offset
function browserOffset(ms) {
    return new Date(ms).getTimezoneOffset() * MINUTE;
}

// the time a Plotly date string shows, as milliseconds whose UTC fields are that time
function parseDate(text) {
    const match = DATE_RE.exec(text);
    if (!match) {
        return Number.NaN;
    }
    const [year, month, day, hour, minute, seconds] = match
        .slice(1)
        .map((part) => Number(part ?? 0));
    return Date.UTC(year, month - 1, day, hour, minute) + seconds * SECOND;
}

function elapsedLayout(label, days) {
    // past a day the labels count days: "day 1" is the first one
    const day = days ? "day %-j, " : "";
    return {
        title: { text: label },
        tickformatstops: [
            { dtickrange: [null, SECOND], value: `${day}%H:%M:%S.%3f` },
            { dtickrange: [SECOND, DAY], value: `${day}%H:%M:%S` },
            { dtickrange: [DAY, null], value: "day %-j" },
        ],
        hoverformat: `${day}%H:%M:%S.%L`,
    };
}

function clockLayout(zoneName) {
    return {
        title: { text: `Time (${zoneName})` },
        // the ticks keep Plotly's own labels: the time, and the date under the first one
        hoverformat: "%Y-%m-%d %H:%M:%S.%L",
    };
}

// origin: start, the absolute time at the log's time 0 (see logStartTime, NaN when unknown);
// timeZone, where the flight was (null for the browser's zone); label, the axis title without an
// absolute time
export function timeAxis({
    start = Number.NaN,
    timeZone = null,
    label = "Time since boot",
} = {}) {
    let base = ELAPSED_BASE;
    let zoneName = null;
    let offset = null;
    if (Number.isFinite(start)) {
        // a zone newer than the browser's time zone data gives an invalid date: the browser's zone then.
        // The offset at the start holds for the whole log, so the time runs on through a clock change.
        let dateTime = DateTime.fromMillis(start);
        const zoned = timeZone ? dateTime.setZone(timeZone) : dateTime;
        if (zoned.isValid) {
            dateTime = zoned;
        }
        base = start + dateTime.offset * MINUTE;
        zoneName = dateTime.offsetNameShort || dateTime.toFormat("'UTC'ZZ");
        offset = dateTime.toFormat("ZZ");
    }
    // the number Plotly shows as the clock time of a log time
    const toAxis = (time) => {
        const clock = base + time;
        return clock + browserOffset(clock + browserOffset(clock));
    };
    return {
        key: JSON.stringify([start, timeZone, label]),
        toAxis,
        // a trace's times: one offset for all, unless the browser's clock changes inside them
        toAxisArray(times) {
            const shift = (time) => toAxis(time) - (base + time);
            const first = shift(times[0]);
            if (times.length === 0 || first !== shift(times.at(-1))) {
                return times.map(toAxis);
            }
            return times.map((time) => base + time + first);
        },
        // the log time of a Plotly position: a date string, or a number given to Plotly
        fromAxis(value) {
            if (typeof value === "string") {
                return toMicroseconds(parseDate(value) - base);
            }
            return toMicroseconds(value - browserOffset(value) - base);
        },
        // the clock time the axis shows for a log time, as ISO 8601 with the flight's UTC offset
        // (e.g. 2026-07-08T11:49:15.123-05:00), or null when the log has no absolute time
        clockTime(time) {
            if (offset === null) {
                return null;
            }
            return new Date(base + time).toISOString().replace("Z", offset);
        },
        // type, title and labels; end is the last plotted time
        layout(end) {
            return {
                type: "date",
                ...(zoneName
                    ? clockLayout(zoneName)
                    : elapsedLayout(label, end >= DAY)),
            };
        },
    };
}

// The log times of the x range a plotly_relayout event changed (a zoom, a pan, an autorange), or null.
// The plot's layout has the new range then, also when the event names only one end of it.
export function relayoutRange(event, gd, axis) {
    const keys = [
        "xaxis.range",
        "xaxis.range[0]",
        "xaxis.range[1]",
        "xaxis.autorange",
    ];
    if (!keys.some((key) => event?.[key] !== undefined)) {
        return null;
    }
    return gd.layout.xaxis.range.map(axis.fromAxis);
}

// The same time range, give or take Plotly's rounding: a plot reports back each range it is given,
// and taking that as a change would update the plots again, round and round
export function sameRange(a, b) {
    return (
        Boolean(a && b) &&
        Math.abs(a[0] - b[0]) < 1 &&
        Math.abs(a[1] - b[1]) < 1
    );
}

// The largest x value of the traces (each trace's x values are in time order)
export function dataEnd(traces) {
    let end = -Infinity;
    for (const trace of traces) {
        const last = trace.x?.at(-1);
        if (last !== undefined) {
            end = Math.max(end, last);
        }
    }
    return end;
}
