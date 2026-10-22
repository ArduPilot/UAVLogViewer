// A time series (x: times, y: values) for the widgets that follow the playback cursor.
// at() returns the sample at or just before the given time, without interpolating
// (https://github.com/igoutta/UAVLogViewer/issues/6). It walks on from the previous
// position, so it is fast while the cursor moves in small steps.
export class Interpolator {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.currentIndex = 0;
    }

    at(point) {
        while (
            this.x[this.currentIndex] < point &&
            this.currentIndex < this.x.length - 2
        ) {
            this.currentIndex += 1;
        }
        while (this.x[this.currentIndex] > point && this.currentIndex > 1) {
            this.currentIndex -= 1;
        }
        return this.y[
            Math.max(0, Math.min(this.currentIndex, this.y.length - 1))
        ];
    }
}
