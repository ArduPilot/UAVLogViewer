import { eventHub } from "../../eventHub.js";

// v-collapse-toggle="'name'": clicking the element opens or closes the <Collapse name="name">
// panels. It has both Vue 2 (bind/update/unbind) and Vue 3 (mounted/updated/unmounted) hooks.
function attach(el, { value }) {
    el.collapseName = value;
    el.collapseToggle = () =>
        eventHub.$emit("collapse-toggle", el.collapseName);
    el.addEventListener("click", el.collapseToggle);
}

function update(el, { value }) {
    el.collapseName = value;
}

function detach(el) {
    el.removeEventListener("click", el.collapseToggle);
}

export const collapseToggle = {
    bind: attach,
    update,
    unbind: detach,
    mounted: attach,
    updated: update,
    unmounted: detach,
};
