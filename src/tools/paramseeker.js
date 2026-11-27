import Vue from 'vue'

export class ParamSeeker {
    // ..and an (optional) custom class constructor. If one is
    // not supplied, a default constructor is used instead:
    // constructor() { }
    constructor (changeArray) {
        this.changeArray = changeArray
        this.currentIndex = changeArray.length - 1
        this.values = {}
        // values at the end of the log, independent of the seek position
        this.lastValues = {}
        // parameters that took more than one value during the log
        this.changedParams = new Set()
        for (const change of changeArray) {
            this.values[change[1]] = change[2]
            if (change[1] in this.lastValues && this.lastValues[change[1]] !== change[2]) {
                this.changedParams.add(change[1])
            }
            this.lastValues[change[1]] = change[2]
        }
        this.seek(0)
        // export to window so the mavextra functions can access them
        window.params = this.values
    }

    seek (time) {
        const indexBefore = this.currentIndex
        while (this.changeArray[this.currentIndex][0] < time && this.currentIndex < this.changeArray.length - 2) {
            this.values[this.changeArray[this.currentIndex][1]] = this.changeArray[this.currentIndex][2]
            this.currentIndex += 1
        }
        while (this.changeArray[this.currentIndex][0] > time && this.currentIndex > 1) {
            this.values[this.changeArray[this.currentIndex][1]] = this.changeArray[this.currentIndex][2]
            this.currentIndex -= 1
        }
        if (this.currentIndex !== indexBefore) {
            if (Vue.prototype.$eventHub !== undefined) {
                // this is undefined when running unit tests
                Vue.prototype.$eventHub.$emit('paramsUpdated')
            }
        }
        return this
    }

    get (param) {
        return this.values[param]
    }

    getLast (param) {
        return this.lastValues[param]
    }

    changedDuringLog (param) {
        return this.changedParams.has(param)
    }

    // Value of param in use at each of times: the latest value logged at or
    // before that time, or the first logged value for times before it was first
    // logged. Returns null if the param is not in the log.
    valuesAt (param, times) {
        const changes = this.changeArray
            .filter(change => change[1] === param)
            .sort((a, b) => a[0] - b[0])
        if (changes.length === 0) {
            return null
        }
        return Array.from(times, time => {
            // first change after time
            let lo = 0
            let hi = changes.length
            while (lo < hi) {
                const mid = (lo + hi) >> 1
                if (changes[mid][0] <= time) {
                    lo = mid + 1
                } else {
                    hi = mid
                }
            }
            return changes[Math.max(lo - 1, 0)][2]
        })
    }

    // We will look at static and subclassed methods shortly
}
