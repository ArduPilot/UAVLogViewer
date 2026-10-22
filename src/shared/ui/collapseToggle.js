import { eventHub } from "@/shared/lib/eventHub.js";

// name -> Set of elements that toggle that panel
const togglesByName = new Map();

function setOpen(el, open) {
    el.classList.toggle("is-open", open);
    // the toggle element is often a wrapper; put aria-expanded on the
    // focusable child (the <a>/<button> that receives the click)
    const focusable = el.matches("button, a, [role='button']")
        ? el
        : el.querySelector("button, a, [role='button']");
    if (focusable) {
        focusable.setAttribute("aria-expanded", open ? "true" : "false");
    }
}

// one listener for all panels; HMR re-registers harmlessly because toggling
// to the same state is idempotent
eventHub.$on("collapse-state", (name, open) => {
    const set = togglesByName.get(name);
    if (set) {
        for (const el of set) {
            setOpen(el, open);
        }
    }
});

// v-collapse-toggle="'name'": clicking the element opens or closes the <Collapse name="name">
// panels. The toggle element gets .is-open (and its focusable child gets aria-expanded)
// when the matching panel opens. Place the toggle element before its <Collapse> in the
// template so the toggle is registered when the panel reports its initial state.
function attach(el, { value }) {
    el.collapseName = value;
    el.collapseToggle = () =>
        eventHub.$emit("collapse-toggle", el.collapseName);
    el.addEventListener("click", el.collapseToggle);
    if (!togglesByName.has(value)) {
        togglesByName.set(value, new Set());
    }
    togglesByName.get(value).add(el);
}

function update(el, { value, oldValue }) {
    if (value === oldValue) {
        return;
    }
    togglesByName.get(oldValue)?.delete(el);
    el.collapseName = value;
    if (!togglesByName.has(value)) {
        togglesByName.set(value, new Set());
    }
    togglesByName.get(value).add(el);
}

function detach(el) {
    el.removeEventListener("click", el.collapseToggle);
    togglesByName.get(el.collapseName)?.delete(el);
}

export const collapseToggle = {
    mounted: attach,
    updated: update,
    unmounted: detach,
};
