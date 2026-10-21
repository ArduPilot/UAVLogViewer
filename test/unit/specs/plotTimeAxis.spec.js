import {
    timeAxis,
    dataEnd,
    relayoutRange,
    sameRange,
} from "@/features/plot/lib/plotTimeAxis.js";

const DAY = 86400000;

// what Plotly does with a number on a date axis: the browser's local time of it, as UTC fields
const plotlyClock = (n) => n - new Date(n).getTimezoneOffset() * 60000;

describe("plot time axis without an absolute time", () => {
    const axis = timeAxis({ label: "Time since boot" });

    test("time 0 shows as 2000-01-01 00:00:00", () => {
        for (const t of [0, 1, 999.5, 100000, 3278605.25]) {
            expect(plotlyClock(axis.toAxis(t))).toBeCloseTo(
                Date.UTC(2000, 0, 1) + t,
                3,
            );
        }
    });

    test("reads Plotly's positions back as log times", () => {
        expect(axis.fromAxis("2000-01-01 00:01:40")).toBe(100000);
        expect(axis.fromAxis("2000-01-01 00:03:20.5")).toBe(200500);
        expect(axis.fromAxis("2000-01-02")).toBe(DAY);
        expect(axis.fromAxis(axis.toAxis(1234.5))).toBeCloseTo(1234.5, 3);
        expect(axis.fromAxis("not a date")).toBeNaN();
    });

    test("labels hours, minutes, seconds and milliseconds; days past one", () => {
        const layout = axis.layout(DAY - 1);
        expect(layout).toMatchObject({
            type: "date",
            title: { text: "Time since boot" },
            hoverformat: "%H:%M:%S.%L",
        });
        expect(axis.layout(DAY).hoverformat).toBe("day %-j, %H:%M:%S.%L");
    });
});

describe("plot time axis with the log's absolute time", () => {
    // 18:00 UTC is 12:00 in Mexico City (UTC-6 all year)
    const start = Date.UTC(2026, 6, 7, 18, 0, 0);

    test("shows the local time where the flight was", () => {
        const axis = timeAxis({ start, timeZone: "America/Mexico_City" });
        expect(axis.fromAxis("2026-07-07 12:00:00")).toBe(0);
        expect(axis.fromAxis("2026-07-07 12:00:01.5")).toBe(1500);
        expect(plotlyClock(axis.toAxis(1500))).toBe(
            Date.UTC(2026, 6, 7, 12, 0, 1, 500),
        );
        const layout = axis.layout(0);
        expect(layout.type).toBe("date");
        expect(layout.title.text).toMatch(/^Time \(.+\)$/);
        expect(layout.hoverformat).toBe("%Y-%m-%d %H:%M:%S.%L");
    });

    test("an unknown zone falls back to the browser's", () => {
        const axis = timeAxis({ start, timeZone: "Not/AZone" });
        const local = new Date(start);
        expect(plotlyClock(axis.toAxis(0))).toBe(
            Date.UTC(
                local.getFullYear(),
                local.getMonth(),
                local.getDate(),
                local.getHours(),
                local.getMinutes(),
            ),
        );
    });

    test("a different start or zone is a different axis", () => {
        const key = timeAxis({ start, timeZone: "UTC" }).key;
        expect(timeAxis({ start, timeZone: "UTC" }).key).toBe(key);
        expect(timeAxis({ start: start + 1, timeZone: "UTC" }).key).not.toBe(
            key,
        );
        expect(timeAxis({ start, timeZone: null }).key).not.toBe(key);
    });
});

describe("plot time axis in a browser with a clock change", () => {
    const tz = process.env.TZ;
    beforeAll(() => {
        process.env.TZ = "America/New_York";
    });
    afterAll(() => {
        process.env.TZ = tz;
    });

    test("every sample keeps its time across the browser's clock change", () => {
        // New York moves to summer time at 2026-03-08 07:00 UTC
        const axis = timeAxis({
            start: Date.UTC(2026, 2, 8, 6, 0),
            timeZone: "UTC",
        });
        const times = Array.from({ length: 121 }, (_, i) => i * 60000);
        const values = axis.toAxisArray(times);
        values.forEach((n, i) => {
            expect(plotlyClock(n)).toBe(Date.UTC(2026, 2, 8, 6, 0) + times[i]);
        });
        expect(axis.toAxisArray([5, 6])).toEqual([5, 6].map(axis.toAxis));
    });
});

describe("plot ranges", () => {
    const axis = timeAxis();
    const gd = {
        layout: {
            xaxis: { range: ["2000-01-01 00:01:40", "2000-01-01 00:03:20.5"] },
        },
    };

    test("a zoom, a pan or an autorange gives the plot's new range", () => {
        for (const event of [
            { "xaxis.range": [0, 1] },
            { "xaxis.range[0]": "x", "xaxis.range[1]": "y" },
            // dragging one end of the axis
            { "xaxis.range[1]": "y" },
            { "xaxis.autorange": true },
        ]) {
            expect(relayoutRange(event, gd, axis)).toEqual([100000, 200500]);
        }
    });

    test("other changes and no event give no range", () => {
        expect(relayoutRange({ "yaxis.range": [0, 1] }, gd, axis)).toBeNull();
        expect(relayoutRange(undefined, gd, axis)).toBeNull();
    });

    test("the range a plot reports back is no change", () => {
        expect(sameRange([1000, 2000], [1000.0001, 1999.9999])).toBe(true);
        expect(sameRange([1000, 2000], [1000, 2002])).toBe(false);
        expect(sameRange([1000, 2000], null)).toBe(false);
    });
});

describe("plotted data", () => {
    test("plotted data ends at the last sample", () => {
        expect(dataEnd([{ x: [1, 5] }, { x: [2, 9] }, { x: [] }])).toBe(9);
        expect(dataEnd([])).toBe(-Infinity);
    });
});
