
function leapSecondsGPS (year, month) {
    return leapSecondsTAI(year, month) - 19
}

function leapSecondsTAI (year, month) {
    const yyyymm = year * 100 + month
    if (yyyymm >= 201701) return 37
    if (yyyymm >= 201507) return 36
    if (yyyymm >= 201207) return 35
    if (yyyymm >= 200901) return 34
    if (yyyymm >= 200601) return 33
    if (yyyymm >= 199901) return 32
    if (yyyymm >= 199707) return 31
    if (yyyymm >= 199601) return 30

    return 0
}

export default function extractStartTime (msgs) {
    for (const i in msgs.time_boot_ms) {
        if (msgs.GWk[i] > 1000) { // lousy validation
            const weeks = msgs.GWk[i]
            const ms = msgs.GMS[i]
            let d = new Date((315964800.0 + ((60 * 60 * 24 * 7) * weeks) + ms / 1000.0) * 1000.0)
            // adjusting for leap seconds
            d = new Date(d.getTime() - leapSecondsGPS(d.getUTCFullYear(), d.getUTCMonth() + 1) * 1000)
            return d
        }
    }
}
