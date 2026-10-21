<template>
    <div id="wrapper">
        <div id="toolbar">
            <div class="infoPanel">
                <select
                    v-model="selectedColorCoder"
                    class="color-coding-select"
                    aria-label="Color coding"
                    @change="updateColor"
                >
                    <option
                        v-for="(value, key) in useableColorCoders"
                        :key="key"
                        :value="key"
                    >
                        {{ key }}
                    </option>
                </select>
                <table>
                    <thead class="visually-hidden">
                        <tr>
                            <th scope="col">Legend</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="mode in colorCodeLegend" :key="mode.name">
                            <td class="mode" :style="{ color: mode.color }">
                                {{ mode.name }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        <!-- opened by the gear on Cesium's toolbar; under the toolbar, on the right -->
        <CesiumSettingsPanel v-show="settingsOpen" class="settings-panel" />
        <div id="cesiumContainer"></div>
        <div v-show="scaleBarLabel" id="distanceLegend">
            <div class="distanceLegendLabel">{{ scaleBarLabel }}</div>
            <div
                class="distanceLegendBar"
                :style="{ width: scaleBarWidth + 'px' }"
            ></div>
        </div>
    </div>
</template>

<script>
import {
    Color,
    ProviderViewModel,
    UrlTemplateImageryProvider,
    Viewer,
    CesiumTerrainProvider,
    EllipsoidTerrainProvider,
    ImageryLayer,
    TileMapServiceImageryProvider,
    buildModuleUrl,
    PointPrimitiveCollection,
    Entity,
    ScreenSpaceEventHandler,
    ScreenSpaceEventType,
    knockout,
    Cartographic,
    sampleTerrainMostDetailed,
    HeadingPitchRange,
    JulianDate,
    ClockRange,
    Cartesian3,
    Cartesian2,
    SampledProperty,
    BoundingSphere,
    LabelStyle,
    SampledPositionProperty,
    Transforms,
    PolylineDashMaterialProperty,
    TimeInterval,
    TimeIntervalCollection,
    HeadingPitchRoll,
    Ellipsoid,
    EllipsoidGeodesic,
    Quaternion,
    defined,
    ColorBlendMode,
    NearFarScalar,
    SingleTileImageryProvider,
    Rectangle,
    GeometryInstance,
    PolylineGeometry,
    ColorGeometryInstanceAttribute,
    PolylineColorAppearance,
    Primitive,
    ShaderSource,
    ImageMaterialProperty,
    CallbackProperty,
} from "cesium";

import { DateTime } from "luxon";

import { keepRaw, store } from "@/shared/stores/index.js";
import { DataflashDataExtractor } from "@/tools/dataflashDataExtractor";
import { MavlinkDataExtractor } from "@/tools/mavlinkDataExtractor";
import { DjiDataExtractor } from "@/tools/djiDataExtractor";
import "cesium/Build/Cesium/Widgets/widgets.css";
import CesiumSettingsPanel from "./CesiumSettingsPanel.vue";
import homeIcon from "@/assets/home2.png";
import maptilerIcon from "@/assets/maptiler.png";
import statkartIcon from "@/assets/statkart.jpg";
import eniroIcon from "@/assets/eniro.png";
import openseamapIcon from "@/assets/openseamap.png";
import submarineModel from "@/assets/bluerovsimple.glb";
import quadPlusModel from "@/assets/quadp.glb";
import quadXModel from "@/assets/quadx.glb";
import boatModel from "@/assets/boat.glb";
import planeModel from "@/assets/plane.glb";
import ColorCoderMode from "@/features/scene/lib/colorCoderMode.js";
import ColorCoderRange from "@/features/scene/lib/colorCoderRange.js";
import ColorCoderPlot from "@/features/scene/lib/colorCoderPlot.js";
import { VehicleVisibility } from "@/features/scene/lib/vehicleVisibility.js";
import { logStartTime, zoneOfFlight } from "@/shared/lib/flightTime.js";

import {
    generateHull,
    smoothGrid,
    interpolateToGrid,
    expandPolygon,
    isPointInPolygon,
} from "@/features/scene/lib/boundingPolygon.js";

// Self-hosted terrain + non-ion imagery: no Cesium ion token required.
// Default imagery is keyless Esri World Imagery (reliable, no key / domain / rate limits).
const ESRI_WORLD_IMAGERY_URL =
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_CREDIT = "Imagery © Esri, Maxar, Earthstar Geographics";
// Self-hosted ArduPilot SRTM quantized-mesh terrain (scripts/terrain), always from the app's own
// origin: plot.ardupilot.org serves its tileset there, the dev server proxies to it, and a Docker
// container serves a mounted one (works offline). Never plot.ardupilot.org directly: deployed
// there it is the same server, and anywhere else it would make production serve every copy.
const TERRAIN_URL = "/quantized/";
// Terrain detail level that counts as real terrain data at a location (level 10 tiles are
// ~20 km wide). Regional tilesets only have coarse levels outside their area.
const MIN_TERRAIN_LEVEL = 10;
const MAPTILER_SATELLITE_URL =
    "https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key=o3JREHNnXex8WSPPm2BU";

const colorCoderMode = new ColorCoderMode(store);
const colorCoderRange = new ColorCoderRange(store);

function getMinTime(data) {
    // returns the minimum time in the array. Used to define the time range
    return data.reduce((min, p) => Math.min(p[3], min), data[0][3]);
}

function getMaxTime(data) {
    // returns the maximum time in   the array. Used to define the time range
    return data.reduce((max, p) => Math.max(p[3], max), data[0][3]);
}

// Fence descriptor: circular fences (single point + radius) become closed cylinders,
// polygon fences walls (a closed vertical tube). Exclusion fences are tagged by the
// extractor; everything else is treated as an inclusion fence.
function fenceItem(fence) {
    const exclusion = fence.exclusion === true;
    if (fence.length === 1) {
        const pos = fence[0];
        if (pos[2] === 0) {
            return null;
        }
        return {
            type: "circle",
            center: Cartographic.fromDegrees(pos[0], pos[1]),
            radius: pos[2],
            exclusion,
        };
    }
    if (fence.length === 0) {
        return null;
    }
    const ring = fence.map((pos) => Cartographic.fromDegrees(pos[0], pos[1]));
    // close the polygon
    ring.push(Cartographic.fromDegrees(fence[0][0], fence[0][1]));
    return { type: "polygon", ring, exclusion };
}

const fencePoints = (f) => (f.type === "circle" ? [f.center] : f.ring);

function fenceCylinder(f, groundPoint, fenceAltMax, color) {
    const ground = groundPoint.height || 0;
    return {
        position: Cartesian3.fromRadians(
            groundPoint.longitude,
            groundPoint.latitude,
            ground + fenceAltMax / 2,
        ),
        cylinder: {
            length: fenceAltMax,
            topRadius: f.radius,
            bottomRadius: f.radius,
            material: color.withAlpha(0.3),
        },
    };
}

function fenceWall(groundPoints, fenceAltMax, color) {
    const positions = [];
    const minimumHeights = [];
    const maximumHeights = [];
    for (const sp of groundPoints) {
        const ground = sp.height || 0;
        minimumHeights.push(ground);
        maximumHeights.push(ground + fenceAltMax);
        positions.push(
            Cartesian3.fromRadians(
                sp.longitude,
                sp.latitude,
                ground + fenceAltMax,
            ),
        );
    }
    return {
        wall: {
            positions,
            minimumHeights,
            maximumHeights,
            material: color.withAlpha(0.3),
            outline: false,
        },
    };
}

export default {
    name: "CesiumViewer",
    components: {
        CesiumSettingsPanel,
    },

    data() {
        return {
            state: store,
            startTimeMs: 0,
            lastEmitted: 0,
            colorCoder: null,
            selectedColorCoder: "Mode",
            scaleBarLabel: "",
            scaleBarWidth: 0,
            // the 3D clock shows local time at the flight, not where the camera happens to be
            flightTimeZone: null,
            settingsOpen: false,
        };
    },
    computed: {
        availableColorCoders() {
            const coders = {
                Mode: colorCoderMode,
                range: colorCoderRange,
            };
            for (const key in this.state.plotCache) {
                coders[key] = new ColorCoderPlot(store, key);
            }
            return coders;
        },
        useableColorCoders() {
            // check if requiredMessages for each color coder are present
            // iterates on key:value pais of this.availableColorCoders and filters them
            // based on the requiredMessages property
            const colorCoders = {};
            for (const [key, value] of Object.entries(
                this.availableColorCoders,
            )) {
                if (
                    value.requiredMessages.every((m) =>
                        Object.keys(this.state.messageTypes).includes(m),
                    )
                ) {
                    colorCoders[key] = value;
                }
            }
            return colorCoders;
        },

        colorCodeLegend() {
            return this.colorCoder?.getLegend() ?? [];
        },
        setOfModes() {
            const set = [];
            for (const mode of this.state.flightModeChanges) {
                if (!set.includes(mode[1])) {
                    set.push(mode[1]);
                }
            }
            return set;
        },
        timeRange() {
            if (this.state.timeRange !== null) {
                return this.state.timeRange;
            }
            return undefined;
        },
        modelScale() {
            // The settings field is free text: ignore values that are not positive numbers
            const value = Number.parseFloat(this.state.modelScale);
            const scale = Number.isNaN(value) || value <= 0 ? 1 : value;
            // bluerovsimple.glb is small, so it is scaled up here (https://github.com/igoutta/UAVLogViewer/issues/1)
            return this.state.vehicle === "submarine" ? scale * 6.86 : scale;
        },
        heightOffset() {
            return Number.parseFloat(this.state.heightOffset);
        },
        cameraType() {
            return this.state.cameraType;
        },
        showTrajectory() {
            return this.state.showTrajectory;
        },
        showClickableTrajectory() {
            return this.state.showClickableTrajectory;
        },
        showWaypoints() {
            return this.state.showWaypoints;
        },
        showFences() {
            return this.state.showFences;
        },
        trajectorySource() {
            return this.state.trajectorySource;
        },
        comparisonTrajectories() {
            return this.state.comparisonTrajectories;
        },
        attitudeSource() {
            return this.state.attitudeSource;
        },
        radioMode() {
            return this.state.radioMode;
        },
    },
    watch: {
        // The model scale is read through CallbackProperty; just redraw (requestRenderMode)
        modelScale() {
            this.viewer.scene.requestRender();
        },
        heightOffset(offset) {
            const value = Number.parseFloat(offset);
            if (!Number.isNaN(value)) {
                this.updateAndPlotTrajectory();
                this.processTrajectory();
                this.addModel();
                this.plotComparisonTrajectories();
                this.viewer.scene.requestRender();
            }
        },
        colorCoder() {
            this.updateAndPlotTrajectory();
            this.processTrajectory();
            this.viewer.scene.requestRender();
        },
        timeRange(range) {
            try {
                if (range[1] > range[0]) {
                    const cesiumStart = this.msToCesiumTime(
                        range[0],
                    ).secondsOfDay;
                    const plotlyStart =
                        this.viewer.timeline._startJulian.secondsOfDay;
                    const cesiumEnd = this.msToCesiumTime(
                        range[1],
                    ).secondsOfDay;
                    const plotlyEnd =
                        this.viewer.timeline._endJulian.secondsOfDay;
                    // If range has changed more than 1 second
                    if (
                        Math.abs(cesiumStart - plotlyStart) > 1 ||
                        Math.abs(cesiumEnd - plotlyEnd) > 1
                    ) {
                        this.viewer.timeline.zoomTo(
                            this.msToCesiumTime(range[0]),
                            this.msToCesiumTime(range[1]),
                        );
                    }
                }
            } catch (e) {
                console.log(e);
            }
        },
        cameraType() {
            this.changeCamera();
        },
        showTrajectory() {
            this.updateAndPlotTrajectory();
            this.plotComparisonTrajectories();
        },
        showClickableTrajectory() {
            this.updateVisibility();
        },
        showWaypoints() {
            this.updateVisibility();
        },
        "state.fences"() {
            // Fences are extracted asynchronously and may be populated after this
            // component has already run its initial setup (timing differs per browser),
            // so re-plot whenever the fence list changes.
            if (this.viewer != null) {
                this.plotFences(this.state.fences);
            }
        },
        trajectorySource() {
            this.loadTrajectory(this.state.trajectorySource);
        },
        comparisonTrajectories: {
            handler() {
                this.plotComparisonTrajectories();
            },
            deep: true,
        },
        attitudeSource() {
            this.loadAttitude(this.state.attitudeSource);
        },
    },
    created() {
        this.updateShader();
        // The objects declared here are not watched by Vue
        this.viewer = null; // Cesium viewer instance
        this.model = null; // Vehicle model
        this.vehicleVisibility = null; // lighting and outline of the vehicle
        this.hasLogTime = false;
        this.waypoints = null; // Autopilot Waypoints
        this.trajectory = null; // GPS trajectory (in degrees)
        this.fences = []; // Geo-fence entities
        this.correctedTrajectory = []; // GPS trajectory (Cartographic array)
        this.globeOpacityInterval = null;
        this.tornDown = false; // set when the component is destroyed (async setup checks it)

        // Link time with plot updates
        this.$eventHub.$on("hoveredTime", this.showAttitude);
        // This fires up the loading spinner
        this.state.mapLoading = true;
        this.state.mapError = null;
    },
    beforeUnmount() {
        // asyncSetup/setup2 may still be waiting for terrain or tiles: let them stop
        this.tornDown = true;
        // they return early without clearing the loading spinner
        this.state.mapLoading = false;
        // remove only this component's listeners (plots and widgets listen to hoveredTime too)
        this.$eventHub.$off("hoveredTime", this.showAttitude);
        document.removeEventListener("setzoom", this.onTimelineZoom);
        clearInterval(this.globeOpacityInterval);
        // free the WebGL context (browsers only allow a few at a time)
        if (this.viewer && !this.viewer.isDestroyed()) {
            this.vehicleVisibility?.destroy();
            this.viewer.destroy();
        }
        this.viewer = null;
    },
    mounted() {
        // create eniro, statkart, and openseamap providers
        this.asyncSetup();
    },
    methods: {
        async tryTerrainProvider(url) {
            try {
                return await CesiumTerrainProvider.fromUrl(url);
            } catch (e) {
                console.warn(`quantized terrain unavailable at ${url}:`, e);
                return null;
            }
        },
        async loadTerrainProvider() {
            const terrain = await this.tryTerrainProvider(TERRAIN_URL);
            if (terrain) {
                return terrain;
            }
            // Fall back to the ellipsoid so the 3D view still works.
            console.warn("no quantized terrain available, using ellipsoid");
            return new EllipsoidTerrainProvider();
        },
        async asyncSetup() {
            try {
                if (this.viewer == null) {
                    this.viewer = this.createViewer(this.state.isOnline);
                    if (this.state.vehicle !== "boat") {
                        const terrainProvider =
                            await this.loadTerrainProvider();
                        if (this.tornDown) {
                            return;
                        }
                        this.viewer.terrainProvider = terrainProvider;
                    }
                    // Cesium's frame time counter: for working on the 3D view, not for users
                    this.viewer.scene.debugShowFramesPerSecond =
                        import.meta.env.DEV;

                    this.viewer.scene.postProcessStages.ambientOcclusion.enabled = false;
                    this.viewer.scene.postProcessStages.bloom.enabled = false;
                    this.clickableTrajectory = this.viewer.scene.primitives.add(
                        new PointPrimitiveCollection(),
                    );
                    this.trajectory = this.viewer.entities.add(new Entity());
                    this.trajectoryUpdateTimeout = null;
                    this.viewer.scene.globe.enableLighting = true;
                    this.vehicleVisibility = new VehicleVisibility(
                        this.viewer,
                        () => this.model,
                    );
                    this.viewer.scene.postRender.addEventListener(
                        this.onFrameUpdate,
                    );
                    this.viewer.camera.moveEnd.addEventListener(
                        this.updateScaleBar,
                    );
                    this.viewer.scene.morphComplete.addEventListener(() => {
                        this.viewer.zoomTo(this.viewer.entities);
                    });
                    this.viewer.animation.viewModel.setShuttleRingTicks([
                        0.1, 0.25, 0.5, 0.75, 1, 2, 5, 10, 15,
                    ]);
                    this.viewer.scene.globe.depthTestAgainstTerrain = true;
                    this.viewer.shadowMap.maximumDistance = 10000;
                    this.viewer.shadowMap.softShadows = true;
                    this.viewer.shadowMap.size = 4096;
                    this.viewer.animation.viewModel.timeFormatter = (date) => {
                        const isoString = JulianDate.toIso8601(date);
                        let dateTime = DateTime.fromISO(isoString);
                        // local time where the flight is (see flightTimeZone); a zone newer
                        // than the browser's time zone data would give an invalid date: keep
                        // the browser's own zone then
                        const zoned = this.flightTimeZone
                            ? dateTime.setZone(this.flightTimeZone)
                            : dateTime;
                        if (zoned.isValid) {
                            dateTime = zoned;
                        }
                        const offset =
                            dateTime.offsetNameShort || dateTime.offsetNameLong;
                        return `${dateTime.toLocaleString(
                            DateTime.TIME_SIMPLE,
                        )} (${offset})`;
                    };
                    // Attach hover handler
                    const handler = new ScreenSpaceEventHandler(
                        this.viewer.scene.canvas,
                    );
                    handler.setInputAction(
                        this.onMove,
                        ScreenSpaceEventType.MOUSE_MOVE,
                    );
                    handler.setInputAction(
                        this.onLeftDown,
                        ScreenSpaceEventType.LEFT_DOWN,
                    );
                    handler.setInputAction(
                        this.onClick,
                        ScreenSpaceEventType.LEFT_CLICK,
                    );
                    handler.setInputAction(
                        this.onLeftUp,
                        ScreenSpaceEventType.LEFT_UP,
                    );
                    // Saving the camera in the URL is off until it can be restored (https://github.com/igoutta/UAVLogViewer/issues/2)
                    // this.viewer.camera.moveEnd.addEventListener(this.onCameraUpdate)

                    knockout
                        .getObservable(
                            this.viewer.clockViewModel,
                            "shouldAnimate",
                        )
                        .subscribe(this.onAnimationChange);
                    const layers = this.viewer.scene.imageryLayers;
                    const xofs = 0.00001;
                    const options = {
                        url: homeIcon,
                        tileWidth: 1920,
                        tileHeight: 1080,
                        rectangle: Rectangle.fromDegrees(
                            -48.530077110530044 + xofs,
                            -27.490619277419633,
                            -48.52971476731231 + xofs,
                            -27.49044182943895,
                        ),
                        credit: "potato",
                    };
                    console.log(options);
                    layers.addImageryProvider(
                        new SingleTileImageryProvider(options),
                    );
                    this.viewer.scene.globe.translucency.frontFaceAlphaByDistance =
                        new NearFarScalar(50, 0.4, 150, 1);
                    this.viewer.scene.globe.translucency.enabled = true;
                    this.viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;
                    this.viewer.scene.globe.undergroundColor =
                        Color.MIDNIGHTBLUE;
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.near = 2;
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.far = 10;
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.nearValue = 0.2;
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.farValue = 1;
                }
                this.addToolbarButtons();

                for (const pos of this.state.currentTrajectory) {
                    this.correctedTrajectory.push(
                        Cartographic.fromDegrees(pos[0], pos[1], pos[2]),
                    );
                }

                this.terrainSampled = false;
                if (
                    this.state.vehicle !== "boat" &&
                    this.viewer.terrainProvider.availability &&
                    this.correctedTrajectory.length > 0
                ) {
                    const promise = sampleTerrainMostDetailed(
                        this.viewer.terrainProvider,
                        this.correctedTrajectory,
                    );
                    promise
                        .then(async (result) => {
                            this.terrainSampled = true;
                            await this.setup2(result);
                        })
                        .catch(() => this.setup2(this.correctedTrajectory));
                } else {
                    this.setup2(this.correctedTrajectory);
                }
            } catch (e) {
                console.error("Error in Cesium asyncSetup:", e);
                this.state.mapLoading = false;
                this.state.mapError =
                    "Failed to initialize 3D map: " +
                    (e.message || "Unknown error");
            }
        },
        updateShader() {
            ShaderSource._czmBuiltinsAndUniforms.czm_translateRelativeToEye =
                ShaderSource._czmBuiltinsAndUniforms.czm_translateRelativeToEye.replace(
                    "low - czm_encodedCameraPositionMCLow;",
                    "(low - czm_encodedCameraPositionMCLow) * (1.0 + czm_epsilon7);",
                );
        },
        async updateColor() {
            const newCoder = this.availableColorCoders[this.selectedColorCoder];
            await this.waitForMessages(newCoder.requiredMessages);
            this.colorCoder = keepRaw(newCoder);
        },
        createViewer(online) {
            if (online) {
                console.log("creating online viewer");
                const imageryProviders = this.createAdditionalProviders();
                return new Viewer("cesiumContainer", {
                    homeButton: false,
                    geocoder: false,
                    timeline: true,
                    animation: true,
                    requestRenderMode: true,
                    shouldAnimate: false,
                    scene3DOnly: false,
                    selectionIndicator: false,
                    shadows: true,
                    // No ion: custom keyless imagery list, and an empty terrain list so
                    // the base layer picker can't fall back to ion's Cesium World Terrain.
                    imageryProviderViewModels: imageryProviders,
                    selectedImageryProviderViewModel: this.esriProvider,
                    terrainProviderViewModels: [],
                    orderIndependentTranslucency: false,
                    useBrowserRecommendedResolution: false,
                });
            }
            console.log("creating offline viewer");
            return new Viewer("cesiumContainer", {
                homeButton: false,
                timeline: true,
                animation: true,
                requestRenderMode: true,
                shouldAnimate: false,
                scene3DOnly: false,
                selectionIndicator: false,
                shadows: true,
                orderIndependentTranslucency: false,
                baseLayerPicker: false,
                // low-resolution world imagery bundled with Cesium (dist/Assets), no network
                baseLayer: ImageryLayer.fromProviderAsync(
                    TileMapServiceImageryProvider.fromUrl(
                        buildModuleUrl("Assets/Textures/NaturalEarthII"),
                    ),
                ),
                geocoder: false,
                useBrowserRecommendedResolution: false,
            });
        },

        createAdditionalProviders() {
            // Base layer picker options. All keyless / non-ion. Esri satellite is the
            // default (this.esriProvider); StatKart, MapTiler, Eniro and OpenSeaMap follow.
            this.esriProvider = new ProviderViewModel({
                name: "Satellite (Esri)",
                iconUrl: maptilerIcon,
                tooltip: "Esri World Imagery (satellite)",
                creationFunction: function () {
                    return new UrlTemplateImageryProvider({
                        url: ESRI_WORLD_IMAGERY_URL,
                        // Esri World Imagery has near-global coverage to z18; z19+ is spotty
                        // (returns "Map data not yet available" tiles in rural areas). Cap at 18
                        // so Cesium upsamples instead of showing those placeholders.
                        maximumLevel: 18,
                        credit: ESRI_CREDIT,
                    });
                },
            });
            return [
                this.esriProvider,
                new ProviderViewModel({
                    name: "StatKart",
                    iconUrl: statkartIcon,
                    tooltip:
                        "Kartverket topographic map \nhttps://www.kartverket.no/",
                    creationFunction: function () {
                        return new UrlTemplateImageryProvider({
                            // opencache.statkart.no was shut down; this is Kartverket's replacement
                            url: "https://cache.kartverket.no/v1/wmts/1.0.0/topo/default/webmercator/{z}/{y}/{x}.png",
                            credit: "Map tiles by Kartverket.",
                        });
                    },
                }),
                new ProviderViewModel({
                    name: "MapTiler",
                    iconUrl: maptilerIcon,
                    tooltip: "Maptiler satellite imagery http://maptiler.com/",
                    creationFunction: function () {
                        return new UrlTemplateImageryProvider({
                            url: MAPTILER_SATELLITE_URL,
                            minimumLevel: 0,
                            maximumLevel: 20,
                            credit: "https://www.maptiler.com/copyright",
                        });
                    },
                }),
                new ProviderViewModel({
                    name: "Eniro",
                    iconUrl: eniroIcon,
                    tooltip: "Eniro aerial imagery \nhttp://map.eniro.com/",
                    creationFunction: function () {
                        return new UrlTemplateImageryProvider({
                            url: "/eniro/{z}/{x}/{reverseY}.png",
                            credit: "Map tiles by Eniro.",
                        });
                    },
                }),
                new ProviderViewModel({
                    name: "OpenSeaMap",
                    iconUrl: openseamapIcon,
                    tooltip:
                        "OpenSeaMap Nautical Maps \nhttp://openseamap.org/",
                    parameters: {
                        transparent: "true",
                        format: "image/png",
                    },
                    creationFunction: function () {
                        return [
                            new UrlTemplateImageryProvider({
                                url: "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
                                credit: "Map tiles by OpenStreetMap.",
                            }),
                            new UrlTemplateImageryProvider({
                                url: "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
                                credit: "Map tiles by OpenSeaMap.",
                            }),
                        ];
                    },
                }),
            ];
        },
        // Resolve once the globe has no tiles left to load (or after timeoutMs, so a slow
        // or failing tile server never blocks the UI). Never rejects.
        waitForCesiumReady(timeoutMs = 10000) {
            const scene = this.viewer.scene;
            const globe = scene.globe;
            return new Promise((resolve) => {
                if (globe.tilesLoaded) {
                    resolve();
                    return;
                }
                let removeListener = null;
                const timer = setTimeout(() => {
                    console.warn(
                        "Cesium tiles still loading after timeout, continuing",
                    );
                    removeListener?.();
                    resolve();
                }, timeoutMs);
                // tileLoadProgressEvent reports the tile load queue length; 0 means done
                removeListener = globe.tileLoadProgressEvent.addEventListener(
                    (queued) => {
                        if (queued === 0 && globe.tilesLoaded) {
                            clearTimeout(timer);
                            removeListener();
                            resolve();
                        }
                    },
                );
                scene.requestRender();
            });
        },
        // Most detailed terrain level available at a position, -1 when there is no terrain tile
        terrainLevelAt(cartographic) {
            const availability = this.viewer.terrainProvider.availability;
            return availability === undefined
                ? -1
                : availability.computeMaximumLevelAtPosition(cartographic);
        },
        async setup2(updatedPositions) {
            if (this.tornDown) {
                return;
            }
            try {
                /*
                 * Second step of setup, happens after the height of the starting point has been returned by Cesium
                 * */
                if (!updatedPositions || updatedPositions.length === 0) {
                    throw new Error(
                        "No GPS trajectory available in this log file.",
                    );
                }
                // Terrain height sampled per trajectory point (same order as the points);
                // processTrajectory uses it to clamp the rendered track to the ground.
                this.terrainHeights = updatedPositions.map((p) => p.height);
                this.state.trajectorySource = this.state.trajectorySources[0];
                this.loadTrajectory(this.state.trajectorySource);
                // Trajectory altitude is absolute AMSL (orthometric); our self-hosted terrain is
                // raw SRTM (also orthometric), so Cesium renders both with the same geoid offset
                // and the vehicle sits at the right height above the visible ground. No terrain
                // offset is added. (This would be wrong against ellipsoidal terrain, e.g. ion.)
                this.state.heightOffset = 0;
                const takeoffLevel = this.terrainLevelAt(
                    this.correctedTrajectory[0],
                );
                if (takeoffLevel < MIN_TERRAIN_LEVEL) {
                    // No terrain data here (offline without a tileset, or outside its area): the
                    // ground is the flat globe or a coarse level, so absolute heights would float.
                    // Put the takeoff on the visible ground instead (adjustable in the settings).
                    // Without any terrain tile the sampler leaves the height unchanged, so the
                    // visible ground is the ellipsoid (0).
                    const ground =
                        this.terrainSampled && takeoffLevel >= 0
                            ? updatedPositions[0].height
                            : 0;
                    // to the centimetre: the settings field shows it
                    this.state.heightOffset =
                        Math.round(
                            (ground - this.state.currentTrajectory[0][2]) * 100,
                        ) / 100;
                    this.terrainHeights = null;
                }
                this.processTrajectory(this.state.currentTrajectory);
                this.addModel();
                this.updateAndPlotTrajectory();
                this.plotComparisonTrajectories();
                await this.plotMission(this.state.mission);
                if (this.tornDown) {
                    return;
                }
                this.plotFences(this.state.fences);
                document.addEventListener("setzoom", this.onTimelineZoom);

                try {
                    await this.waitForCesiumReady();
                } catch (e) {
                    console.warn(
                        "Cesium loading timeout, continuing anyway",
                        e,
                    );
                } finally {
                    this.state.mapLoading = false;
                }
                if (this.tornDown) {
                    return;
                }
                // Default to a framed top-down view of the flight (not vehicle-follow, which
                // frames a point and ends up too wide to find the flight). Follow is available
                // via the centre-vehicle button.
                this.state.cameraType = "free";
                this.changeCamera();
                setTimeout(this.updateTimelineColors, 500);
                this.globeOpacityInterval = setInterval(
                    this.updateGlobeOpacity,
                    1000,
                );
                setTimeout(() => {
                    this.fitTrajectoryBounds();
                }, 1000);
            } catch (e) {
                console.error("Error in Cesium setup2:", e);
                this.state.mapLoading = false;
                this.state.mapError =
                    e.message || "Unknown error during map processing";
            }
        },
        async waitForMessages(messages) {
            for (const message of messages) {
                this.$eventHub.$emit("loadType", message);
            }
            let interval;
            let counter = 0;
            return new Promise((resolve, reject) => {
                interval = setInterval(() => {
                    for (const message of messages) {
                        if (!this.state.messages[message]) {
                            counter += 1;
                            if (counter > 30) {
                                // 30 * 300ms = 9 s timeout
                                console.log("not resolving");
                                clearInterval(interval);
                                reject(
                                    new Error(
                                        `Could not load messageType ${message}`,
                                    ),
                                );
                            }
                            return;
                        }
                    }
                    clearInterval(interval);
                    console.log("resolved for " + messages);
                    resolve();
                }, 300);
            });
        },
        updateGlobeOpacity() {
            if (!this.viewer) {
                return;
            }
            /*
            Makes the Globe transparent when the vehicle is underground/underwater. Called every 1 second
            */
            if (!this.viewer.clock.currentTime) {
                console.log("no time");
                return;
            }
            const cartesian = this.model.position.getValue(
                this.viewer.clock.currentTime,
            );
            if (!cartesian) {
                return;
            }
            const position = Cartographic.fromCartesian(cartesian);
            const height = position.height;

            const update = function (updatedPositions) {
                const altitude = height - updatedPositions[0].height;
                const globe = this.viewer.scene.globe;
                if (altitude < 0) {
                    globe.showGroundAtmosphere = true;
                    globe.translucency.enabled = true;
                } else {
                    globe.translucency.enabled = false;
                }
            }.bind(this);

            if (this.state.vehicle === "boat") {
                update([position]);
                console.log("skipping sample");
            } else {
                const promise = sampleTerrainMostDetailed(
                    this.viewer.terrainProvider,
                    [position],
                );
                promise.then(update).catch(() => {});
            }
        },
        // A button on Cesium's toolbar (top right), styled like Cesium's own; icon is its HTML
        addToolbarButton({ id, title, icon, onClick, className = "" }) {
            const toolbar = this.viewer.container.querySelector(
                ".cesium-viewer-toolbar",
            );
            const wrapper = document.createElement("span");
            wrapper.classList.add("cesium-navigationHelpButton-wrapper");
            const button = document.createElement("button");
            button.type = "button";
            button.id = id;
            button.className =
                `cesium-button cesium-toolbar-button ${className}`.trim();
            button.title = title;
            button.innerHTML = icon;
            button.addEventListener("click", onClick);
            wrapper.append(button);
            toolbar.append(wrapper);
        },
        addToolbarButtons() {
            const fontAwesome = (name) =>
                `<i class="fa-solid fa-${name}" style="font-style: unset;"></i>`;
            this.addToolbarButton({
                id: "cesium-bathymetry-button",
                title: "Toggle Bathymetry",
                icon: fontAwesome("ship"),
                onClick: () => {
                    this.plotBathymetry()
                        .catch((e) =>
                            console.warn(
                                "Could not plot bathymetry:",
                                e.message,
                            ),
                        )
                        .finally(() => this.viewer.scene.requestRender());
                },
            });
            this.addToolbarButton({
                id: "cesium-center-vehicle-button",
                title: "Center vehicle",
                icon: fontAwesome("car"),
                onClick: () => {
                    this.$nextTick(() => {
                        this.state.cameraType = "follow";
                        this.changeCamera();
                    });
                },
            });
            this.addToolbarButton({
                id: "cesium-fit-button",
                title: "Re-center view",
                icon: fontAwesome("expand"),
                onClick: () => {
                    this.$nextTick(() => {
                        this.state.cameraType = "free";
                        this.changeCamera();
                        this.fitTrajectoryBounds();
                    });
                },
            });
            this.addToolbarButton({
                id: "cesium-settings-button",
                title: "3D view settings",
                icon: fontAwesome("gear"),
                onClick: () => {
                    this.settingsOpen = !this.settingsOpen;
                },
            });
            this.addToolbarButton({
                id: "cesium-close-button",
                title: "Close 3D view",
                className: "cesium-close-button",
                icon:
                    '<svg viewbox="0 0 40 40">' +
                    '<path class="close-x" d="M 10,10 L 30,30 M 30,10 L 10,30" />' +
                    "</svg>",
                onClick: () => {
                    this.state.showMap = false;
                },
            });
        },
        onCameraUpdate() {
            const query = { ...this.$route.query };
            const cam = this.viewer.camera;
            query.cam = [
                cam.position.x.toFixed(2),
                cam.position.y.toFixed(2),
                cam.position.z.toFixed(2),
                cam.direction.x.toFixed(2),
                cam.direction.y.toFixed(2),
                cam.direction.z.toFixed(2),
                cam.up.x.toFixed(2),
                cam.up.y.toFixed(2),
                cam.up.z.toFixed(2),
                this.cameraType,
            ].join(",");
            this.$router.push({ query });
        },

        // the real sun needs the log's absolute time and the flight's position
        applyLighting() {
            this.vehicleVisibility?.setRealLighting(
                this.hasLogTime && this.flightTimeZone !== null,
            );
        },

        // the absolute time at the first trajectory point (startTimeMs)
        getTimeStart() {
            const start = new Date(
                logStartTime(this.state.metadata) + this.startTimeMs,
            );
            this.hasLogTime = !Number.isNaN(start.getTime());
            if (!this.hasLogTime) {
                // no absolute time in the log: an arbitrary fixed date
                return JulianDate.fromDate(new Date(2015, 2, 25, 16));
            }
            return JulianDate.fromDate(start);
        },

        mouseIsOnPoint(point) {
            // Checks if there is a trajectory point under the coordinate "point"
            const pickedObjects = this.viewer.scene.drillPick(point);
            if (!defined(pickedObjects)) return false;

            for (const entity of pickedObjects) {
                const time = entity.id?.time;
                if (time !== undefined && time !== null) {
                    this.lastHoveredTime = time;
                    return true;
                }
            }
            return false;
        },
        changeCamera() {
            if (
                this.cameraType === "follow" &&
                this.viewer.trackedEntity !== this.model
            ) {
                this.viewer.trackedEntity = this.model;
            } else {
                this.viewer.trackedEntity = undefined;
            }
        },
        fitTrajectoryBounds() {
            if (!this.viewer) {
                return;
            }
            // Frame the flight so it fills ~2/3 of the view, never zooming tighter than a ~100 m
            // view (so a hover/stationary flight stays visible). Use a 3D bounding sphere of the
            // actual track positions so the view accounts for terrain elevation (framing a 2D
            // rectangle puts the camera at ellipsoid height 0 and ends up below high terrain).
            if (!this.points || this.points.length === 0) {
                this.viewer.flyTo(this.viewer.entities);
                return;
            }
            const cartesians = [];
            for (const p of this.points) {
                if (
                    Number.isFinite(p[0]) &&
                    Number.isFinite(p[1]) &&
                    Number.isFinite(p[2])
                ) {
                    cartesians.push(Cartesian3.fromDegrees(p[0], p[1], p[2]));
                }
            }
            if (cartesians.length === 0) {
                return;
            }
            const sphere = BoundingSphere.fromPoints(cartesians);
            // x1.5 -> flight fills ~2/3 of the view; floor radius 50 m -> view never under ~100 m
            sphere.radius = Math.max(sphere.radius * 1.5, 50);
            this.viewer.camera.flyToBoundingSphere(sphere, { duration: 1.5 });
        },
        updateScaleBar() {
            // Traditional map scale bar (bottom-right): measure the ground distance spanned by
            // one pixel at the bottom-centre of the view and pick a round value for the bar.
            if (!this.viewer) {
                return;
            }
            const scene = this.viewer.scene;
            const width = scene.canvas.clientWidth;
            const height = scene.canvas.clientHeight;
            const globe = scene.globe;
            const left = scene.camera.getPickRay(
                new Cartesian2(Math.trunc(width / 2), height - 1),
            );
            const right = scene.camera.getPickRay(
                new Cartesian2(1 + Math.trunc(width / 2), height - 1),
            );
            const leftPos = left && globe.pick(left, scene);
            const rightPos = right && globe.pick(right, scene);
            if (!defined(leftPos) || !defined(rightPos)) {
                this.scaleBarLabel = "";
                return;
            }
            const lc = globe.ellipsoid.cartesianToCartographic(leftPos);
            const rc = globe.ellipsoid.cartesianToCartographic(rightPos);
            this._geodesic = this._geodesic || new EllipsoidGeodesic();
            this._geodesic.setEndPoints(lc, rc);
            const pixelDistance = this._geodesic.surfaceDistance;
            if (!Number.isFinite(pixelDistance) || pixelDistance <= 0) {
                this.scaleBarLabel = "";
                return;
            }
            const steps = [
                1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300, 500, 1000, 2000,
                3000, 5000, 10000, 20000, 30000, 50000, 100000, 200000, 300000,
                500000, 1000000, 2000000, 5000000,
            ];
            const maxBarPx = 120;
            let distance;
            for (let i = steps.length - 1; i >= 0; i--) {
                if (steps[i] / pixelDistance < maxBarPx) {
                    distance = steps[i];
                    break;
                }
            }
            if (distance === undefined) {
                this.scaleBarLabel = "";
                return;
            }
            this.scaleBarWidth = Math.round(distance / pixelDistance);
            this.scaleBarLabel =
                distance >= 1000 ? distance / 1000 + " km" : distance + " m";
        },
        onAnimationChange(isAnimating) {
            this.$eventHub.$emit("animation-changed", isAnimating);
        },
        // onRangeChanged (event) {
        //     this.viewer.timeline.zoomTo(this.msToCesiumTime(event[0]), this.msToCesiumTime(event[1]))
        // },
        updateTimelineColors() {
            if (!this.viewer) {
                return;
            }
            const start = this.cesiumTimeToMs(
                this.viewer.timeline._startJulian,
            );
            const end = this.cesiumTimeToMs(this.viewer.timeline._endJulian);

            const timeline = this.viewer.container.querySelector(
                ".cesium-timeline-bar",
            );
            let colors = [];
            let previousColor = null;
            for (const change of this.state.flightModeChanges) {
                if (change[0] < start || previousColor === null) {
                    previousColor = this.getModeColor(change[0]);
                    colors = [[0, previousColor]];
                }
                if (change[0] > start && change[0] < end) {
                    const percentage =
                        ((change[0] - start) * 100) / (end - start);
                    colors.push(
                        [percentage - 0.001, previousColor],
                        [percentage, this.getModeColor(change[0])],
                    );
                    previousColor = this.getModeColor(change[0]);
                }
            }
            colors.push([100, previousColor]);

            let string = "linear-gradient(to right";
            if (colors.length > 1) {
                for (const change of colors) {
                    string =
                        string +
                        ", rgba(" +
                        change[1].red * 150 +
                        "," +
                        change[1].green * 150 +
                        "," +
                        change[1].blue * 150 +
                        ", 100) " +
                        change[0] +
                        "%";
                }

                string = string + ")";
                timeline.style.background = string;
            }
        },
        onTimelineZoom(event) {
            this.timelineStart = event.startJulian;
            this.timelineStop = event.endJulian;

            const start = this.cesiumTimeToMs(event.startJulian);
            const end = this.cesiumTimeToMs(event.endJulian);
            this.state.timeRange = [start, end];
            this.updateTimelineColors();

            if (this.trajectoryUpdateTimeout !== null) {
                clearTimeout(this.trajectoryUpdateTimeout);
            }
            setTimeout(this.updateAndPlotTrajectory, 500);
        },

        onLeftDown(movement) {
            if (this.mouseIsOnPoint(movement.position)) {
                this.isDragging = true;
                this.viewer.scene.screenSpaceCameraController.enableInputs = false;
            }
        },

        onLeftUp() {
            this.isDragging = false;
            this.viewer.container.style.cursor = "default";
            this.viewer.scene.screenSpaceCameraController.enableInputs = true;
        },

        onClick(movement) {
            if (this.mouseIsOnPoint(movement.position)) {
                this.$eventHub.$emit(
                    "cesium-time-changed",
                    this.lastHoveredTime,
                );
                this.viewer.clock.currentTime = JulianDate.addSeconds(
                    this.getTimeStart(),
                    (this.lastHoveredTime - this.startTimeMs) / 1000,
                    new JulianDate(),
                );
            }
            this.onLeftUp();
        },

        onMove(movement) {
            if (this.showClickableTrajectory) {
                if (this.isDragging) {
                    if (this.mouseIsOnPoint(movement.endPosition)) {
                        this.$eventHub.$emit(
                            "cesium-time-changed",
                            this.lastHoveredTime,
                        );
                        this.viewer.clock.currentTime = JulianDate.addSeconds(
                            this.getTimeStart(),
                            (this.lastHoveredTime - this.startTimeMs) / 1000,
                            new JulianDate(),
                        );
                    }
                } else if (this.mouseIsOnPoint(movement.endPosition)) {
                    this.viewer.container.style.cursor = "pointer";
                } else {
                    this.viewer.container.style.cursor = "default";
                }
            }
        },

        onFrameUpdate() {
            // emits in "boot_time_ms" units.
            let current = this.viewer.clock.currentTime.secondsOfDay;
            current =
                current > this.viewer.clock.startTime.secondsOfDay
                    ? current
                    : current + 86400;
            const newFrameTime =
                (current - this.viewer.clock.startTime.secondsOfDay) * 1000 +
                this.startTimeMs;
            if (newFrameTime === this.lastEmitted) {
                // False alarm.
                return;
            }
            this.lastEmitted = newFrameTime;
            this.$eventHub.$emit("cesium-time-changed", newFrameTime);
            if (
                this.viewer.clock.currentTime < this.timelineStart ||
                this.viewer.clock.currentTime > this.timelineStop
            ) {
                this.viewer.clock.currentTime = this.timelineStart.clone();
            }
        },

        cesiumTimeToMs(time) {
            let result = time.secondsOfDay - this.start.secondsOfDay;
            if (result < 0) {
                result += 86400;
            }
            return this.startTimeMs + result * 1000;
        },

        msToCesiumTime(ms) {
            return JulianDate.addSeconds(
                this.start,
                (ms - this.startTimeMs) / 1000,
                new JulianDate(),
            );
        },

        showAttitude(time) {
            this.viewer.scene.requestRender();
            this.viewer.clock.currentTime = this.msToCesiumTime(time);
        },

        processTrajectory() {
            this.correctedTrajectory = [];
            this.points =
                this.state.trajectories[this.state.trajectorySource].trajectory;
            // Clamp the rendered track to the terrain surface so it never disappears below the
            // opaque ground (pre-GPS-lock samples whose AMSL is under the local terrain). Terrain
            // heights were sampled per point in setup2; points above terrain keep their true AMSL.
            // Done here (not just setup2) because loadTrajectory re-extracts points asynchronously.
            // Submarines operate below the surface, so their true track is legitimately under the
            // terrain/water datum; clamping would flatten the whole dive onto the ground.
            if (
                this.state.vehicle !== "submarine" &&
                this.terrainHeights &&
                this.terrainHeights.length === this.points.length
            ) {
                for (let i = 0; i < this.points.length; i++) {
                    if (this.terrainHeights[i] > this.points[i][2]) {
                        this.points[i][2] = this.terrainHeights[i];
                    }
                }
            }
            for (const pos of this.points) {
                this.correctedTrajectory.push(
                    Cartographic.fromDegrees(pos[0], pos[1], pos[2]),
                );
            }
            this.flightTimeZone = zoneOfFlight(this.points);
            // process time_boot_ms into cesium time
            this.startTimeMs = getMinTime(this.points);
            const timespan = getMaxTime(this.points) - this.startTimeMs;
            this.state.timeRange = [
                this.startTimeMs,
                this.startTimeMs + timespan,
            ];
            const viewer = this.viewer;
            this.start = this.getTimeStart();
            this.applyLighting();
            this.stop = JulianDate.addSeconds(
                this.start,
                Math.round(timespan / 1000),
                new JulianDate(),
            );
            // Make sure viewer is at the desired time.
            viewer.clock.startTime = this.start.clone();
            this.timelineStart = this.start;
            this.timelineStop = this.stop;
            viewer.clock.stopTime = this.stop.clone();
            viewer.clock.clockRange = ClockRange.LOOP_STOP;
            viewer.clock.multiplier = 1;
            // Set timeline to simulation bounds
            viewer.timeline.zoomTo(this.start, this.stop);
            let position;
            this.positions = [];
            this.sampledPos = new SampledPositionProperty();

            // clean entities
            if (this.clickableTrajectory !== null) {
                this.clickableTrajectory.removeAll();
            }
            // Create sampled position
            const isBoat = this.state.vehicle === "boat";
            for (const posIndex in this.points) {
                const pos = this.points[posIndex];
                if (isBoat) {
                    position = Cartesian3.fromDegrees(pos[0], pos[1], 0);
                } else {
                    position = Cartesian3.fromDegrees(
                        pos[0],
                        pos[1],
                        pos[2] + this.heightOffset,
                    );
                }
                this.positions.push(position);
                const time = JulianDate.addSeconds(
                    this.start,
                    (pos[3] - this.startTimeMs) / 1000,
                    new JulianDate(),
                );

                this.sampledPos.addSample(time, position);
                // this.clickableTrajectory.add({
                //     position: position,
                //     pixelSize: 10,
                //     show: false,
                //     color: this.getModeColor(pos[3]),
                //     id: {time: pos[3]}
                // })
                if (this.model !== null) {
                    this.model.position = this.sampledPos;
                }
            }
        },
        // =========================================================================
        // 1. DATA PREPARATION
        // =========================================================================
        aggregateDepth(bathymetry, positions) {
            const positionsWithDepth = [];
            let lastIndex = 0;
            for (let i = 0; i < positions.time_boot_ms.length; i++) {
                while (
                    lastIndex < bathymetry.time_boot_ms.length - 1 &&
                    bathymetry.time_boot_ms[lastIndex] <
                        positions.time_boot_ms[i]
                ) {
                    lastIndex++;
                }
                if (
                    bathymetry.time_boot_ms[lastIndex] >=
                    positions.time_boot_ms[i]
                ) {
                    positionsWithDepth.push({
                        latitude: positions.Lat[i] * 1e-7,
                        longitude: positions.Lng[i] * 1e-7,
                        depth: bathymetry.Dist[lastIndex],
                    });
                }
            }
            return positionsWithDepth;
        },
        filterOutliers(pointsWithDepth) {
            const depths = pointsWithDepth
                .map((p) => p.depth)
                .filter((d) => d > 0.1);
            if (depths.length === 0) return [];
            const mean = depths.reduce((a, b) => a + b, 0) / depths.length;
            const stdDev = Math.sqrt(
                depths.reduce((a, b) => a + Math.pow(b - mean, 2), 0) /
                    depths.length,
            );
            return pointsWithDepth.filter(
                (p) =>
                    p.depth > 0.1 &&
                    Math.abs(p.depth - mean) < 2.5 * stdDev &&
                    p.latitude !== 0 &&
                    p.longitude !== 0,
            );
        },
        normalizeToGridSpace(points) {
            const minLat = Math.min(...points.map((p) => p.latitude));
            const maxLat = Math.max(...points.map((p) => p.latitude));
            const minLng = Math.min(...points.map((p) => p.longitude));
            const maxLng = Math.max(...points.map((p) => p.longitude));
            return points.map((p) => ({
                x: ((p.longitude - minLng) / (maxLng - minLng)) * 1000,
                y: ((p.latitude - minLat) / (maxLat - minLat)) * 1000,
                depth: p.depth,
            }));
        },
        // =========================================================================
        // 2. GRID, HULL, AND DEPTH RANGE
        // =========================================================================

        prepareGridAndHull(points, gridSize = 200, margin = 50) {
            const hull = generateHull(points);
            const expandedHull = expandPolygon(hull, margin);
            let grid = interpolateToGrid(points, gridSize);
            grid = smoothGrid(grid, 1);
            return { grid, expandedHull };
        },
        getDepthRange(grid) {
            let min = Infinity;
            let max = -Infinity;
            grid.forEach((row) =>
                row.forEach((d) => {
                    if (d !== null) {
                        min = Math.min(min, d);
                        max = Math.max(max, d);
                    }
                }),
            );
            return { min, max };
        },
        // =========================================================================
        // 3. COLOR CONVERSION AND PIXEL MANIPULATION
        // =========================================================================
        getDepthColor(depth, minDepth, maxDepth) {
            const norm = (depth - minDepth) / (maxDepth - minDepth);
            return {
                r: Math.floor(100 * (1 - norm)),
                g: Math.floor(149 * (1 - norm)),
                b: Math.floor(237 * (1 - norm * 0.5)),
            };
        },
        setPixel(imageData, width, x, y, r, g, b, a = 255) {
            const idx = (y * width + x) * 4;
            imageData.data[idx] = r;
            imageData.data[idx + 1] = g;
            imageData.data[idx + 2] = b;
            imageData.data[idx + 3] = a;
        },
        fillCellPixels(
            imageData,
            width,
            height,
            cellX,
            cellY,
            cellW,
            cellH,
            color,
            expandedHull,
        ) {
            for (let dx = 0; dx <= cellW; dx++) {
                for (let dy = 0; dy <= cellH; dy++) {
                    const px = cellX + dx;
                    const py = cellY + dy;
                    const inside = isPointInPolygon(
                        (px / width) * 1000,
                        (py / height) * 1000,
                        expandedHull,
                    );
                    if (inside) {
                        this.setPixel(
                            imageData,
                            width,
                            px,
                            py,
                            color.r,
                            color.g,
                            color.b,
                            255,
                        );
                    } else {
                        this.setPixel(imageData, width, px, py, 0, 0, 0, 0);
                    }
                }
            }
        },
        fillColoredPixels(
            ctx,
            width,
            height,
            grid,
            cellW,
            cellH,
            expandedHull,
            depthMin,
            depthMax,
        ) {
            const imageData = ctx.getImageData(0, 0, width, height);
            for (let i = 0; i < grid.length; i++) {
                for (let j = 0; j < grid[0].length; j++) {
                    const depth = grid[i][j];
                    if (depth === null) continue;
                    const color = this.getDepthColor(depth, depthMin, depthMax);
                    const cellX = Math.floor(i * cellW);
                    const cellY = Math.floor(j * cellH);
                    this.fillCellPixels(
                        imageData,
                        width,
                        height,
                        cellX,
                        cellY,
                        cellW,
                        cellH,
                        color,
                        expandedHull,
                    );
                }
            }
            ctx.putImageData(imageData, 0, 0);
        },
        // =========================================================================
        // 4. CONTOUR LINES
        // =========================================================================
        crossesThreshold(a, b, threshold) {
            return (
                (a < threshold && b >= threshold) ||
                (a >= threshold && b < threshold)
            );
        },
        drawContoursForLevel(ctx, grid, cellW, cellH, threshold) {
            for (let i = 0; i < grid.length - 1; i++) {
                for (let j = 0; j < grid[0].length - 1; j++) {
                    const cell = [
                        grid[i][j],
                        grid[i + 1][j],
                        grid[i + 1][j + 1],
                        grid[i][j + 1],
                    ];
                    if (cell.includes(null)) continue;
                    const x = i * cellW;
                    const y = j * cellH;
                    // neighbours along x cross the level: vertical segment between them
                    if (this.crossesThreshold(cell[0], cell[1], threshold)) {
                        ctx.moveTo(x + cellW, y);
                        ctx.lineTo(x + cellW, y + cellH);
                    }
                    // neighbours along y cross the level: horizontal segment between them
                    if (this.crossesThreshold(cell[0], cell[3], threshold)) {
                        ctx.moveTo(x, y + cellH);
                        ctx.lineTo(x + cellW, y + cellH);
                    }
                }
            }
        },
        drawContourLines(
            ctx,
            width,
            height,
            grid,
            cellW,
            cellH,
            depthMin,
            depthMax,
            contourLevels = 10,
        ) {
            ctx.save();
            ctx.strokeStyle = "rgba(0,0,0,0.2)";
            ctx.lineWidth = 0.5;
            for (let level = 0; level < contourLevels; level++) {
                const threshold =
                    depthMin + (depthMax - depthMin) * (level / contourLevels);
                ctx.beginPath();
                this.drawContoursForLevel(ctx, grid, cellW, cellH, threshold);
                ctx.stroke();
            }
            ctx.restore();
        },
        // =========================================================================
        // 5. HULL OUTLINE
        // =========================================================================
        drawHullOutline(ctx, width, height, expandedHull) {
            ctx.beginPath();
            expandedHull.forEach((p, i) => {
                const x = (p.x / 1000) * width;
                const y = (p.y / 1000) * height;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.closePath();
            ctx.strokeStyle = "rgba(0,0,0,0.5)";
            ctx.lineWidth = 2;
            ctx.stroke();
        },
        // =========================================================================
        // 6. MAIN DRAW FUNCTION (orchestrator)
        // =========================================================================
        drawBathymetryCanvas(
            normalizedPoints,
            gridSize = 200,
            margin = 50,
            contourLevels = 10,
        ) {
            const { grid, expandedHull } = this.prepareGridAndHull(
                normalizedPoints,
                gridSize,
                margin,
            );
            const { min: depthMin, max: depthMax } = this.getDepthRange(grid);

            const width = 512;
            const height = 512;
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            const cellW = width / gridSize;
            const cellH = height / gridSize;

            this.fillColoredPixels(
                ctx,
                width,
                height,
                grid,
                cellW,
                cellH,
                expandedHull,
                depthMin,
                depthMax,
            );

            // Clip to hull for contour drawing
            ctx.save();
            ctx.beginPath();
            expandedHull.forEach((p, i) => {
                const x = (p.x / 1000) * width;
                const y = (p.y / 1000) * height;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.closePath();
            ctx.clip();
            this.drawContourLines(
                ctx,
                width,
                height,
                grid,
                cellW,
                cellH,
                depthMin,
                depthMax,
                contourLevels,
            );
            ctx.restore();

            this.drawHullOutline(ctx, width, height, expandedHull);

            return canvas;
        },
        // =========================================================================
        // 7. MAIN PLOT FUNCTION
        // =========================================================================
        waitForBathymetryMessages(timeoutMs = 9000) {
            for (const message of ["RFND", "POS"]) {
                this.$eventHub.$emit("loadType", message);
            }
            const ready = () =>
                (this.state.messages.RFND || this.state.messages["RFND[0]"]) &&
                this.state.messages.POS;
            const deadline = Date.now() + timeoutMs;
            return new Promise((resolve, reject) => {
                const check = () => {
                    if (ready()) {
                        resolve();
                    } else if (Date.now() > deadline) {
                        reject(
                            new Error("Bathymetry needs RFND and POS messages"),
                        );
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            });
        },
        async plotBathymetry() {
            await this.waitForBathymetryMessages();
            const bath =
                this.state.messages.RFND || this.state.messages["RFND[0]"];
            let points = this.aggregateDepth(bath, this.state.messages.POS);
            points = this.filterOutliers(points);
            if (points.length === 0) return;

            const normalized = this.normalizeToGridSpace(points);
            const canvas = this.drawBathymetryCanvas(normalized);
            const rectangle = Rectangle.fromCartographicArray(
                points.map((p) =>
                    Cartographic.fromDegrees(p.longitude, p.latitude),
                ),
            );

            this.viewer.entities.add({
                rectangle: {
                    coordinates: rectangle,
                    material: new ImageMaterialProperty({
                        image: canvas,
                        transparent: true,
                        repeat: new Cartesian2(1, -1),
                        offset: new Cartesian2(0, 1),
                    }),
                    outline: true,
                    outlineColor: Color.BLACK,
                },
            });
            this.viewer.scene.requestRender();
        },
        // =========================================================================
        // 1. SAMPLED POSITION PROPERTY
        // =========================================================================
        buildSampledPositionProperty() {
            const sampled = new SampledPositionProperty();
            const isBoat = this.state.vehicle === "boat";
            for (const pos of this.points) {
                const position = isBoat
                    ? Cartesian3.fromDegrees(pos[0], pos[1], 0)
                    : Cartesian3.fromDegrees(
                          pos[0],
                          pos[1],
                          pos[2] + this.heightOffset,
                      );
                const time = JulianDate.addSeconds(
                    this.start,
                    (pos[3] - this.startTimeMs) / 1000,
                    new JulianDate(),
                );
                sampled.addSample(time, position);
            }
            return sampled;
        },
        // =========================================================================
        // 2. ORIENTATION FROM QUATERNIONS (timeAttitudeQ)
        // =========================================================================
        quaternionToHeadingPitchRoll(q1, q2, q3, q4) {
            const roll = Math.atan2(
                2 * (q1 * q2 + q3 * q4),
                1 - 2 * (q2 * q2 + q3 * q3),
            );
            let pitch = Math.asin(2 * (q1 * q3 - q4 * q2));
            if (Number.isNaN(pitch)) pitch = 0;
            const yaw = Math.atan2(
                2 * (q1 * q4 + q2 * q3),
                1 - 2 * (q3 * q3 + q4 * q4),
            );
            // Signs and roll offset are ad hoc for the models' axes (https://github.com/igoutta/UAVLogViewer/issues/3)
            return new HeadingPitchRoll(-yaw, -pitch, roll - Math.PI);
        },
        addQuaternionSample(sampled, timeMs, positionAtTime) {
            const att = this.state.timeAttitudeQ[timeMs];
            if (!att) return;
            const [q1, q2, q3, q4] = att;
            const hpRoll = this.quaternionToHeadingPitchRoll(q1, q2, q3, q4);
            const quat = Transforms.headingPitchRollQuaternion(
                positionAtTime,
                hpRoll,
                Ellipsoid.WGS84,
                Transforms.localFrameToFixedFrameGenerator("north", "east"),
            );
            const time = JulianDate.addSeconds(
                this.start,
                (timeMs - this.startTimeMs) / 1000,
                new JulianDate(),
            );
            sampled.addSample(time, quat);
        },
        // =========================================================================
        // 3. ORIENTATION FROM EULER ANGLES (timeAttitude)
        // =========================================================================
        eulerToHeadingPitchRoll(roll, pitch, yaw) {
            // The angles are in radians (roll, pitch, yaw)
            return new HeadingPitchRoll(yaw, pitch, roll);
        },
        addEulerSample(sampled, timeMs, positionAtTime) {
            const att = this.state.timeAttitude[timeMs];
            if (!att) return;
            const [roll, pitch, yaw] = att;
            const hpRoll = this.eulerToHeadingPitchRoll(roll, pitch, yaw);
            const quat = Transforms.headingPitchRollQuaternion(
                positionAtTime,
                hpRoll,
                Ellipsoid.WGS84,
                Transforms.localFrameToFixedFrameGenerator("north", "west"),
            );
            const time = JulianDate.addSeconds(
                this.start,
                (timeMs - this.startTimeMs) / 1000,
                new JulianDate(),
            );
            sampled.addSample(time, quat);
        },
        // =========================================================================
        // 4. SAMPLED ORIENTATION PROPERTY (picks the attitude source)
        // =========================================================================
        buildSampledOrientationProperty() {
            const sampled = new SampledProperty(Quaternion);
            const hasQuat = Object.keys(this.state.timeAttitudeQ).length > 0;
            const dataSource = hasQuat
                ? this.state.timeAttitudeQ
                : this.state.timeAttitude;
            if (Object.keys(dataSource).length === 0) return sampled;

            // Each sample needs a reference position; outside the GPS time range the
            // nearest end of the trajectory is used
            const firstPoint = this.points[0];
            const lastPoint = this.points.at(-1);
            const toCartesian = (p) =>
                Cartesian3.fromDegrees(
                    p[0],
                    p[1],
                    this.state.vehicle === "boat"
                        ? 0
                        : p[2] + this.heightOffset,
                );
            const firstPosition = toCartesian(firstPoint);
            const lastPosition = toCartesian(lastPoint);
            for (const timeMs in dataSource) {
                const time = JulianDate.addSeconds(
                    this.start,
                    (timeMs - this.startTimeMs) / 1000,
                    new JulianDate(),
                );
                const positionAtTime =
                    this.sampledPos.getValue(time) ||
                    (Number(timeMs) < firstPoint[3]
                        ? firstPosition
                        : lastPosition);
                if (hasQuat) {
                    this.addQuaternionSample(sampled, timeMs, positionAtTime);
                } else {
                    this.addEulerSample(sampled, timeMs, positionAtTime);
                }
            }
            return sampled;
        },
        // =========================================================================
        // 5. MODEL ENTITY
        // =========================================================================
        createModelEntity(positionProp, orientationProp) {
            return this.viewer.entities.add({
                availability: new TimeIntervalCollection([
                    new TimeInterval({
                        start: this.start,
                        stop: this.stop,
                    }),
                ]),
                position: positionProp,
                orientation: orientationProp,
                model: {
                    uri: this.getVehicleModel(),
                    minimumPixelSize: 15,
                    scale: new CallbackProperty(
                        () => this.modelScale / 10,
                        false,
                    ),
                },
                viewFrom: new Cartesian3(5, 0, 3),
            });
        },
        // =========================================================================
        // 6. addModel
        // =========================================================================
        async addModel() {
            if (this.model) {
                this.viewer.entities.remove(this.model);
            }
            this.sampledPos = this.buildSampledPositionProperty();
            const sampledOrientation = this.buildSampledOrientationProperty();
            // Reused by the comparison-trajectory vehicles (position differs, orientation shared).
            this.sampledOrientation = sampledOrientation;
            this.model = this.createModelEntity(
                this.sampledPos,
                sampledOrientation,
            );
            this.changeCamera();

            if (this.state.vehicle === "boat") {
                setTimeout(() => {
                    this.viewer
                        .flyTo(this.model, {
                            offset: new HeadingPitchRange(0, -0.5, 100),
                        })
                        .then(() => this.changeCamera());
                }, 3000);
            }
        },
        // =========================================================================
        // 1. TRAJECTORY POINTS WITHIN THE TIME RANGE
        // =========================================================================

        getPointsInTimeRange(startTimeMs, endTimeMs) {
            const isBoat = this.state.vehicle === "boat";
            const pointsInRange = [];
            for (const pos of this.points) {
                if (pos[3] >= startTimeMs && pos[3] <= endTimeMs) {
                    pointsInRange.push({
                        position: Cartesian3.fromDegrees(
                            pos[0],
                            pos[1],
                            isBoat ? 0.1 : pos[2] + this.heightOffset,
                        ),
                        time: pos[3],
                        color: this.getModeColor(pos[3]),
                    });
                }
            }
            return pointsInRange;
        },

        // =========================================================================
        // 2. GROUP POINTS INTO SEGMENTS BY COLOR (a new color starts a new segment)
        // =========================================================================

        groupPointsByColor(points) {
            if (points.length === 0) return [];
            const segments = [];
            let currentSegment = {
                positions: [points[0].position],
                color: points[0].color,
            };
            for (let i = 1; i < points.length; i++) {
                const point = points[i];
                if (Color.equals(point.color, currentSegment.color)) {
                    currentSegment.positions.push(point.position);
                } else {
                    segments.push(currentSegment);
                    currentSegment = {
                        positions: [
                            currentSegment.positions[
                                currentSegment.positions.length - 1
                            ],
                            point.position,
                        ],
                        color: point.color,
                    };
                }
            }
            segments.push(currentSegment);
            return segments;
        },

        // =========================================================================
        // 3. GEOMETRY INSTANCE FOR ONE SEGMENT
        // =========================================================================

        createPolylineGeometryInstance(positions, color, width = 3) {
            return new GeometryInstance({
                geometry: new PolylineGeometry({
                    positions,
                    width,
                }),
                attributes: {
                    color: ColorGeometryInstanceAttribute.fromColor(color),
                },
            });
        },

        // =========================================================================
        // 4. GEOMETRY INSTANCES FOR ALL SEGMENTS
        // =========================================================================

        buildGeometryInstancesFromSegments(segments) {
            const instances = [];
            for (const seg of segments) {
                if (seg.positions.length > 1) {
                    instances.push(
                        this.createPolylineGeometryInstance(
                            seg.positions,
                            seg.color,
                        ),
                    );
                }
            }
            return instances;
        },

        // =========================================================================
        // 5. TRAJECTORY PRIMITIVE IN THE SCENE
        // =========================================================================

        updateTrajectoryPrimitive(instances) {
            // Remove the previous primitive, if any
            if (this.trajectoryPrimitive) {
                this.viewer.scene.primitives.remove(this.trajectoryPrimitive);
            }
            // Nothing to draw without instances or with the trajectory hidden
            if (!this.showTrajectory || instances.length === 0) {
                this.viewer.scene.requestRender();
                return;
            }
            // Create the new primitive
            this.trajectoryPrimitive = new Primitive({
                geometryInstances: instances,
                appearance: new PolylineColorAppearance(),
            });
            this.viewer.scene.primitives.add(this.trajectoryPrimitive);
            this.viewer.scene.primitives.raiseToTop(this.trajectoryPrimitive);
            this.viewer.scene.requestRender();
        },

        // =========================================================================
        // 6. updateAndPlotTrajectory
        // =========================================================================

        async updateAndPlotTrajectory() {
            if (!this.viewer) {
                return;
            }
            // Make sure there is a color coder
            if (!this.colorCoder) {
                this.colorCoder =
                    this.availableColorCoders[this.selectedColorCoder];
            }
            // Time range visible on the timeline
            const startTime = this.cesiumTimeToMs(this.timelineStart);
            const endTime = this.cesiumTimeToMs(this.timelineStop);
            // Filter the points
            const pointsInRange = this.getPointsInTimeRange(startTime, endTime);
            // Group them by color
            const segments = this.groupPointsByColor(pointsInRange);
            // Build the geometry instances
            const instances = this.buildGeometryInstancesFromSegments(segments);
            // Update the primitive in the scene
            this.updateTrajectoryPrimitive(instances);
        },

        async plotMission(points) {
            console.log(points);
            const cesiumPoints = [];
            const cesiumPointsOrig = [];

            for (const pos of points) {
                const position = Cartographic.fromDegrees(
                    pos[0],
                    pos[1],
                    pos[2],
                );
                if (
                    Number.isNaN(pos[0]) ||
                    Number.isNaN(pos[1]) ||
                    Number.isNaN(pos[2])
                ) {
                    continue;
                }
                cesiumPoints.push(position);
                cesiumPointsOrig.push(position);
            }
            if (this.state.vehicle === "boat") {
                this.plotMissionPoints(
                    cesiumPointsOrig,
                    cesiumPointsOrig,
                    points,
                );
            } else {
                sampleTerrainMostDetailed(
                    this.viewer.terrainProvider,
                    cesiumPoints,
                    true,
                )
                    .then((finalPoints) => {
                        this.plotMissionPoints(
                            finalPoints,
                            cesiumPointsOrig,
                            points,
                        );
                    })
                    .catch(() =>
                        this.plotMissionPoints(
                            cesiumPointsOrig,
                            cesiumPointsOrig,
                            points,
                        ),
                    );
            }
        },

        plotMissionPoints(finalPoints, cesiumPointsOrig, points) {
            // Resolve each waypoint's height per its MAV_FRAME (a mission can mix frames):
            //   GLOBAL (0) / GLOBAL_INT (5)                -> alt is absolute AMSL
            //   GLOBAL_RELATIVE_ALT (3) / _INT (6)         -> alt is above home
            //   GLOBAL_TERRAIN_ALT (10) / _INT (11)        -> alt is above terrain
            // finalPoints[i].height is the sampled terrain; cesiumPointsOrig[i].height is the
            // raw alt. Our terrain is orthometric (same datum as AMSL), so absolute alt renders
            // at the right height above the visible ground (geoid cancels) just like the track.
            // Home altitude (AMSL) for relative frames is the home waypoint (seq 0).
            const homeAlt = points.find((point) => point[5] === 0)?.[2] ?? 0;
            for (let i = 0; i < cesiumPointsOrig.length; i++) {
                const frame = points[i][6];
                const alt = points[i][2];
                if (frame === 10 || frame === 11) {
                    finalPoints[i].height += alt;
                } else if (frame === 3 || frame === 6) {
                    finalPoints[i].height = homeAlt + alt + this.heightOffset;
                } else {
                    // GLOBAL/absolute. Use the raw alt directly: cesiumPointsOrig shares its
                    // Cartographic objects with the terrain-sampled array, so its height has
                    // been overwritten with terrain.
                    finalPoints[i].height = alt + this.heightOffset;
                }
            }

            this.waypoints = this.viewer.entities.add({
                polyline: {
                    positions: finalPoints.map((pos) =>
                        Cartesian3.fromRadians(
                            pos.longitude,
                            pos.latitude,
                            pos.height,
                        ),
                    ),
                    width: 1,
                    material: new PolylineDashMaterialProperty({
                        color: Color.WHITE,
                        dashLength: 8,
                    }),
                },
            });
            const labelPoints = finalPoints.map((pos) =>
                Cartesian3.fromRadians(
                    pos.longitude,
                    pos.latitude,
                    pos.height + 0.3,
                ),
            );
            for (const i in labelPoints) {
                this.viewer.entities.add({
                    parent: this.waypoints,
                    position: labelPoints[i],
                    label: {
                        text: `${points[i][5]}`,
                        font: "12px sans-serif",
                        style: LabelStyle.FILL_AND_OUTLINE,
                        fillColor: Color.WHITE,
                        outlineColor: Color.BLACK,
                        showBackground: false,
                        outlineWidth: 3,
                    },
                });
            }
        },
        // Fence ceiling height (metres above terrain): ArduPilot's FENCE_ALT_MAX,
        // falling back to a sensible default when the param isn't logged
        fenceCeiling() {
            try {
                const v = this.state.params?.values
                    ? this.state.params.values.FENCE_ALT_MAX
                    : undefined;
                // a positive number (null, undefined, NaN and text that is no number are not)
                if (Number(v) > 0) {
                    return v;
                }
            } catch {
                /* use default */
            }
            return 120;
        },
        // The points with their terrain height, so fences stand on the ground rather
        // than at ellipsoid height 0 (boats stay at sea level)
        async groundPoints(points) {
            if (this.state.vehicle === "boat") {
                return points;
            }
            try {
                return await sampleTerrainMostDetailed(
                    this.viewer.terrainProvider,
                    points,
                    true,
                );
            } catch {
                return points;
            }
        },
        async plotFences(fencesList) {
            // Remove any previously plotted fences so re-plotting (e.g. when state.fences
            // is populated after this component has already run setup) doesn't leave
            // orphaned entities behind.
            for (const f of this.fences ?? []) {
                this.viewer.entities.remove(f);
            }
            this.fences = [];

            const fenceAltMax = this.fenceCeiling();
            const fenceItems = fencesList.map(fenceItem).filter(Boolean);
            if (fenceItems.length === 0) {
                return;
            }
            const sampledPoints = await this.groundPoints(
                fenceItems.flatMap(fencePoints),
            );

            let idx = 0;
            for (const f of fenceItems) {
                // Inclusion fences green, exclusion fences red.
                const color = f.exclusion ? Color.RED : Color.LIME;
                const entity =
                    f.type === "circle"
                        ? fenceCylinder(
                              f,
                              sampledPoints[idx],
                              fenceAltMax,
                              color,
                          )
                        : fenceWall(
                              sampledPoints.slice(idx, idx + f.ring.length),
                              fenceAltMax,
                              color,
                          );
                idx += fencePoints(f).length;
                this.fences.push(this.viewer.entities.add(entity));
            }
            this.viewer.scene.requestRender();
        },

        getModeColor(time) {
            if (this.colorCoder === undefined) {
                return new Color(1, 1, 1, 1);
            }
            return this.colorCoder.getColor(time);
        },
        getMode(time) {
            for (const mode in this.state.flightModeChanges) {
                if (this.state.flightModeChanges[mode][0] > time) {
                    if (mode - 1 < 0) {
                        return this.state.flightModeChanges[0][1];
                    }
                    return this.state.flightModeChanges[mode - 1][1];
                }
            }
            return this.state.flightModeChanges[
                this.state.flightModeChanges.length - 1
            ][1];
        },
        updateVisibility() {
            this.waypoints.show = this.showWaypoints;
            this.trajectory.show = this.showTrajectory;
            this.fences.show = this.showFences;

            const len = this.clickableTrajectory.length;
            for (let i = 0; i < len; ++i) {
                this.clickableTrajectory.get(i).show =
                    this.showClickableTrajectory;
            }
            this.viewer.scene.requestRender();
        },
        getVehicleModel() {
            const type = this.state.vehicle;
            if (type === "submarine") {
                return submarineModel;
            }
            if (type === "quadcopter+") {
                return quadPlusModel;
            }
            if (type === "quadcopterx" || type === "quadcopter") {
                return quadXModel;
            }
            if (type === "boat") {
                return boatModel;
            }
            return planeModel;
        },
        getDataExtractor() {
            if (this.state.logType === "tlog") {
                return MavlinkDataExtractor;
            } else if (this.state.logType === "dji") {
                return DjiDataExtractor;
            }
            return DataflashDataExtractor;
        },
        loadTrajectory(source) {
            this.waitForMessages([source]).then(() => {
                // the 3D view may have been closed while the messages loaded
                if (this.tornDown) {
                    return;
                }
                const dataExtractor = this.getDataExtractor();
                this.state.trajectories = dataExtractor.extractTrajectory(
                    this.state.messages,
                    source,
                );
                this.processTrajectory();
            });
        },
        removeComparisonTrajectories() {
            for (const primitive of this.comparisonPrimitives ?? []) {
                this.viewer.scene.primitives.remove(primitive);
            }
            this.comparisonPrimitives = [];
            for (const model of this.comparisonModels ?? []) {
                this.viewer.entities.remove(model);
            }
            this.comparisonModels = [];
        },
        // Track positions, and the same positions over time for the comparison vehicle
        comparisonPositions(points, isBoat) {
            const positions = [];
            const sampledPos = new SampledPositionProperty();
            for (const pos of points) {
                const cartesian = Cartesian3.fromDegrees(
                    pos[0],
                    pos[1],
                    isBoat ? 0.1 : pos[2] + this.heightOffset,
                );
                positions.push(cartesian);
                if (
                    this.start !== undefined &&
                    this.startTimeMs !== undefined
                ) {
                    const time = JulianDate.addSeconds(
                        this.start,
                        (pos[3] - this.startTimeMs) / 1000,
                        new JulianDate(),
                    );
                    sampledPos.addSample(time, cartesian);
                }
            }
            return { positions, sampledPos };
        },
        // One comparison source; dataExtractor, isBoat and colors are read once per redraw
        async plotComparisonTrajectory(
            source,
            idx,
            { dataExtractor, isBoat, colors },
        ) {
            try {
                await this.waitForMessages([source]);
            } catch (e) {
                console.warn(
                    "comparison trajectory source unavailable:",
                    source,
                    e,
                );
                return;
            }
            const trajectories = dataExtractor.extractTrajectory(
                this.state.messages,
                source,
            );
            if (!trajectories[source]) {
                return;
            }
            const { positions, sampledPos } = this.comparisonPositions(
                trajectories[source].trajectory,
                isBoat,
            );
            if (positions.length < 2) {
                return;
            }
            const color = Color.fromCssColorString(colors[idx % colors.length]);
            const primitive = new Primitive({
                geometryInstances: new GeometryInstance({
                    geometry: new PolylineGeometry({
                        positions,
                        width: 3.0,
                    }),
                    attributes: {
                        color: ColorGeometryInstanceAttribute.fromColor(color),
                    },
                }),
                appearance: new PolylineColorAppearance(),
            });
            this.viewer.scene.primitives.add(primitive);
            this.comparisonPrimitives.push(primitive);

            // Vehicle that flies the comparison track on the shared clock, tinted with the
            // source's color so it can be told apart from the primary vehicle. Lets you read
            // each source's position at the same instant in time.
            if (this.start !== undefined && this.stop !== undefined) {
                const comparisonModel = this.viewer.entities.add({
                    availability: new TimeIntervalCollection([
                        new TimeInterval({
                            start: this.start,
                            stop: this.stop,
                        }),
                    ]),
                    position: sampledPos,
                    orientation: this.sampledOrientation,
                    model: {
                        uri: this.getVehicleModel(),
                        minimumPixelSize: 15,
                        scale: new CallbackProperty(
                            () => this.modelScale / 10,
                            false,
                        ),
                        color,
                        colorBlendMode: ColorBlendMode.MIX,
                        colorBlendAmount: 0.7,
                    },
                });
                this.comparisonModels.push(comparisonModel);
            }
        },
        async plotComparisonTrajectories() {
            if (!this.viewer) {
                return;
            }
            // Remove the previously drawn comparison overlays and their vehicles.
            this.removeComparisonTrajectories();
            const sources = this.state.comparisonTrajectories || [];
            if (sources.length === 0 || !this.showTrajectory) {
                this.viewer.scene.requestRender();
                return;
            }
            const context = {
                dataExtractor: this.getDataExtractor(),
                isBoat: this.state.vehicle === "boat",
                colors: this.state.comparisonTrajectoryColors,
            };
            for (let idx = 0; idx < sources.length; idx++) {
                if (sources[idx]) {
                    await this.plotComparisonTrajectory(
                        sources[idx],
                        idx,
                        context,
                    );
                }
            }
            this.viewer.scene.requestRender();
        },
        loadAttitude(source) {
            this.waitForMessages([source]).then(() => {
                if (this.tornDown) {
                    return;
                }
                const dataExtractor =
                    this.state.logType === "tlog"
                        ? MavlinkDataExtractor
                        : DataflashDataExtractor;
                try {
                    this.state.timeAttitudeQ = [];
                    this.state.timeAttitude = dataExtractor.extractAttitude(
                        this.state.messages,
                        source,
                    );
                } catch {
                    this.state.timeAttitude = [];
                    this.state.timeAttitudeQ = dataExtractor.extractAttitudeQ(
                        this.state.messages,
                        source,
                    );
                }
                this.addModel();
            });
        },
    },
};
</script>

<style scoped>
#cesiumContainer {
    display: flex;
    height: 100%;
}

#distanceLegend {
    position: absolute;
    bottom: 34px;
    right: 10px;
    z-index: 5;
    color: #fff;
    font-size: 11px;
    font-family: sans-serif;
    text-align: center;
    text-shadow:
        0 0 3px #000,
        0 0 3px #000;
    pointer-events: none;
    user-select: none;
}

#distanceLegend .distanceLegendLabel {
    margin-bottom: 1px;
}

#distanceLegend .distanceLegendBar {
    height: 5px;
    min-width: 2px;
    margin: 0 auto;
    background: rgb(255 255 255 / 55%);
    border: 1px solid #fff;
    border-top: none;
    box-sizing: border-box;
}

#loadingOverlay h1 {
    text-align: center;
    position: relative;
    top: 50%;
    margin-top: -0.5em;
}

.sandcastle-loading #loadingOverlay {
    display: block;
}

.sandcastle-loading #toolbar {
    display: none;
}

#toolbar {
    margin: 5px;
    padding: 5px;
    position: absolute;
    top: 0;
    color: #eee;
    font-family: Montserrat, sans-serif;
    font-size: 9pt;
    z-index: 1;
    height: fit-content;
    display: flex;
}

/* INFO PANEL */

.infoPanel {
    top: 10px;
    background-color: rgb(40 40 40 / 70%);
    padding: 6px 10px;
    border-radius: 5px;
    border: 1px solid #444;
}

#wrapper {
    width: 100%;
    height: 100%;
    position: relative;
}

.mode {
    padding: 0 4px;
}

.settings-panel {
    position: absolute;
    top: 42px;
    right: 5px;
    z-index: 2;
}

.cesium-button {
    display: inline-block;
    position: relative;
    background: #303336;
    border: 1px solid #444;
    color: #edffff;
    fill: #edffff;
    border-radius: 4px;
    padding: 5px 12px;
    margin: 2px 3px;
    cursor: pointer;
    overflow: hidden;
    user-select: none;
}

.demo-container {
    background-color: #303336;
    border-radius: 5px;
    padding: 5px;
    margin: 5px 3px;
    float: left;
}

.demo-container input {
    vertical-align: middle;
    margin-top: 0;
    margin-right: 5px;
}

.demo-container div {
    margin: 0;
}

input#collapsible {
    display: none;
}

.lbl-toggle {
    display: block;
    text-transform: uppercase;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease-out;
    margin: 0;
}

.lbl-toggle:hover {
    color: #5b5b5b;
}

.lbl-toggle::before {
    content: " ";
    display: inline-block;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-left: 5px solid currentcolor;
    vertical-align: middle;
    margin-right: 0.7rem;
    transform: translateY(-2px);
    transition: transform 0.2s ease-out;
}

.toggle:checked + .lbl-toggle::before {
    transform: rotate(90deg) translateX(-3px);
}

.collapsible-content {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.25s ease-in-out;
}

.toggle:checked + .lbl-toggle + .collapsible-content {
    max-height: 350px;
}

.toggle:checked + .lbl-toggle {
    border-bottom-right-radius: 0;
    border-bottom-left-radius: 0;
}

.collapsible-content .content-inner {
    background: rgb(250 224 66 / 20%);
    border-bottom: 1px solid rgb(250 224 66 / 45%);
    border-bottom-left-radius: 7px;
    border-bottom-right-radius: 7px;
    padding: 0.5rem 1rem;
}
</style>

<style>
/* TOOLBAR BUTTONS */

.cesium-toolbar-button {
    background-color: rgb(61 58 56);
    border-radius: 3px;

    /* the icon in the middle of the button (the Font Awesome ones sat lower right) */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
}

.cesium-toolbar-button:hover {
    background-color: rgb(102 90 79);
    color: #fff;
    box-shadow: none;
    border: #5b5b5b;
    transition: all 1s ease;
}

/* HELP BUTTON */

.cesium-navigation-help-button svg {
    width: 27px;
    padding-left: 3px;
    color: #fff;
}

/* CLOSE BUTTON */

.cesium-close-button svg {
    stroke: white;
    stroke-width: 2px;
    width: 25px;
}

.color-coding-select {
    margin: 4px;
}
</style>
