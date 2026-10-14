# TODO

Everything still open on the `upgrade` branch (local, not pushed). Phases 1–4 are done (Vue 3.5, Vite 8, Vitest, Plotly 4, Cesium 1.146).

## UI fixes you reported (not done yet)

- [ ] Widgets: the horizontal scrollbar now sits 22 px above the bottom (side effect of ending the lists above the resize handle). Better: no horizontal scrolling in widgets (text wraps to the window width) and the vertical bar still clear of the handle.
- [ ] Main sidebar scrollbar is ugly: make it thin and dark like the widgets', or hide it.
- [ ] Button consistency: ten different corner radii today (pills of 15–50 px in the sidebar and plot setup, 3–5 px in the 3D view and Cesium, 3–20 px in widgets and inputs). Decide one system and apply it everywhere.
- [ ] Hover animation consistency: sidebar buttons fade a glow in 0.5–1 s, our 3D toolbar buttons fade colour in 1 s, Cesium's own toolbar buttons change instantly. Pick one timing for all.
- [ ] EKF helper: the raw value at the top ("107391 0") has no label (leftover debug output): label it or remove it.
- [ ] Drop zone text: does not mention DJI `.txt` logs, and the text touches the box's right border.
- [ ] Message viewer looked empty in a test with the real `.bin`: check whether that is expected.
- [ ] `?plots=` with an instance the log lacks (e.g. `GPS[0]`) shows a blocking `alert()`: use a non-blocking message.
- [ ] The radius system of the UI should be consistent. Is not doable to have comboboxes almost squared alongside the semi-circle textboxes por plots, for example.
- [ ] Make animations consistent between menus of the sidebar, right now they all differs.

## Decisions pending (yours)

- [ ] Load Google Analytics only on plot.ardupilot.org, so dev servers, containers, forks and tests stop counting as visits (changes upstream behaviour).
- [ ] Tell ArduPilot that plot.ardupilot.org's nginx sends the app (about 13 MB of JS) and the 3.5 MB terrain `layer.json` uncompressed: `gzip on` would cut it to about a third. Outside this repo.

## Housekeeping

- [ ] PR #485 description says 52 commits; it has 53 now.
- [ ] Delete the backup branch `upgrade-before-split` once the split history is fine.
- [ ] Run the Nightwatch e2e on the Vite build (skipped: it loads the page online and reports a visit to ArduPilot's analytics).
- [ ] `npm audit`: 27 findings (dev dependencies). Recheck after Phase 5 and update what is left.
- [ ] Test data: `HeliCopter-test.tlog` fails the tlog spec (fewer than 50 attitude samples).

## Phase 5: optimize

- [ ] Load Cesium and Plotly only when needed (`defineAsyncComponent`): today the first screen downloads Cesium (4.2 MB), Plotly (1.1 MB) and the app (3.1 MB).
- [ ] Shrink the app chunk: the MAVLink binding and the XML docs are loaded on the main thread.
- [ ] Assets: `home2.png` (3.2 MB) to a small WebP/PNG; `boat.glb` (9.3 MB) and `bluerovsimple.glb` (2.9 MB) with meshopt/Draco and smaller textures.
- [ ] Consistent vehicle models: scale `bluerovsimple.glb` in the file and drop the code special case (fork issue #1); check sizes and axes of all models (fork issue #3).
- [ ] Split the 2800-line `CesiumViewer.vue` into modules. This also clears SonarQube's leftovers there: the bathymetry functions with 8–9 parameters and an `await` inside a loop.
- [ ] Merge the duplicated code of `Plotly.vue` and `PlotlyPopup.vue` (mode bands, zoom, CSV, cursor).
- [ ] One shared stylesheet for the widgets (each repeats the pane, handle and content CSS).
- [ ] Cognitive complexity: lower SonarJS's limit once the splits are done.
- [ ] Performance tests: a repeatable benchmark (parse time, 3D ready, heap after GC, frame time, plot redraw) from `perf-pre.js`/`perf-eval.js`, run offline with the local terrain, before and after each change. Known cost: the date axis adds about 1 µs per plotted point per redraw.

## Improvements

- [ ] Search tool should allow me to search throught index like GPS\[0\] or CTUN.

## Phase 6: finish

- [ ] Minor visual rework (the consistency items above belong here): spacing, colours, buttons, fonts.
- [ ] Reorganize folders and file names (confirm the scope first).
- [ ] Version 2.0.0 in `package.json` and tag `v2.0.0` at the merge.
- [ ] Docs: README build and development notes for Vite and Vitest.
- [ ] Rebase `upgrade` onto the fork's `master` (`a68586b` widgets fix, `c0ad4f4` terrain fix); conflicts expected in `SideBarFileManager.vue` and `ParamViewer.vue`.
- [ ] Merge into the fork's `master` (publishes the GHCR image); rebuild the local container.
- [ ] Remove this TODO.md before the upstream PR.
- [ ] Open the upgrade PR upstream after #485 is merged.
- [ ] Switch `.gitmodules` back to Williangalvani/JsDataflashParser once its PR #26 is merged.

## Later (fork issues)

Fork issues #1 submarine model scale, #2 camera in the URL, #3 model orientation, #4 presets as objects, #5 MagFit points, #6 widget interpolation, #7 MAVLink 2 signatures, #8 compass widget, #9 PX4 ULog, #10 more plot axes and colours.
