import fs from "node:fs";
import { DataflashDataExtractor } from "@/features/loader/extractors/dataflashDataExtractor.js";
import DataflashParser from "@/features/loader/parsers/JsDataflashParser/parser.js";
import { findTestLogs } from "../testlogs.js";

const files = findTestLogs(["bin"]);
console.log("Testing dataflash files:", files);

const suite = files.length > 0 ? describe : describe.skip;
suite("parse binary logs", () => {
    test.each(files.length > 0 ? files : ["(no .bin logs found)"])(
        "parse %s",
        (a) => {
            const logfile = fs.readFileSync(a);
            const parser = new DataflashParser();
            // Hide progress messages meant for the web worker
            self.postMessage = function () {};
            const result = parser.processData(logfile.buffer);
            const messageTypes = result.types;
            const messages = result.messages;
            expect(Object.keys(messageTypes)).toContain("MODE");
            // logs that recorded events (EV messages) must yield them
            if ("EV" in messageTypes) {
                expect(
                    DataflashDataExtractor.extractEvents(messages).length,
                ).toBeGreaterThan(0);
            }
            const attitudeSources =
                DataflashDataExtractor.extractAttitudeSources(messages);
            const attitude = DataflashDataExtractor.extractAttitude(
                messages,
                attitudeSources.eulers[0] || "ATT",
            );
            expect(Object.keys(attitude).length).toBeGreaterThan(50);
            expect(
                DataflashDataExtractor.extractFlightModes(messages).length,
            ).toBeGreaterThan(0);

            expect(
                DataflashDataExtractor.extractParams(messages),
            ).toBeDefined();

            expect(
                DataflashDataExtractor.extractTextMessages(messages).length,
            ).toBeGreaterThan(0);
            const sources =
                DataflashDataExtractor.extractTrajectorySources(messages);
            expect(sources.length).toBeGreaterThan(0);
            const trajectory = DataflashDataExtractor.extractTrajectory(
                messages,
                sources[0],
            );
            expect(Object.keys(trajectory)).toContain(sources[0]);
            expect(trajectory[sources[0]].trajectory.length).toBeGreaterThan(
                10,
            );
        },
    );
});
