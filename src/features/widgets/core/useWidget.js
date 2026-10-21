import { onMounted, ref } from "vue";
import { eventHub } from "@/shared/lib/eventHub.js";

// The floating tool windows (div#pane<name>): moved by dragging their top-left corner, resized by
// dragging their bottom-right one, closed with a "close" event. Widgets that list parameters call
// dependOnParams() in a computed, which then runs again on "paramsUpdated" (the parameters are not
// reactive).
export const widgetProps = {
    resizeable: { type: Boolean, default: true },
};

// Corner hit zones, as multiples of --uav-handle-size (the painted
// handle size, defined in widget.css). At the current 20px these come
// out to 40px (move) and 25px (resize) — larger than the painted handle
// so a trackpad or finger can grab the corner without precision aiming.
// If the CSS var grows, the hit zones follow.
const MOVE_HIT_MULTIPLIER = 1.5;
const RESIZE_HIT_MULTIPLIER = 1.5;
const DEFAULT_HANDLE_SIZE = 20;

// Smallest size a widget can be dragged or resized to, in pixels.
const MIN_SIZE = 70;

function pointer(event) {
    return event.touches === undefined ? event : event.touches[0];
}

// Follow the pointer until the button is released; move(pageX, pageY) gets each position
function track(move) {
    const onMove = (event) => {
        const { pageX, pageY } = pointer(event);
        move(pageX, pageY);
    };
    const stop = (event) => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("touchmove", onMove);
        document.removeEventListener("mouseup", stop);
        document.removeEventListener("touchend", stop);
        event.preventDefault();
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("mouseup", stop);
    document.addEventListener("touchend", stop);
}

// geometry: the widget's name and its initial width, height, left and top in pixels
export function useWidget(props, emit, { name, width, height, left, top }) {
    const box = {
        width: ref(width),
        height: ref(height),
        left: ref(left),
        top: ref(top),
    };
    const paramsVersion = ref(0);
    const divName = `pane${name}`;

    // Hit zones for this widget, resolved from CSS at mount.
    let moveHit = DEFAULT_HANDLE_SIZE * MOVE_HIT_MULTIPLIER;
    let resizeHit = DEFAULT_HANDLE_SIZE * RESIZE_HIT_MULTIPLIER;

    const onPointerDown = (event) => {
        const pane = event.currentTarget;
        const {
            offsetWidth: w,
            offsetHeight: h,
            offsetLeft: l,
            offsetTop: t,
        } = pane;
        const { pageX, pageY } = pointer(event);
        // the pointer's distance from the bottom-right corner
        const x = l + w - pageX;
        const y = t + h - pageY;
        if (x > w - moveHit && y > h - moveHit) {
            track((px, py) => {
                box.top.value = Math.max(
                    0,
                    Math.min(py + y - h, window.innerHeight - h),
                );
                box.left.value = Math.max(
                    0,
                    Math.min(px + x - w, window.innerWidth - w),
                );
            });
        } else if (x < resizeHit && y < resizeHit) {
            track((px, py) => {
                if (!props.resizeable) {
                    return;
                }
                box.width.value = Math.max(px - l + x, MIN_SIZE);
                box.height.value = Math.max(py - t + y, MIN_SIZE);
            });
            event.preventDefault();
        }
    };
    const onParamsUpdated = () => {
        paramsVersion.value += 1;
    };

    onMounted(() => {
        const pane = document.getElementById(divName);

        const handleSize =
            Number.parseFloat(
                getComputedStyle(pane).getPropertyValue("--uav-handle-size"),
            ) || DEFAULT_HANDLE_SIZE;
        moveHit = handleSize * MOVE_HIT_MULTIPLIER;
        resizeHit = handleSize * RESIZE_HIT_MULTIPLIER;

        pane.addEventListener("mousedown", onPointerDown);
        pane.addEventListener("touchstart", onPointerDown);
        eventHub.$on("paramsUpdated", onParamsUpdated);
    });

    return {
        ...box,
        close: () => emit("close"),
        dependOnParams: () => paramsVersion.value,
        getDivName: () => divName,
    };
}
