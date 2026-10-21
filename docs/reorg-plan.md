# Project reorganization — plan

Status: **complete** (2026-10-20).
Steps 1b–7 not started. See §10 for current-state checklist.

## 1. Why

Six problems, all visible in the tree:

1. `src/components/Globals.js` is a reactive store imported by almost
   everything. Its location claims it's a component.
2. `src/components/widgets/` mixes 7 widgets (call `useWidget()`),
   3 non-widgets (`CesiumSettingsWidget.vue`, `TreeMenu.vue`,
   `flightIndicators/AttitudeIndicator.vue`), and 2 infrastructure
   files (`useWidget.js`, `interpolator.js`).
3. `src/tools/` is a junk drawer: 8 utilities, 6 parser files, 2 extractor
   files, 1 worker in one folder.
4. `src/assets/` is flat: `.glb`, `.png`, `.jpg`, `.svg`, `.xml`, `.tlog`
   and a Python script (`parse_mavgraph.py`) in one directory.
5. `src/components/` root has feature clusters (4 `SideBar*`, 3 `Plotly*`,
   `CesiumViewer.vue`, `PlotSetup.vue`) next to genuinely shared files.
6. `CesiumViewer.vue` is 2800 lines (own TODO item, out of scope here).

## 2. Decisions locked

| Decision                         | Answer                                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Reorg shape                      | **Option A — feature slices.** Upstream rebase is not a concern.                                               |
| `ExpressionEditor.vue`           | → `features/plot/components/` (only `PlotSetup` uses it)                                                       |
| `SideBarMessageMenu.vue`         | → `features/sidebar/components/` (sidebar's message list, not the widget)                                      |
| `CesiumSettingsWidget.vue`       | → `features/scene/components/CesiumSettingsPanel.vue` (**renamed**)                                            |
| `interpolator.js`                | → `shared/lib/` (time-interpolation helper)                                                                    |
| `assets/`                        | **Split** into `models/`, `images/`, `xml/`, `samples/`                                                        |
| `parse_mavgraph.py`              | → `scripts/` (it's a dev tool; `scripts/` already exists with `terrain/`)                                      |
| `Home.vue`                       | → `app/Layout.vue` (**renamed**)                                                                               |
| `TreeMenu.vue`                   | → `shared/ui/`                                                                                                 |
| `useWidget.js` / `widget.css`    | Stay in `features/widgets/core/`                                                                               |
| `SideBarFileManager` file rename | **Deferred.** The move to `features/loader/components/` is step 4c; the file rename is a separate follow-up.   |
| Relative-import style            | **Enforced by ESLint in step 1b.** Cross-directory imports use `@/`; sibling imports (`./X.js`) stay relative. |

## 3. Target tree

```plain
src/
├── app/
│   ├── App.vue
│   ├── Layout.vue                         ← from components/Home.vue
│   ├── main.js
│   └── router/index.js
├── features/
│   ├── widgets/
│   │   ├── core/
│   │   │   ├── useWidget.js
│   │   │   ├── widget.css
│   │   │   └── registry.js                ← to be created (separate task)
│   │   └── instances/
│   │       ├── AttitudeWidget.vue
│   │       ├── DeviceIDViewer.vue
│   │       ├── EkfHelperTool.vue
│   │       ├── MagFitTool.vue
│   │       ├── MessageViewer.vue
│   │       ├── ParamViewer.vue
│   │       └── TxInputsViewer.vue
│   ├── scene/
│   │   ├── components/
│   │   │   ├── CesiumViewer.vue
│   │   │   └── CesiumSettingsPanel.vue    ← renamed
│   │   └── lib/
│   │       ├── boundingPolygon.js
│   │       ├── colorCoderMode.js
│   │       ├── colorCoderPlot.js
│   │       ├── colorCoderRange.js
│   │       └── vehicleVisibility.js
│   ├── plot/
│   │   ├── components/
│   │   │   ├── Plotly.vue
│   │   │   ├── PlotlyPopup.vue
│   │   │   ├── PlotSetup.vue
│   │   │   └── ExpressionEditor.vue
│   │   └── lib/
│   │       ├── plotCsv.js
│   │       └── plotTimeAxis.js
│   ├── loader/
│   │   ├── components/
│   │   │   ├── SideBarFileManager.vue
│   │   │   └── SideBarFileManagerProgressBar.vue
│   │   ├── parsers/
│   │   │   ├── mavlinkParser.js
│   │   │   ├── djiParser.js
│   │   │   ├── parser.worker.js
│   │   │   ├── workerMessages.js
│   │   │   ├── modeMaps.js
│   │   │   └── JsDataflashParser/         ← submodule
│   │   └── extractors/
│   │       ├── mavlinkDataExtractor.js
│   │       ├── dataflashDataExtractor.js
│   │       └── djiDataExtractor.js
│   └── sidebar/
│       └── components/
│           ├── Sidebar.vue
│           └── SideBarMessageMenu.vue
├── shared/
│   ├── stores/
│   │   └── index.js                       ← from components/Globals.js
│   ├── lib/
│   │   ├── cssColor.js
│   │   ├── datetools.js
│   │   ├── download.js
│   │   ├── eventHub.js
│   │   ├── flightTime.js
│   │   ├── interpolator.js
│   │   ├── mavlink.js                     ← from libs/mavlink.js
│   │   ├── paramseeker.js
│   │   └── mavextra/
│   │       ├── matrix3.js
│   │       ├── mavextra.js
│   │       ├── mymavextra.js
│   │       └── vector3.js
│   └── ui/
│       ├── AttitudeIndicator.vue          ← from widgets/flightIndicators/
│       ├── Collapse.vue
│       ├── Modal.vue
│       ├── TreeMenu.vue
│       ├── collapseToggle.js
│       └── img/                           ← from widgets/flightIndicators/img/
└── assets/
    ├── models/                            *.glb
    ├── images/                            *.png, *.jpg, *.svg
    ├── xml/                               *.xml, logmetadata/
    └── samples/                           *.tlog
```

## 4. Facts confirmed by `reorg-context.txt`

### `vite.config.js` — no changes at any step

- `viteStaticCopy` copies from `node_modules/cesium/...`, **not** from
  `src/assets/`. Step 6 (assets split) does not touch this file.
- `resolve.alias["@"]` is layout-agnostic.
- `assetsInclude` glob is layout-agnostic.
- `optimizeDeps.entries: ["index.html"]` — layout-agnostic.
- `worker: { format: "es" }` — the worker URL change (step 4c) is inside
  `SideBarFileManager.vue`, not here.

### `package.json` — no changes at any step

Every script is `dist`-relative or glob-based. `start`, `unit`, `e2e`,
`lint`, `lint:css` — none hardcode `src/...` paths.

### `index.html` — one change, step 5

```html
<!-- before -->
<script type="module" src="/src/main.js"></script>
<!-- after -->
<script type="module" src="/src/app/main.js"></script>
```

### `src/main.js` — internal imports that change per step

| Step | Import                              | Before                                 | After                                    |
| ---- | ----------------------------------- | -------------------------------------- | ---------------------------------------- |
| 1    | `@/shared/lib/eventHub.js`          | already correct (done in working tree) | —                                        |
| 2    | `./components/ui/collapseToggle.js` | relative                               | `@/shared/ui/collapseToggle.js`          |
| 3    | `./styles/widget.css`               | relative                               | `@/features/widgets/core/widget.css`     |
| 5    | `./App.vue`                         | relative                               | relative (both in `src/app/`, no change) |
| 5    | `./router`                          | relative                               | relative (both in `src/app/`, no change) |

### `AttitudeIndicator.vue` — five relative img imports, all `./img/*.svg`

Move `img/` alongside the `.vue` file (`shared/ui/img/`) → **no import
changes needed**.

### Worker reference — one line, step 4c

`src/components/SideBarFileManager.vue` line 59:

```js
new Worker(new URL("../tools/parsers/parser.worker.js", import.meta.url), ...)
```

After both files move:

- `SideBarFileManager.vue` → `features/loader/components/SideBarFileManager.vue`
- `parser.worker.js` → `features/loader/parsers/parser.worker.js`

New relative path from `components/` to `parsers/` is `../parsers/...`:

```js
new Worker(new URL("../parsers/parser.worker.js", import.meta.url), ...)
```

Must be in the same commit as step 4c. `npm run build` verifies it —
Vite resolves worker URLs at build time and fails loudly if missing.

### `JsDataflashParser/` — git submodule, 4 files

`index.html`, `LICENSE`, `parser.js`, `Readme.md`. The submodule's own
`index.html` loads `parser.js` as a worker — internal, no change needed
when the folder moves.

`git mv` alone will **not** update `.gitmodules`. Step 4c must edit
`.gitmodules` too:

```powershell
git mv src/tools/parsers/JsDataflashParser src/features/loader/parsers/JsDataflashParser
# edit .gitmodules: change "path = src/tools/parsers/JsDataflashParser"
#                   to     "path = src/features/loader/parsers/JsDataflashParser"
git add .gitmodules
```

Verify after: `git submodule status` and `rg -n "^path" .gitmodules`
must both show the new path.

### `scripts/` — exists, contains `terrain/` only

`scripts/terrain/` has `build_coarse.py`, `README.md`, `requirements.txt`,
`srtm_to_qmesh.py`. `parse_mavgraph.py` moves here in step 2.

### E2E runner — `test/e2e/runner.js`, no `nightwatch.conf.js`

E2E runs via `test/e2e/runner.js` (per `package.json`). `eslint.config.js`
still applies nightwatch globals to `test/e2e/*.js` via the `files:` block
— that's still valid, no config change.

## 5. Risk register — every hardcoded path

### `eslint.config.js`

| Line | Before                                   | After                                              | Step |
| ---- | ---------------------------------------- | -------------------------------------------------- | ---- |
| 21   | `"src/tools/parsers/JsDataflashParser/"` | `"src/features/loader/parsers/JsDataflashParser/"` | 4c   |
| 52   | comment `(see src/mavextra/)`            | `(see src/shared/lib/mavextra/)`                   | 1    |
| 53   | `"src/components/Plotly.vue"`            | `"src/features/plot/components/Plotly.vue"`        | 4b   |
| 58   | `"src/tools/parsers/**/*.js"`            | `"src/features/loader/parsers/**/*.js"`            | 4c   |

**Why narrowing the ignore:** `"src/libs/"` becomes `"src/shared/lib/mavlink.js"`
(step 1, already done). Replacing it with `"src/shared/lib/"` would also
ignore `eventHub.js`, `interpolator.js`, and `mavextra/` — files you want
linted.

### `index.html` — see §4

### `src/main.js` — see §4

### `src/components/SideBarFileManager.vue` worker URL — see §4

### `.gitmodules` — see §4

### Files with **no changes at any step**

| File                              | Why                                                                               |
| --------------------------------- | --------------------------------------------------------------------------------- |
| `vite.config.js`                  | `resolve.alias["@"]`, `assetsInclude`, `optimizeDeps.entries` — layout-agnostic   |
| `vitest.config.js`                | Merges `vite.config.js`; nothing hardcoded                                        |
| `stylelint.config.js`             | Globs `src/**/*.{vue,css,scss}`                                                   |
| `ruff.toml`                       | Globs; no hardcoded paths                                                         |
| `package.json` scripts            | `vite build`, `vite`, `serve -s dist`, `vitest run`, `eslint .` — layout-agnostic |
| `Containerfile.dev`, `Dockerfile` | `COPY src ./src` — layout-agnostic                                                |
| `test/e2e/*`                      | Uses `test/e2e/runner.js`, not source paths                                       |
| `.github/workflows/nodejs.yml`    | Runs npm scripts; no hardcoded source paths                                       |

## 6. Migration steps

Each step is **one commit**. Each has a hard verification gate before the
commit runs. Rollback is `git reset --hard HEAD~1`.

### Step 1 — `shared/lib/`

**Status: in progress** (moves done in working tree, uncommitted).

**Moves:**

- `src/eventHub.js` → `src/shared/lib/eventHub.js`
- `src/libs/mavlink.js` → `src/shared/lib/mavlink.js`
- `src/mavextra/*.js` → `src/shared/lib/mavextra/*.js`
- `src/components/widgets/interpolator.js` → `src/shared/lib/interpolator.js`

**Same-commit config updates:**

- `eslint.config.js` line 19: `"src/libs/"` → `"src/shared/lib/mavlink.js"`
- `eslint.config.js` line 52: comment `(see src/mavextra/)` → `(see src/shared/lib/mavextra/)`
- `CLAUDE.md` line 59, 72, 77: `src/libs/mavlink.js` / `src/mavextra/` / `src/libs/`
  → new paths (see Appendix A)

**Pre-check (fast — literal fragments, not `.*` regex):**

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/JsDataflashParser/**' -g '!**/coverage/**' "libs/mavlink|mavextra/|widgets/interpolator|shared/lib/eventHub" src/ test/unit/
```

**Verification gate:**

- `npm run lint` exits 0
- `npx vitest run test/unit/specs/helpers.spec.js` passes (this spec
  imports `interpolator` — proves the path is right)
- `npm run dev` serves; load a log; open Attitude widget; open TxInputs
  widget — both render
- `npm run build` completes
- `git status --short` shows only step-1-related files

### Step 1b — orphaned `src/tools/` leaf files + relative-import rule

**Why this step exists:** five files in `src/tools/` are neither extractors
(4c) nor plot helpers (4b) nor parsers (4c), and no other step moves them.
Also: add the lint rule that normalises the remaining `../` imports before
every later step starts chasing mixed relative and aliased imports.

**Moves:**

- `src/tools/cssColor.js` → `src/shared/lib/cssColor.js`
- `src/tools/datetools.js` → `src/shared/lib/datetools.js`
- `src/tools/download.js` → `src/shared/lib/download.js`
- `src/tools/flightTime.js` → `src/shared/lib/flightTime.js`
- `src/tools/paramseeker.js` → `src/shared/lib/paramseeker.js`

**Same-commit updates (moves):**

- `test/unit/specs/flightTime.spec.js`: two import paths (`flightTime.js`,
  `datetools.js`) → `@/shared/lib/...`
- `CLAUDE.md` line 62: `tools/flightTime.js` → `shared/lib/flightTime.js`
- Any remaining `../` imports pointing at the moved files — the lint rule
  below will catch them

**Same-commit work (relative-import rule):**

1. Install the plugin:

    ```powershell
    npm install -D eslint-plugin-no-relative-import-paths
    ```

2. Add to `eslint.config.js` — import at the top:

    ```js
    import noRelativeImportPaths from "eslint-plugin-no-relative-import-paths";
    ```

    …and a scoped block near the other Vue rules:

    ```js
    {
        files: ["src/**/*.{js,vue}"],
        plugins: { "no-relative-import-paths": noRelativeImportPaths },
        rules: {
            // Cross-directory imports use the @/ alias; sibling imports
            // (./Collapse.vue) stay relative. --fix rewrites the rest.
            // See the plugin README to confirm the option names.
            "no-relative-import-paths/no-relative-import-paths": [
                "error",
                { allowSameFolder: true, rootDir: "src", prefix: "@" },
            ],
        },
    }
    ```

    **Confirm option names against the plugin README before saving** — the
    plugin has changed its option shape across versions.

3. Run the autofix over `src/`:

    ```powershell
    npx eslint --fix src/
    ```

    Expect ~40–60 files changed, each a mechanical single-line rewrite
    (`../mavextra/vector3` → `@/shared/lib/mavextra/vector3`).

4. Review 3 samples to confirm the pattern; trust the rest.

**Verification gate:**

- `npm run lint` exits 0 (with the new rule active — this also proves no
  remaining `../` cross-directory imports slipped through)
- `npx vitest run test/unit/specs/flightTime.spec.js` passes
- `npm run build` completes (catches template-string or dynamic `import()`
  cases that `eslint --fix` may have missed)
- `npm run dev` serves; load a log; **every widget** opens; 3D view loads;
  a plot renders
- `git status --short` shows only step-1b-related files

### Step 2 — `shared/stores/` + `shared/ui/` + `parse_mavgraph.py`

**Moves:**

- `src/components/Globals.js` → `src/shared/stores/index.js`
- `src/components/ui/Collapse.vue` → `src/shared/ui/Collapse.vue`
- `src/components/ui/collapseToggle.js` → `src/shared/ui/collapseToggle.js`
- `src/components/ui/Modal.vue` → `src/shared/ui/Modal.vue`
- `src/components/widgets/TreeMenu.vue` → `src/shared/ui/TreeMenu.vue`
- `src/components/widgets/flightIndicators/AttitudeIndicator.vue` → `src/shared/ui/AttitudeIndicator.vue`
- `src/components/widgets/flightIndicators/img/` → `src/shared/ui/img/`
- `src/assets/parse_mavgraph.py` → `scripts/parse_mavgraph.py`

**Same-commit config updates:**

- `src/main.js`: `./components/ui/collapseToggle.js` → `@/shared/ui/collapseToggle.js`
- `CLAUDE.md` line 24: `src/assets/parse_mavgraph.py` → `scripts/parse_mavgraph.py`
- `CLAUDE.md` line 62: `components/Globals.js` → `shared/stores/index.js`

**Pre-check:**

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/coverage/**' "components/Globals|components/ui/|widgets/TreeMenu|widgets/flightIndicators|parse_mavgraph" src/ test/unit/ scripts/ CLAUDE.md
```

**Verification gate:**

- `npm run lint` exits 0
- `npx vitest run test/unit/specs/helpers.spec.js` passes (imports `Globals`)
- `npm run dev` serves; Attitude widget canvas renders; Cesium settings
  panel expands preset tree; any modal opens; store mutations still work
- `npm run build` completes

### Step 3 — `features/widgets/`

**Moves:**

- 7 widget `.vue` files → `src/features/widgets/instances/`
- `useWidget.js` → `src/features/widgets/core/useWidget.js`
- `src/styles/widget.css` → `src/features/widgets/core/widget.css`

**Same-commit config updates:**

- `src/main.js`: `import "./styles/widget.css"` → `import "@/features/widgets/core/widget.css"`
- `Home.vue` (still `Home.vue` at this point): update 7 widget import paths
- `CLAUDE.md` lines 64: `components/widgets/` → `features/widgets/instances/`;
  `widgets/useWidget.js` → `features/widgets/core/useWidget.js`

**Pre-check:**

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/coverage/**' "widgets/|widget.css" src/ test/unit/
```

**Verification gate:**

- `npm run lint` exits 0
- `npm run dev` serves; **open every widget** — shared shell, handles, scrollbars all work
- Browser console: `document.querySelectorAll('.uav-widget__content').length` matches open-widget count
- `npm run build` completes

### Step 4 — feature slices (four sub-commits)

#### Step 4a — `features/scene/`

**Moves:**

- `src/components/CesiumViewer.vue` → `src/features/scene/components/CesiumViewer.vue`
- `src/components/widgets/CesiumSettingsWidget.vue` → `src/features/scene/components/CesiumSettingsPanel.vue` (**rename inside file too**)
- `src/components/cesiumExtra/*.js` → `src/features/scene/lib/*.js`

**Same-commit edits:**

- Inside `CesiumSettingsPanel.vue`: `name: "CesiumSettingsWidget"` → `"CesiumSettingsPanel"`
- `Home.vue`: import path for `CesiumViewer`
- `CesiumViewer.vue`: import path for `CesiumSettingsPanel` (was `CesiumSettingsWidget`), tag rename
- `CLAUDE.md` line 64: `components/cesiumExtra/` → `features/scene/lib/`

**Pre-check:**

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/coverage/**' "CesiumViewer|CesiumSettingsWidget|cesiumExtra" src/ test/unit/
```

**Verification gate:**

- `npm run lint` exits 0
- `npm run dev` serves; 3D view loads, settings panel opens, presets expand
- `npm run build` completes

#### Step 4b — `features/plot/`

**Moves:**

- `src/components/Plotly.vue`, `PlotlyPopup.vue`, `PlotSetup.vue`, `ExpressionEditor.vue` → `src/features/plot/components/`
- `src/tools/plotCsv.js`, `src/tools/plotTimeAxis.js` → `src/features/plot/lib/`

**Same-commit config updates:**

- `eslint.config.js` line 53: `"src/components/Plotly.vue"` → `"src/features/plot/components/Plotly.vue"`
- `eslint.config.js` line 52 comment stays (updated in step 1)
- `Home.vue`: import paths
- `test/unit/specs/helpers.spec.js`: `ExpressionEditor.vue`, `Plotly.vue` paths
- `test/unit/specs/plotCsv.spec.js`: `plotCsv.js`, `plotTimeAxis.js` paths
- `test/unit/specs/plotTimeAxis.spec.js`: `plotTimeAxis.js` path
- `CLAUDE.md` line 64: `tools/plotTimeAxis.js` → `features/plot/lib/plotTimeAxis.js`

**Verification gate:**

- `npm run lint` exits 0 (critical — this proves the `code-eval` override still applies to the new Plotly path)
- `npx vitest run test/unit/specs/plotCsv.spec.js test/unit/specs/plotTimeAxis.spec.js` passes
- `npm run dev` serves; open a plot, add a curve, popup works, expression editor opens
- `npm run build` completes

#### Step 4c — `features/loader/`

**Moves:**

- `src/components/SideBarFileManager.vue` → `src/features/loader/components/SideBarFileManager.vue`
- `src/components/SideBarFileManagerProgressBar.vue` → `src/features/loader/components/`
- `src/tools/parsers/*` (5 JS files + submodule) → `src/features/loader/parsers/`
- `src/tools/{mavlink,dataflash,dji}DataExtractor.js` → `src/features/loader/extractors/`

**Same-commit config updates:**

- `eslint.config.js` line 21: `"src/tools/parsers/JsDataflashParser/"` → `"src/features/loader/parsers/JsDataflashParser/"`
- `eslint.config.js` line 58: `"src/tools/parsers/**/*.js"` → `"src/features/loader/parsers/**/*.js"`
- `.gitmodules`: submodule path
- `SideBarFileManager.vue` line 59: `"../tools/parsers/parser.worker.js"` → `"../parsers/parser.worker.js"`
- `Home.vue`: import paths
- `test/unit/specs/mavlinklogs.spec.js`, `dataflashlogs.spec.js`: extractor and parser paths
- `CLAUDE.md` lines 56, 57, 63: `components/SideBarFileManager.vue`,
  `tools/parsers/parser.worker.js`, `tools/*DataExtractor.js`

**Submodule-specific procedure:**

```powershell
git mv src/tools/parsers/JsDataflashParser src/features/loader/parsers/JsDataflashParser
# edit .gitmodules
git add .gitmodules
```

**Verification gate (all must pass):**

- `npm run lint` exits 0
- `npx vitest run test/unit/specs/mavlinklogs.spec.js test/unit/specs/dataflashlogs.spec.js` passes
- `npm run dev` serves; **load a real .bin log** through `SideBarFileManager` — the worker runs, the log parses
- `npm run build` completes (this is the worker URL verification)
- `git submodule status` shows `src/features/loader/parsers/JsDataflashParser`

#### Step 4d — `features/sidebar/`

**Moves:**

- `src/components/Sidebar.vue` → `src/features/sidebar/components/Sidebar.vue`
- `src/components/SideBarMessageMenu.vue` → `src/features/sidebar/components/`

**Same-commit config updates:**

- `Home.vue`: import paths

**Verification gate:**

- `npm run lint` exits 0
- `npm run dev` serves; sidebar opens, message menu filters, clicking a message navigates
- `npm run build` completes

### Step 5 — `app/`

**Moves:**

- `src/App.vue` → `src/app/App.vue`
- `src/main.js` → `src/app/main.js`
- `src/router/index.js` → `src/app/router/index.js`
- `src/components/Home.vue` → `src/app/Layout.vue` (**renamed**)

**Same-commit config updates:**

- `index.html`: `<script src="/src/app/main.js">`
- `App.vue`: `Home.vue` import → `Layout.vue` (new path)
- `router/index.js`: any `Home.vue` import → `Layout.vue`
- `CLAUDE.md` line 46: `<script src="/src/main.js">` → `<script src="/src/app/main.js">`
- `CLAUDE.md` line 63: `components/Home.vue#extractFlightData` → `app/Layout.vue#extractFlightData`
- `CLAUDE.md` line 64: `src/router/index.js` → `src/app/router/index.js`

**Pre-check:**

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '*.html' "Home\.vue|from ['\"].*App\.vue|src/main\.js" src/ index.html
```

**Verification gate:**

- `npm run lint` exits 0
- `npm run dev` serves; **entire app loads** (home page, log loader, 3D view, plot, all widgets)
- `npm run build` completes
- `npm start` serves the production build correctly on :8080

### Step 6 — `assets/` split

**Moves:**

- `src/assets/*.glb` → `src/assets/models/`
- `src/assets/*.{png,jpg,svg}` → `src/assets/images/`
- `src/assets/*.xml` + `src/assets/logmetadata/` → `src/assets/xml/`
- `src/assets/*.tlog` → `src/assets/samples/`

**Same-commit edits:** every reference in code. Find them:

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/coverage/**' "assets/" src/ test/unit/
```

Also update `CLAUDE.md`:

- line 49: `../assets/x.png` example → `../assets/images/x.png`
- line 72: `src/assets/mavgraphs*.xml`, `ekf*Graphs.xml` → `src/assets/xml/...`

**Verification gate:**

- `npm run lint` exits 0
- `npm run dev` serves; 3D models load, terrain renders, images show, sample log loads
- `npm run build` completes
- `npm start` serves correctly (check `dist/static/` has the models and images)

### Step 7 — post-reorg docs

Update `docs/widgets.md` and `TODO.md` (see Appendix A, "docs/widgets.md
and TODO.md"). Then update the top of this file.
<!-- markdownlint-disable MD046 -->

Replace:

    Status: **step 1 in progress** …

With:

    Status: **complete** (commits <first>..<last>)

Do this as a 4-space indented block, not a fenced one — nested fences break
renderers.
<!-- markdownlint-disable MD046 -->

## 7. Verification protocol

Run after each step before committing:

1. `npm run lint` — exit 0
2. `npx vitest run test/unit/specs/<spec>.spec.js` — the spec(s) that
   import the moved files, one per step (see each step's gate)
3. `npm run dev` — serves without build errors
4. Browser: exercise the feature that moved
5. `npm run build` — completes
6. `git status --short` — no stray files

After committing:

1. `git log --oneline -1` — commit landed
2. `git diff HEAD~1 --stat` — diff is exactly what was intended

## 8. Rollback

Any step fails or regresses:

```powershell
git reset --hard HEAD~1
```

Each step is one commit. Do not amend forward — reset, fix in the working
tree, recommit cleanly.

## 9. Out of scope

Not touched by this reorg:

- Splitting `CesiumViewer.vue` (2800 lines) — own session
- Widget registry in `Layout.vue` — own commit after reorg
- Debug `console.log` cleanup — done or tracked separately
- `SideBarFileManager` → `FileManager` file rename — separate follow-up
- Everything under "Phase 5", "Phase 6", "Improvements" in `TODO.md`

## 10. Current state

All steps 1–7 complete. See git log for the commit sequence.

## Appendix A — path reference inventory

Every path mentioned in a doc or config, mapped to the step that must
update it. The same-commit rule (§6, Appendix C) applies to these files
exactly as it does to `eslint.config.js`.

### `CLAUDE.md`

| Line | Current                                                                 | New                                                    | Step |
| ---- | ----------------------------------------------------------------------- | ------------------------------------------------------ | ---- |
| 24   | `src/assets/parse_mavgraph.py`                                          | `scripts/parse_mavgraph.py`                            | 2    |
| 46   | `src="/src/main.js"`                                                    | `src="/src/app/main.js"`                               | 5    |
| 49   | `../assets/x.png` (example)                                             | `../assets/images/x.png`                               | 6    |
| 56   | `components/SideBarFileManager.vue`                                     | `features/loader/components/SideBarFileManager.vue`    | 4c   |
| 56   | `parser.worker.js` (2×)                                                 | same name, new folder `features/loader/parsers/`       | 4c   |
| 57   | `tools/parsers/parser.worker.js`                                        | `features/loader/parsers/parser.worker.js`             | 4c   |
| 59   | `src/libs/mavlink.js`                                                   | `src/shared/lib/mavlink.js`                            | 1    |
| 62   | `components/Globals.js`                                                 | `shared/stores/index.js`                               | 2    |
| 62   | `tools/flightTime.js`                                                   | `shared/lib/flightTime.js`                             | 1b   |
| 63   | `components/Home.vue#extractFlightData`                                 | `app/Layout.vue#extractFlightData`                     | 5    |
| 63   | `tools/dataflashDataExtractor.js`                                       | `features/loader/extractors/dataflashDataExtractor.js` | 4c   |
| 63   | `mavlinkDataExtractor.js`, `djiDataExtractor.js`                        | same folder as above                                   | 4c   |
| 64   | `tools/plotTimeAxis.js`                                                 | `features/plot/lib/plotTimeAxis.js`                    | 4b   |
| 64   | `components/cesiumExtra/`                                               | `features/scene/lib/`                                  | 4a   |
| 64   | `components/widgets/`                                                   | `features/widgets/instances/`                          | 3    |
| 64   | `widgets/useWidget.js`                                                  | `features/widgets/core/useWidget.js`                   | 3    |
| 64   | `src/router/index.js`                                                   | `src/app/router/index.js`                              | 5    |
| 68   | `src/shared/lib/eventHub.js`                                            | no change (already correct after step 1)               | —    |
| 72   | `src/mavextra/mavextra.js`, `mymavextra.js`, `vector3.js`, `matrix3.js` | `src/shared/lib/mavextra/...`                          | 1    |
| 72   | `src/assets/mavgraphs*.xml`, `ekf*Graphs.xml`                           | `src/assets/xml/mavgraphs*.xml`, `ekf*Graphs.xml`      | 6    |
| 72   | `parse_mavgraph.py` (second mention)                                    | `scripts/parse_mavgraph.py`                            | 2    |
| 77   | `src/libs/` (generated)                                                 | `src/shared/lib/mavlink.js` (generated)                | 1    |

### `eslint.config.js` — step mapping

| Line | Current                                  | New                                                | Step |
| ---- | ---------------------------------------- | -------------------------------------------------- | ---- |
| 19   | `"src/libs/"`                            | `"src/shared/lib/mavlink.js"` (narrowed)           | 1    |
| 21   | `"src/tools/parsers/JsDataflashParser/"` | `"src/features/loader/parsers/JsDataflashParser/"` | 4c   |
| 52   | comment `(see src/mavextra/)`            | `(see src/shared/lib/mavextra/)`                   | 1    |
| 53   | `"src/components/Plotly.vue"`            | `"src/features/plot/components/Plotly.vue"`        | 4b   |
| 58   | `"src/tools/parsers/**/*.js"`            | `"src/features/loader/parsers/**/*.js"`            | 4c   |

### `test/unit/specs/*.js`

| Spec                    | Stale imports                                                                               | Step     |
| ----------------------- | ------------------------------------------------------------------------------------------- | -------- |
| `mavlinklogs.spec.js`   | `src/tools/mavlinkDataExtractor.js`, `src/tools/parsers/mavlinkParser.js`                   | 4c       |
| `dataflashlogs.spec.js` | `src/tools/dataflashDataExtractor.js`, `src/tools/parsers/JsDataflashParser/parser.js`      | 4c       |
| `helpers.spec.js`       | `Globals.js` (2), `widgets/interpolator.js` (1), `ExpressionEditor.vue` + `Plotly.vue` (4b) | 1, 2, 4b |
| `plotCsv.spec.js`       | `tools/plotCsv.js`, `tools/plotTimeAxis.js`                                                 | 4b       |
| `flightTime.spec.js`    | `tools/flightTime.js`, `tools/datetools.js`                                                 | 1b       |
| `plotTimeAxis.spec.js`  | `tools/plotTimeAxis.js`                                                                     | 4b       |

### `docs/widgets.md` and `TODO.md`

Post-reorg cleanup — step 7.

| File                                               | Fix                                                    |
| -------------------------------------------------- | ------------------------------------------------------ |
| `docs/widgets.md` — "adding a new widget" examples | Path examples updated to `features/widgets/instances/` |
| `docs/widgets.md` — "Pending 2 — split" section    | Mark done                                              |
| `TODO.md` — folder-split section                   | Mark done, update completed bullet paths               |
| `docs/reorg-plan.md` — top of file                 | `## Status: complete`                                  |

### Files that reference `src/` but need no change

| File                              | Why                                                                               |
| --------------------------------- | --------------------------------------------------------------------------------- |
| `vite.config.js`                  | `resolve.alias["@"]`, `assetsInclude`, `optimizeDeps.entries` — layout-agnostic   |
| `vitest.config.js`                | Merges `vite.config.js`; nothing hardcoded                                        |
| `stylelint.config.js`             | Globs `src/**/*.{vue,css,scss}`                                                   |
| `ruff.toml`                       | Globs; no hardcoded paths                                                         |
| `package.json` scripts            | `vite build`, `vite`, `serve -s dist`, `vitest run`, `eslint .` — layout-agnostic |
| `Containerfile.dev`, `Dockerfile` | `COPY src ./src` — layout-agnostic                                                |
| `test/e2e/*`                      | Uses `test/e2e/runner.js`, not source paths                                       |
| `.github/workflows/nodejs.yml`    | Runs npm scripts; no hardcoded source paths                                       |

## Appendix B — verification gates, condensed

For quick reference when running steps. Full content in §6.

| Step | rg pre-check (fast)                                                                              | Test                                           | Build             |
| ---- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------- | ----------------- |
| 1    | `libs/mavlink\|mavextra/\|widgets/interpolator\|shared/lib/eventHub`                             | `helpers.spec.js`                              | yes               |
| 1b   | `tools/(cssColor\|datetools\|download\|flightTime\|paramseeker)` + `eslint --fix src/`           | `flightTime.spec.js`                           | yes               |
| 2    | `components/Globals\|components/ui/\|widgets/TreeMenu\|widgets/flightIndicators\|parse_mavgraph` | `helpers.spec.js`                              | yes               |
| 3    | `widgets/\|widget.css`                                                                           | —                                              | yes               |
| 4a   | `CesiumViewer\|CesiumSettingsWidget\|cesiumExtra`                                                | —                                              | yes               |
| 4b   | `Plotly\|ExpressionEditor\|plotCsv\|plotTimeAxis`                                                | `plotCsv.spec.js`, `plotTimeAxis.spec.js`      | yes               |
| 4c   | `SideBarFileManager\|parsers/\|DataExtractor`                                                    | `mavlinklogs.spec.js`, `dataflashlogs.spec.js` | yes               |
| 4d   | `Sidebar\|SideBarMessageMenu`                                                                    | —                                              | yes               |
| 5    | `Home\.vue\|App\.vue\|src/main\.js`                                                              | —                                              | yes + `npm start` |
| 6    | `assets/`                                                                                        | —                                              | yes + `npm start` |

Every pre-check runs with:

```powershell
rg -n --max-filesize 200K -g '*.js' -g '*.vue' -g '!**/JsDataflashParser/**' -g '!**/coverage/**' "<pattern>" src/ test/unit/
```

## Appendix C — the same-commit rule, restated

For every step, the commit includes:

1. The `git mv` operations
2. Import updates in `src/`
3. Import updates in `test/unit/specs/`
4. `eslint.config.js` updates (§5)
5. `CLAUDE.md` path reference updates (Appendix A)
6. Any other config or doc update the step's grep pre-check catches

If any of 1–6 is deferred to a later commit, the intermediate commit is
broken — `npm run lint`, `npm run dev`, or `npm run build` fails on a tree
that `git bisect` will land on. The verification gate exists to catch
that, not to fix it after the fact.
