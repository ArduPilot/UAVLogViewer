export default class ColorCoderMode {
    requiredMessages = [];

    constructor(state) {
        this.state = state;
    }

    // Distinct flight modes of the current log, recomputed when another log is loaded
    get modes() {
        if (this.modesSource !== this.state.flightModeChanges) {
            this.modesSource = this.state.flightModeChanges;
            this.setOfModes = this.calculateSetOfModes();
        }
        return this.setOfModes;
    }

    getLegend() {
        const legend = [];
        for (const mode of this.modes) {
            legend.push({
                name: mode,
                color: this.state.cssColors[this.modes.indexOf(mode)],
            });
        }
        return legend;
    }

    getColor(time) {
        return this.state.colors[this.modes.indexOf(this.getMode(time))];
    }

    getMode(time) {
        let previousMode = this.state.flightModeChanges[0][1];
        for (const mode of this.state.flightModeChanges) {
            if (mode[0] > time) {
                return previousMode;
            }
            previousMode = mode[1];
        }
        return this.state.flightModeChanges[
            this.state.flightModeChanges.length - 1
        ][1];
    }

    calculateSetOfModes() {
        const set = [];
        for (const mode of this.state.flightModeChanges) {
            if (!set.includes(mode[1])) {
                set.push(mode[1]);
            }
        }
        return set;
    }
}
