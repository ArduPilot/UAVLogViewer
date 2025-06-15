'use strict'

class Vector3 {
    constructor (x, y, z) {
        this.x = x
        this.y = y
        this.z = z
    }

    subtract (v) {
        this.x = this.x - v.x
        this.y = this.y - v.y
        this.z = this.z - v.z
        return this
    }

    add (v) {
        this.x = this.x + v.x
        this.y = this.y + v.y
        this.z = this.z + v.z
        return this
    }

    multiply (s) {
        this.x = this.x * s
        this.y = this.y * s
        this.z = this.z * s
        return this
    }

    length () {
        return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z)
    }

    equals (v) {
        return this.x === v.x && this.y === v.y && this.z === v.z
    }

    isNaN () {
        return isNaN(this.x) || isNaN(this.y) || isNaN(this.z)
    }
}

export { Vector3 }
