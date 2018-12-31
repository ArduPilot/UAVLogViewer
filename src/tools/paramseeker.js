export class ParamSeeker {
    // ..and an (optional) custom class constructor. If one is
    // not supplied, a default constructor is used instead:
    // constructor() { }
    constructor (changeArray) {
        this.changeArray = changeArray
        this.currentIndex = changeArray.length - 1
        this.values = {}
        for (let change of changeArray) {
            this.values[change[1]] = change[2]
        }
        this.seek(0)
    }

    seek (time) {
        while (this.changeArray[this.currentIndex][0] < time && this.currentIndex < this.changeArray.length - 2) {
            this.values[this.changeArray[this.currentIndex][1]] = this.changeArray[this.currentIndex][2]
            this.currentIndex += 1
        }
        while (this.changeArray[this.currentIndex][0] > time && this.currentIndex > 1) {
            this.values[this.changeArray[this.currentIndex][1]] = this.changeArray[this.currentIndex][2]
            this.currentIndex -= 1
        }
        return this
    }

    get (param) {
        return this.values[param]
    }

    // We will look at static and subclassed methods shortly
}
