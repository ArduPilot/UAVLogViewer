import Vue from 'vue'
import { ParamSeeker } from '../../../src/tools/paramseeker'
import { applyCalibration, identityCalibration } from '../../../src/tools/magfit'

global._COMMIT_ = 'test'
global._BUILDDATE_ = 'test'
const { store } = require('../../../src/components/Globals.js')
const MagFitTool = require('../../../src/components/widgets/MagFitTool.vue').default

const N = 600
const CHANGE_TIME = 30000
const time = [...Array(N).keys()].map(i => i * 100)
const raw = {
    x: time.map((t, i) => 200 * Math.sin(i / 10) + 30),
    y: time.map((t, i) => 150 * Math.cos(i / 13) - 40),
    z: time.map((t, i) => -400 + 50 * Math.sin(i / 7))
}
const current = time.map((t, i) => 4 + 10 * Math.abs(Math.sin(i / 20)))

// Field the vehicle logged with cal(i) applied to each sample
function logField (cal) {
    const out = { x: [], y: [], z: [] }
    for (let i = 0; i < N; i++) {
        const v = applyCalibration({ x: [raw.x[i]], y: [raw.y[i]], z: [raw.z[i]] }, cal(i), [current[i]])
        out.x.push(v.x[0])
        out.y.push(v.y[0])
        out.z.push(v.z[0])
    }
    return out
}

// ParamSeeker changes for a calibration that switches from before to after at CHANGE_TIME
function paramChanges (before, after) {
    const changes = []
    for (const [t, cal] of [[0, before], [CHANGE_TIME, after]]) {
        ['X', 'Y', 'Z'].forEach((axis, k) => {
            changes.push([t, `COMPASS_OFS_${axis}`, cal.offsets[k]])
            changes.push([t, `COMPASS_DIA_${axis}`, cal.diagonals[k]])
            changes.push([t, `COMPASS_ODI_${axis}`, cal.offDiagonals[k]])
            changes.push([t, `COMPASS_MOT_${axis}`, cal.motor[k]])
        })
        changes.push([t, 'COMPASS_SCALE', cal.scale])
        changes.push([t, 'COMPASS_MOTCT', cal.motorType])
    }
    return new ParamSeeker(changes)
}

function makeTool () {
    const vm = new (Vue.extend(MagFitTool))({ propsData: { resizeable: false } })
    vm.computeData()
    return vm
}

function expectRaw (actual) {
    for (const axis of ['x', 'y', 'z']) {
        for (let i = 0; i < N; i++) {
            expect(Math.abs(actual[axis][i] - raw[axis][i])).toBeLessThan(1e-6)
        }
    }
}

describe('MagFitTool existing calibration removal', () => {
    test('dataflash: SCALE, DIA and ODI changes are undone per sample', () => {
        const before = { ...identityCalibration(), offsets: [10, -5, 20], scale: 0.954, motorType: 0 }
        const after = { ...before, scale: 1.0055, diagonals: [1.02, 0.99, 1.0], offDiagonals: [0.01, 0, -0.02] }
        const cal = i => time[i] < CHANGE_TIME ? before : after
        const logged = logField(cal)
        store.logType = 'bin'
        store.params = paramChanges(before, after)
        store.messages = {
            'MAG[0]': {
                // eslint-disable-next-line camelcase
                time_boot_ms: time,
                MagX: logged.x,
                MagY: logged.y,
                MagZ: logged.z,
                OfsX: time.map(() => 10),
                OfsY: time.map(() => -5),
                OfsZ: time.map(() => 20),
                MOX: time.map(() => 0),
                MOY: time.map(() => 0),
                MOZ: time.map(() => 0)
            },
            // eslint-disable-next-line camelcase
            ATT: { time_boot_ms: time, Roll: time.map(() => 0), Pitch: time.map(() => 0), Yaw: time.map(() => 0) }
        }
        const vm = makeTool()
        expectRaw(vm.compassInputs[0].raw)
        expect(vm.calibrationNotes.join(' ')).toMatch(/per sample.*COMPASS_DIA_X.*COMPASS_SCALE/)
    })

    test('telemetry log: OFS, MOT and MOTCT changes are undone per sample', () => {
        const before = { ...identityCalibration(), offsets: [10, -5, 20], motorType: 0 }
        const after = { ...before, offsets: [12, -8, 25], motor: [1.5, -0.5, 2], motorType: 2 }
        const cal = i => time[i] < CHANGE_TIME ? { ...before, motor: [0, 0, 0] } : after
        const logged = logField(cal)
        store.logType = 'tlog'
        store.params = paramChanges(before, after)
        store.messages = {
            // eslint-disable-next-line camelcase
            RAW_IMU: { time_boot_ms: time, xmag: logged.x, ymag: logged.y, zmag: logged.z },
            // eslint-disable-next-line camelcase
            ATTITUDE: { time_boot_ms: time, roll: time.map(() => 0), pitch: time.map(() => 0), yaw: time.map(() => 0) },
            // eslint-disable-next-line camelcase
            SYS_STATUS: { time_boot_ms: time, current_battery: current.map(a => a * 100) }
        }
        const vm = makeTool()
        expect(vm.compassInputs[0].motorRemoved).toBe(true)
        expectRaw(vm.compassInputs[0].raw)
    })
})
