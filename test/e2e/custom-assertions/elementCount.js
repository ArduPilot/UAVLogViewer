// A custom Nightwatch assertion.
// The assertion name is the filename.
// Example usage:
//
//   browser.assert.elementCount(selector, count)
//
// For more information on custom assertions see:
// http://nightwatchjs.org/guide#writing-custom-assertions

export function assertion(selector, count) {
    this.message = "Testing if element <" + selector + "> has count: " + count;
    this.expected = count;
    this.pass = function (val) {
        return val === this.expected;
    };
    this.value = function (res) {
        return res.value;
    };
    this.command = function (cb) {
        return this.api.execute(
            function (selector) {
                return document.querySelectorAll(selector).length;
            },
            [selector],
            (res) => {
                cb.call(this, res);
            },
        );
    };
}
