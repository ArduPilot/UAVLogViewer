const NTP_UNIX_OFFSET = 2208988800;
const GPS_MINUS_TAI = 19;

// Fallback table, oldest first: [since yyyymm, TAI-UTC seconds].
// Used only if the runtime leap-seconds.list cannot be loaded.
const FALLBACK_TAI_MINUS_UTC = [
    [199601, 30],
    [199707, 31],
    [199901, 32],
    [200601, 33],
    [200901, 34],
    [201207, 35],
    [201507, 36],
    [201701, 37],
];

let leapTable = null; // [{ ntp, taiMinusUtc }], sorted ascending
let leapExpiresNtp = null;

export function parseLeapSecondsList(text) {
    const entries = [];
    let expiresNtp = null;
    let updatedNtp = null;

    for (const line of text.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("#@")) {
            expiresNtp = Number(trimmed.slice(2).trim());
            continue;
        }
        if (trimmed.startsWith("#$")) {
            updatedNtp = Number(trimmed.slice(2).trim());
            continue;
        }
        if (trimmed.startsWith("#")) continue;

        const [ntpStr, taiStr] = trimmed.split(/\s+/);
        const ntp = Number(ntpStr);
        const taiMinusUtc = Number(taiStr);
        if (Number.isFinite(ntp) && Number.isFinite(taiMinusUtc)) {
            entries.push({ ntp, taiMinusUtc });
        }
    }

    entries.sort((a, b) => a.ntp - b.ntp);
    return { entries, expiresNtp, updatedNtp };
}

function taiMinusUtcFromFallback(year, month) {
    const yyyymm = year * 100 + month;
    let value = 0;
    for (const [since, offset] of FALLBACK_TAI_MINUS_UTC) {
        if (yyyymm >= since) value = offset;
    }
    return value;
}

function taiMinusUtcAt(unixSeconds) {
    if (!leapTable || leapTable.length === 0) {
        const date = new Date(unixSeconds * 1000);
        return taiMinusUtcFromFallback(
            date.getUTCFullYear(),
            date.getUTCMonth() + 1,
        );
    }

    const ntp = unixSeconds + NTP_UNIX_OFFSET;
    let lo = 0;
    let hi = leapTable.length - 1;
    let best = null;

    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (leapTable[mid].ntp <= ntp) {
            best = leapTable[mid];
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }

    // Before 1972 the offset was 10 s; GPS didn't exist, but returning
    // something sane beats 0 if a pre-1980 log ever appears.
    return best ? best.taiMinusUtc : 10;
}

function leapSecondsGPS(unixSeconds) {
    return taiMinusUtcAt(unixSeconds) - GPS_MINUS_TAI;
}

// Call once at startup. Tries a same-origin copy first, then IANA
// (best effort — CORS may block it), then silently keeps the fallback.
export async function initLeapSeconds() {
    const candidates = [
        new URL("/leap-seconds.list", window.location.origin), // public/
        "https://data.iana.org/time-zones/data/leap-seconds.list", // best effort
    ];

    for (const url of candidates) {
        try {
            const response = await fetch(url, { cache: "no-cache" });
            if (!response.ok) continue;

            const parsed = parseLeapSecondsList(await response.text());
            if (parsed.entries.length === 0) continue;

            leapTable = parsed.entries;
            leapExpiresNtp = parsed.expiresNtp;

            if (leapExpiresNtp) {
                const expiresUnix = leapExpiresNtp - NTP_UNIX_OFFSET;
                if (Date.now() / 1000 > expiresUnix) {
                    console.warn(
                        "leap-seconds.list is past its expiry:",
                        new Date(expiresUnix * 1000).toISOString(),
                    );
                }
            }
            return;
        } catch {
            // CORS or network failure — try the next candidate.
        }
    }

    console.warn("leap-seconds.list unavailable; using built-in table");
}

// GPS week + time-of-week (ms) to a UTC Date, adjusted for leap seconds.
// The offset is looked up from GPS time interpreted as if it were UTC;
// this can be off by at most one leap second across an insertion
// boundary, which nothing downstream cares about.
function gpsTimeToUtc(gpsWeek, gpsMs) {
    const unixSeconds = 315964800 + 7 * 86400 * gpsWeek + gpsMs / 1000;
    const leapSeconds = leapSecondsGPS(unixSeconds);
    return new Date((unixSeconds - leapSeconds) * 1000);
}

// The absolute time at boot (the log's time 0), from the first GPS sample
// with a plausible GPS week.
export default function extractStartTime(msgs) {
    const i = msgs.time_boot_ms.findIndex((_, j) => msgs.GWk[j] > 2000);
    if (i === -1) return;

    const bootUtc = gpsTimeToUtc(msgs.GWk[i], msgs.GMS[i]);
    return new Date(bootUtc.getTime() - msgs.time_boot_ms[i]);
}
