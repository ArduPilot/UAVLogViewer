# UI standard

One system, two size tiers. Every value below is extracted from existing code, not invented. Change the standard here, then change the code.

## Two tiers

|                    | Sidebar tier     | Widget tier      |
| ------------------ | ---------------- | ---------------- |
| Control height     | 32px (2rem)      | 24px (1.5rem)    |
| Font size          | 13px (0.8125rem) | 11px (0.6875rem) |
| Horizontal padding | 12px (0.75rem)   | 10px (0.625rem)  |

Rationale: sidebar is primary UI, widget content is 11px dense text — 32px buttons inside 11px content look broken. Two tiers, not three.

## Radii

| Element                                                    | Radius          |
| ---------------------------------------------------------- | --------------- |
| All controls (buttons, inputs, selects, swatches, toggles) | 4px             |
| Widget shells (.uav-widget)                                | 5px (unchanged) |
| Swatch chips, checkboxes                                   | 2px             |

No pills. No per-file exceptions.

## Surfaces

Sidebar (dark surface #1a1e24):

| Element                                        | Background | Text    |
| ---------------------------------------------- | ---------- | ------- |
| Buttons, selects, axis toggles, color swatches | #1a1e24    | #fff    |
| Text inputs                                    | #fff       | #141924 |

Widgets (light surface rgb(253 254 255 / 85.6%)):

| Element              | Background | Text    |
| -------------------- | ---------- | ------- |
| Buttons              | #263547    | #fff    |
| Text inputs, selects | #fff       | #141924 |

Inputs are the one place the user types into, so they are white everywhere. Everything clicked (buttons, selects, swatches, toggles) is dark: #1a1e24 on the sidebar, #263547 inside widgets.

## Borders

| Context                           | Border                          |
| --------------------------------- | ------------------------------- |
| Sidebar buttons / selects on dark | 1px solid rgb(91 100 117 / 76%) |
| Sidebar inputs on white           | 1px solid rgb(133 133 133)      |
| Widget buttons                    | none                            |
| Widget inputs / selects           | 1px solid rgb(133 133 133)      |

## Focus — amber glow

Every focusable control uses the same focus treatment. No outline.

For bordered controls:

    border-color: #d47f00;
    box-shadow: 0 0 4px 0 rgb(212 127 0 / 40%);
    outline: none;

For borderless controls (widget buttons):

    box-shadow: inset 0 0 0 2px rgb(212 127 0 / 60%);
    outline: none;

The amber `#d47f00` (plane icon in Sidebar.vue) is the single accent for focus, everywhere.

## Hover

|                 | Background change                                 | Timing     |
| --------------- | ------------------------------------------------- | ---------- |
| Sidebar buttons | #1a1e24 to color-mix(in srgb, #1a1e24 92%, white) | 0.15s ease |
| Widget buttons  | #263547 to #3a4f6b                                | 0.15s ease |
| Selects, inputs | border-color to #a0a8b8                           | 0.15s ease |

Use the existing `#3a4f6b` from widget.css. Do not invent a second lighter navy.

## Active / pressed

| Context         | Background                            |
| --------------- | ------------------------------------- |
| Sidebar buttons | #252b33 (one step lighter than hover) |
| Widget buttons  | #162442 (darker than base)            |

## Disabled

    background: #b8c0cc;
    color: #666;
    cursor: not-allowed;

No transition when disabled.

## Transitions

| Purpose                                  | Timing     |
| ---------------------------------------- | ---------- |
| Interactive state (hover, focus, active) | 0.15s ease |
| Collapse / expand (caret, panel)         | 0.2s ease  |
| Everything else                          | none       |

No 0.5s, no 1s. Two durations, everywhere.

## Typography

- Family: inherit everywhere. Monospace only in ExpressionEditor.
- Button weight: 600.
- Button transform: uppercase.
- Button letter-spacing: 0.5px.

## Carets / collapse indicators

Two icons, no rotation:

    <i class="expand--closed fa-solid fa-caret-right"></i>
    <i class="expand--open fa-solid fa-caret-down"></i>

    .expand--open { display: none; }
    .is-open .expand--closed { display: none; }
    .is-open .expand--open { display: inline; }

Rotating a filled fa-caret-down shifts its visual center. Two static glyphs are centered by construction. Do not reintroduce a rotate transform on filled carets.

The wrapper element receives .is-open from v-collapse-toggle (see collapseToggle.js); aria-expanded goes on the inner focusable child.

## What is NOT part of this standard

- Element layout (flex, grid, gap) — per-component.
- Widget shell geometry (position, min-size, shadow) — see widget.css.
- Cesium's own toolbar — third-party, untouched.

## Implementation map

Sidebar tier — declared per file:

- `PlotSetup.vue` — buttons (`.add-expression`, `.save-preset`), axis toggle (`.axis-toggle`)
- `ColorPicker.vue` — trigger, item cells
- `SideBarMessageMenu.vue` — `#filterbox`
- `ExpressionEditor.vue` — `.code-input`

Widget tier — declared once, shared:

- `features/widgets/core/widget.css` — `.uav-widget button`, `.uav-widget input[type="text"]`, `.uav-widget select`
- Per-widget `<style scoped>` blocks must not override height, padding, radius, background, colour or focus. Strip them when found; the shared rule wins.
