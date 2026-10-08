// Worker.js
// import MavlinkParser from 'mavlinkParser'
import { MavlinkParser } from "./mavlinkParser";
import DataflashParser from "./JsDataflashParser/parser";
import DjiParser from "./djiParser";

let parser;
self.addEventListener("message", async function (event) {
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
        }
        parser.loadType(event.data.type.split("[")[0]);
    } else if (event.data.action === "trimFile") {
        parser.trimFile(event.data.time);
    }
});
