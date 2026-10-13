import { plotCsv } from "../../../src/tools/plotCsv.js";
import { timeAxis } from "../../../src/tools/plotTimeAxis.js";

// traces as the plot has them: x on the time axis
const traces = (axis) => [
    {
        name: "ATT.Roll | Min: 0.00 Max: 30.00 Mean: 15.00",
        x: axis.toAxisArray([1000, 1100, 1200, 1300]),
        y: [0, 10, 20, 30],
    },
    {
        // starts later, ends earlier, and has a gap (the null sample)
        name: "max(ATT.Roll, 1)",
        x: axis.toAxisArray([1150, 1250, 1290]),
        y: [5, null, 7],
    },
];
const rows = (csv) => csv.split("\n").map((line) => line.split(","));

describe("plot csv without an absolute time", () => {
    const axis = timeAxis();

    test("the first row has the values at the first sample", () => {
        expect(rows(plotCsv(traces(axis), axis, null))).toEqual([
            ["timestamp(ms)", "ATT.Roll", "max(ATT.Roll; 1)"],
            ["1000", "0", ""],
            ["1100", "10", ""],
            ["1200", "20", ""],
            ["1300", "30", ""],
        ]);
    });

    test("interpolates between samples over the visible range", () => {
        expect(rows(plotCsv(traces(axis), axis, [1050, 1300]))).toEqual([
            ["timestamp(ms)", "ATT.Roll", "max(ATT.Roll; 1)"],
            ["1050", "5", ""],
            ["1150", "15", "5"],
            ["1250", "25", ""],
        ]);
    });

    test("no data, no rows", () => {
        expect(plotCsv([{ name: "A", x: [], y: [] }], axis, null)).toBe(
            "timestamp(ms),A",
        );
    });
});

describe("plot csv with the log's absolute time", () => {
    // 16:49:15 UTC is 11:49:15 in Ecuador (UTC-5)
    const axis = timeAxis({
        start: Date.UTC(2026, 6, 8, 16, 49, 15) - 1000,
        timeZone: "America/Guayaquil",
    });

    test("adds the time the axis shows, with the flight's UTC offset", () => {
        const csv = rows(plotCsv(traces(axis), axis, [1000, 1123]));
        expect(csv[0]).toEqual([
            "timestamp(ms)",
            "time",
            "ATT.Roll",
            "max(ATT.Roll; 1)",
        ]);
        expect(csv[1]).toEqual([
            "1000",
            "2026-07-08T11:49:15.000-05:00",
            "0",
            "",
        ]);
        expect(csv[2][1]).toBe("2026-07-08T11:49:15.100-05:00");
    });

    test("log times come back exact from the large clock numbers", () => {
        for (const time of [57643.625, 1945914.557, 0.001]) {
            expect(axis.fromAxis(axis.toAxis(time))).toBe(time);
        }
        expect(timeAxis().clockTime(0)).toBeNull();
    });
});
