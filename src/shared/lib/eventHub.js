// The app-wide event bus. It used to be a bare Vue 2 instance (Vue 3 has none); this keeps its
// API: $on, $once, $off and $emit with any number of arguments. As in Vue, a listener that throws
// (or rejects) is logged and the other listeners still run.
export function createEventHub() {
    const listeners = new Map();

    const report = (event, error) =>
        console.error(`Error in event handler for "${event}":`, error);

    return {
        $on(event, handler) {
            if (!listeners.has(event)) {
                listeners.set(event, []);
            }
            listeners.get(event).push(handler);
            return this;
        },
        $once(event, handler) {
            const once = (...args) => {
                this.$off(event, once);
                return handler(...args);
            };
            return this.$on(event, once);
        },
        // Removes this handler for the event. Every listener must remove its own handler:
        // a missing handler is an error here, where Vue removed everyone's listeners.
        $off(event, handler) {
            if (typeof handler !== "function") {
                throw new TypeError(
                    `eventHub.$off("${event}") needs the handler to remove`,
                );
            }
            const list = listeners.get(event);
            if (list) {
                listeners.set(
                    event,
                    list.filter((h) => h !== handler),
                );
            }
            return this;
        },
        $emit(event, ...args) {
            for (const handler of [...(listeners.get(event) ?? [])]) {
                try {
                    const result = handler(...args);
                    if (typeof result?.catch === "function") {
                        result.catch((error) => report(event, error));
                    }
                } catch (error) {
                    report(event, error);
                }
            }
            return this;
        },
        listenerCount(event) {
            return listeners.get(event)?.length ?? 0;
        },
    };
}

export const eventHub = createEventHub();
