import fs from "node:fs";
import { MavlinkDataExtractor } from "@/features/loader/extractors/mavlinkDataExtractor.js";
import { MavlinkParser } from "@/features/loader/parsers/mavlinkParser.js";
import { findTestLogs } from "../testlogs.js";

const files = findTestLogs(["tlog"]);
console.log("Testing MAVLink files:", files);

const suite = files.length > 0 ? describe : describe.skip;
suite("parse tlogs", () => {
    test.each(files.length > 0 ? files : ["(no .tlog logs found)"])(
        "parse %s",
        (a) => {
            const logfile = fs.readFileSync(a);
            const parser = new MavlinkParser();
            // Hide progress messages meant for the web worker
            self.postMessage = function () {};
            const result = parser.processData(logfile);
            const messageTypes = result.types;
            const messages = result.messages;
            expect(Object.keys(messageTypes)).toContain("HEARTBEAT");
            expect(
                MavlinkDataExtractor.extractEvents(messages).length,
            ).toBeGreaterThan(0);
            const attitude = MavlinkDataExtractor.extractAttitude(
                messages,
                "ATTITUDE",
            );
            expect(Object.keys(attitude).length).toBeGreaterThan(50);
            expect(
                MavlinkDataExtractor.extractFlightModes(messages).length,
            ).toBeGreaterThan(0);

            expect(MavlinkDataExtractor.extractParams(messages)).toBeDefined();

            expect(
                MavlinkDataExtractor.extractTextMessages(messages).length,
            ).toBeGreaterThan(0);
            const sources =
                MavlinkDataExtractor.extractTrajectorySources(messages);
            expect(sources.length).toBeGreaterThan(0);
            const trajectory = MavlinkDataExtractor.extractTrajectory(
                messages,
                sources[0],
            );
            expect(Object.keys(trajectory)).toContain(sources[0]);
            expect(trajectory[sources[0]].trajectory.length).toBeGreaterThan(
                10,
            );
            // one value per message in every column
            for (const [type, columns] of Object.entries(messages)) {
                const count = columns.time_boot_ms.length;
                for (const [field, values] of Object.entries(columns)) {
                    expect(values.length, `${type}.${field}`).toBe(count);
                }
            }
        },
    );
});
