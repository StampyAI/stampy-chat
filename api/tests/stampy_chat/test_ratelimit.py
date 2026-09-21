from stampy_chat.ratelimit import Limiter

def mk(**kw): return Limiter(**{"burst": 3, "burst_window": 60, "ip_daily": 10, "repeat": 2, "max_chars": 100, "global_daily": 6, **kw})

def test_normal_traffic_from_many_ips_passes():
    lim = mk(global_daily=1000)
    for i in range(50):
        assert lim.check(f"ip{i}", "what is alignment?", now=1000 + i) is None

def test_burst_from_one_ip():
    lim = mk()
    assert [lim.check("a", f"q{i}", now=10 + i) for i in range(4)] == [None, None, None, "burst"]
    assert lim.check("a", "q9", now=10 + 61) is None  # window slid

def test_repeat_of_same_message():
    lim = mk(burst=99)
    assert [lim.check("a", "same", now=i) for i in range(3)] == [None, None, "repeat"]

def test_long_query_costs_more_daily_budget_and_too_long_is_refused():
    lim = mk(burst=99, ip_daily=4, max_chars=100)
    assert lim.check("a", "x" * 101, now=0) == "too_long"
    assert lim.check("a", "y" * 80, now=1) is None      # cost 1 + 80//25 = 4
    assert lim.check("a", "z", now=2) == "ip_daily"

def test_settle_charges_real_api_calls_to_both_budgets():
    lim = mk(burst=99, ip_daily=5, global_daily=6)
    assert lim.check("a", "q", now=0) is None       # provisional cost 1
    lim.settle("a", api_calls=4, now=1)             # +3 -> 4 used of 5
    assert lim.check("a", "q2", now=2) is None      # 5 of 5
    assert lim.check("a", "q3", now=3) == "ip_daily"
    assert lim.check("b", "q", now=4) is None       # global: 4+1+1 = 6
    assert lim.check("c", "q", now=5) == "global_daily"

def test_stale_keys_are_reclaimed():
    lim = mk(burst=99); lim.sweep_at = 0
    lim.check("a", "q", now=0)
    lim.check("a", "q", now=90000)  # a day later: old entries pruned, key rebuilt with one entry
    assert len(lim.hits["a"]) == 1 and len(lim.repeats["a", "q"]) == 1
    lim.check("a", "other", now=180000)  # over sweep_at: the stale ("a","q") key is dropped
    assert set(lim.repeats) == {("a", "other")}

def test_global_daily_budget():
    lim = mk(burst=99)
    assert [lim.check(f"ip{i}", f"q{i}", now=i) for i in range(7)][-2:] == [None, "global_daily"]


class _Req:
    def __init__(self, addr, **headers): self.remote_addr, self.headers = addr, headers

def test_client_ip_believes_header_only_from_cloudflare():
    from stampy_chat.ratelimit import client_ip
    spoof = {"CF-Connecting-IP": "1.2.3.4", "X-Forwarded-For": "5.6.7.8"}
    assert client_ip(_Req("203.0.113.9", **spoof)) == "203.0.113.9"      # direct hit: header ignored
    assert client_ip(_Req("104.16.0.1", **spoof)) == "1.2.3.4"           # via Cloudflare: header used
    assert client_ip(_Req("104.16.0.1", **{"X-Forwarded-For": "5.6.7.8, 9.9.9.9"})) == "5.6.7.8"
