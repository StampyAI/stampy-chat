from datetime import datetime
from stampy_chat import worldbrief as wb

ROWS = [
    dict(title="Big {event}", url="u1", source="lesswrong", authors="A, B", date_published=datetime(2026, 9, 10), karma=300),
    dict(title="Old but big", url="u2", source="eaforum", authors="C", date_published=datetime(2026, 7, 1), karma=200),
    dict(title="Tiny", url="u3", source="blogs", authors="", date_published=datetime(2026, 9, 20), karma=None),
]

def test_format_escapes_braces_and_orders_by_date():
    text = wb.format_brief(ROWS, datetime(2026, 9, 21))
    assert "Big {{event}}" in text and "2026-09-21" in text
    assert text.index("Tiny") < text.index("Big") < text.index("Old but big")
    assert "almost certainly missing" in text

def test_cache_refreshes_after_ttl(monkeypatch):
    calls = []
    monkeypatch.setattr(wb, "fetch_rows", lambda now: calls.append(now) or ROWS)
    wb._cache.clear()
    a = wb.world_brief(now=datetime(2026, 9, 21, 10)); b = wb.world_brief(now=datetime(2026, 9, 21, 10, 30))
    c = wb.world_brief(now=datetime(2026, 9, 21, 12))
    assert a == b == c and len(calls) == 2
