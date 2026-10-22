// Worker.js
// Must stay the first import: registers this worker's message handler before the parsers' own
import { onMessage } from "./workerMessages";
import { MavlinkParser } from "./mavlinkParser";
import DataflashParser from "./JsDataflashParser/parser";
import DjiParser from "./djiParser";

let parser;
onMessage(async function (event) {
    if (event.data === null) {
        console.log("got bad file message!");
    } else if (event.data.action === "parse") {
        const data = event.data.file;
        if (event.data.isTlog) {
            parser = new MavlinkParser();
            parser.processData(data);
        } else if (event.data.isDji) {
            parser = new DjiParser();
            await parser.processData(data);
        } else {
            parser = new DataflashParser(true);
            parser.processData(data, [
                "CMD",
                "MSG",
                "FILE",
                "MODE",
                "AHR2",
                "ATT",
                "GPS",
                "POS",
                "SIM",
                "XKQ1",
                "XKQ",
                "NKQ1",
                "NKQ2",
                "XKQ2",
                "PARM",
                "MSG",
                "STAT",
                "EV",
                "XKF4",
                "FNCE",
            ]);
        }
    } else if (event.data.action === "loadType") {
        if (!parser) {
            console.log("parser not ready");
            return;
        }
        try {
            parser.loadType(event.data.type.split("[")[0]);
        } catch (e) {
            // e.g. a type the log does not contain; the page times out waiting for it
            console.warn(`could not load message type ${event.data.type}:`, e);
        }
    } else if (event.data.action === "trimFile") {
        parser.trimFile(event.data.time);
    }
});
