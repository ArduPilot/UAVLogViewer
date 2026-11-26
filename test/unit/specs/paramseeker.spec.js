import { ParamSeeker } from '../../../src/tools/paramseeker'

describe('ParamSeeker', () => {
    const seeker = new ParamSeeker([
        [0, 'COMPASS_SCALE', 0.99],
        [0, 'COMPASS_OFS_X', 5],
        [399000, 'COMPASS_SCALE', 0.9985],
        [500000, 'COMPASS_SCALE', 1.01],
        [500000, 'COMPASS_SCALE', 1.02]
    ])

    test('valuesAt gives the value in use at each time', () => {
        expect(seeker.valuesAt('COMPASS_SCALE', [-10, 0, 398999, 399000, 450000, 500000, 900000]))
            .toEqual([0.99, 0.99, 0.99, 0.9985, 0.9985, 1.02, 1.02])
        expect(seeker.valuesAt('COMPASS_OFS_X', [0, 1e6])).toEqual([5, 5])
        expect(seeker.valuesAt('COMPASS_OFS_Y', [0])).toBeNull()
    })

    test('tracks the last value and params changed during the log', () => {
        expect(seeker.getLast('COMPASS_SCALE')).toBe(1.02)
        expect(seeker.changedDuringLog('COMPASS_SCALE')).toBe(true)
        expect(seeker.changedDuringLog('COMPASS_OFS_X')).toBe(false)
    })
})
