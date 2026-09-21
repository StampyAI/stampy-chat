import json
import main


def test_stream_refusal_is_an_sse_error_event(monkeypatch):
    monkeypatch.setattr(main.limiter, "check", lambda *a: "burst")
    c = main.app.test_client()
    r = c.post("/chat", json={"query": "q", "sessionId": "s", "stream": True})
    assert r.status_code == 200 and r.mimetype == "text/event-stream"
    events = [json.loads(l[6:]) for l in r.get_data(as_text=True).splitlines() if l.startswith("data: ")]
    assert events[0]["state"] == "error" and "minute" in events[0]["error"]
    assert r.headers["X-RateLimited"] == "burst"


def test_get_refusal_has_status(monkeypatch):
    monkeypatch.setattr(main.limiter, "check", lambda *a: "global_daily")
    r = main.app.test_client().get("/chat/hello")
    assert r.status_code == 503 and r.json["reason"] == "global_daily"


def test_allowed_request_reaches_run_query(monkeypatch):
    monkeypatch.setattr(main.limiter, "check", lambda *a: None)
    monkeypatch.setattr(main, "run_query", lambda *a, **k: iter([{"state": "streaming", "content": "hi"}, {"state": "done"}]))
    charged = []
    monkeypatch.setattr(main.limiter, "settle", lambda ip, calls, now: charged.append(calls))
    r = main.app.test_client().post("/chat", json={"query": "q", "sessionId": "s", "stream": False})
    assert r.json == "hi"


def test_real_cost_is_settled_after_the_answer(monkeypatch):
    monkeypatch.setattr(main.limiter, "check", lambda *a: None)
    charged = []
    monkeypatch.setattr(main.limiter, "settle", lambda ip, calls, now: charged.append(calls))
    turns = [{"state": "turn", "role": "assistant", "content": []}, {"state": "turn", "role": "tool", "tool": "x"},
             {"state": "turn", "role": "assistant", "content": []}, {"state": "streaming", "content": "hi"}, {"state": "done"}]
    monkeypatch.setattr(main, "run_query", lambda *a, **k: iter(turns))
    r = main.app.test_client().post("/chat", json={"query": "q", "sessionId": "s", "stream": True})
    r.get_data()
    assert charged == [2]
