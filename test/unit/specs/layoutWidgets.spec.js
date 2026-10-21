import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

// The seven floating widgets. Not Plotly, CesiumViewer, Sidebar — those
// are layout, not widgets, and don't have @close.
const WIDGETS = [
    "TxInputsViewer",
    "ParamViewer",
    "MessageViewer",
    "DeviceIDViewer",
    "AttitudeViewer",
    "MagFitTool",
    "EkfHelperTool",
];

const layout = readFileSync(
    resolve(__dirname, "../../../src/app/Layout.vue"),
    "utf8",
);

describe("Layout.vue widget mounts", () => {
    for (const name of WIDGETS) {
        test(`${name} is mounted with @close`, () => {
            const match = layout.match(
                new RegExp(`<${name}\\b[\\s\\S]*?(?:</${name}>|/>)`),
            );
            expect(match, `${name} not found in Layout.vue`).not.toBeNull();
            expect(match[0]).toContain("@close");
        });
    }

    test("no widget is listed in WIDGETS that Layout.vue does not mount", () => {
        for (const name of WIDGETS) {
            expect(layout).toContain(`<${name}`);
        }
    });
});
