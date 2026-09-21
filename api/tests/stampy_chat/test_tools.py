import pytest
from stampy_chat import tools


def _tool(name, events=None):
    return next(t for t in tools.make_anthropic_tools(events if events is not None else []) if t.name == name)


@pytest.fixture
def article(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "_get_article", lambda **kw: calls.append(kw) or None)
    return calls


def test_get_doc_accepts_hash_id_alias(article):
    # Search results label the id field "hash_id", so Claude calls get_doc(hash_id=...)
    _tool("lw_af_arxivsafety_get_doc").func(hash_id="abc")
    assert article == [{"id": "abc", "url": None, "title": None}]


def test_unknown_kwarg_is_a_tool_error_not_a_crash(article):
    events = []
    out = _tool("lw_af_arxivsafety_get_doc", events).func(bogus="x")
    assert out.startswith("Error:") and "bogus" in out
    assert article == []
    # chat.py pairs tool events to tool_use ids positionally, so the failed call must still emit one
    assert len(events) == 1 and events[0]["model_output"] == out
