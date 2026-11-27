// Compass calibration fitting used by the MAGFit widget.
//
// The calibration model is the one applied by ArduPilot in
// AP_Compass_Backend::correct_field():
//
//   corrected = iron * (scale * (raw + offsets)) + motor * current
//
// iron is the symmetric matrix built from COMPASS_DIA_* (diagonal) and
// COMPASS_ODI_* (off-diagonal). The firmware only applies the scale when it is
// within [1/1.5, 1.5] and only applies iron when the diagonals are not all zero.
//
// Fields are passed around as { x: [], y: [], z: [] } (one entry per sample)
// and calibrations as { offsets: [3], diagonals: [3], offDiagonals: [3],
// scale, motor: [3] }. Angles are in radians and fields in mGauss.

export const FIT_TYPES = {
    offsets: 'Offsets',
    scale: 'Offsets and scale',
    iron: 'Offsets and iron'
}

export const YAW_SOURCES = {
    mag: 'Compass (tilt compensated)',
    att: 'Attitude (EKF) yaw'
}

// Fits with any parameter outside of these (open) ranges are invalid. Offsets
// to scale are the WebTools MAGFit limits, motor is the COMPASS_MOT_* param
// range. All are inside the firmware limits: |OFS| < COMPASS_OFFS_MAX (default
// 1800), the compass calibrator accepts DIA in (0.2, 5) and |ODI| < 1, and
// SCALE is only applied within [1/1.5, 1.5].
export const PARAM_RANGES = {
    offsets: [-1500, 1500],
    diagonals: [0.8, 1.2],
    offDiagonals: [-0.2, 0.2],
    scale: [0.8, 1.2],
    motor: [-1000, 1000]
}

// COMPASS_MOTCT value for current based motor compensation
export const MOT_COMP_CURRENT = 2

// Minimum variation of the expected field direction, in the direction it
// varies least, for an iron fit. Below this (mostly level flight) the Z
// diagonal can't be separated from the Z offset.
export const MIN_IRON_EXCITATION = 0.05

// Minimum fraction of the attitude bins with samples for an iron fit, the
// WebTools coverage hint. With fewer, the field varies enough in a few
// directions to pass the excitation check but the matrix is still poorly
// determined.
export const MIN_IRON_COVERAGE = 0.3

const MAX_SCALE_FACTOR = 1.5
const MIN_SAMPLES = 30
const MIN_CURRENT_RANGE = 0.5
const AXES = ['x', 'y', 'z']
const UNOBSERVABLE = 'Fit failed: the data does not constrain all parameters ' +
    '(not enough attitude or current variation)'

// Whether the firmware applies a COMPASS_SCALE value (it ignores others, 0 = unset)
export function scaleValid (scale) {
    return Number.isFinite(scale) && scale >= 1 / MAX_SCALE_FACTOR && scale <= MAX_SCALE_FACTOR
}

export function identityCalibration () {
    return {
        offsets: [0, 0, 0],
        diagonals: [1, 1, 1],
        offDiagonals: [0, 0, 0],
        scale: 1,
        motor: [0, 0, 0]
    }
}

export function ironMatrix (diagonals, offDiagonals) {
    return [
        [diagonals[0], offDiagonals[0], offDiagonals[1]],
        [offDiagonals[0], diagonals[1], offDiagonals[2]],
        [offDiagonals[1], offDiagonals[2], diagonals[2]]
    ]
}

function determinant3 (m) {
    return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
        m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
        m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
}

export function invert3 (m) {
    const det = determinant3(m)
    if (!Number.isFinite(det) || Math.abs(det) < 1e-12) {
        return null
    }
    const d = 1 / det
    return [
        [
            d * (m[1][1] * m[2][2] - m[1][2] * m[2][1]),
            d * (m[0][2] * m[2][1] - m[0][1] * m[2][2]),
            d * (m[0][1] * m[1][2] - m[0][2] * m[1][1])
        ],
        [
            d * (m[1][2] * m[2][0] - m[1][0] * m[2][2]),
            d * (m[0][0] * m[2][2] - m[0][2] * m[2][0]),
            d * (m[0][2] * m[1][0] - m[0][0] * m[1][2])
        ],
        [
            d * (m[1][0] * m[2][1] - m[1][1] * m[2][0]),
            d * (m[0][1] * m[2][0] - m[0][0] * m[2][1]),
            d * (m[0][0] * m[1][1] - m[0][1] * m[1][0])
        ]
    ]
}

function mul3 (m, x, y, z) {
    return [
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z
    ]
}

function ironApplies (diagonals) {
    return !(diagonals[0] === 0 && diagonals[1] === 0 && diagonals[2] === 0)
}

// v is either a constant [x, y, z] or per-sample { x: [], y: [], z: [] }
function valueAt (v, axis, i) {
    if (v == null) {
        return 0
    }
    if (Array.isArray(v)) {
        return v[axis]
    }
    return v[AXES[axis]][i]
}

function emptyField (n) {
    return { x: new Array(n), y: new Array(n), z: new Array(n) }
}

// Undo the calibration the vehicle applied to a logged field, returning the
// raw sensor field. Each of offsets, motorOffsets, diagonals and offDiagonals
// may be constant [x, y, z] or per-sample (as logged in MAG.OfsX and MAG.MOX,
// or the param values in use at each sample), and scale a number or an array.
// A scale the firmware ignores (e.g. 0, unset) is treated as 1, as the
// firmware did. Returns null if an iron matrix cannot be inverted.
export function removeCalibration (field, { offsets, motorOffsets, diagonals, offDiagonals, scale }) {
    const n = field.x.length
    const raw = emptyField(n)
    let iron = null
    let invIron = null
    for (let i = 0; i < n; i++) {
        const d = diagonals ? [0, 1, 2].map(k => valueAt(diagonals, k, i)) : null
        if (d !== null && ironApplies(d)) {
            const o = [0, 1, 2].map(k => valueAt(offDiagonals, k, i))
            const m = d.concat(o)
            if (iron === null || m.some((v, k) => v !== iron[k])) {
                iron = m
                invIron = invert3(ironMatrix(d, o))
                if (invIron === null) {
                    return null
                }
            }
        } else {
            iron = null
            invIron = null
        }
        const s = typeof scale === 'number' || scale == null ? scale : scale[i]
        const invScale = scaleValid(s) ? 1 / s : 1
        let v = [
            field.x[i] - valueAt(motorOffsets, 0, i),
            field.y[i] - valueAt(motorOffsets, 1, i),
            field.z[i] - valueAt(motorOffsets, 2, i)
        ]
        if (invIron !== null) {
            v = mul3(invIron, v[0], v[1], v[2])
        }
        raw.x[i] = v[0] * invScale - valueAt(offsets, 0, i)
        raw.y[i] = v[1] * invScale - valueAt(offsets, 1, i)
        raw.z[i] = v[2] * invScale - valueAt(offsets, 2, i)
    }
    return raw
}

// Apply a calibration to a raw field, the same way the firmware does.
// current is only needed if the calibration has motor compensation. The scale
// must be one the firmware applies, otherwise the result would not be what the
// vehicle does with these params.
export function applyCalibration (raw, cal, current) {
    if (!scaleValid(cal.scale)) {
        throw new Error(`Scale ${cal.scale} is outside the range the firmware applies`)
    }
    const iron = ironApplies(cal.diagonals) ? ironMatrix(cal.diagonals, cal.offDiagonals) : null
    const scale = cal.scale
    const motor = cal.motor || [0, 0, 0]
    const hasMotor = motor[0] !== 0 || motor[1] !== 0 || motor[2] !== 0
    const n = raw.x.length
    const out = emptyField(n)
    for (let i = 0; i < n; i++) {
        let v = [
            (raw.x[i] + cal.offsets[0]) * scale,
            (raw.y[i] + cal.offsets[1]) * scale,
            (raw.z[i] + cal.offsets[2]) * scale
        ]
        if (iron !== null) {
            v = mul3(iron, v[0], v[1], v[2])
        }
        if (hasMotor) {
            const amps = current ? current[i] : NaN
            v[0] += motor[0] * amps
            v[1] += motor[1] * amps
            v[2] += motor[2] * amps
        }
        out.x[i] = v[0]
        out.y[i] = v[1]
        out.z[i] = v[2]
    }
    return out
}

// Linear interpolation of values sampled at (non-decreasing) times onto
// queryTimes. Queries outside of the sampled time range give NaN. If period is
// given the values are treated as angles wrapping at that period.
export function interpolate (times, values, queryTimes, period = null) {
    const n = times.length
    const out = new Array(queryTimes.length)
    let j = 0
    for (let q = 0; q < queryTimes.length; q++) {
        const t = queryTimes[q]
        if (n === 0 || !(t >= times[0]) || !(t <= times[n - 1])) {
            out[q] = NaN
            continue
        }
        if (t < times[j]) {
            j = 0
        }
        while (j < n - 2 && times[j + 1] <= t) {
            j++
        }
        const t0 = times[j]
        const t1 = times[Math.min(j + 1, n - 1)]
        const v0 = values[j]
        let delta = values[Math.min(j + 1, n - 1)] - v0
        if (period !== null) {
            delta -= period * Math.round(delta / period)
        }
        const ratio = t1 > t0 ? (t - t0) / (t1 - t0) : 0
        out[q] = v0 + ratio * delta
    }
    return out
}

// Body to earth rotation matrix, same convention as Matrix3.fromEuler
export function dcmFromEuler (roll, pitch, yaw) {
    const cp = Math.cos(pitch)
    const sp = Math.sin(pitch)
    const sr = Math.sin(roll)
    const cr = Math.cos(roll)
    const sy = Math.sin(yaw)
    const cy = Math.cos(yaw)
    return [
        cp * cy, (sr * sp * cy) - (cr * sy), (cr * sp * cy) + (sr * sy),
        cp * sy, (sr * sp * sy) + (cr * cy), (cr * sp * sy) - (sr * cy),
        -sp, sr * cp, cr * cp
    ]
}

// Earth field (NED) rotated into the body frame
export function bodyFrameField (earthField, roll, pitch, yaw) {
    const r = dcmFromEuler(roll, pitch, yaw)
    return [
        r[0] * earthField[0] + r[3] * earthField[1] + r[6] * earthField[2],
        r[1] * earthField[0] + r[4] * earthField[1] + r[7] * earthField[2],
        r[2] * earthField[0] + r[5] * earthField[1] + r[8] * earthField[2]
    ]
}

// Tilt compensated magnetic heading, matching the firmware's calculation
export function magHeading (mx, my, mz, roll, pitch) {
    const cx = -Math.sin(pitch)
    const cy = Math.sin(roll) * Math.cos(pitch)
    const cz = Math.cos(roll) * Math.cos(pitch)
    const headY = my * cz - mz * cy
    const headX = mx * (1 - cx * cx) - cx * (my * cy + mz * cz)
    return Math.atan2(-headY, headX)
}

export function declinationOf (earthField) {
    return Math.atan2(earthField[1], earthField[0])
}

// Expected body frame field for an attitude source yaw
export function expectedFromYaw (earthField, roll, pitch, yaw, indices) {
    const idx = indices || [...roll.keys()]
    const out = emptyField(idx.length)
    for (let j = 0; j < idx.length; j++) {
        const i = idx[j]
        const v = bodyFrameField(earthField, roll[i], pitch[i], yaw[i])
        out.x[j] = v[0]
        out.y[j] = v[1]
        out.z[j] = v[2]
    }
    return out
}

// Expected body frame field using the yaw implied by the (corrected) compass
// field itself. This avoids depending on the EKF yaw, which is itself derived
// from the compass, but makes the fit nonlinear.
export function expectedFromMagYaw (earthField, field, roll, pitch, indices) {
    const declination = declinationOf(earthField)
    const idx = indices || [...roll.keys()]
    const out = emptyField(idx.length)
    for (let j = 0; j < idx.length; j++) {
        const i = idx[j]
        const yaw = magHeading(field.x[i], field.y[i], field.z[i], roll[i], pitch[i]) + declination
        const v = bodyFrameField(earthField, roll[i], pitch[i], yaw)
        out.x[j] = v[0]
        out.y[j] = v[1]
        out.z[j] = v[2]
    }
    return out
}

// Per-sample error length between a corrected and expected field, NaN where
// either is invalid.
export function fieldErrors (corrected, expected) {
    const n = corrected.x.length
    const out = new Array(n)
    for (let i = 0; i < n; i++) {
        out[i] = Math.sqrt(
            (corrected.x[i] - expected.x[i]) ** 2 +
            (corrected.y[i] - expected.y[i]) ** 2 +
            (corrected.z[i] - expected.z[i]) ** 2
        )
    }
    return out
}

export function rms (values) {
    let sum = 0
    let count = 0
    for (const v of values) {
        if (Number.isFinite(v)) {
            sum += v * v
            count++
        }
    }
    return count > 0 ? Math.sqrt(sum / count) : NaN
}

// Error of an already corrected field against the expected field for the
// given yaw source. Returns { rms, errors, expected }, rms is bin weighted if
// bins (from fieldBins) are given.
export function calibrationError ({ corrected, roll, pitch, yaw, earthField, yawSource, bins = null }) {
    const expected = yawSource === 'att'
        ? expectedFromYaw(earthField, roll, pitch, yaw)
        : expectedFromMagYaw(earthField, corrected, roll, pitch)
    const errors = fieldErrors(corrected, expected)
    return { rms: bins ? weightedRms(errors, bins) : rms(errors), errors, expected }
}

// Solve min |A x - b| with Householder QR. A is column-major (A[col * rows + row])
// and is overwritten. Returns null if A is rank deficient or the result is not
// finite, for example when the data does not vary enough to observe a parameter.
export function solveLeastSquares (A, b, rows, cols) {
    if (rows < cols) {
        return null
    }
    // Normalise columns so the rank test does not depend on parameter units
    const colScale = new Float64Array(cols)
    for (let c = 0; c < cols; c++) {
        let norm = 0
        for (let r = 0; r < rows; r++) {
            norm += A[c * rows + r] ** 2
        }
        norm = Math.sqrt(norm)
        if (!(norm > 0) || !Number.isFinite(norm)) {
            return null
        }
        colScale[c] = norm
        for (let r = 0; r < rows; r++) {
            A[c * rows + r] /= norm
        }
    }

    const qtb = Float64Array.from(b)
    const diag = new Float64Array(cols)
    for (let k = 0; k < cols; k++) {
        const base = k * rows
        let norm = 0
        for (let r = k; r < rows; r++) {
            norm += A[base + r] ** 2
        }
        norm = Math.sqrt(norm)
        const alpha = A[base + k] > 0 ? -norm : norm
        A[base + k] -= alpha
        let vNorm2 = 0
        for (let r = k; r < rows; r++) {
            vNorm2 += A[base + r] ** 2
        }
        if (vNorm2 > 0) {
            for (let c = k + 1; c < cols; c++) {
                const cBase = c * rows
                let dot = 0
                for (let r = k; r < rows; r++) {
                    dot += A[base + r] * A[cBase + r]
                }
                const f = 2 * dot / vNorm2
                for (let r = k; r < rows; r++) {
                    A[cBase + r] -= f * A[base + r]
                }
            }
            let dot = 0
            for (let r = k; r < rows; r++) {
                dot += A[base + r] * qtb[r]
            }
            const f = 2 * dot / vNorm2
            for (let r = k; r < rows; r++) {
                qtb[r] -= f * A[base + r]
            }
        }
        diag[k] = alpha
    }

    let maxDiag = 0
    for (let k = 0; k < cols; k++) {
        maxDiag = Math.max(maxDiag, Math.abs(diag[k]))
    }
    for (let k = 0; k < cols; k++) {
        if (!(Math.abs(diag[k]) > 1e-9 * maxDiag)) {
            return null
        }
    }

    const x = new Array(cols)
    for (let k = cols - 1; k >= 0; k--) {
        let sum = qtb[k]
        for (let c = k + 1; c < cols; c++) {
            sum -= A[c * rows + k] * x[c]
        }
        x[k] = sum / diag[k]
    }
    for (let k = 0; k < cols; k++) {
        x[k] /= colScale[k]
        if (!Number.isFinite(x[k])) {
            return null
        }
    }
    return x
}

function numColumns (fitType, fitMotor) {
    const base = { offsets: 3, scale: 4, iron: 9 }[fitType]
    return base + (fitMotor ? 3 : 0)
}

// Build and solve the linear system for a fixed expected field, same
// formulation as WebTools MAGFit:
//   offsets: expected - raw = offsets + motor * current
//   scale:   expected = scale * raw + (scale * offsets) + motor * current
//   iron:    expected = iron * raw + (iron * offsets) + motor * current
//
// If down (the body frame down axis of each sample) is given, each sample's
// three equations are projected onto the expected horizontal direction and
// the down axis, dropping the component along the horizontal tangent. That is
// the Gauss-Newton step for the compass yaw cost, where the heading follows
// the calibrated field so only horizontal magnitude and vertical component
// are constrained.
//
// Each sample's equations are scaled by sqrtWeights (the square root of its
// bin weight).
function solveLinear (raw, expected, current, sqrtWeights, indices, fitType, fitMotor, down = null) {
    const n = indices.length
    const perSample = down ? 2 : 3
    const rows = n * perSample
    const cols = numColumns(fitType, fitMotor)
    const A = new Float64Array(rows * cols)
    const b = new Float64Array(rows)
    const motorCol = cols - 3
    const block = [new Float64Array(cols), new Float64Array(cols), new Float64Array(cols)]
    const rhs = [0, 0, 0]

    for (let j = 0; j < n; j++) {
        const i = indices[j]
        const r = [raw.x[i], raw.y[i], raw.z[i]]
        const e = [expected.x[j], expected.y[j], expected.z[j]]
        for (let k = 0; k < 3; k++) {
            block[k].fill(0)
            block[k][k] = 1
            rhs[k] = fitType === 'offsets' ? e[k] - r[k] : e[k]
        }
        if (fitType === 'scale') {
            for (let k = 0; k < 3; k++) {
                block[k][3] = r[k]
            }
        } else if (fitType === 'iron') {
            // diagonals
            block[0][3] = r[0]
            block[1][4] = r[1]
            block[2][5] = r[2]
            // off-diagonals: xy, xz, yz
            block[0][6] = r[1]
            block[1][6] = r[0]
            block[0][7] = r[2]
            block[2][7] = r[0]
            block[1][8] = r[2]
            block[2][8] = r[1]
        }
        if (fitMotor) {
            for (let k = 0; k < 3; k++) {
                block[k][motorCol + k] = current[i]
            }
        }

        const w = sqrtWeights[i]
        if (down === null) {
            for (let k = 0; k < 3; k++) {
                const row = j * 3 + k
                for (let c = 0; c < cols; c++) {
                    A[c * rows + row] = w * block[k][c]
                }
                b[row] = w * rhs[k]
            }
            continue
        }

        const d = down[j]
        const vertical = e[0] * d[0] + e[1] * d[1] + e[2] * d[2]
        const h = [e[0] - vertical * d[0], e[1] - vertical * d[1], e[2] - vertical * d[2]]
        const hNorm = Math.hypot(h[0], h[1], h[2])
        const directions = [hNorm > 0 ? h.map(v => v / hNorm) : [0, 0, 0], d]
        for (let k = 0; k < 2; k++) {
            const u = directions[k]
            const row = j * 2 + k
            for (let c = 0; c < cols; c++) {
                A[c * rows + row] = w * (u[0] * block[0][c] + u[1] * block[1][c] + u[2] * block[2][c])
            }
            b[row] = w * (u[0] * rhs[0] + u[1] * rhs[1] + u[2] * rhs[2])
        }
    }

    const x = solveLeastSquares(A, b, rows, cols)
    if (x === null) {
        return { error: UNOBSERVABLE }
    }

    const cal = identityCalibration()
    if (fitMotor) {
        cal.motor = x.slice(motorCol, motorCol + 3)
    }
    if (fitType === 'offsets') {
        cal.offsets = x.slice(0, 3)
    } else if (fitType === 'scale') {
        const scale = x[3]
        if (!scaleValid(scale)) {
            return {
                error: `Fit failed: the best fit scale (${scale.toFixed(3)}) is outside the range the firmware ` +
                    `applies (${(1 / MAX_SCALE_FACTOR).toFixed(3)} to ${MAX_SCALE_FACTOR}), the expected field ` +
                    'does not match the data (check the location and yaw source)'
            }
        }
        cal.scale = scale
        cal.offsets = x.slice(0, 3).map(v => v / scale)
    } else {
        const diagonals = x.slice(3, 6)
        const offDiagonals = x.slice(6, 9)
        const inv = invert3(ironMatrix(diagonals, offDiagonals))
        if (inv === null) {
            return { error: UNOBSERVABLE }
        }
        cal.offsets = mul3(inv, x[0], x[1], x[2])
        // Normalise the iron matrix into the scale param like WebTools, unless
        // the firmware would then ignore the scale: keep it all in DIA/ODI so the
        // params still give the fitted correction
        const scale = (diagonals[0] + diagonals[1] + diagonals[2]) / 3
        const norm = scaleValid(scale) ? scale : 1
        cal.scale = norm
        cal.diagonals = diagonals.map(v => v / norm)
        cal.offDiagonals = offDiagonals.map(v => v / norm)
    }
    return { cal }
}

// Attitude coverage bins, as in WebTools MAGFit: a Fibonacci lattice of
// directions, each sample goes in the bin nearest its expected field direction
export const NUM_BINS = 80
const BIN_DIRECTIONS = (() => {
    const out = []
    for (let i = 0; i < NUM_BINS; i++) {
        const k = i + 0.5
        const phi = Math.acos(1 - 2 * k / NUM_BINS)
        const theta = Math.PI * (1 + Math.sqrt(5)) * k
        out.push([Math.cos(theta) * Math.sin(phi), Math.sin(theta) * Math.sin(phi), Math.cos(phi)])
    }
    return out
})()

function nearestBin (x, y, z) {
    let best = -1
    let bestDot = -Infinity
    for (let k = 0; k < NUM_BINS; k++) {
        const d = BIN_DIRECTIONS[k]
        const dot = d[0] * x + d[1] * y + d[2] * z
        if (dot > bestDot) {
            bestDot = dot
            best = k
        }
    }
    return best
}

// Starting yaw for a sample: attitude yaw if available, otherwise the heading
// of the raw field
function startingYaw (earthField, raw, roll, pitch, yaw, i) {
    if (yaw && Number.isFinite(yaw[i])) {
        return yaw[i]
    }
    return magHeading(raw.x[i], raw.y[i], raw.z[i], roll[i], pitch[i]) + declinationOf(earthField)
}

// Bin of each sample's expected field direction (using the attitude yaw where
// available, otherwise the raw heading), -1 where the sample is not usable
export function fieldBins ({ raw, roll, pitch, yaw, earthField }) {
    return Array.from(raw.x, (v, i) => sampleBin(earthField, raw, roll, pitch, yaw, i))
}

function sampleBin (earthField, raw, roll, pitch, yaw, i) {
    const v = bodyFrameField(earthField, roll[i], pitch[i], startingYaw(earthField, raw, roll, pitch, yaw, i))
    const len = Math.hypot(v[0], v[1], v[2])
    return len > 0 ? nearestBin(v[0] / len, v[1] / len, v[2] / len) : -1
}

// WebTools weighting: each occupied bin gets the same total weight, scaled so
// the mean weight is 1. Samples with bin -1 get weight 0. coverage is the
// fraction of bins with samples.
export function binWeights (bins) {
    const count = new Array(NUM_BINS).fill(0)
    let total = 0
    let occupied = 0
    for (const b of bins) {
        if (b >= 0) {
            if (count[b] === 0) {
                occupied++
            }
            count[b]++
            total++
        }
    }
    const meanBinSize = occupied > 0 ? total / occupied : 0
    return {
        weights: Array.from(bins, b => b >= 0 ? meanBinSize / count[b] : 0),
        coverage: occupied / NUM_BINS
    }
}

// Bin weighted RMS of errors, skipping non-finite errors
export function weightedRms (errors, bins) {
    const used = Array.from(bins, (b, i) => Number.isFinite(errors[i]) ? b : -1)
    const { weights } = binWeights(used)
    let sum = 0
    let count = 0
    for (let i = 0; i < used.length; i++) {
        if (used[i] >= 0) {
            sum += weights[i] * errors[i] ** 2
            count++
        }
    }
    return count > 0 ? Math.sqrt(sum / count) : NaN
}

// Positions of at most max samples (or one per occupied bin, if more), taking
// the same number from every bin that has enough, spread evenly in time within
// the bin, and all samples of the bins that don't. With the bin weighting this
// keeps every bin's share of the cost while rare attitudes survive.
export function binnedSubset (bins, max) {
    if (!(bins.length > max)) {
        return [...bins.keys()]
    }
    const members = Array.from({ length: NUM_BINS }, () => [])
    bins.forEach((b, k) => members[b].push(k))
    const sizes = members.map(m => m.length).filter(size => size > 0).sort((a, b) => a - b)
    let remaining = max
    let left = sizes.length
    let cap = 1
    for (const size of sizes) {
        if (size * left > remaining) {
            cap = Math.max(1, Math.floor(remaining / left))
            break
        }
        remaining -= size
        left--
    }
    return members.flatMap(m => strideIndices(m, cap)).sort((a, b) => a - b)
}

// Smallest eigenvalue of a symmetric 3x3 matrix (closed form)
function minEigenvalue3 (m) {
    const p1 = m[0][1] ** 2 + m[0][2] ** 2 + m[1][2] ** 2
    if (p1 === 0) {
        return Math.min(m[0][0], m[1][1], m[2][2])
    }
    const q = (m[0][0] + m[1][1] + m[2][2]) / 3
    const p = Math.sqrt(((m[0][0] - q) ** 2 + (m[1][1] - q) ** 2 + (m[2][2] - q) ** 2 + 2 * p1) / 6)
    const shifted = m.map((row, i) => row.map((v, j) => (v - (i === j ? q : 0)) / p))
    const r = Math.min(1, Math.max(-1, determinant3(shifted) / 2))
    return q + 2 * p * Math.cos(Math.acos(r) / 3 + 2 * Math.PI / 3)
}

// How much the direction of the expected (body frame) field varies: the
// standard deviation of the unit field vector in the direction it varies
// least. About 0 for level flight, where only the yaw changes. Samples are
// weighted by weights if given (the same weighting as the fit).
export function fieldExcitation (expected, weights = null) {
    const n = expected.x.length
    const units = []
    const unitWeights = []
    for (let j = 0; j < n; j++) {
        const len = Math.hypot(expected.x[j], expected.y[j], expected.z[j])
        const w = weights ? weights[j] : 1
        if (len > 0 && w > 0) {
            units.push([expected.x[j] / len, expected.y[j] / len, expected.z[j] / len])
            unitWeights.push(w)
        }
    }
    if (units.length < 2) {
        return 0
    }
    const totalWeight = unitWeights.reduce((sum, w) => sum + w, 0)
    const mean = [0, 1, 2].map(k => units.reduce((sum, u, j) => sum + unitWeights[j] * u[k], 0) / totalWeight)
    const cov = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    units.forEach((u, j) => {
        const w = unitWeights[j] / totalWeight
        for (let a = 0; a < 3; a++) {
            for (let b = 0; b < 3; b++) {
                cov[a][b] += w * (u[a] - mean[a]) * (u[b] - mean[b])
            }
        }
    })
    return Math.sqrt(Math.max(0, minEigenvalue3(cov)))
}

function subsetField (field, indices) {
    const out = emptyField(indices.length)
    for (let j = 0; j < indices.length; j++) {
        const i = indices[j]
        out.x[j] = field.x[i]
        out.y[j] = field.y[i]
        out.z[j] = field.z[i]
    }
    return out
}

function subset (values, indices) {
    return indices.map(i => values[i])
}

// Evenly spaced subset of at most max indices
export function strideIndices (indices, max) {
    if (!(indices.length > max)) {
        return indices
    }
    const out = []
    const step = indices.length / max
    for (let k = 0; k < max; k++) {
        out.push(indices[Math.floor(k * step)])
    }
    return out
}

function failure (message) {
    return { ok: false, message }
}

// Fit a calibration to raw (uncalibrated) compass data.
//
// raw: raw field, roll/pitch/yaw: attitude interpolated to the compass samples
// (yaw is required for yawSource 'att' and is used as the starting point for
// 'mag'), current: battery current at the compass samples (required for
// fitMotor), earthField: NED earth field in mGauss.
//
// With yawSource 'att' the problem is linear and solved in one step. With
// 'mag' the expected field depends on the calibration through the compass
// heading, so starting from the linear solution the problem is re-linearised
// with the heading from the latest solution until the cost stops improving.
// Each pass takes a Gauss-Newton step, or if that doesn't reduce the cost,
// re-solves with the heading held fixed, so the cost never increases.
//
// Like WebTools, samples are binned by expected field direction and weighted
// so every occupied bin counts the same, otherwise a long level log swamps
// the few tilted samples that make iron observable. The cost, reported error
// and excitation check all use these weights.
//
// Returns { ok: false, message } if no fit is possible, otherwise { ok: true,
// valid, violations, cal, ... } where valid is false if any param is outside
// PARAM_RANGES (listed in violations).
export function fitCalibration ({
    raw, roll, pitch, yaw, current, earthField,
    fitType = 'offsets', fitMotor = false, yawSource = 'mag',
    maxSamples = 5000, maxIterations = 100, tolerance = 1e-9
}) {
    if (!(fitType in FIT_TYPES)) {
        return failure(`Unknown fit type ${fitType}`)
    }
    if (!(yawSource in YAW_SOURCES)) {
        return failure(`Unknown yaw source ${yawSource}`)
    }
    if (!earthField || !earthField.every(Number.isFinite) || Math.hypot(...earthField) === 0) {
        return failure('Invalid earth field, check the location')
    }
    if (!raw || !raw.x || raw.x.length === 0) {
        return failure('No compass data')
    }
    if (fitMotor && !current) {
        return failure('No battery current data for motor compensation')
    }
    const useAttYaw = yawSource === 'att'
    const hasYaw = Boolean(yaw)
    if (useAttYaw && !hasYaw) {
        return failure('No attitude yaw data')
    }

    const valid = []
    const validBins = []
    for (let i = 0; i < raw.x.length; i++) {
        if (!Number.isFinite(raw.x[i]) || !Number.isFinite(raw.y[i]) || !Number.isFinite(raw.z[i])) {
            continue
        }
        if (!Number.isFinite(roll[i]) || !Number.isFinite(pitch[i])) {
            continue
        }
        if (useAttYaw && !Number.isFinite(yaw[i])) {
            continue
        }
        if (fitMotor && !Number.isFinite(current[i])) {
            continue
        }
        const bin = sampleBin(earthField, raw, roll, pitch, yaw, i)
        if (bin < 0) {
            continue
        }
        valid.push(i)
        validBins.push(bin)
    }
    const minSamples = Math.max(MIN_SAMPLES, numColumns(fitType, fitMotor))
    if (valid.length < minSamples) {
        return failure(`Not enough valid samples (${valid.length}, need ${minSamples})`)
    }
    // Decimate by attitude bin rather than in time, so a short manoeuvre in a
    // long level log is not thinned out
    const picked = binnedSubset(validBins, maxSamples)
    const indices = picked.map(k => valid[k])
    const { weights, coverage } = binWeights(picked.map(k => validBins[k]))
    const sqrtWeights = weights.map(Math.sqrt)

    if (fitMotor) {
        let min = Infinity
        let max = -Infinity
        for (const i of indices) {
            min = Math.min(min, current[i])
            max = Math.max(max, current[i])
        }
        if (max - min < MIN_CURRENT_RANGE) {
            return failure('Battery current does not vary enough to fit motor compensation')
        }
    }

    // Work on the subset only from here
    const rawSel = subsetField(raw, indices)
    const rollSel = subset(roll, indices)
    const pitchSel = subset(pitch, indices)
    const yawSel = hasYaw ? subset(yaw, indices) : null
    const currentSel = fitMotor ? subset(current, indices) : null
    const all = [...indices.keys()]

    const evaluate = (cal) => {
        const corrected = applyCalibration(rawSel, cal, currentSel)
        const expected = useAttYaw
            ? expectedFromYaw(earthField, rollSel, pitchSel, yawSel)
            : expectedFromMagYaw(earthField, corrected, rollSel, pitchSel)
        let cost = 0
        fieldErrors(corrected, expected).forEach((e, j) => {
            cost += weights[j] * e * e
        })
        return { cost, expected }
    }

    // Starting point (and binning direction): attitude yaw if available,
    // otherwise the uncalibrated heading
    const startYaw = all.map(j => startingYaw(earthField, rawSel, rollSel, pitchSel, yawSel, j))
    const expected = expectedFromYaw(earthField, rollSel, pitchSel, startYaw)

    const excitation = fieldExcitation(expected, weights)
    if (fitType === 'iron') {
        if (!(excitation >= MIN_IRON_EXCITATION)) {
            return failure('Not enough attitude variation to fit iron: the field direction varies by ' +
                `${(excitation * 100).toFixed(1)}% in its least varied direction, need ` +
                `${MIN_IRON_EXCITATION * 100}% (mostly level flight). Fit offsets or scale instead, ` +
                'or use a log with more tilt')
        }
        if (!(coverage >= MIN_IRON_COVERAGE)) {
            return failure('Not enough attitude coverage to fit iron: the log covers ' +
                `${(coverage * 100).toFixed(0)}% of orientations (${Math.round(coverage * NUM_BINS)} of ` +
                `${NUM_BINS} bins), need ${MIN_IRON_COVERAGE * 100}%. Fit offsets or scale instead, ` +
                'or use a log with more varied attitudes')
        }
    }

    const initial = solveLinear(rawSel, expected, currentSel, sqrtWeights, all, fitType, fitMotor)
    if (initial.error) {
        return failure(initial.error)
    }
    let cal = initial.cal
    let state = evaluate(cal)
    let iterations = 1
    let converged = useAttYaw
    if (!useAttYaw) {
        const down = all.map(j => bodyFrameField([0, 0, 1], rollSel[j], pitchSel[j], 0))
        while (iterations < maxIterations) {
            // Gauss-Newton step, falling back to re-solving with the heading held
            // fixed (which can't increase the cost) if it doesn't improve
            let next = null
            let nextState = null
            for (const projection of [down, null]) {
                const solution = solveLinear(rawSel, state.expected, currentSel, sqrtWeights, all,
                    fitType, fitMotor, projection)
                if (solution.error) {
                    continue
                }
                const candidate = solution.cal
                const candidateState = evaluate(candidate)
                if (candidateState.cost <= state.cost) {
                    next = candidate
                    nextState = candidateState
                    break
                }
            }
            if (next === null) {
                // no step improves on the current solution
                converged = true
                break
            }
            const improvement = (state.cost - nextState.cost) / Math.max(state.cost, 1e-12)
            cal = next
            state = nextState
            iterations++
            if (improvement < tolerance) {
                converged = true
                break
            }
        }
    }

    // Like WebTools, a fit with any param out of range is invalid. It is still
    // returned so the values can be shown.
    const violations = rangeViolations(cal)
    return {
        ok: true,
        valid: violations.length === 0,
        violations,
        cal,
        // bin weighted, the mean weight is 1
        rmsError: Math.sqrt(state.cost / indices.length),
        numSamples: indices.length,
        coverage,
        excitation,
        iterations,
        converged
    }
}

// Parameters outside of PARAM_RANGES: [{ name, value, range }] where name is
// the param suffix (OFS_X, DIA_Y, ODI_Z, SCALE, MOT_X)
export function rangeViolations (cal) {
    const violations = []
    const check = (name, value, range) => {
        if (!(value > range[0] && value < range[1])) {
            violations.push({ name, value, range })
        }
    }
    for (let i = 0; i < 3; i++) {
        const axis = AXES[i].toUpperCase()
        check(`OFS_${axis}`, cal.offsets[i], PARAM_RANGES.offsets)
        check(`DIA_${axis}`, cal.diagonals[i], PARAM_RANGES.diagonals)
        check(`ODI_${axis}`, cal.offDiagonals[i], PARAM_RANGES.offDiagonals)
    }
    check('SCALE', cal.scale, PARAM_RANGES.scale)
    for (let i = 0; i < 3; i++) {
        check(`MOT_${AXES[i].toUpperCase()}`, cal.motor[i], PARAM_RANGES.motor)
    }
    return violations
}
