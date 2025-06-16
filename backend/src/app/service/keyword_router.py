KEYWORD_MAP = {
    "altitude": {"ATT", "AHR2"},
    "attitude": {"ATT", "AHR2"},
    "gps": {"GPS"},
    "battery": {"BAT", "POWR"},
    "error": {"ERR", "MSG"},
    "rc": {"RCIN", "RCOU"},
    "vibe": {"VIBE"},
}

def infer_message_types(query: str) -> set[str]:
    hit = set()
    q = query.lower()
    for kw, types in KEYWORD_MAP.items():
        if kw in q:
            hit.update(types)
    return hit or {"ERR"}
