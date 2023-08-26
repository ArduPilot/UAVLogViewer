
export default class ColorCoderMode {
    requiredMessages = []

    constructor (state) {
        this.state = state
        this.setOfModes = this.calculateSetOfModes()
    }

    getLegend () {
        const legend = []
        for (const mode of this.setOfModes) {
            legend.push({
                name: mode,
                color: this.state.cssColors[this.setOfModes.indexOf(mode)]
            })
        }
        return legend
    }

    getColor (time) {
        return this.state.colors[this.setOfModes.indexOf(this.getMode(time))]
    }

    getMode (time) {
        for (const mode of this.state.flightModeChanges) {
            if (mode[0] > time) {
                return mode[1]
            }
        }
        return this.state.flightModeChanges[this.state.flightModeChanges.length - 1][1]
    }

    calculateSetOfModes () {
        const set = []
        for (const mode of this.state.flightModeChanges) {
            if (!set.includes(mode[1])) {
                set.push(mode[1])
            }
        }
        return set
    }
}
