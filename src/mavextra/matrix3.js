'use strict'

import { Vector3 } from './vector3'

class Matrix3 {
    constructor (i11, i12, i13, i21, i22, i23, i31, i32, i33) {
        // check if we're receiving 3 vector3, if so, use its elements:
        if (i11 instanceof Vector3 &&
            i12 instanceof Vector3 &&
            i13 instanceof Vector3) {
            this._elements = [
                i11.x, i11.y, i11.z,
                i12.x, i12.y, i12.z,
                i13.x, i13.y, i13.z
            ]
            return
        }
        this._elements = [i11, i12, i13, i21, i22, i23, i31, i32, i33]
    }

    get a () {
        return new Vector3(
            this._elements[0],
            this._elements[1],
            this._elements[2]
        )
    }

    get b () {
        return new Vector3(
            this._elements[3],
            this._elements[4],
            this._elements[5]
        )
    }

    get c () {
        return new Vector3(
            this._elements[6],
            this._elements[7],
            this._elements[8]
        )
    }

    fromEuler (roll, pitch, yaw) {
        this._elements = []
        const cp = Math.cos(pitch)
        const sp = Math.sin(pitch)
        const sr = Math.sin(roll)
        const cr = Math.cos(roll)
        const sy = Math.sin(yaw)
        const cy = Math.cos(yaw)
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

    multiply (matrix) {
        const m = this._elements
        const n = matrix._elements
        return new Matrix3(
            m[0] * n[0] + m[1] * n[3] + m[2] * n[6],
            m[0] * n[1] + m[1] * n[4] + m[2] * n[7],
            m[0] * n[2] + m[1] * n[5] + m[2] * n[8],
            m[3] * n[0] + m[4] * n[3] + m[5] * n[6],
            m[3] * n[1] + m[4] * n[4] + m[5] * n[7],
            m[3] * n[2] + m[4] * n[5] + m[5] * n[8],
            m[6] * n[0] + m[7] * n[3] + m[8] * n[6],
            m[6] * n[1] + m[7] * n[4] + m[8] * n[7],
            m[6] * n[2] + m[7] * n[5] + m[8] * n[8]
        )
    }

    transposed () {
        return new Matrix3(
            this._elements[0], this._elements[3], this._elements[6],
            this._elements[1], this._elements[4], this._elements[7],
            this._elements[2], this._elements[5], this._elements[8]
        )
    }

    determinant () {
        const m = this._elements
        return m[0] * m[4] * m[8] -
            m[0] * m[5] * m[7] -
            m[1] * m[3] * m[8] +
            m[1] * m[5] * m[6] +
            m[2] * m[3] * m[7] -
            m[2] * m[4] * m[6]
    }

    invert () {
        const d = this.determinant()
        if (d === 0) {
            return null
        }
        const invD = 1 / d
        const m = this._elements
        return new Matrix3(
            invD * (m[8] * m[4] - m[7] * m[5]),
            invD * -(m[8] * m[1] - m[7] * m[2]),
            invD * (m[5] * m[1] - m[4] * m[2]),
            invD * -(m[8] * m[3] - m[6] * m[5]),
            invD * (m[8] * m[0] - m[6] * m[2]),
            invD * -(m[5] * m[0] - m[3] * m[2]),
            invD * (m[7] * m[3] - m[6] * m[4]),
            invD * -(m[7] * m[0] - m[6] * m[1]),
            invD * (m[4] * m[0] - m[3] * m[1])
        )
    }
}

export { Matrix3 }
