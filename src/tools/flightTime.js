import tzlookup from "@photostructure/tz-lookup";

// The absolute time at the log's time 0 (metadata.startTime: a Date or milliseconds since 1970),
// in milliseconds since 1970, or NaN when the log has none
export function logStartTime(metadata) {
    return new Date(metadata?.startTime ?? Number.NaN).getTime();
}

// Time zone at the start of the trajectory ([lon, lat, alt, time] points), or null
export function zoneOfFlight(points) {
    const [longitude, latitude] = points?.[0] ?? [];
    try {
        return tzlookup(latitude, longitude);
    } catch {
        // no usable position
        return null;
    }
}
