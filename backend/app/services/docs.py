from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx


ARDUPILOT_LOG_MESSAGES_URL = "https://ardupilot.org/plane/docs/logmessages.html"
_DOCS_CACHE: Optional[str] = None


def set_docs_cache(text: str) -> None:
    global _DOCS_CACHE
    _DOCS_CACHE = text


def _fetch_docs_text(timeout_s: float = 10.0) -> str:
    global _DOCS_CACHE
    if _DOCS_CACHE is not None:
        return _DOCS_CACHE
    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.get(ARDUPILOT_LOG_MESSAGES_URL)
            r.raise_for_status()
            _DOCS_CACHE = r.text
            return _DOCS_CACHE
    except Exception:
        # Fallback to empty content if offline; callers should handle no snippets
        return ""


def docs_lookup(query: str, max_snippets: int = 2) -> Dict[str, Any]:
    """Very lightweight docs search over the ArduPilot log messages page.

    Returns small snippets and the canonical URL. Tests can inject content via set_docs_cache.
    """
    text = _fetch_docs_text()
    if not text:
        return {"snippets": []}

    # Normalize
    q = query.strip().lower()

    # Heuristic: split by section headings (e.g., lines starting with <h2>ACC</h2>) or all-caps terms followed by paragraphs
    # For simplicity, search for occurrences of the query and extract nearby context.
    snippets: List[Dict[str, str]] = []
    for m in re.finditer(re.escape(q), text.lower()):
        start = max(0, m.start() - 200)
        end = min(len(text), m.end() + 200)
        excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
        # Title heuristic: previous heading in the HTML
        before = text[:m.start()]
        title_match = re.findall(r"<h[12][^>]*>([^<]+)</h[12]>", before[-2000:], flags=re.IGNORECASE)
        title = title_match[-1] if title_match else "ArduPilot Log Messages"
        snippets.append({"title": title, "excerpt": excerpt, "url": ARDUPILOT_LOG_MESSAGES_URL})
        if len(snippets) >= max_snippets:
            break

    return {"snippets": snippets}


