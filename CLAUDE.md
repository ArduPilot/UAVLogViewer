# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

UAV Log Viewer is a browser-only Vue 3.5 + Vite 8 app (live at plot.ardupilot.org) for viewing drone logs: ArduPilot DataFlash `.bin`, MAVLink telemetry `.tlog`, and DJI `.txt` logs. Logs are parsed client-side in a Web Worker, then plotted with Plotly and rendered in 3D with Cesium. There is no backend. The 3D view needs no Cesium ion token: terrain is a self-hosted quantized-mesh tileset served at `/quantized/` (the dev server proxies it to plot.ardupilot.org, see `vite.config.js`), and imagery is keyless (Esri by default).

## Setup and commands

Node >= 22.12 (Vite 8 and Plotly 4 require it; CI uses Node 24).

```bash
git submodule update --init --recursive   # required: the DataFlash parser is a submodule
npm install

npm run dev           # Vite dev server with hot reload on 0.0.0.0:8080
npm run build         # production build into dist/ (vite build)
npm start             # serve dist/ on :8080
npm run lint          # ESLint (eslint.config.js); npm run lint:fix applies the autofixes
npm run lint:css      # Stylelint on the component styles
npm run lint:md       # markdownlint
npm run lint:all      # the three above + format:check
ruff check && ruff format --check   # Python tooling (scripts/terrain, src/assets/parse_mavgraph.py)
npm run format        # prettier --write .
npm run format:check  # prettier --check .
npm run unit          # Vitest with coverage (vitest.config.js)
npx vitest run test/unit/specs/mavlinklogs.spec.js   # single spec file
npx vitest run -t "parse"                            # filter by test name
```

- The parser specs need real logs. They read `$TEST_LOG_DIR`, else `<os tmpdir>/testlogs` (filled by `test/testlogfiles/logdownloader.sh` from the current autotest logs), else `test/testlogfiles/`. Without logs both suites are skipped, not failed. Use full flight logs: the assertions expect more than 50 attitude samples.
- Specs can import `.vue` components (`@vitejs/plugin-vue`) and `?raw` files; `vitest.config.js` defines `_COMMIT_`/`_BUILDDATE_`, and `describe`/`test`/`expect`/`vi` are globals. A spec importing `Plotly.vue` must `vi.mock("plotly.js/lib/core", () => ({ default: {} }))`. `vi.mock` calls are hoisted above everything else in the file, so their factories can't use the file's own variables.
- CI (`.github/workflows/nodejs.yml`) has a lint job: `npm run lint:all`, Ruff (pinned to 0.17.0, its default rules change between releases), ShellCheck, hadolint and actionlint. Keep all of them clean.
- `npm run e2e` builds, serves `dist/` on port 8089 and runs Nightwatch 3 in headless Chrome; use `npm run e2e -- --env edgeHeadless` where only Edge is installed. Nightwatch starts the browser driver itself; `selenium-webdriver` is overridden in package.json because the version Nightwatch pins can no longer download Edge drivers. On Windows its startup prints a harmless `wmic.exe` not-found message.
- The dev server runs ESLint with `fix: true` (`vite-plugin-eslint2`), so **it rewrites source files while it runs**. Check `git status` after a dev session.
- `serve` is the only entry in `dependencies`; everything else, browser libraries included, is a devDependency because it is bundled at build time. Add packages with `npm install -D`, so the Docker runtime image (`npm prune --omit=dev`) keeps only the static server.
- The Dockerfile is a two-stage build (build stage with git, runtime stage running as a non-root user with `USER_UID`/`USER_GID` build args). Keep it clean under `hadolint --failure-threshold style`; CI runs hadolint.
- `scripts/terrain` (Python): `uv venv scripts/terrain/.venv` then `uv pip install --python scripts/terrain/.venv -r scripts/terrain/requirements.txt` also works on Windows (the rasterio wheel bundles GDAL). Pass `--coarse-dem` (from `build_coarse.py`) for the low zooms, or one worker reads gigabytes for a long time. Tiles are gzipped with the write time in the header, so compare tilesets after decompressing.
- Offline use: mount a quantized-mesh tileset (built with `scripts/terrain`, see README) at `dist/quantized` in the container. `serve.json` (used by `npm start`) sends `Content-Encoding: gzip` for the gzipped `.terrain` tiles; `layer.json` is plain JSON. Icons (Font Awesome) and the offline globe imagery (Cesium's Natural Earth II in `dist/Assets`) are bundled; only analytics, a Google web font and the online check need the network.

## Module system and build

- `package.json` has `"type": "module"`: every `.js` file is an ES module. Configs whose tools load them synchronously stay CommonJS with a `.cjs` name: `test/e2e/nightwatch.conf.cjs`. Everything else (`vite.config.js`, `vitest.config.js`, `.postcssrc.js`, `eslint.config.js`, `stylelint.config.js`, `scripts/`) uses `import`/`export`.
- In configs, use `fileURLToPath(new URL(..., import.meta.url))` for paths. `import.meta.resolve` returns a `file://` URL, not a path.
- `vite.config.js` holds the whole build; `vitest.config.js` merges it, so tests see the same plugins, defines and aliases (`@` is `src/`). `index.html` at the root is the entry (`<script type="module" src="/src/main.js">`).
- `define`: `_COMMIT_` (read from `.git`, also in a worktree, without running git) and `_BUILDDATE_` (used in `Globals.js`), `CESIUM_BASE_URL`, and `global` as `globalThis` (Plotly's `has-hover` uses Node's name). `@vitejs/plugin-vue` sets Vue's feature flags.
- Cesium's `Workers`, `ThirdParty`, `Assets` and `Widgets` are copied to the root of `dist/` (`vite-plugin-static-copy`); Cesium loads them at runtime. Built files go to `dist/static/`; Cesium, Plotly, Vue and the other libraries are separate chunks from the app's, so a new app version does not download them again. `base: "./"` keeps every URL relative.
- Assets are imported as URLs (`import icon from "../assets/x.png"`; `.glb` and `.tlog` through `assetsInclude`; files under 10 kB become data URLs), the XML presets and docs as text with `?raw`. The parser is a module worker (`worker.format: "es"`). The `buffer` and `events` packages stand in for Node's modules in the MAVLink code, which imports them.
- Vite empties `dist/` on every build, so a terrain tileset belongs in the container mount (`dist/quantized`), not in a local `dist/`.

## Architecture

### Data flow: file → worker → global store → extractors → views

1. **Loading** — `components/SideBarFileManager.vue` owns a single `parser.worker.js` instance, created with `new Worker(new URL(..., import.meta.url), { type: "module" })`, which Vite bundles by itself. It posts `{action: 'parse', file, isTlog, isDji}`, later `{action: 'loadType', type}` (lazy per-message decoding) and `{action: 'trimFile', time}`. Logs can also come from drag and drop, a URL (`?file=<url>`, or `?file=sample` for the bundled `vtol.tlog`), or `window.postMessage({type: 'arrayBuffer'})` from an embedding page. The file manager is only mounted while the sidebar's "home" tab is selected.
2. **Parsing (worker)** — `tools/parsers/parser.worker.js` dispatches to one of three parsers:
    - `JsDataflashParser/parser.js` (git submodule. It comes from the fork igoutta/JsDataflashParser for now, which adds newer flight modes: switch `.gitmodules` back to Williangalvani/JsDataflashParser once Williangalvani/JsDataflashParser#26 is merged) for `.bin`. It eagerly decodes only a fixed list of message types (MODE, ATT, GPS, PARM, …); everything else is decoded on demand through `loadType`.
    - `mavlinkParser.js` for `.tlog`, built on the generated MAVLink binding in `src/shared/lib/mavlink.js` (hand-converted to ES classes: message types `extend mavlink20.message`; regenerating it with mavgen would undo that).
    - `djiParser.js` for DJI logs (uses `dji-log-parser-js`).
      Parsers talk back only through `self.postMessage` with keyed payloads: `percentage`, `availableMessages`, `metadata`, `messages`, `messageType`+`messageList`, `messagesDoneLoading`, `files`, `url`. `SideBarFileManager`'s `worker.onmessage` maps each key onto the store and emits event-bus events. Keep to this message contract when adding parser features. Both parsers' `processData()` also return `{ types, messages }`, which the specs use.
3. **Store** — `components/Globals.js` exports the `reactive()` `store` (no Vuex or Pinia). Components get it as `state: store` in `data()` and mutate it directly. Large log data (messages, trajectories, attitudes, parameters, plot data, Cesium colors) goes in with `keepRaw()` (`markRaw`), so Vue does not proxy it: replace it rather than edit it in place, and pass `toRaw()` copies of store values to the worker or another window, which can't take Vue's proxies. `state.messages` is columnar: `messages[TYPE][field]` is an array, and `time_boot_ms` is the shared time axis (ms since boot for DataFlash, since the first packet or frame for tlog and DJI). `state.metadata.startTime` is the absolute time at time 0 for every log type, `state.metadata.timeZone` the zone where the flight was (`tools/flightTime.js`). Instanced DataFlash messages are stored as `TYPE[n]` (e.g. `RFND[0]`).
4. **Extraction** — once `messagesDoneLoading` fires, `components/Home.vue#extractFlightData` picks an extractor from `state.logType` (`tools/dataflashDataExtractor.js`, `mavlinkDataExtractor.js`, `djiDataExtractor.js`). All three expose the same static API (`extractFlightModes`, `extractEvents`, `extractMission`, `extractParams`, `extractAttitudeSources` + `extractAttitude(Q)(messages, source)`, `extractTrajectorySources` + `extractTrajectory(messages, source)`, `extractFences`, `extractStartTime`, …). New log-derived features need a method on **each** extractor.
5. **Views** — `Plotly.vue` (time-series plots; mounted only while `state.plotOn`; the x axis is a Plotly date axis showing the flight's local time, or the elapsed time from 00:00:00 without an absolute time. Store values, events and `state.timeRange` stay in log ms: convert only at Plotly's boundary with `timeAxis()` from `tools/plotTimeAxis.js`, `toAxis` for data, shapes and ranges, `fromAxis` for the date strings Plotly reports), `CesiumViewer.vue` (3D map and vehicle playback, split into small helpers for bathymetry, sampled position/orientation, model entity and trajectory segments; extra helpers in `components/cesiumExtra/`). Terrain comes only from the app's own `/quantized/` (never from plot.ardupilot.org directly: that is where the app is deployed), else the flat ellipsoid. Heights are absolute AMSL over real terrain; where the terrain has no detailed level at the takeoff (`terrainLevelAt` < `MIN_TERRAIN_LEVEL`), `state.heightOffset` puts the takeoff on the visible ground instead, and floating tool windows in `components/widgets/` (each gets its position, size, dragging and `close` event from the `useWidget` composable in `widgets/useWidget.js`, toggled by `state.show*` flags). `PlotlyPopup.vue` is the `/plot` route for detached plot windows. Routes: `/`, `/plot` and `/v/:id` (see `src/router/index.js`).

### Event bus

`$eventHub` (`app.config.globalProperties`, set in `main.js`) is the small emitter in `src/shared/lib/eventHub.js` (`$on`, `$once`, `$off` with the handler, `$emit`), used for cross-component communication: `messages`, `messageTypes`, `messagesDoneLoading`, `loadType`, `trimFile`, `addPlots`, `togglePlot`, `cesium-time-changed`, and others. Grep for `$eventHub.$on("<name>"` to find listeners.

### Plot expressions

Plot series are user expressions such as `ATT.Roll * 2` or `lowpass(ATTITUDE.pitch, 0.9)`. `Plotly.vue#evaluateExpression` finds the uppercase message names in the expression (whole words not preceded by a dot, so `Math.PI` is not a message), rewrites them to `a[i].`, compiles the result with `new Function`, and evaluates it over time-aligned rows. Results are cached in `state.plotCache` by expression string. Expressions can call helpers that `src/shared/lib/mavextra/mavextra.js` and `mymavextra.js` attach to `globalThis` (a port of pymavlink's mavextra; uses `vector3.js` and `matrix3.js`). Their snake_case names are public API, used by saved expressions and by the preset graphs in `src/assets/mavgraphs*.xml` and `ekf*Graphs.xml` (MAVExplorer format; `parse_mavgraph.py` is the converter). Don't rename them.

## Code style

- Prettier 3 owns formatting (`.prettierrc.json`: 4-space indent, double quotes, semicolons, trailing commas). Run `npm run format` rather than hand-formatting; `.prettierignore` excludes the submodule, XML assets and `package-lock.json`. Line endings are LF (`.gitattributes`).
- ESLint 10 flat config (`eslint.config.js`) checks code quality only: `@eslint/js` recommended, neostandard (`noStyle`; its `files` option adds `.vue`, which it skips by default), eslint-plugin-vue `flat/recommended`, SonarJS recommended (cognitive complexity at most 15 per function) and eslint-config-prettier. `camelcase` checks our identifiers but not property names (MAVLink, DataFlash, Plotly and Nightwatch use snake_case). Rule exceptions live in `eslint.config.js` with their reason, not in inline `eslint-disable` comments. `src/shared/lib/mavlink.js` (generated) and the JsDataflashParser submodule are not linted.
- Stylelint (`stylelint.config.js`: standard + recommended-vue) checks the component styles. Ids and classes may be camelCase or snake_case (scripts build names like `"pane" + name`); media queries keep `min-`/`max-` (the range syntax needs Safari 16.4); autoprefixer adds vendor prefixes, so don't write them.
- Ruff (`ruff.toml`) uses its default rules and formatter for the Python tooling; use f-strings.
- Vue 3: `:key` goes on the `<template v-for>` itself, not on the elements inside it. A component's template has one root element (a comment beside it makes a fragment in dev builds); `$el` is that element.
- Use `Number.isNaN(Number(x))` where the old code relied on the global `isNaN` coercing strings (for...in keys, preset color indices, expression values). Plain `Number.isNaN("abc")` is `false`.
