from app.models.memory import memory_store
from app.services.telemetry_tools import telemetry_query, anomaly_scan


def _seed_session():
    sid = memory_store.create_or_get(None, {
        "meta": {"duration_s": 1100},
        "extrema": {"max_altitude_m": 121.4, "max_altitude_t": 482.3, "min_voltage_v": 10.7, "min_voltage_t": 910.2},
        "gps": {"loss_intervals": [{"start": 615.2, "end": 640.8}], "worst_hdop": {"value": 3.2, "t": 618.9}},
        "battery": {"max_temp_c": 48.0, "max_temp_t": 780.5},
        "errors": [{"t": 742.1, "severity": "CRITICAL", "code": "EKF", "msg": "EKF variance increased"}],
        "timeline": [{"t": 95.0, "from": "STABILIZE", "to": "ALT_HOLD"}],
        "series_opt": {
            "ALT": [[0,0],[120,30],[240,65],[360,95],[480,121.4],[600,118],[720,90],[840,45],[960,12]],
            "VOLT": [[0,12.3],[200,12.0],[400,11.6],[600,11.2],[800,10.9],[900,10.7],[1000,11.0]],
            "HDOP": [[580,1.1],[600,1.8],[620,3.2],[640,1.4]]
        }
    }, None)
    return sid


def test_telemetry_query_core_metrics():
    sid = _seed_session()
    out = telemetry_query(sid, ["max_altitude", "gps_first_loss", "flight_time", "battery_min_voltage", "battery_max_temp", "critical_errors", "mode_changes"]) 
    assert out["max_altitude"]["value_m"] == 121.4
    assert out["gps_first_loss"]["start"] == 615.2
    assert out["flight_time"]["seconds"] == 1100
    assert out["battery_min_voltage"]["value_v"] == 10.7
    assert out["battery_max_temp"]["value_c"] == 48.0
    assert len(out["critical_errors"]) == 1
    assert len(out["mode_changes"]) == 1


def test_anomaly_scan_basic():
    sid = _seed_session()
    findings = anomaly_scan(sid)
    assert "findings" in findings
    assert any(f["signal"] == "ALT" for f in findings["findings"]) or any(f["signal"] == "HDOP" for f in findings["findings"]) or any(f["signal"] == "VOLT" for f in findings["findings"]) 


