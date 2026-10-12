"use strict";

class Vector3 {
    constructor(x, y, z) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    subtract(v) {
        this.x = this.x - v.x;
        this.y = this.y - v.y;
        this.z = this.z - v.z;
        return this;
    }

    add(v) {
        this.x = this.x + v.x;
        this.y = this.y + v.y;
        this.z = this.z + v.z;
        return this;
    }

    multiply(s) {
        this.x = this.x * s;
        this.y = this.y * s;
        this.z = this.z * s;
        return this;
    }

    length() {
        return Math.hypot(this.x, this.y, this.z);
    }

    equals(v) {
        return this.x === v.x && this.y === v.y && this.z === v.z;
    }

    isNaN() {
        return (
            Number.isNaN(this.x) || Number.isNaN(this.y) || Number.isNaN(this.z)
        );
    }
}

export { Vector3 };
