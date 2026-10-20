# TODO — `upgrade` branch

Local work, not yet pushed. Phases 1–4 complete (Vue 3.5, Vite 8, Vitest,
Plotly 4, Cesium 1.146). Phase 5 (optimize) in progress. Phase 6 (finish)
not started.

See [`docs/widgets.md`](docs/widgets.md) for the widget architecture and its
pending rework plan.

---

## Widget standardization — pending follow-ups

- [x] Shared shell (`src/styles/widget.css`) is done and 7 widgets are converted
(`Attitude`, `DeviceID`, `EkfHelper`, `MagFit`, `Message`, `Param`,
`TxInputs`). See [`docs/widgets.md`](docs/widgets.md) for what the shared
shell provides. The five items below are what remains.

### Pending: `Containerfile.dev` user model

- [ ] Remove `USER node` (currently at line 14, before `npm ci` — the build
      fails with EACCES on `node_modules/`). See README "Troubleshooting →
      Container runs as root" for the reasoning and the non-root alternative
      (chown after `npm ci` + `--userns=keep-id`).

### Pending: split `src/components/widgets/`

Move non-widgets out of the folder:

- [ ] `CesiumSettingsWidget.vue` → `src/components/cesium/CesiumSettingsPanel.vue`
      (embedded overlay panel, dark theme, no `useWidget`).
- [ ] `TreeMenu.vue` → `src/components/ui/TreeMenu.vue` (recursive sub-component).
- [ ] `flightIndicators/AttitudeIndicator.vue` → `src/components/ui/AttitudeIndicator.vue`
      (only consumer is `AttitudeWidget.vue`).
- [ ] Delete the empty `flightIndicators/` folder.
- [ ] Rule afterwards: **if it calls `useWidget()`, it lives in `widgets/`;
      otherwise it doesn't.**

### Pending: widget registry in `Home.vue`

Each widget currently has a hand-written `@close="state.showX = false"`.
`TxInputsViewer` shipped without one — its close button was a silent no-op.
A registry that enumerates widgets and wires their close handlers at
registration time makes that class of bug impossible by construction.

- [ ] Introduce `state.widgets = { <key>: { component, show, gate? }, ... }`.
- [ ] Migrate the 8 widget mounts in `Home.vue`.
- [ ] Decide `v-show` (keep state on hide) vs `v-if` (fresh widget on show).
- [ ] Delete the per-widget `state.showX` flags.

### Pending: hit zones vs. visual handles

- [ ] `useWidget.js` uses `MOVE_HANDLE = 40` and `RESIZE_HANDLE = 25` — about
      twice the visible handle footprint. Intentional (easier to grab on
      touchpads) but undocumented, and out of sync if the visible handles grow.
      Pick one: (a) add a comment above the constants explaining the ratio, or
      (b) expose the visual handle size as CSS vars and read them from
      `useWidget.js` at mount.

### Pending: debug output

- [ ] `DeviceIDViewer.vue`: `console.log(devids)` in `update()`,
      multi-line `console.log` inside `decode()`.
- [ ] `MagFitTool.vue`: `console.log("getting compass params")`,
      `console.log(bounds)`, `console.log("optimizing")`,
      `console.log("Optimization result: ", result)`,
      `console.log(data, corrections)` in `wmmErrorOnce`.
- [ ] `EkfHelperTool.vue`: unlabeled `{{ solutionValue }} {{ closestIndex }}`
      at the top of the template. Replace with a labelled readout or delete.

### Pending: orphaned ids

- [ ] After the folder split:
      `rg -n "#paneContent|#paneinputViewer|div #pane" src`
      — confirm nothing outside the widget files still references old ids.

---

## UI consistency backlog

- [ ] Main sidebar scrollbar is ugly: make it thin and dark like the
      widgets', or hide it.
- [ ] Button consistency: ten different corner radii today (pills of 15–50 px
      in the sidebar and plot setup, 3–5 px in the 3D view and Cesium,
      3–20 px in widgets and inputs). Decide one system and apply it.
- [ ] Hover animation consistency: sidebar buttons fade a glow in 0.5–1 s,
      the 3D toolbar buttons fade colour in 1 s, Cesium's own toolbar
      buttons change instantly. Pick one timing for all.
- [ ] Drop zone text: does not mention DJI `.txt` logs, and the text touches
      the box's right border.
- [ ] Message viewer looked empty in a test with the real `.bin`: check whether
      that is expected.
- [ ] `?plots=` with an instance the log lacks (e.g. `GPS[0]`) shows a blocking
      `alert()`: use a non-blocking message.
- [ ] The radius system of the UI should be consistent. Squares and semi-circles
      side by side (e.g. plot textboxes next to comboboxes) is not workable —
      pick a scale.
- [ ] Make animations consistent between sidebar menus — right now they all
      differ.

## Phase 5 — optimize

- [ ] Load Cesium and Plotly only when needed (`defineAsyncComponent`): today
      the first screen downloads Cesium (4.2 MB), Plotly (1.1 MB) and the app
      (3.1 MB).
- [ ] Shrink the app chunk: the MAVLink binding and the XML docs load on the
      main thread.
- [ ] Assets: `home2.png` (3.2 MB) to a small WebP/PNG; `boat.glb` (9.3 MB) and
      `bluerovsimple.glb` (2.9 MB) with meshopt/Draco and smaller textures.
- [ ] Consistent vehicle models: scale `bluerovsimple.glb` in the file and drop
      the code special case (fork issue #1); check sizes and axes of all models
      (fork issue #3).
- [ ] Split the 2800-line `CesiumViewer.vue` into modules. This also clears
      SonarQube's leftovers there: the bathymetry functions with 8–9 parameters
      and an `await` inside a loop.
- [ ] Merge the duplicated code of `Plotly.vue` and `PlotlyPopup.vue`
      (mode bands, zoom, CSV, cursor).
- [ ] Cognitive complexity: lower SonarJS's limit once the splits are done.
- [ ] Performance tests: a repeatable benchmark (parse time, 3D ready, heap
      after GC, frame time, plot redraw) from `perf-pre.js` / `perf-eval.js`,
      run offline with the local terrain, before and after each change.
      Known cost: the date axis adds about 1 µs per plotted point per redraw.

## Decisions pending (yours)

- [ ] Load Google Analytics only on plot.ardupilot.org, so dev servers,
      containers, forks and tests stop counting as visits (changes upstream
      behaviour).
- [ ] Tell ArduPilot that plot.ardupilot.org's nginx sends the app (about
      13 MB of JS) and the 3.5 MB terrain `layer.json` uncompressed:
      `gzip on` would cut it to about a third. Outside this repo.

## Housekeeping

- [ ] PR #485 description says 52 commits; it has 53 now.
- [ ] Delete the backup branch `upgrade-before-split` once the split history
      is fine.
- [ ] Run the Nightwatch e2e on the Vite build (skipped: it loads the page
      online and reports a visit to ArduPilot's analytics).
- [ ] `npm audit`: 27 findings (dev dependencies). Recheck after Phase 5 and
      update what is left.
- [ ] Test data: `HeliCopter-test.tlog` fails the tlog spec (fewer than 50
      attitude samples).

## Phase 6 — finish

- [ ] Minor visual rework (the consistency items above belong here): spacing,
      colours, buttons, fonts.
- [ ] Reorganize folders and file names (confirm the scope first).
- [ ] Version 2.0.0 in `package.json` and tag `v2.0.0` at the merge.
- [ ] Docs: README build and development notes for Vite and Vitest.
- [ ] Rebase `upgrade` onto the fork's `master` (`a68586b` widgets fix,
      `c0ad4f4` terrain fix); conflicts expected in `SideBarFileManager.vue`
      and `ParamViewer.vue`.
- [ ] Merge into the fork's `master` (publishes the GHCR image); rebuild the
      local container.
- [ ] Remove this `TODO.md` before the upstream PR.
- [ ] Open the upgrade PR upstream after #485 is merged.
- [ ] Switch `.gitmodules` back to Williangalvani/JsDataflashParser once its
      PR #26 is merged.

## Improvements

- [ ] Search tool should allow searching through instance indices like
      `GPS[0]` or `CTUN`.
- [ ] Fix the load-file window: currently doesn't filter to `*.tlog` / `*.bin`.

## Later (fork issues)

#1 submarine model scale · #2 camera in the URL · #3 model orientation ·
#4 presets as objects · #5 MagFit points · #6 widget interpolation ·
#7 MAVLink 2 signatures · #8 compass widget · #9 PX4 ULog ·
#10 more plot axes and colours.

### Done

- [x] Horizontal scrollbar in widgets: text wraps, no horizontal scroll,
      vertical bar clears the resize handle.
- [x] Shared shell `src/styles/widget.css` (`__move` / `__resize` / `__close` /
      `__content`) and the seven widgets converted onto it.
- [x] Widget handles migrated from Unicode glyphs to Font Awesome 7 icons.
- [x] `TxInputs` → `TxInputsViewer` rename.
- [x] Close button fixed on `TxInputsViewer` and `MagFitTool`
      (missing `@close` in `Home.vue`).
- [x] `MagFitTool.computeData()` filters out messages without compass fields
      (fixes a `TypeError` on logs with a `MAG` candidate lacking
      `xmag`/`ymag`/`zmag`).
- [x] `MagFitTool` genetic optimizer: await-in-loop refactored into recursive
      `runGeneration`; `Math.random` funnelled through `optimizerRandom()`;
      `selectParent` made sync; `Number.parseFloat` / `Set` / spread over
      `Object.assign`.
- [x] `MagFitTool.waitForMessages` resolves with `console.warn` on timeout
      (missing optional messages like `MAG2`/`MAG3` are normal).
