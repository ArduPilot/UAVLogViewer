"use strict";

export default {
    // Vue 2.7's template compiler calls prettier.format() synchronously to beautify
    // dev render functions; with prettier 3 that returns a Promise and breaks the build
    prettify: false,
};
