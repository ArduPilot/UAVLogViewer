# Widgets — architecture and rework plan

All floating widget windows share one shell, one set of handles, one content
wrapper, and one set of rules. This document is both the reference for
adding or converting a widget and the tracking file for the remaining rework.

## Directory map

```plain
src/
├── styles/
│   └── widget.css                    shared shell, handles, content, modifiers
├── components/
│   ├── Home.vue                      mounts every widget, wires @close
│   ├── widgets/
│   │   ├── useWidget.js              drag / resize / close logic
│   │   ├── AttitudeWidget.vue        converted  ←  useWidget
│   │   ├── DeviceIDViewer.vue        converted  ←  useWidget
│   │   ├── EkfHelperTool.vue         converted  ←  useWidget
│   │   ├── MagFitTool.vue            converted  ←  useWidget
│   │   ├── MessageViewer.vue         converted  ←  useWidget
│   │   ├── ParamViewer.vue           converted  ←  useWidget
│   │   ├── TxInputsViewer.vue        converted  ←  useWidget
│   │   ├── CesiumSettingsWidget.vue  NOT A WIDGET (pending move)
│   │   ├── TreeMenu.vue              NOT A WIDGET (pending move)
│   │   └── flightIndicators/
│   │       └── AttitudeIndicator.vue NOT A WIDGET (pending move)
│   ├── cesium/                       ←  target for CesiumSettingsPanel.vue
│   └── ui/                           ←  target for TreeMenu.vue, AttitudeIndicator.vue
```

The rule afterwards: **if it calls `useWidget()`, it lives in `widgets/`;
otherwise it does not.** See "Pending 2" for the move procedure.

## Reference

### Template skeleton

```vue
<template>
    <div
        :id="getDivName()"
        class="uav-widget"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <span class="uav-widget__move"></span>
        <span class="uav-widget__resize"></span>
        <span class="uav-widget__close" @click="close()"></span>
        <div class="uav-widget__content">
            <!-- widget content -->
        </div>
    </div>
</template>
```

The three handle spans are required. `useWidget.js` attaches its `mousedown`
handler to the outer `<div>` and uses the click position to decide whether
the event is a move (top-left 40×40 hit zone), a resize (bottom-right 25×25),
or none. Removing or renaming a span breaks the corresponding gesture.

### Script skeleton

```js
import { useWidget, widgetProps } from "./useWidget.js";

export default {
    name: "<Name>Viewer",
    props: widgetProps, // or spread + resizeable: false
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "<Name>Viewer", // MUST equal the component name
            width: 300,
            height: 215,
            left: 0,
            top: 0,
        });
    },
};
```

The component `name:` and the `useWidget` `name:` must match —
`useWidget` calls `getElementById(pane${name})`, and drag/resize silently
break when they don't.

### CSS classes

All in `src/features/widgets/core/widget.css`.

| Class                     | Role                                                                                                                                                                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.uav-widget`             | Shell. `position: absolute`, min sizes, background, shadow, `border-radius: 5px`, `z-index: 10000`, `user-select: none`.                                                               |
| `.uav-widget__move`       | Top-left drag handle (FA `fa-up-down-left-right`). Corner-conforming shape, mirrors `__resize` diagonally.                                                                             |
| `.uav-widget__resize`     | Bottom-right resize handle (FA `fa-expand`). Shape: `border-radius: 10px 0 1px`.                                                                                                       |
| `.uav-widget__close`      | Top-right close button (FA `fa-xmark`). Fires `emit("close")` on click; hover inverts to solid blue.                                                                                   |
| `.uav-widget__content`    | Scroll region. `padding: 24px 16px 16px 16px`, `overflow-x: hidden`, `height: calc(100% - 22px)`, `overflow-wrap: break-word`, rounded top corners so the scrollbar follows the shell. |
| `.uav-widget__content ul` | Flush list inside content.                                                                                                                                                             |
| `.uav-widget__value`      | Right-floated value inside a list item.                                                                                                                                                |

### Modifiers

Layered on top of `.uav-widget`. Pick only what a widget needs.

| Modifier                      | Effect                                                                                       | Used by                                    |
| ----------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `.uav-widget--no-resize`      | Hides `__resize`. Pair with `resizeable: false` in `widgetProps`.                            | AttitudeWidget, MagFitTool, TxInputsViewer |
| `.uav-widget--auto`           | Content-driven size (`width: max-content`, `height: auto`).                                  | MagFitTool                                 |
| `.uav-widget--radio`          | Green pill identity, dark-green tinted handles, `overflow: visible` so corners clip cleanly. | TxInputsViewer                             |
| `.uav-widget__content--fixed` | Content fills full widget height, no scroll, rounds to the widget corners.                   | AttitudeWidget, TxInputsViewer             |
| `.uav-widget__content--dense` | Auto-height content with tighter side padding.                                               | MagFitTool                                 |

## Procedure — adding a new widget

1. Create `src/features/widgets/instances/<Name>Viewer.vue` with the skeleton above.
2. Component `name:` and `useWidget` `name:` must be **the same string**
   (`<Name>Viewer`). Mismatched names are the most common source of subtle
   drag/resize bugs.
3. Only add per-widget CSS for things the shared shell doesn't cover. If you
   find yourself re-declaring `background`, `box-shadow`, `border-radius`,
   handles, or scroll rules, something is being shadowed by another selector
   — fix the shadow, not the widget.
4. Wire it in `Home.vue`:

    ```vue
    <ParamViewer
        v-if="state.showParams"
        @close="state.showParams = false"
    ></ParamViewer>
    ```

    Missing `@close` is silent: the widget emits `close`, no listener runs,
    nothing happens.

5. If it can't be resized, set `resizeable: { type: Boolean, default: false }`
   in `props` (spreading over `widgetProps`) and add `uav-widget--no-resize`
   to the outer `<div>`.

## Pending rework

### Done 2 — split the widgets folder

Done 2026-10-20. Widgets now live in `features/widgets/instances/`,
`useWidget.js` and `widget.css` in `features/widgets/core/`, and the
non-widgets (CesiumSettingsPanel, TreeMenu, AttitudeIndicator) in
`features/scene/components/` and `shared/ui/`. See docs/reorg-plan.md
for the full migration.

### Pending 3 — widget registry in `Home.vue`

Current wiring: each widget is gated by a `state.showX` boolean and each
`@close="state.showX = false"` is written by hand. Missing one is silent —
`TxInputsViewer` shipped without `@close` and its close button was a no-op
with no error.

Proposal:

```js
// state.widgets = {
//   params:    { component: ParamViewer,    show: true },
//   messages:  { component: MessageViewer,  show: true },
//   txInputs:  { component: TxInputsViewer, show: true, gate: "mapAvailable" },
//   ...
// }

<component
    v-for="(w, key) in state.widgets"
    :key="key"
    :is="w.component"
    v-show="w.show"
    @close="w.show = false"
/>
```

Two wins:

- `@close` is wired once, not per widget — a new widget that forgets to add
  it is impossible by construction.
- `v-show` instead of `v-if` keeps widget state (scroll position, local
  data) across hide/show. `v-if` is fine too if "reopen = fresh widget" is
  preferred. Decide explicitly and document.

### Pending 4 — hit zones vs. visible handles

`useWidget.js` uses `MOVE_HANDLE = 40` and `RESIZE_HANDLE = 25` — about
twice the visible handle footprint. Intentional (easier to grab on
touchpads) but undocumented, and if the visible handles ever grow, the hit
zones don't follow.

Two options:

- **A** — leave as-is, add a comment block above the constants explaining
  the ratio.
- **B** — expose the visible handle size as CSS vars (`--uav-handle-w`,
  `--uav-handle-h`) and read them in `useWidget.js` via `getComputedStyle`
  at mount. Then visual handle and hit zone stay in sync.

A is a one-line comment; B is a small refactor. Pick one and document it
here.

### Pending 5 — debug output cleanup

All three were logged during development and are still in the tree:

- `DeviceIDViewer.vue`: `console.log(devids)` in `update()`; the multi-line
  `console.log` inside `decode()`.
- `MagFitTool.vue`: `console.log("getting compass params")`,
  `console.log(bounds)`, `console.log("optimizing")`,
  `console.log("Optimization result: ", result)`, and the
  `console.log(data, corrections)` at the top of `wmmErrorOnce`.
- `EkfHelperTool.vue`: the unlabeled `{{ solutionValue }} {{ closestIndex }}`
  line at the top of the template. Replace with a labelled readout if it was
  actually useful, or delete.

Delete all of them in one commit, before the folder split, so the reorg diff
stays clean.

## Common bugs (all seen during this refactor)

| Symptom                                                               | Cause                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Close button visible but does nothing                                 | `@close` missing on the widget's tag in `Home.vue`.                                                                                                                                                                                      |
| Close button invisible AND unclickable                                | Widget has `border-radius` > 5px and `overflow: hidden`, and the close sits inside the rounded-corner arc. Move the handle inward (`top: 22px; right: 22px` for a 20px radius), or mirror the corner shape as `.uav-widget--radio` does. |
| Handle has correct cursor but no hover highlight                      | `:hover` was placed on `::before` / `::after` — Firefox does not fire pseudo-element `:hover`. Convert the pseudo-element to a real `<span>`.                                                                                            |
| Widget content starts at a different top/left than other widgets      | Content padding is set on the widget's children (e.g. `<ul>` padding) instead of `.uav-widget__content`. Move it up.                                                                                                                     |
| Horizontal scrollbar across the bottom of the widget                  | Content is allowed `overflow-x: auto`. Use `.uav-widget__content` (which is `overflow-x: hidden`) and make long tokens wrap with `overflow-wrap: break-word`.                                                                            |
| Two widgets open at once → one stops receiving input                  | Both still use `id="paneContent"` (duplicate id). Use the `.uav-widget__content` class instead.                                                                                                                                          |
| `podman-compose up --build` builds the production Dockerfile silently | Python `podman-compose` ignores the `dockerfile:` key on the build path. Use `podman build -f Containerfile.dev` directly. See README "Troubleshooting".                                                                                 |

## Diagnosis aids

Open the browser console (Firefox: **Ctrl+Shift+K**) and run:

```js
// How many widgets are still on the old id?
document.querySelectorAll('[id="paneContent"]').length; // want 0

// How many widgets are on the new class?
document.querySelectorAll(".uav-widget__content").length; // want = open widgets

// Which compose file does the provider resolve?
// (PowerShell) podman compose -f compose.yaml config | Select-String "dockerfile"
```

For a widget that won't close, verify emission first:

```js
const w = document.getElementById("paneParamViewer");
new MutationObserver(() => console.log("DOM changed")).observe(w.parentNode, {
    childList: true,
});
// then click the ✕
```

No log → `@close` isn't wired in `Home.vue`. Log but widget still visible →
the parent re-adds it (check `state.showX` reactivity).
