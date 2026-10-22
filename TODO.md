# TODO — `upgrade` branch

Local work, partially pushed. Phases 1–4 complete (Vue 3.5, Vite 8,
Vitest, Plotly 4, Cesium 1.146). Phase 5 (optimize) in progress. Phase 6
(finish) not started.

See [`docs/widgets.md`](docs/widgets.md) for the widget architecture and
[`docs/reorg-plan.md`](docs/reorg-plan.md) for the reorganization log.

---

## Reorganization — done (2026-10-20)

Feature-slice layout: `src/{app,features,shared,assets}`.

- [x] `features/widgets/{core,instances}/`, `features/scene/`,
      `features/plot/`, `features/loader/`, `features/sidebar/`.
- [x] `shared/lib/` (leaf utilities, `mavextra/`), `shared/stores/index.js`
      (reactive store), `shared/ui/` (Collapse, Modal, TreeMenu,
      AttitudeIndicator).
- [x] `app/{App.vue,Layout.vue,main.js,router/}`.
- [x] Cross-directory imports enforced via
      `eslint-plugin-no-relative-import-paths` (allowSameFolder,
      rootDir: src, prefix: @). `npx eslint --fix src/` rewrote 19 files.
- [x] `JsDataflashParser` submodule moved to
      `src/features/loader/parsers/JsDataflashParser`; `.gitmodules`,
      `eslint.config.js`, `.markdownlint-cli2.jsonc` updated.
- [x] `vitest.config.js` exclude paths updated.
- [x] Assets split: `src/assets/{models,images,xml,samples}/`, with
      `logmetadata/` as its own folder.
- [x] `scripts/parse_mavgraph.py` → `scripts/mavgraph/parse_mavgraph.py`
      with its own `requirements.txt` (bs4).

## Date/time — done

- [x] `datetools.js` leap-second lookup refactored from eight sequential
      if-returns to a table + binary search over a runtime
      `leap-seconds.list`. GPS→UTC conversion extracted into
      `gpsTimeToUtc`; `extractStartTime` uses `findIndex` and returns
      `undefined` on no match (same as before).
- [x] `public/leap-seconds.list` (IANA copy) fetched at startup via
      `initLeapSeconds()`; `main.js` mounts inside `.finally()` so a
      failed fetch still mounts with the built-in fallback table.
      Warns if the fetched list is past its `#@` expiry date.

## Widget standardization

- [x] Shared shell `src/features/widgets/core/widget.css` (`__move` /
      `__resize` / `__close` / `__content`), seven widgets converted
      (Attitude, DeviceID, EkfHelper, MagFit, Message, Param, TxInputs).
- [x] Widget handles migrated from Unicode glyphs to Font Awesome 7 icons.
- [x] `TxInputs` → `TxInputsViewer` rename.
- [x] Close button fixed on `TxInputsViewer` and `MagFitTool`
      (missing `@close` in `Home.vue` before the reorg).
- [x] `MagFitTool.computeData()` filters out messages without compass
      fields (fixes a `TypeError` on logs with a `MAG` candidate lacking
      `xmag`/`ymag`/`zmag`).
- [x] `MagFitTool` genetic optimizer: await-in-loop refactored into
      recursive `runGeneration`; `Math.random` funnelled through
      `optimizerRandom()`; `selectParent` made sync;
      `Number.parseFloat` / `Set` / spread over `Object.assign`.
- [x] `MagFitTool.waitForMessages` resolves with `console.warn` on
      timeout (missing optional messages like `MAG2`/`MAG3` are normal).
- [x] Horizontal scrollbar in widgets: text wraps, no horizontal scroll,
      vertical bar clears the resize handle.
- [x] Folder split: non-widgets moved out of `widgets/` —
      `CesiumSettingsPanel.vue` → `features/scene/components/`,
      `TreeMenu.vue` → `shared/ui/`,
      `AttitudeIndicator.vue` → `shared/ui/`.
- [x] Debug output removed from `DeviceIDViewer.vue`, `MagFitTool.vue`,
      `EkfHelperTool.vue`.
- [x] Orphaned ids swept: `#paneContent` and `paneinputViewer` confirmed
      gone from all sources outside the widget files.

### Closed: widget registry in `src/app/Layout.vue`

- [x] Not done as a v-for + :is registry — decided against for seven
      widgets. The failure mode (a widget shipping without `@close`) is
      covered by test/unit/specs/layout-widgets.spec.js instead, which
      reads Layout.vue and asserts every widget tag has `@close`. Keeps
      explicit tags, prevents the bug. Revisit the registry past ~10
      widgets or 2+ maintainers.

### Done: hit zones vs. visual handles

- [x] Hit zones read `--uav-handle-size` from widget.css at mount and
      multiply it (MOVE_HIT_MULTIPLIER = 1.5, RESIZE_HIT_MULTIPLIER = 1.5).
      At the current 20px handle size that's a 30px hit zone on each
      corner — same feel as before on the move side, slightly tighter
      on resize. Changing the CSS var now grows both the painted handle
      and its hit zone together.

## UI consistency backlog

- [x] Main sidebar scrollbar styled (thin, white thumb on transparent,
      scoped to `.nav-side-menu`). White was chosen over the widget's
      dark so it stands out against the sidebar's dark gradient.
- [ ] Button consistency: PlotSetup buttons and the axis toggle are
      now 4 px / 32 px / `#1a1e24`. Remaining offenders: sidebar pills
      (15 px), 3D view / Cesium (3–5 px), widget inputs (3–20 px).
      Standard: 4 px radius, 32 px height, `#1a1e24` surface.
- [ ] Hover animation consistency: PlotSetup uses `background-color`
      `0.15 s ease`. Sidebar buttons glow in 0.5–1 s, 3D toolbar buttons
      fade colour in 1 s, Cesium's own buttons change instantly. Pick one
      timing for all.
- [ ] `ExpressionEditor.vue` input still has `border-radius: 20px`,
      white background, grey border — inconsistent with the 4 px / dark
      controls in the same row. Match to `#1a1e24` / 4 px / 32 px and
      dark-theme the `.suggestions-box`.
- [ ] Drop zone text: does not mention DJI `.txt` logs, and the text
      touches the box's right border.
- [ ] Message viewer looked empty in a test with the real `.bin`: check
      whether that is expected.
- [ ] `?plots=` with an instance the log lacks (e.g. `GPS[0]`) shows a
      blocking `alert()`: use a non-blocking message.
- [ ] The radius system of the UI should be consistent. Squares and
      semi-circles side by side (e.g. plot textboxes next to comboboxes)
      is not workable — pick a scale.
- [ ] Make animations consistent between sidebar menus — right now they
      all differ.
- [ ] Scope the large `<style>` block in `Sidebar.vue`. It is currently
      unscoped, so every rule leaks app-wide. The `.nav-side-menu li a i`
      rule (meant for the tabholder) gives 40 px of footprint to every
      `<li><a><i>` inside the sidebar, which broke the TreeMenu and
      MessageMenu carets and required local `.section i` overrides. Fix:
      first narrow that selector to `.tabholder a i`; then audit each
      remaining rule for what it was actually meant to reach before
      wrapping the block in `<style scoped>` — some rules may silently
      style PlotSetup / MessageMenu / TreeMenu and were never intended
      to. Do not convert to scoped until the audit is done.

## Phase 5 — optimize

- [ ] Load Cesium and Plotly only when needed (`defineAsyncComponent`):
      today the first screen downloads Cesium (4.2 MB), Plotly (1.1 MB)
      and the app (3.1 MB).
- [ ] Shrink the app chunk: the MAVLink binding and the XML docs load on
      the main thread.
- [ ] Assets: `home2.png` (3.2 MB) to a small WebP/PNG; `boat.glb`
      (9.3 MB) and `bluerovsimple.glb` (2.9 MB) with meshopt/Draco and
      smaller textures.
- [ ] Consistent vehicle models: scale `bluerovsimple.glb` in the file
      and drop the code special case (fork issue #1); check sizes and axes
      of all models (fork issue #3).
- [ ] Split the 2800-line `CesiumViewer.vue` into modules. This also
      clears SonarQube's leftovers there: the bathymetry functions with
      8–9 parameters and an `await` inside a loop.
- [ ] Merge the duplicated code of `Plotly.vue` and `PlotlyPopup.vue`
      (mode bands, zoom, CSV, cursor).
- [ ] Cognitive complexity: lower SonarJS's limit once the splits are
      done. (The leap-second if-chain was one contributor — already
      cleared.)
- [ ] Performance tests: a repeatable benchmark (parse time, 3D ready,
      heap after GC, frame time, plot redraw) from `perf-pre.js` /
      `perf-eval.js`, run offline with the local terrain, before and
      after each change. Known cost: the date axis adds about 1 µs per
      plotted point per redraw.

## Housekeeping

- [ ] PR #485 description says 52 commits; the reorg and datetools work
      have added substantially. Update the number before merging.
- [ ] Delete the backup branch `upgrade-before-split` once the split
      history is fine.
- [ ] Run the Nightwatch e2e on the Vite build (skipped: it loads the
      page online and reports a visit to ArduPilot's analytics).
- [ ] `npm audit`: recheck after the `--force` revert and Phase 5.
- [ ] Test data: `HeliCopter-test.tlog` fails the tlog spec (fewer than
      50 attitude samples).

## Phase 6 — finish

- [ ] Minor visual rework (the consistency items above belong here):
      spacing, colours, buttons, fonts.
- [ ] Version 2.0.0 in `package.json` and tag `v2.0.0` at the merge.
- [ ] Docs: README build and development notes for Vite and Vitest.
- [ ] Rebase `upgrade` onto the fork's `master` (`a68586b` widgets fix,
      `c0ad4f4` terrain fix); conflicts expected in `SideBarFileManager.vue`
      and `ParamViewer.vue`.
- [ ] Merge into the fork's `master` (publishes the GHCR image); rebuild
      the local container.
- [ ] Remove this `TODO.md` before the upstream PR.
- [ ] Open the upgrade PR upstream after #485 is merged.
- [ ] Switch `.gitmodules` back to Williangalvani/JsDataflashParser once
      its PR #26 is merged.

## Decisions pending (yours)

- [ ] Load Google Analytics only on plot.ardupilot.org, so dev servers,
      containers, forks and tests stop counting as visits (changes
      upstream behaviour).
- [ ] Tell ArduPilot that plot.ardupilot.org's nginx sends the app (about
      13 MB of JS) and the 3.5 MB terrain `layer.json` uncompressed:
      `gzip on` would cut it to about a third. Outside this repo.
- [ ] Plot colours: `state.allColors` still drives `firstFreeColor`.
      `ColorPicker.vue` allows a per-plot custom colour, but the
      auto-assigned pool is unchanged. Expanding the pool is fork
      issue #10.

## Improvements

- [ ] Search tool should allow searching through instance indices like
      `GPS[0]` or `CTUN`.
- [ ] Fix the load-file window: currently doesn't filter to `*.tlog` /
      `*.bin`.
- [ ] Add a rule in the 3D scene view to measure distances and angles.
- [ ] Add a linear compass visualizer in the 3D scene view for the drone.

## Later (fork issues)

- #1 submarine model scale
- #2 camera in the URL
- #3 model orientation
- #4 presets as objects
- #5 MagFit points
- #6 widget interpolation
- #7 MAVLink 2 signatures
- #8 compass widget
- #9 PX4 ULog
- #10 more plot axes and colours
