/* eslint-disable camelcase */
export function buildSummaryFromState (state) {
    const durationSeconds = typeof state.lastTime === 'number'
        ? Math.max(0, Math.round(state.lastTime / 1000))
        : 0

    const timeline = Array.isArray(state.flightModeChanges)
        ? state.flightModeChanges.map((entry) => ({ t: entry[0], to: entry[1] }))
        : []

    const errors = []

    return {
        meta: { durationSeconds, duration_s: durationSeconds },
        timeline,
        errors
    }
}

function downsamplePairs (tArray, vArray, maxPoints) {
    const n = Math.min(tArray.length, vArray.length)
    if (n === 0) return []
    const step = Math.max(1, Math.floor(n / maxPoints))
    const out = []
    for (let i = 0; i < n; i += step) {
        const tSec = (tArray[i] || 0) / 1000
        out.push([tSec, vArray[i]])
    }
    return out
}

function getTimeArray (obj) {
    if (!obj) return []
    return obj.time_boot_ms || obj.timeUS || obj.TimeUS || obj.timeMS || obj.TimeMS || []
}

export function buildSummaryFromMessages (messages, maxSeriesPoints = 300) {
    const summary = { meta: {}, timeline: [], errors: [], series_opt: {} }

    // Duration: max time_boot_ms over any message
    let maxMs = 0
    Object.keys(messages || {}).forEach((k) => {
        const m = messages[k]
        if (m && Array.isArray(m.time_boot_ms)) {
            const arr = m.time_boot_ms
            if (arr.length > 0) {
                const last = arr[arr.length - 1]
                if (typeof last === 'number') maxMs = Math.max(maxMs, last)
            }
        }
    })
    const durationSeconds = Math.max(0, Math.round(maxMs / 1000))
    summary.meta.durationSeconds = durationSeconds
    summary.meta.duration_s = durationSeconds
    try { console.log('[summary] durationSeconds:', durationSeconds) } catch (e) {}

    // Extrema: altitude from DataFlash (AHR2.Alt, GPS.Alt) or MAVLink tlog
    // (GLOBAL_POSITION_INT.relative_alt, VFR_HUD.alt)
    let alt = null
    let tAlt = null
    if (messages && messages.AHR2 && Array.isArray(messages.AHR2.Alt)) {
        alt = messages.AHR2.Alt
        tAlt = getTimeArray(messages.AHR2)
        try { console.log('[summary] ALT source: AHR2 (len=', alt.length, ')') } catch (e) {}
    } else if (messages && messages.GPS && Array.isArray(messages.GPS.Alt)) {
        alt = messages.GPS.Alt
        tAlt = getTimeArray(messages.GPS)
        try { console.log('[summary] ALT source: GPS (len=', alt.length, ')') } catch (e) {}
    } else if (messages && messages.GLOBAL_POSITION_INT && Array.isArray(messages.GLOBAL_POSITION_INT.relative_alt)) {
        // MAVLink tlog path: relative_alt is meters (we normalized in parser)
        alt = messages.GLOBAL_POSITION_INT.relative_alt
        tAlt = getTimeArray(messages.GLOBAL_POSITION_INT)
        try {
            console.log('[summary] ALT source: GLOBAL_POSITION_INT.relative_alt (len=', alt.length, ')')
        } catch (e) {}
    } else if (messages && messages.VFR_HUD && Array.isArray(messages.VFR_HUD.alt)) {
        // MAVLink tlog fallback
        alt = messages.VFR_HUD.alt
        tAlt = getTimeArray(messages.VFR_HUD)
        try { console.log('[summary] ALT source: VFR_HUD.alt (len=', alt.length, ')') } catch (e) {}
    }
    if (alt && tAlt) {
        let maxVal = null
        let maxIdx = -1
        for (let i = 0; i < alt.length; i++) {
            const v = alt[i]
            if (typeof v === 'number' && (maxVal === null || v > maxVal)) {
                maxVal = v
                maxIdx = i
            }
        }
        if (maxVal !== null && maxIdx >= 0) {
            const ext = {}
            ext.max_altitude_m = maxVal
            ext.max_altitude_t = (tAlt[maxIdx] || 0) / 1000
            summary.extrema = ext
            try { console.log('[summary] max_altitude_m:', maxVal, 't:', summary.extrema.max_altitude_t) } catch (e) {}
        }
        summary.series_opt = summary.series_opt || {}
        summary.series_opt.ALT = downsamplePairs(tAlt, alt, maxSeriesPoints)
        try { console.log('[summary] ALT downsampled len:', summary.series_opt.ALT.length) } catch (e) {}
    }

    // GPS loss intervals (<3 means unreliable)
    if (messages && (messages.GPS || messages.GPS_RAW_INT)) {
        const gps = messages.GPS || messages.GPS_RAW_INT
        const t = getTimeArray(gps)
        const fix = gps.fix_type || gps.Status || []
        const intervals = []
        let inLoss = false
        let start = null
        for (let i = 0; i < Math.min(t.length, fix.length); i++) {
            const ok = (typeof fix[i] === 'number' ? fix[i] : 3) >= 3
            if (!ok && !inLoss) {
                inLoss = true
                start = (t[i] || 0) / 1000
            } else if (ok && inLoss) {
                inLoss = false
                const end = (t[i] || 0) / 1000
                intervals.push({ start, end })
                start = null
            }
        }
        if (inLoss && start !== null) {
            intervals.push({ start, end: (t[t.length - 1] || 0) / 1000 })
        }
        if (intervals.length > 0) {
            summary.gps = { loss_intervals: intervals }
        }
        try {
            const count = (summary.gps && summary.gps.loss_intervals)
                ? summary.gps.loss_intervals.length
                : 0
            console.log('[summary] gps loss intervals:', count)
        } catch (e) {}
    }

    return summary
}

export function buildAutoSummary (state) {
    const msgSummary = buildSummaryFromMessages(state.messages || {})
    const stateSummary = buildSummaryFromState(state)

    msgSummary.meta = msgSummary.meta || {}
    if (!msgSummary.meta.durationSeconds || msgSummary.meta.durationSeconds === 0) {
        msgSummary.meta.durationSeconds = stateSummary.meta.durationSeconds
        msgSummary.meta.duration_s = stateSummary.meta.duration_s
    }
    if (!Array.isArray(msgSummary.timeline) || msgSummary.timeline.length === 0) {
        msgSummary.timeline = stateSummary.timeline
    }
    msgSummary.errors = msgSummary.errors || []
    return msgSummary
}
