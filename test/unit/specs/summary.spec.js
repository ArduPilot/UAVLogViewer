import { buildSummaryFromMessages, buildAutoSummary } from '@/services/summary'

describe('summary aggregation', () => {
    test('buildSummaryFromMessages computes duration and max altitude from AHR2', () => {
        const messages = {
            AHR2: {
                time_boot_ms: [0, 1000, 2000, 3000],
                Alt: [1, 10, 3, 7]
            }
        }
        const s = buildSummaryFromMessages(messages, 10)
        expect(s.meta.durationSeconds).toBe(3)
        expect(s.extrema.max_altitude_m).toBe(10)
        expect(s.extrema.max_altitude_t).toBe(1)
        expect(Array.isArray(s.series_opt.ALT)).toBe(true)
        expect(s.series_opt.ALT.length).toBeGreaterThan(0)
    })

    test('buildSummaryFromMessages computes gps loss intervals from fix_type', () => {
        const messages = {
            GPS: {
                time_boot_ms: [0, 1000, 2000, 3000, 4000],
                fix_type: [3, 2, 2, 3, 3]
            }
        }
        const s = buildSummaryFromMessages(messages, 10)
        expect(s.gps.loss_intervals.length).toBe(1)
        expect(s.gps.loss_intervals[0].start).toBe(1)
        expect(s.gps.loss_intervals[0].end).toBe(3)
    })

    test('buildAutoSummary fills duration and timeline from state when messages sparse', () => {
        const state = {
            lastTime: 5500,
            flightModeChanges: [[1, 'STABILIZE'], [100, 'AUTO']],
            messages: {}
        }
        const s = buildAutoSummary(state)
        expect(s.meta.durationSeconds).toBe(6)
        expect(s.timeline.length).toBe(2)
    })
})
