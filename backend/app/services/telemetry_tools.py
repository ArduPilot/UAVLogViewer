from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from ..models.memory import memory_store, SessionData


def _in_window(t: float, from_t: Optional[float], to_t: Optional[float]) -> bool:
    if from_t is not None and t < from_t:
        return False
    if to_t is not None and t > to_t:
        return False
    return True


def _series_window(series: List[List[float]], from_t: Optional[float], to_t: Optional[float]) -> List[List[float]]:
    if not series:
        return series
    return [pt for pt in series if _in_window(pt[0], from_t, to_t)]


def _max_with_time(series: List[List[float]]) -> Optional[Tuple[float, float]]:
    if not series:
        return None
    t, v = max(series, key=lambda p: p[1])
    return v, t


def _min_with_time(series: List[List[float]]) -> Optional[Tuple[float, float]]:
    if not series:
        return None
    t, v = min(series, key=lambda p: p[1])
    return v, t


def _mean_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / len(values)
    return m, math.sqrt(var)


def telemetry_query(session_id: str, metrics: List[str], from_t: Optional[float] = None, to_t: Optional[float] = None) -> Dict[str, Any]:
    session: Optional[SessionData] = memory_store.get(session_id)
    if session is None:
        raise ValueError("invalid session_id")

    summary = session.summary or {}
    series_opt = (summary.get("series_opt") or {})
    alt_series = _series_window(series_opt.get("ALT", []), from_t, to_t)
    volt_series = _series_window(series_opt.get("VOLT", []), from_t, to_t)

    out: Dict[str, Any] = {}

    for metric in metrics:
        if metric == "max_altitude":
            # Prefer summary extrema if available, else compute from series
            extrema = summary.get("extrema") or {}
            if "max_altitude_m" in extrema and _in_window(extrema.get("max_altitude_t", 0.0), from_t, to_t):
                out["max_altitude"] = {
                    "value_m": extrema["max_altitude_m"],
                    "t": extrema.get("max_altitude_t"),
                }
            else:
                mx = _max_with_time(alt_series)
                if mx:
                    v, t = mx
                    out["max_altitude"] = {"value_m": v, "t": t}
                else:
                    out["max_altitude"] = None

        elif metric == "gps_first_loss":
            gps = summary.get("gps") or {}
            intervals = gps.get("loss_intervals") or []
            first = next((iv for iv in intervals if _in_window(iv.get("start", 0.0), from_t, to_t)), None)
            out["gps_first_loss"] = first if first else None

        elif metric == "flight_time":
            meta = summary.get("meta") or {}
            out["flight_time"] = {"seconds": meta.get("duration_s")}

        elif metric == "battery_min_voltage":
            extrema = summary.get("extrema") or {}
            if "min_voltage_v" in extrema and _in_window(extrema.get("min_voltage_t", 0.0), from_t, to_t):
                out["battery_min_voltage"] = {
                    "value_v": extrema["min_voltage_v"],
                    "t": extrema.get("min_voltage_t"),
                }
            else:
                mn = _min_with_time(volt_series)
                if mn:
                    v, t = mn
                    out["battery_min_voltage"] = {"value_v": v, "t": t}
                else:
                    out["battery_min_voltage"] = None

        elif metric == "battery_max_temp":
            battery = summary.get("battery") or {}
            t = battery.get("max_temp_t")
            if t is not None and _in_window(t, from_t, to_t):
                out["battery_max_temp"] = {"value_c": battery.get("max_temp_c"), "t": t}
            else:
                out["battery_max_temp"] = None

        elif metric == "rc_first_loss":
            # Not present in MVP summary; return None to be explicit
            out["rc_first_loss"] = None

        elif metric == "critical_errors":
            errors = summary.get("errors") or []
            crit = [e for e in errors if (e.get("severity") or "").upper() == "CRITICAL" and _in_window(e.get("t", 0.0), from_t, to_t)]
            out["critical_errors"] = crit

        elif metric == "mode_changes":
            timeline = summary.get("timeline") or []
            out["mode_changes"] = [ev for ev in timeline if _in_window(ev.get("t", 0.0), from_t, to_t)]

    return out


def anomaly_scan(session_id: str, signals: Optional[List[str]] = None, window_s: int = 10, sensitivity: str = "normal") -> Dict[str, Any]:
    session: Optional[SessionData] = memory_store.get(session_id)
    if session is None:
        raise ValueError("invalid session_id")

    summary = session.summary or {}
    series_opt = (summary.get("series_opt") or {})

    signals = signals or ["ALT", "VOLT", "HDOP"]
    findings: List[Dict[str, Any]] = []

    # Sensitivity thresholds
    if sensitivity == "high":
        alt_z_threshold = 1.5
        volt_drop_threshold = 0.15
        hdop_threshold = 2.0
    elif sensitivity == "low":
        alt_z_threshold = 3.5
        volt_drop_threshold = 0.35
        hdop_threshold = 3.5
    else:  # normal
        alt_z_threshold = 2.5
        volt_drop_threshold = 0.25
        hdop_threshold = 3.0

    if "ALT" in signals and series_opt.get("ALT"):
        alt = series_opt["ALT"]
        values = [v for _, v in alt]
        m, s = _mean_std(values)
        if s > 0:
            # identify the single strongest peak by z-score
            peak = max(alt, key=lambda p: p[1])
            z = (peak[1] - m) / s
            if z >= alt_z_threshold:
                findings.append({"signal": "ALT", "t": peak[0], "type": "peak", "zscore": round(z, 2)})

    if "VOLT" in signals and series_opt.get("VOLT"):
        volt = series_opt["VOLT"]
        # detect largest negative step
        best_drop: Optional[Tuple[float, float, float]] = None  # (t, delta, v)
        for i in range(1, len(volt)):
            t_prev, v_prev = volt[i - 1]
            t_cur, v_cur = volt[i]
            delta = v_cur - v_prev
            if best_drop is None or delta < best_drop[1]:
                best_drop = (t_cur, delta, v_cur)
        if best_drop and abs(best_drop[1]) >= volt_drop_threshold and best_drop[1] < 0:
            findings.append({
                "signal": "VOLT",
                "t": best_drop[0],
                "type": "voltage_sag",
                "delta_v": round(best_drop[1], 3),
            })

    if "HDOP" in signals and series_opt.get("HDOP"):
        hdop = series_opt["HDOP"]
        worst = max(hdop, key=lambda p: p[1])
        if worst[1] >= hdop_threshold:
            findings.append({"signal": "HDOP", "t": worst[0], "type": "hdop_degradation", "value": worst[1]})

    return {"findings": findings}


