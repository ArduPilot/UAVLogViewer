import Vue from 'vue'

export class ParamSeeker {
    // ..and an (optional) custom class constructor. If one is
    // not supplied, a default constructor is used instead:
    // constructor() { }
    constructor (changeArray) {
        this.changeArray = changeArray
        this.currentIndex = changeArray.length - 1
        this.values = {}
        for (const change of changeArray) {
            this.values[change[1]] = change[2]
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

    // We will look at static and subclassed methods shortly
}
