from typing import Dict, Any
from datetime import datetime, timedelta

class FlightDataCache:
    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._ttl = timedelta(minutes=60)
    
    def get(self, log_id: str) -> dict | None:
        entry = self._cache.get(log_id)
        if entry and datetime.now() < entry["expires"]:
            return entry["data"]
        return None
    
    def set(self, log_id: str, data: Any):
        self._cache[log_id] = {
            "data": data,
            "expires": datetime.now() + self._ttl
        }