// JsDataflashParser registers its own standalone "message" handler when it is imported. In this
// worker that handler would parse every file a second time (also tlogs, as DataFlash) and throw
// on every later message. parser.worker.js imports this module before the parsers, so this
// listener is registered first, runs first (same target and phase run in registration order) and
// stops the message from reaching any later listener.
let handler = null;

self.addEventListener("message", (event) => {
    event.stopImmediatePropagation();
    if (handler) {
        handler(event);
    }
});

export function onMessage(fn) {
    handler = fn;
}
