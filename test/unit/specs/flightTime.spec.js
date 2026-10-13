import { logStartTime, zoneOfFlight } from "../../../src/tools/flightTime.js";
import extractStartTime from "../../../src/tools/datetools.js";

describe("log start time and place", () => {
    test("metadata start time as milliseconds", () => {
        expect(logStartTime({ startTime: new Date(5000) })).toBe(5000);
        expect(logStartTime({ startTime: 5000 })).toBe(5000);
        expect(logStartTime(null)).toBeNaN();
    });

    test("time zone of the first trajectory point", () => {
        expect(zoneOfFlight([[-99.13, 19.43, 2240, 0]])).toBe(
            "America/Mexico_City",
        );
        expect(zoneOfFlight([])).toBeNull();
        expect(zoneOfFlight(undefined)).toBeNull();
    });

    test("DataFlash start time is the time at boot", () => {
        // the first sample with a GPS time was logged 2 s after boot
        const gps = {
            time_boot_ms: [1000, 2000],
            GWk: [0, 2300],
            GMS: [0, 100000],
        };
        const gpsTime = (315964800 + 2300 * 7 * 86400 + 100) * 1000;
        // 18 leap seconds between GPS time and UTC
        expect(extractStartTime(gps).getTime()).toBe(gpsTime - 18000 - 2000);
    });
});
