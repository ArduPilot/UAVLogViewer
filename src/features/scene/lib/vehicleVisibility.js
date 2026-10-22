import {
    BoundingSphere,
    BoundingSphereState,
    Cartesian3,
    Color,
    DirectionalLight,
    SceneTransforms,
    SunLight,
} from "cesium";

// The outline is checked against what surrounds the vehicle on screen about once a second
const OUTLINE_SIZE = 2; // pixels
const CHECK_INTERVAL_MS = 1000;
// the background is sampled in a ring this far outside the vehicle (CSS pixels)
const RING_GAP = 6;
const RING_WIDTH = 24;
// the area around the vehicle is scaled down to at most this many pixels a side before it is read,
// so a large vehicle on screen costs no more than a small one
const SAMPLE_SIZE = 64;

// Keeps the vehicle visible in the 3D view.
// Lighting: with the log's real time and place, the sun lights the vehicle and the ground as it
// did then, night included. Without them (no absolute time or no position), a light from the
// camera shows the vehicle in its own colours and the ground stays fully lit.
// Outline: black or white around the vehicle, whichever contrasts with what surrounds it.
export class VehicleVisibility {
    constructor(viewer, getVehicle) {
        this.viewer = viewer;
        this.getVehicle = getVehicle;
        const globe = viewer.scene.globe;
        this.defaultFade = [
            globe.lightingFadeOutDistance,
            globe.lightingFadeInDistance,
        ];
        this.sunLight = new SunLight();
        this.cameraLight = new DirectionalLight({
            direction: new Cartesian3(0, 0, -1),
        });
        this.realLighting = true;
        this.outlineDark = null;
        this.lastCheck = 0;
        this.sample = document.createElement("canvas");
        this.sphere = new BoundingSphere();
        this.onPreRender = () => this.followCamera();
        this.onPostRender = (scene, time) => this.updateOutline(time);
        viewer.scene.preRender.addEventListener(this.onPreRender);
        viewer.scene.postRender.addEventListener(this.onPostRender);
    }

    setRealLighting(real) {
        const scene = this.viewer.scene;
        this.realLighting = real;
        scene.light = real ? this.sunLight : this.cameraLight;
        // Cesium only shades the ground from far away (beyond about 10,000 km) by default; with
        // real lighting shade it at any distance (its night side keeps 30 % of the brightness)
        const [fadeOut, fadeIn] = real ? [0, 1] : this.defaultFade;
        scene.globe.lightingFadeOutDistance = fadeOut;
        scene.globe.lightingFadeInDistance = fadeIn;
        scene.requestRender();
    }

    followCamera() {
        if (!this.realLighting) {
            Cartesian3.clone(
                this.viewer.scene.camera.directionWC,
                this.cameraLight.direction,
            );
        }
    }

    updateOutline(time) {
        const now = performance.now();
        if (now - this.lastCheck < CHECK_INTERVAL_MS) {
            return;
        }
        this.lastCheck = now;
        const vehicle = this.getVehicle();
        const luminance =
            vehicle?.model && this.backgroundLuminance(vehicle, time);
        if (luminance === undefined || luminance === null) {
            return;
        }
        // switch only past a margin, so a background near the middle does not make it flicker
        let threshold = 0.5;
        if (this.outlineDark !== null) {
            threshold = this.outlineDark ? 0.4 : 0.6;
        }
        const dark = luminance > threshold;
        if (dark !== this.outlineDark) {
            this.outlineDark = dark;
            vehicle.model.silhouetteColor = dark ? Color.BLACK : Color.WHITE;
            vehicle.model.silhouetteSize = OUTLINE_SIZE;
            this.viewer.scene.requestRender();
        }
    }

    // Mean luminance (0-1) of the frame just rendered, in a ring around the vehicle; null when the
    // vehicle is not on screen
    backgroundLuminance(vehicle, time) {
        const scene = this.viewer.scene;
        const position = vehicle.position?.getValue(time);
        const center =
            position &&
            SceneTransforms.worldToWindowCoordinates(scene, position);
        if (!center) {
            return null;
        }
        const canvas = scene.canvas;
        const scale = canvas.width / canvas.clientWidth; // drawing-buffer pixels per CSS pixel
        let radius = 8; // CSS pixels, when the model's size is not known yet
        if (
            this.viewer.dataSourceDisplay.getBoundingSphere(
                vehicle,
                false,
                this.sphere,
            ) === BoundingSphereState.DONE
        ) {
            const metersPerPixel = scene.camera.getPixelSize(
                this.sphere,
                canvas.width,
                canvas.height,
            );
            // 0 with the camera inside the vehicle's bounding sphere (a large wingspan, close up)
            if (!Number.isFinite(metersPerPixel) || metersPerPixel <= 0) {
                return null;
            }
            radius = this.sphere.radius / metersPerPixel / scale;
        }
        const inner = (radius + RING_GAP) * scale;
        const outer = inner + RING_WIDTH * scale;
        // a ring larger than the view: the vehicle fills it, there is no background to measure
        if (
            !Number.isFinite(outer) ||
            outer >= Math.hypot(canvas.width, canvas.height)
        ) {
            return null;
        }
        const size = Math.ceil(2 * outer);
        const left = Math.round(center.x * scale - outer);
        const top = Math.round(center.y * scale - outer);
        // the same ring, in the scaled-down sample (at least a pixel and a half wide)
        const sampleSize = Math.min(size, SAMPLE_SIZE);
        const k = sampleSize / size;
        const middle = outer * k;
        const sampleInner = inner * k;
        const sampleOuter = Math.max(middle, sampleInner + 1.5);
        this.sample.width = sampleSize;
        this.sample.height = sampleSize;
        const context = this.sample.getContext("2d", {
            willReadFrequently: true,
        });
        // the WebGL drawing buffer still holds this frame during postRender
        context.drawImage(
            canvas,
            left,
            top,
            size,
            size,
            0,
            0,
            sampleSize,
            sampleSize,
        );
        const pixels = context.getImageData(0, 0, sampleSize, sampleSize).data;
        let sum = 0;
        let count = 0;
        for (let y = 0; y < sampleSize; y++) {
            for (let x = 0; x < sampleSize; x++) {
                const d = Math.hypot(x - middle, y - middle);
                const i = 4 * (y * sampleSize + x);
                // pixels outside the canvas come back transparent: skip them
                if (d >= sampleInner && d <= sampleOuter && pixels[i + 3] > 0) {
                    sum +=
                        (0.2126 * pixels[i] +
                            0.7152 * pixels[i + 1] +
                            0.0722 * pixels[i + 2]) /
                        255;
                    count++;
                }
            }
        }
        return count > 0 ? sum / count : null;
    }

    destroy() {
        this.viewer.scene.preRender.removeEventListener(this.onPreRender);
        this.viewer.scene.postRender.removeEventListener(this.onPostRender);
    }
}
