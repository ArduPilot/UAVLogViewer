import {
    applyCalibration,
    binnedSubset,
    binWeights,
    bodyFrameField,
    calibrationError,
    declinationOf,
    expectedFromYaw,
    fieldBins,
    fieldExcitation,
    fitCalibration,
    identityCalibration,
    interpolate,
    magHeading,
    MIN_IRON_COVERAGE,
    MIN_IRON_EXCITATION,
    NUM_BINS,
    rangeViolations,
    removeCalibration,
    solveLeastSquares,
    strideIndices,
    weightedRms
} from '../../../src/tools/magfit'

// NED earth field in mGauss, roughly Canberra (SITL default location)
const EARTH_FIELD = [226.8, 48.2, -520.7]

// Deterministic pseudo random numbers so the tests are repeatable
function makeRandom (seed) {
    let state = seed
    return () => {
        state = (state * 1664525 + 1013904223) % 4294967296
        return state / 4294967296
    }
}

function gaussian (random) {
    return Math.sqrt(-2 * Math.log(random() + 1e-12)) * Math.cos(2 * Math.PI * random())
}

const TRUE_CAL = {
    offsets: [120, -85, 240],
    diagonals: [1.04, 0.97, 0.99],
    offDiagonals: [0.03, -0.02, 0.015],
    scale: 1.05,
    motor: [2.5, -1.2, 4.0]
}

// Build a flight with varied attitude, the raw sensor field the given calibration
// would correct to the expected field, and the battery current.
function syntheticFlight (cal, { n = 1500, noise = 0, seed = 1, maxTilt = 60, maxYaw = 180 } = {}) {
    const random = makeRandom(seed)
    const roll = []
    const pitch = []
    const yaw = []
    const current = []
    for (let i = 0; i < n; i++) {
        roll.push((random() * 2 - 1) * maxTilt * Math.PI / 180)
        pitch.push((random() * 2 - 1) * maxTilt * Math.PI / 180)
        yaw.push((random() * 2 - 1) * maxYaw * Math.PI / 180)
        current.push(5 + 25 * Math.abs(Math.sin(i / 50)))
    }
    const expected = expectedFromYaw(EARTH_FIELD, roll, pitch, yaw)
    const measured = {
        x: expected.x.map(v => v + noise * gaussian(random)),
        y: expected.y.map(v => v + noise * gaussian(random)),
        z: expected.z.map(v => v + noise * gaussian(random))
    }
    const motorOffsets = {
        x: current.map(a => a * cal.motor[0]),
        y: current.map(a => a * cal.motor[1]),
        z: current.map(a => a * cal.motor[2])
    }
    const raw = removeCalibration(measured, { ...cal, motorOffsets })
    return { raw, roll, pitch, yaw, current, expected }
}

function expectClose (actual, expected, tolerance) {
    expect(actual.length).toBe(expected.length)
    for (let i = 0; i < expected.length; i++) {
        expect(Math.abs(actual[i] - expected[i])).toBeLessThan(tolerance)
    }
}

describe('solveLeastSquares', () => {
    test('solves an overdetermined consistent system', () => {
        // columns [1, t, t^2], b = 3 - 2t + 0.5t^2
        const rows = 20
        const A = new Float64Array(rows * 3)
        const b = new Float64Array(rows)
        for (let r = 0; r < rows; r++) {
            const t = r - 7
            A[r] = 1
            A[rows + r] = t
            A[2 * rows + r] = t * t
            b[r] = 3 - 2 * t + 0.5 * t * t
        }
        expectClose(solveLeastSquares(A, b, rows, 3), [3, -2, 0.5], 1e-9)
    })

    test('returns null for rank deficient systems', () => {
        const rows = 10
        const A = new Float64Array(rows * 2)
        const b = new Float64Array(rows)
        for (let r = 0; r < rows; r++) {
            A[r] = r
            A[rows + r] = 2 * r
            b[r] = r
        }
        expect(solveLeastSquares(A, b, rows, 2)).toBeNull()
        expect(solveLeastSquares(new Float64Array(4), new Float64Array(2), 2, 2)).toBeNull()
    })
})

describe('calibration model', () => {
    test('removeCalibration undoes applyCalibration', () => {
        const raw = { x: [100, -250, 30], y: [12, 400, -90], z: [-300, 50, 610] }
        const current = [0, 10, 35]
        const corrected = applyCalibration(raw, TRUE_CAL, current)
        const motorOffsets = {
            x: current.map(a => a * TRUE_CAL.motor[0]),
            y: current.map(a => a * TRUE_CAL.motor[1]),
            z: current.map(a => a * TRUE_CAL.motor[2])
        }
        const back = removeCalibration(corrected, { ...TRUE_CAL, motorOffsets })
        expectClose(back.x, raw.x, 1e-9)
        expectClose(back.y, raw.y, 1e-9)
        expectClose(back.z, raw.z, 1e-9)
    })

    test('order of operations matches the firmware', () => {
        // offsets, then scale, then iron, then motor
        const cal = {
            offsets: [10, 0, 0],
            diagonals: [2, 1, 1],
            offDiagonals: [0, 0, 0],
            scale: 1.25,
            motor: [1, 0, 0]
        }
        const out = applyCalibration({ x: [2], y: [0], z: [0] }, cal, [3])
        expect(out.x[0]).toBeCloseTo((2 + 10) * 1.25 * 2 + 3, 9)
    })

    test('logged scale the firmware ignores and zero diagonals are not removed', () => {
        const cal = { offsets: [1, 2, 3], diagonals: [0, 0, 0], offDiagonals: [0, 0, 0], scale: 0, motor: [0, 0, 0] }
        const back = removeCalibration({ x: [2], y: [3], z: [4] }, cal)
        expectClose([back.x[0], back.y[0], back.z[0]], [1, 1, 1], 1e-12)
        const out = applyCalibration(back, { ...cal, scale: 1 })
        expectClose([out.x[0], out.y[0], out.z[0]], [2, 3, 4], 1e-12)
    })

    test('applyCalibration refuses a scale the firmware would ignore', () => {
        const raw = { x: [1], y: [1], z: [1] }
        for (const scale of [0, 0.6, 1.6, NaN]) {
            expect(() => applyCalibration(raw, { ...identityCalibration(), scale })).toThrow()
        }
    })

    test('removeCalibration undoes params that change per sample', () => {
        const raw = { x: [100, -250, 30, 75], y: [12, 400, -90, 5], z: [-300, 50, 610, -20] }
        const calA = { ...TRUE_CAL, motor: [0, 0, 0], scale: 0.954 }
        const calB = { ...calA, scale: 1.0055, diagonals: [1.02, 0.98, 1.0], offDiagonals: [0, 0.01, 0] }
        const cals = [calA, calA, calB, calB]
        const logged = { x: [], y: [], z: [] }
        cals.forEach((cal, i) => {
            const out = applyCalibration({ x: [raw.x[i]], y: [raw.y[i]], z: [raw.z[i]] }, cal)
            logged.x.push(out.x[0])
            logged.y.push(out.y[0])
            logged.z.push(out.z[0])
        })
        const perSample = key => ({
            x: cals.map(c => c[key][0]),
            y: cals.map(c => c[key][1]),
            z: cals.map(c => c[key][2])
        })
        const back = removeCalibration(logged, {
            offsets: calA.offsets,
            diagonals: perSample('diagonals'),
            offDiagonals: perSample('offDiagonals'),
            scale: cals.map(c => c.scale)
        })
        expectClose(back.x, raw.x, 1e-9)
        expectClose(back.y, raw.y, 1e-9)
        expectClose(back.z, raw.z, 1e-9)
    })

    test('singular iron matrix cannot be removed', () => {
        const cal = { offsets: [0, 0, 0], diagonals: [1, 1, 0], offDiagonals: [0, 0, 0], scale: 1 }
        expect(removeCalibration({ x: [1], y: [1], z: [1] }, cal)).toBeNull()
    })
})

describe('attitude helpers', () => {
    test('interpolate is linear and NaN outside the data', () => {
        const out = interpolate([0, 10, 20], [0, 100, 300], [-1, 0, 5, 10, 15, 20, 21])
        expect(out[0]).toBeNaN()
        expectClose(out.slice(1, 6), [0, 50, 100, 200, 300], 1e-12)
        expect(out[6]).toBeNaN()
    })

    test('interpolate wraps angles', () => {
        const out = interpolate([0, 10], [350, 10], [5], 360)
        expect(Math.abs(((out[0] % 360) + 360) % 360)).toBeLessThan(1e-9)
    })

    test('magnetic heading of the expected field gives back the yaw', () => {
        const declination = declinationOf(EARTH_FIELD)
        for (const [roll, pitch, yaw] of [[0, 0, 0.3], [0.5, -0.4, 2.0], [-0.9, 0.7, -2.5]]) {
            const field = bodyFrameField(EARTH_FIELD, roll, pitch, yaw)
            const heading = magHeading(field[0], field[1], field[2], roll, pitch) + declination
            const diff = Math.atan2(Math.sin(heading - yaw), Math.cos(heading - yaw))
            expect(Math.abs(diff)).toBeLessThan(1e-9)
        }
    })
})

describe('fitCalibration', () => {
    const cases = [
        ['offsets', false, { ...identityCalibration(), offsets: [120, -85, 240] }],
        ['scale', false, { ...identityCalibration(), offsets: [120, -85, 240], scale: 1.08 }],
        ['iron', false, { ...TRUE_CAL, motor: [0, 0, 0] }],
        ['offsets', true, { ...identityCalibration(), offsets: [120, -85, 240], motor: [2.5, -1.2, 4.0] }],
        ['scale', true, { ...identityCalibration(), offsets: [120, -85, 240], scale: 0.93, motor: [2.5, -1.2, 4.0] }],
        ['iron', true, TRUE_CAL]
    ]

    for (const yawSource of ['att', 'mag']) {
        test.each(cases)(`recovers %s (motor: %s) without noise, yaw source ${yawSource}`, (fitType, fitMotor, cal) => {
            const flight = syntheticFlight(cal)
            const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitType, fitMotor, yawSource })
            expect(result.ok).toBe(true)
            expect(result.valid).toBe(true)
            expect(result.violations).toEqual([])
            expect(result.converged).toBe(true)
            expect(result.rmsError).toBeLessThan(0.05)
            expectClose(result.cal.offsets, cal.offsets, 0.05)
            expectClose(result.cal.diagonals, cal.diagonals, 1e-4)
            expectClose(result.cal.offDiagonals, cal.offDiagonals, 1e-4)
            expect(Math.abs(result.cal.scale - cal.scale)).toBeLessThan(1e-4)
            expectClose(result.cal.motor, cal.motor, 1e-3)
        })

        const noisyName = `recovers %s (motor: %s) with 5 mGauss noise, yaw source ${yawSource}`
        test.each(cases)(noisyName, (fitType, fitMotor, cal) => {
            const flight = syntheticFlight(cal, { noise: 5, seed: 7 })
            const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitType, fitMotor, yawSource })
            expect(result.ok).toBe(true)
            // per axis noise of 5 gives an error length of about 5 * sqrt(3)
            expect(result.rmsError).toBeLessThan(10)
            expectClose(result.cal.offsets, cal.offsets, 3)
            expectClose(result.cal.diagonals, cal.diagonals, 0.01)
            expectClose(result.cal.offDiagonals, cal.offDiagonals, 0.01)
            expect(Math.abs(result.cal.scale - cal.scale)).toBeLessThan(0.01)
            expectClose(result.cal.motor, cal.motor, 0.15)
        })
    }

    test('compass yaw is not biased by a wrong attitude yaw', () => {
        // EKF yaw off by 30 deg (for example because it used the bad compass)
        const cal = { ...identityCalibration(), offsets: [120, -85, 240] }
        const flight = syntheticFlight(cal, { noise: 2, seed: 3 })
        const badYaw = flight.yaw.map(y => y + 30 * Math.PI / 180)
        const mag = fitCalibration({ ...flight, yaw: badYaw, earthField: EARTH_FIELD, yawSource: 'mag' })
        expect(mag.ok).toBe(true)
        expectClose(mag.cal.offsets, cal.offsets, 1)
        const att = fitCalibration({ ...flight, yaw: badYaw, earthField: EARTH_FIELD, yawSource: 'att' })
        expect(att.ok).toBe(true)
        expect(att.rmsError).toBeGreaterThan(mag.rmsError * 10)
    })

    test('compass yaw works without attitude yaw', () => {
        const cal = { ...identityCalibration(), offsets: [-300, 45, 80], scale: 1.1 }
        const flight = syntheticFlight(cal)
        const result = fitCalibration({ ...flight, yaw: null, earthField: EARTH_FIELD, fitType: 'scale' })
        expect(result.ok).toBe(true)
        expectClose(result.cal.offsets, cal.offsets, 0.05)
        expect(Math.abs(result.cal.scale - 1.1)).toBeLessThan(1e-4)
    })

    test('is deterministic', () => {
        const flight = syntheticFlight(TRUE_CAL, { noise: 5, seed: 11 })
        const options = { ...flight, earthField: EARTH_FIELD, fitType: 'iron', fitMotor: true, yawSource: 'mag' }
        expect(fitCalibration(options)).toEqual(fitCalibration(options))
    })

    test('skips samples with NaN values', () => {
        const cal = { ...identityCalibration(), offsets: [50, 60, -70] }
        const flight = syntheticFlight(cal)
        for (let i = 0; i < 100; i++) {
            flight.raw.x[i * 7] = NaN
            flight.roll[i * 11 + 1] = NaN
            flight.yaw[i * 13 + 2] = undefined
            flight.current[i * 5 + 3] = NaN
        }
        for (const yawSource of ['att', 'mag']) {
            const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitMotor: true, yawSource })
            expect(result.ok).toBe(true)
            expectClose(result.cal.offsets, cal.offsets, 0.05)
        }
    })

    test('fails cleanly without enough data', () => {
        const base = { earthField: EARTH_FIELD, roll: [], pitch: [], yaw: [] }
        expect(fitCalibration({ ...base, raw: { x: [], y: [], z: [] } }).ok).toBe(false)
        expect(fitCalibration({ ...base, raw: null }).ok).toBe(false)
        const flight = syntheticFlight(TRUE_CAL, { n: 10 })
        expect(fitCalibration({ ...flight, earthField: EARTH_FIELD }).ok).toBe(false)
        const nanFlight = syntheticFlight(TRUE_CAL)
        nanFlight.roll.fill(NaN)
        expect(fitCalibration({ ...nanFlight, earthField: EARTH_FIELD }).ok).toBe(false)
    })

    test('fails cleanly when parameters are not observable', () => {
        // constant attitude: iron cannot be separated from offsets
        const flight = syntheticFlight(TRUE_CAL, { maxTilt: 0 })
        flight.yaw.fill(0.3)
        flight.raw = removeCalibration(expectedFromYaw(EARTH_FIELD, flight.roll, flight.pitch, flight.yaw), TRUE_CAL)
        const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitType: 'iron', yawSource: 'att' })
        expect(result.ok).toBe(false)

        // constant current: motor compensation cannot be separated from offsets
        const steady = syntheticFlight(TRUE_CAL)
        steady.current.fill(12)
        const motor = fitCalibration({ ...steady, earthField: EARTH_FIELD, fitMotor: true })
        expect(motor.ok).toBe(false)
        expect(motor.message).toMatch(/current/)

        expect(fitCalibration({ ...steady, earthField: EARTH_FIELD, fitMotor: true, current: null }).ok).toBe(false)
        expect(fitCalibration({ ...steady, earthField: [NaN, 0, 0] }).ok).toBe(false)
        expect(fitCalibration({ ...steady, earthField: EARTH_FIELD, fitType: 'bogus' }).ok).toBe(false)
    })

    test('rejects iron fits on low tilt data, offsets and scale still work', () => {
        // +-7 deg of roll and pitch with full yaw rotation, the Z diagonal and
        // offset can't be separated
        const cal = { ...identityCalibration(), offsets: [120, -85, 240], scale: 1.05 }
        const flight = syntheticFlight(cal, { noise: 3, seed: 5, maxTilt: 7 })
        const expected = expectedFromYaw(EARTH_FIELD, flight.roll, flight.pitch, flight.yaw)
        expect(fieldExcitation(expected)).toBeLessThan(MIN_IRON_EXCITATION)
        expect(fieldExcitation(syntheticFlight(cal).expected)).toBeGreaterThan(MIN_IRON_EXCITATION)
        for (const yawSource of ['att', 'mag']) {
            for (const fitMotor of [false, true]) {
                const options = { ...flight, earthField: EARTH_FIELD, fitMotor, yawSource }
                const iron = fitCalibration({ ...options, fitType: 'iron' })
                expect(iron.ok).toBe(false)
                expect(iron.message).toMatch(/attitude variation/)
                const scale = fitCalibration({ ...options, fitType: 'scale' })
                expect(scale.ok).toBe(true)
                expect(scale.valid).toBe(true)
                expect(Math.abs(scale.cal.scale - 1.05)).toBeLessThan(0.01)
                expectClose(scale.cal.offsets, cal.offsets, 10)
            }
        }
    })

    test('rejects iron fits with too little attitude coverage, even with enough tilt', () => {
        // +-30 deg of roll and pitch but only +-60 deg of yaw: the field direction
        // varies enough, but only in a few directions
        const cal = { ...identityCalibration(), offsets: [120, -85, 240], scale: 1.05 }
        const flight = syntheticFlight(cal, { noise: 3, seed: 3, maxTilt: 30, maxYaw: 60 })
        for (const yawSource of ['att', 'mag']) {
            for (const fitMotor of [false, true]) {
                const options = { ...flight, earthField: EARTH_FIELD, fitMotor, yawSource }
                const offsets = fitCalibration({ ...options, fitType: 'offsets' })
                expect(offsets.ok).toBe(true)
                expect(offsets.coverage).toBeLessThan(MIN_IRON_COVERAGE)
                expect(offsets.excitation).toBeGreaterThan(2 * MIN_IRON_EXCITATION)
                const iron = fitCalibration({ ...options, fitType: 'iron' })
                expect(iron.ok).toBe(false)
                expect(iron.message).toMatch(/coverage.* \d+% of orientations .*need 30%.*offsets or scale/)
                const scale = fitCalibration({ ...options, fitType: 'scale' })
                expect(scale.ok).toBe(true)
                expect(scale.valid).toBe(true)
                expect(Math.abs(scale.cal.scale - 1.05)).toBeLessThan(0.01)
            }
        }
    })

    // A long, mostly level flight with full yaw rotation and low current, then a
    // short segment with lots of tilt and current
    function levelThenTilted (cal, { nLevel = 50000, nTilted = 400, noise = 3, seed = 21 } = {}) {
        const random = makeRandom(seed)
        const roll = []
        const pitch = []
        const yaw = []
        const current = []
        for (let i = 0; i < nLevel; i++) {
            roll.push(gaussian(random) * Math.PI / 180)
            pitch.push(gaussian(random) * Math.PI / 180)
            yaw.push((i / nLevel) * 12 * Math.PI % (2 * Math.PI) - Math.PI)
            current.push(3 + Math.sin(i / 700))
        }
        for (let i = 0; i < nTilted; i++) {
            roll.push((random() * 2 - 1) * 45 * Math.PI / 180)
            pitch.push((random() * 2 - 1) * 45 * Math.PI / 180)
            yaw.push((random() * 2 - 1) * Math.PI)
            current.push(5 + 25 * Math.abs(Math.sin(i / 20)))
        }
        const expected = expectedFromYaw(EARTH_FIELD, roll, pitch, yaw)
        const measured = {
            x: expected.x.map(v => v + noise * gaussian(random)),
            y: expected.y.map(v => v + noise * gaussian(random)),
            z: expected.z.map(v => v + noise * gaussian(random))
        }
        const motorOffsets = {
            x: current.map(a => a * cal.motor[0]),
            y: current.map(a => a * cal.motor[1]),
            z: current.map(a => a * cal.motor[2])
        }
        const raw = removeCalibration(measured, { ...cal, motorOffsets })
        return { raw, roll, pitch, yaw, current, expected }
    }

    test('binning keeps a short tilted segment of a long level log', () => {
        const flight = levelThenTilted(TRUE_CAL)
        // thinning evenly in time keeps too little tilt for the iron check
        const thinned = strideIndices([...flight.roll.keys()], 4000)
        const thinnedExpected = expectedFromYaw(EARTH_FIELD, flight.roll, flight.pitch, flight.yaw, thinned)
        expect(fieldExcitation(thinnedExpected)).toBeLessThan(MIN_IRON_EXCITATION)

        for (const yawSource of ['att', 'mag']) {
            const result = fitCalibration({
                ...flight, earthField: EARTH_FIELD, fitType: 'iron', fitMotor: true, yawSource, maxSamples: 4000
            })
            expect(result.ok).toBe(true)
            expect(result.valid).toBe(true)
            expect(result.numSamples).toBeLessThanOrEqual(4000)
            expect(result.excitation).toBeGreaterThan(4 * MIN_IRON_EXCITATION)
            expect(result.coverage).toBeGreaterThan(0.3)
            expectClose(result.cal.offsets, TRUE_CAL.offsets, 2)
            expectClose(result.cal.diagonals, TRUE_CAL.diagonals, 0.005)
            expectClose(result.cal.offDiagonals, TRUE_CAL.offDiagonals, 0.005)
            expect(Math.abs(result.cal.scale - TRUE_CAL.scale)).toBeLessThan(0.005)
            expectClose(result.cal.motor, TRUE_CAL.motor, 0.05)
        }
    })

    test('a SCALE change during the log is undone per sample', () => {
        // the vehicle used COMPASS_SCALE 0.954 for the first half and 1.0055 after
        const flight = syntheticFlight(TRUE_CAL, { noise: 1, seed: 9 })
        const n = flight.raw.x.length
        const vehicleScale = flight.raw.x.map((v, i) => i < n / 2 ? 0.954 : 1.0055)
        const vehicleCal = { ...identityCalibration(), offsets: [10, -5, 20] }
        const logged = applyCalibration(flight.raw, vehicleCal)
        for (let i = 0; i < n; i++) {
            for (const axis of ['x', 'y', 'z']) {
                logged[axis][i] *= vehicleScale[i]
            }
        }
        const fit = raw => fitCalibration({
            ...flight, raw, earthField: EARTH_FIELD, fitType: 'iron', fitMotor: true, yawSource: 'mag'
        })

        const perSample = fit(removeCalibration(logged, { offsets: vehicleCal.offsets, scale: vehicleScale }))
        expect(perSample.ok).toBe(true)
        expect(perSample.rmsError).toBeLessThan(3)
        expectClose(perSample.cal.offsets, TRUE_CAL.offsets, 0.5)
        expect(Math.abs(perSample.cal.scale - TRUE_CAL.scale)).toBeLessThan(0.002)

        // with the end of log value for the whole log, half the data is 5% off
        const lastValue = fit(removeCalibration(logged, { offsets: vehicleCal.offsets, scale: 1.0055 }))
        expect(lastValue.rmsError).toBeGreaterThan(5 * perSample.rmsError)
    })

    // Data that needs the field shrunk by factor: raw = expected / factor - offsets
    function shrunkFlight (factor) {
        const flight = syntheticFlight(identityCalibration())
        const offsets = [40, -30, 60]
        flight.raw = {
            x: flight.expected.x.map(v => v / factor - offsets[0]),
            y: flight.expected.y.map(v => v / factor - offsets[1]),
            z: flight.expected.z.map(v => v / factor - offsets[2])
        }
        return { flight, offsets }
    }

    test('scale fit outside of the typical range is invalid but reported', () => {
        const { flight, offsets } = shrunkFlight(0.75)
        for (const yawSource of ['att', 'mag']) {
            const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitType: 'scale', yawSource })
            expect(result.ok).toBe(true)
            expect(result.valid).toBe(false)
            expect(result.violations.map(v => v.name)).toEqual(['SCALE'])
            expect(Math.abs(result.cal.scale - 0.75)).toBeLessThan(1e-4)
            expectClose(result.cal.offsets, offsets, 0.05)
            // the reported error is the error of the params as written
            expect(result.rmsError).toBeLessThan(0.05)
        }
    })

    test('scale the firmware would ignore is never returned', () => {
        const { flight, offsets } = shrunkFlight(0.6)
        for (const yawSource of ['att', 'mag']) {
            const options = { ...flight, earthField: EARTH_FIELD, yawSource }
            const scale = fitCalibration({ ...options, fitType: 'scale' })
            expect(scale.ok).toBe(false)
            expect(scale.message).toMatch(/scale \(0\.600\)/)

            // iron can't be normalised into SCALE 0.6, so it stays in DIA with
            // SCALE 1 and the params still give the fitted correction
            const iron = fitCalibration({ ...options, fitType: 'iron' })
            expect(iron.ok).toBe(true)
            expect(iron.valid).toBe(false)
            expect(iron.cal.scale).toBe(1)
            expectClose(iron.cal.diagonals, [0.6, 0.6, 0.6], 1e-4)
            expectClose(iron.cal.offsets, offsets, 0.05)
            expect(iron.rmsError).toBeLessThan(0.05)
            expect(iron.violations.map(v => v.name)).toEqual(['DIA_X', 'DIA_Y', 'DIA_Z'])
        }
    })

    test('iron in the firmware scale range is normalised into SCALE', () => {
        const { flight } = shrunkFlight(0.9)
        const result = fitCalibration({ ...flight, earthField: EARTH_FIELD, fitType: 'iron', yawSource: 'att' })
        expect(result.valid).toBe(true)
        expect(Math.abs(result.cal.scale - 0.9)).toBeLessThan(1e-4)
        expectClose(result.cal.diagonals, [1, 1, 1], 1e-4)
    })
})

describe('calibrationError', () => {
    test('is zero for a perfect calibration with either yaw source', () => {
        const flight = syntheticFlight(TRUE_CAL)
        const corrected = applyCalibration(flight.raw, TRUE_CAL, flight.current)
        for (const yawSource of ['att', 'mag']) {
            const error = calibrationError({ corrected, ...flight, earthField: EARTH_FIELD, yawSource })
            expect(error.rms).toBeLessThan(1e-6)
        }
    })
})

describe('binning', () => {
    test('every lattice direction is its own bin and the bins cover the sphere', () => {
        const bins = new Set()
        const random = makeRandom(4)
        for (let i = 0; i < 20000; i++) {
            const v = [gaussian(random), gaussian(random), gaussian(random)]
            bins.add(fieldBins({
                raw: { x: [0], y: [0], z: [0] },
                roll: [0],
                pitch: [0],
                yaw: [0],
                earthField: v
            })[0])
        }
        expect(bins.size).toBe(NUM_BINS)
        expect(Math.min(...bins)).toBe(0)
        expect(Math.max(...bins)).toBe(NUM_BINS - 1)
    })

    test('weights give each occupied bin the same total, with a mean of 1', () => {
        const { weights, coverage } = binWeights([3, 3, 3, 7, -1])
        expectClose(weights, [2 / 3, 2 / 3, 2 / 3, 2, 0], 1e-12)
        expect(coverage).toBe(2 / NUM_BINS)
        // rare bins count as much as common ones
        expect(weightedRms([1, 1, 1, 3, 100], [3, 3, 3, 7, -1])).toBeCloseTo(Math.sqrt((3 * 2 / 3 + 9 * 2) / 4), 12)
        expect(weightedRms([1, NaN, 1, 3], [3, 3, 3, 7])).toBeCloseTo(Math.sqrt(5), 12)
    })

    test('subset keeps small bins whole and thins large ones evenly', () => {
        const bins = [...new Array(1000).fill(0), 1, 1, 1, ...new Array(10).fill(2)]
        const picked = binnedSubset(bins, 100)
        expect(picked.length).toBeLessThanOrEqual(100)
        const counts = [0, 1, 2].map(b => picked.filter(k => bins[k] === b).length)
        expect(counts).toEqual([87, 3, 10])
        // spread over the whole of the large bin
        expect(picked[0]).toBe(0)
        expect(picked[86]).toBeGreaterThan(980)
        expect(binnedSubset([0, 1, 2], 100)).toEqual([0, 1, 2])
    })
})

describe('rangeViolations', () => {
    test('flags values outside the valid ranges', () => {
        expect(rangeViolations(identityCalibration())).toEqual([])
        const cal = {
            offsets: [1600, 0, -1501],
            diagonals: [1, 0.7, 1],
            offDiagonals: [0, 0, 0.25],
            scale: 1.3,
            motor: [0, 1200, 0]
        }
        expect(rangeViolations(cal).map(w => w.name)).toEqual(['OFS_X', 'DIA_Y', 'OFS_Z', 'ODI_Z', 'SCALE', 'MOT_Y'])
        expect(rangeViolations({ ...identityCalibration(), scale: NaN }).map(w => w.name)).toEqual(['SCALE'])
        // the limits themselves are out of range, like WebTools
        expect(rangeViolations({ ...identityCalibration(), scale: 0.8 }).map(w => w.name)).toEqual(['SCALE'])
    })
})
