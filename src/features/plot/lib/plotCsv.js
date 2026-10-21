// The plotted series as csv: a row every 100 ms over the visible range with the log time, the time
// the axis shows when the log has an absolute one (clockTime in plotTimeAxis.js), and each series' value

const INTERVAL = 100;

// A series' value at a log time, interpolated between its samples; empty before the series starts,
// after it ends and in its gaps (null samples). next is the series' first sample not before the
// previous row, so each series is read once.
function valueAt(series, time) {
    const { times, values } = series;
    while (series.next < times.length && times[series.next] < time) {
        series.next += 1;
    }
    const k = series.next;
    if (k === times.length) {
        return "";
    }
    if (times[k] === time) {
        return values[k] ?? "";
    }
    if (k === 0 || values[k - 1] === null || values[k] === null) {
        return "";
    }
    const share = (time - times[k - 1]) / (times[k] - times[k - 1]);
    return values[k - 1] + (values[k] - values[k - 1]) * share;
}

// traces: the plot's (x on the time axis); range: the visible log times, or null for all of them
export function plotCsv(traces, axis, range) {
    const series = traces.map((trace) => ({
        name: trace.name.split(" |")[0],
        times: trace.x.map(axis.fromAxis),
        values: trace.y,
        next: 0,
    }));
    const plotted = series.filter((s) => s.times.length > 0);
    const [from, to] = range ?? [-Infinity, Infinity];
    const start = Math.max(from, Math.min(...plotted.map((s) => s.times[0])));
    const end = Math.min(to, Math.max(...plotted.map((s) => s.times.at(-1))));
    const clock = axis.clockTime(0) !== null;

    const header = ["timestamp(ms)", ...(clock ? ["time"] : [])];
    // a comma in an expression would split its column (#412)
    header.push(...series.map((s) => s.name.replaceAll(",", ";")));
    const lines = [header.join(",")];
    for (let k = 0; start + k * INTERVAL <= end; k++) {
        const time = Number((start + k * INTERVAL).toFixed(3));
        const row = [time, ...(clock ? [axis.clockTime(time)] : [])];
        row.push(...series.map((s) => valueAt(s, time)));
        lines.push(row.join(","));
    }
    return lines.join("\n");
}
