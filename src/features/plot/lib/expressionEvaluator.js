import jsep from "jsep";

// A plot expression may reference only the names below. Anything else
// (fetch, eval, alert, document, Function, import, ...) is unknown to the
// evaluator and throws before any user code runs.
//
// Math methods are picked up automatically. Mavextra/mymavextra helpers
// are attached to globalThis by src/shared/lib/mavextra/*.js; they are
// discovered here at first compile, with a denylist for browser globals
// that must never leak into a plot expression.
const BLOCKED_GLOBALS = new Set([
    "eval",
    "fetch",
    "alert",
    "confirm",
    "prompt",
    "open",
    "close",
    "print",
    "stop",
    "focus",
    "blur",
    "scroll",
    "scrollBy",
    "scrollTo",
    "atob",
    "btoa",
]);

const BLOCKED_PROPERTIES = new Set([
    "constructor",
    "__proto__",
    "prototype",
    "caller",
    "callee",
    "arguments",
]);

let cachedFunctions = null;

function getSafeFunctions() {
    if (cachedFunctions) return cachedFunctions;
    const fns = {};
    for (const name of Object.getOwnPropertyNames(Math)) {
        if (typeof Math[name] === "function") fns[name] = Math[name];
    }
    for (const name of Object.getOwnPropertyNames(globalThis)) {
        if (BLOCKED_GLOBALS.has(name)) continue;
        if (!/^[a-z][a-z0-9_]*$/.test(name)) continue;
        if (typeof globalThis[name] === "function") {
            fns[name] = globalThis[name];
        }
    }
    cachedFunctions = fns;
    return fns;
}

const SAFE_NAMESPACES = { Math, Number };
const SAFE_CONSTANTS = {
    PI: Math.PI,
    E: Math.E,
    LN2: Math.LN2,
    LN10: Math.LN10,
    LOG2E: Math.LOG2E,
    LOG10E: Math.LOG10E,
    SQRT2: Math.SQRT2,
    SQRT1_2: Math.SQRT1_2,
};

// Plot-expression aliases. `ln` is what users of MAVExplorer / MATLAB
// write for natural log; JavaScript calls it `log`. Both work.
const SAFE_FUNCTION_ALIASES = {
    ln: Math.log,
    arcsin: Math.asin,
    arccos: Math.acos,
    arctan: Math.atan,
};

// Same shape as Plotly.vue#findMessagesInExpression, so the rewrite and
// the discovery agree on what counts as a message reference.
const MESSAGE_RE =
    /(?<!\.)\b(?<message>[A-Z][A-Z0-9_]+\b(\[[\w.]+\])?)(\.(?<field>\w+))?/g;

function rewriteMessages(expression, messages) {
    const ids = new Map(messages.map((msg, i) => [msg, `__m${i}`]));
    return expression.replace(MESSAGE_RE, (match, ...args) => {
        const groups = args.at(-1);
        const replacement = ids.get(groups.message);
        if (replacement === undefined) return match;
        return groups.field ? `${replacement}.${groups.field}` : replacement;
    });
}

function applyUnary(op, v) {
    switch (op) {
        case "-":
            return { value: -v };
        case "+":
            return { value: +v };
        case "!":
            return { value: !v };
        case "~":
            return { value: ~v };
        default:
            throw new Error(`unsupported unary operator: ${op}`);
    }
}

/* eslint-disable eqeqeq -- user expressions may write == / != */
const BINARY_OPS = {
    "+": (l, r) => l + r,
    "-": (l, r) => l - r,
    "*": (l, r) => l * r,
    "/": (l, r) => l / r,
    "%": (l, r) => l % r,
    "**": (l, r) => Math.pow(l, r),
    "==": (l, r) => l == r,
    "!=": (l, r) => l != r,
    "===": (l, r) => l === r,
    "!==": (l, r) => l !== r,
    "<": (l, r) => l < r,
    "<=": (l, r) => l <= r,
    ">": (l, r) => l > r,
    ">=": (l, r) => l >= r,
    "&": (l, r) => l & r,
    "|": (l, r) => l | r,
    "^": (l, r) => l ^ r,
    "<<": (l, r) => l << r,
    ">>": (l, r) => l >> r,
    ">>>": (l, r) => l >>> r,
};
/* eslint-enable eqeqeq */

function applyBinary(op, l, r) {
    const fn = BINARY_OPS[op];
    if (!fn) {
        throw new Error(`unsupported binary operator: ${op}`);
    }
    return fn(l, r);
}

// Turn a jsep AST node into (row) => value. `row` is the array of message
// samples at one time — row[0] is the first message in the expression,
// row[1] the second, etc.
const NODE_COMPILERS = {};

function compileLiteral(node) {
    const v = node.value;
    return () => v;
}

function compileIdentifier(node) {
    if (node.name.startsWith("__m")) {
        const i = Number(node.name.slice(3));
        return (row) => row[i];
    }
    if (node.name in SAFE_CONSTANTS) {
        const v = SAFE_CONSTANTS[node.name];
        return () => v;
    }
    if (node.name in SAFE_FUNCTION_ALIASES) {
        const fn = SAFE_FUNCTION_ALIASES[node.name];
        return () => fn;
    }
    if (node.name in SAFE_NAMESPACES) {
        const v = SAFE_NAMESPACES[node.name];
        return () => v;
    }
    const fns = getSafeFunctions();
    if (node.name in fns) {
        const fn = fns[node.name];
        return () => fn;
    }
    throw new Error(`unknown name: ${node.name}`);
}

function compileMember(node) {
    if (!node.computed && BLOCKED_PROPERTIES.has(node.property.name)) {
        throw new Error(`forbidden property: ${node.property.name}`);
    }
    if (
        node.computed &&
        node.property.type === "Literal" &&
        typeof node.property.value === "string" &&
        BLOCKED_PROPERTIES.has(node.property.value)
    ) {
        throw new Error(`forbidden property: ${node.property.value}`);
    }
    const objFn = compileNode(node.object);
    if (node.computed) {
        const propFn = compileNode(node.property);
        return (row) => {
            const o = objFn(row);
            if (o == null) return undefined;
            const k = String(propFn(row));
            if (BLOCKED_PROPERTIES.has(k)) {
                throw new Error(`forbidden property: ${k}`);
            }
            return o[k];
        };
    }
    const key = node.property.name;
    return (row) => {
        const o = objFn(row);
        if (o == null) return undefined;
        return o[key];
    };
}

function compileCall(node) {
    const fnFn = compileNode(node.callee);
    const argFns = node.arguments.map(compileNode);
    return (row) => {
        const fn = fnFn(row);
        if (typeof fn !== "function") {
            throw new TypeError("attempted to call a non-function");
        }
        return fn(...argFns.map((f) => f(row)));
    };
}

function compileUnary(node) {
    const argFn = compileNode(node.argument);
    const op = node.operator;
    return (row) => applyUnary(op, argFn(row)).value;
}

function compileBinary(node) {
    const leftFn = compileNode(node.left);
    const rightFn = compileNode(node.right);
    const op = node.operator;
    if (op === "&&") return (row) => leftFn(row) && rightFn(row);
    if (op === "||") return (row) => leftFn(row) || rightFn(row);
    return (row) => applyBinary(op, leftFn(row), rightFn(row));
}

function compileConditional(node) {
    const testFn = compileNode(node.test);
    const consFn = compileNode(node.consequent);
    const altFn = compileNode(node.alternate);
    return (row) => (testFn(row) ? consFn(row) : altFn(row));
}

function compileArray(node) {
    const elems = node.elements.map(compileNode);
    return (row) => elems.map((f) => f(row));
}

NODE_COMPILERS.Literal = compileLiteral;
NODE_COMPILERS.Identifier = compileIdentifier;
NODE_COMPILERS.MemberExpression = compileMember;
NODE_COMPILERS.CallExpression = compileCall;
NODE_COMPILERS.UnaryExpression = compileUnary;
NODE_COMPILERS.BinaryExpression = compileBinary;
NODE_COMPILERS.ConditionalExpression = compileConditional;
NODE_COMPILERS.ArrayExpression = compileArray;

function compileNode(node) {
    const compiler = NODE_COMPILERS[node.type];
    if (!compiler) {
        throw new Error(`unsupported syntax: ${node.type}`);
    }
    return compiler(node);
}

// Compile an expression with the given message names to a function
// (row) => value. Throws if the expression uses a name or syntax the
// evaluator does not allow.
export function compileExpression(expression, messages) {
    const body = rewriteMessages(expression, messages);
    let ast;
    try {
        ast = jsep(body);
    } catch (e) {
        throw new Error(`could not parse expression: ${e.message}`, {
            cause: e,
        });
    }
    return compileNode(ast);
}
