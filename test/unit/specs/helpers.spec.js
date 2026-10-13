import {
    store,
    firstFreeAxis,
    firstFreeColor,
} from "../../../src/components/Globals.js";
import { Interpolator } from "../../../src/components/widgets/interpolator.js";
import ExpressionEditor from "../../../src/components/ExpressionEditor.vue";
import Plotly from "../../../src/components/Plotly.vue";

// the plot component is only needed for its expression parsing
jest.mock("plotly.js", () => ({}));
jest.mock("d3", () => ({}));

describe("free plot axis and color", () => {
    const state = (expressions) => ({
        allAxis: store.allAxis,
        allColors: store.allColors,
        expressions,
    });

    test("start with the first axis and color", () => {
        expect(firstFreeAxis(state([]))).toBe(0);
        expect(firstFreeColor(state([]))).toBe(store.allColors[0]);
    });

    test("skip the ones in use, also axes saved as strings", () => {
        const s = state([
            { axis: 0, color: store.allColors[0] },
            { axis: "1", color: store.allColors[2] },
        ]);
        expect(firstFreeAxis(s)).toBe(2);
        expect(firstFreeColor(s)).toBe(store.allColors[1]);
    });

    test("fall back to the last ones when all are taken", () => {
        const s = state(
            store.allAxis.map((axis, i) => ({
                axis,
                color: store.allColors[i],
            })),
        );
        expect(firstFreeAxis(s)).toBe(store.allAxis.at(-1));
        expect(firstFreeColor(s)).toBe(store.allColors.at(-1));
    });
});

describe("Interpolator", () => {
    const series = new Interpolator([0, 10, 20, 30, 40], [1, 2, 3, 4, 5]);

    test("returns the sample at or just before the time", () => {
        expect(series.at(10)).toBe(2);
        expect(series.at(25)).toBe(3);
        expect(series.at(12)).toBe(2);
    });
});

describe("plot expressions", () => {
    const find = (expression) =>
        Plotly.methods.findMessagesInExpression(expression);

    test("find messages, instances and fields", () => {
        expect(find("ATT.Roll * 2")).toEqual([["ATT", "Roll"]]);
        expect(find("lowpass(RFND[0].Dist, 0.9) + GPS.Alt")).toEqual([
            ["RFND[0]", "Dist"],
            ["GPS", "Alt"],
        ]);
    });

    test("ignore names after a dot, like Math.PI", () => {
        expect(find("ATT.Roll * Math.PI / 180")).toEqual([["ATT", "Roll"]]);
    });

    test("the editor completes the word being typed", () => {
        const word = ExpressionEditor.methods.getCurrentWord;
        expect(word("ATT.Roll*GP")).toBe("GP");
        expect(word("lowpass(ATT")).toBe("ATT");
        expect(word("ATT.Roll / ")).toBe("");
    });
});
