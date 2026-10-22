import { describe, expect, test } from "vitest";
import { compileExpression } from "@/features/plot/lib/expressionEvaluator.js";

describe("compileExpression", () => {
    test("arithmetic without message references", () => {
        expect(compileExpression("sqrt(4) + 2 * 3", [])([])).toBe(
            Math.sqrt(4) + 6,
        );
    });

    test("resolves a message field", () => {
        expect(compileExpression("GPS.Alt + 1", ["GPS"])([{ Alt: 100 }])).toBe(
            101,
        );
    });

    test("resolves an instanced message field", () => {
        expect(
            compileExpression("XKF2[0].VWN * XKF2[0].VWN", ["XKF2[0]"])([
                { VWN: -5 },
            ]),
        ).toBe(25);
    });

    test("Math.PI and bare PI agree", () => {
        expect(compileExpression("Math.PI", [])([])).toBe(Math.PI);
        expect(compileExpression("PI", [])([])).toBe(Math.PI);
    });

    test("ln is natural log", () => {
        expect(compileExpression("ln(E)", [])([])).toBeCloseTo(1);
        expect(compileExpression("log(E)", [])([])).toBeCloseTo(1);
    });

    test("arcsin/arccos/arctan alias the Math functions", () => {
        expect(compileExpression("arcsin(1)", [])([])).toBe(Math.PI / 2);
        expect(compileExpression("arccos(1)", [])([])).toBe(0);
        expect(compileExpression("arctan(1)", [])([])).toBeCloseTo(Math.PI / 4);
    });

    test("rejects fetch", () => {
        expect(() => compileExpression("fetch('x')", [])).toThrow(
            /unknown name/,
        );
    });

    test("rejects eval", () => {
        expect(() => compileExpression("eval('1')", [])).toThrow(
            /unknown name/,
        );
    });

    test("rejects alert", () => {
        expect(() => compileExpression("alert(1)", [])).toThrow(/unknown name/);
    });

    test("rejects unsupported syntax", () => {
        expect(() => compileExpression("function () {}", [])).toThrow();
    });

    test("rejects constructor access", () => {
        expect(() => compileExpression("Math.constructor", [])).toThrow(
            /forbidden/,
        );
        expect(() => compileExpression("Math['constructor']", [])).toThrow(
            /forbidden/,
        );
        expect(() =>
            compileExpression("Math.max.constructor('alert(1)')()", []),
        ).toThrow(/forbidden/);
    });
});
