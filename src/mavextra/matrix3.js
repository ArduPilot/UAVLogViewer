'use strict'

import { Vector3 } from './vector3'

class Matrix3 {
    constructor (i11, i12, i13, i21, i22, i23, i31, i32, i33) {
        this._elements = [i11, i12, i13, i21, i22, i23, i31, i32, i33]
    }

    fromEuler (roll, pitch, yaw) {
        this._elements = []
        let cp = Math.cos(pitch)
        let sp = Math.sin(pitch)
        let sr = Math.sin(roll)
        let cr = Math.cos(roll)
        let sy = Math.sin(yaw)
        let cy = Math.cos(yaw)
        this._elements.push(cp * cy)
        this._elements.push((sr * sp * cy) - (cr * sy))
        this._elements.push((cr * sp * cy) + (sr * sy))
        this._elements.push(cp * sy)
        this._elements.push((sr * sp * sy) + (cr * cy))
        this._elements.push((cr * sp * sy) - (sr * cy))
        this._elements.push(-sp)
        this._elements.push(sr * cp)
        this._elements.push(cr * cp)
        return this
    }

    e (i) {
        // validate?
        return this._elements[i]
    }

    times (vector) {
        return new Vector3(
            this._elements[0] * vector.x + this._elements[1] * vector.y + this._elements[2] * vector.z,
            this._elements[3] * vector.x + this._elements[4] * vector.y + this._elements[5] * vector.z,
            this._elements[6] * vector.x + this._elements[7] * vector.y + this._elements[8] * vector.z
        )
    }

    transposed () {
        return new Matrix3(
            this._elements[0], this._elements[3], this._elements[6],
            this._elements[1], this._elements[4], this._elements[7],
            this._elements[2], this._elements[5], this._elements[8]
        )
    }
}

export {Matrix3}
