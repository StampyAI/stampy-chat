"""Budget-shaped rate limiting, in-process (prod runs one gunicorn worker).
Real traffic = many IPs, few requests each: passes every trigger. Abuse = one IP
hammering, one message repeated, or long pasted work: trips one of them.
Order matters: the cheapest, most specific reason is returned first."""
import ipaddress
import os
import threading
from collections import defaultdict, deque

_env = lambda k, d: int(os.environ.get(k, d))


class Limiter:
    def __init__(self, burst=None, burst_window=None, ip_daily=None, repeat=None,
                 max_chars=None, global_daily=None):
        self.burst = burst or _env("RL_BURST", 8)                  # requests per ip per burst_window
        self.burst_window = burst_window or _env("RL_BURST_WINDOW", 60)
        self.ip_daily = ip_daily or _env("RL_IP_DAILY", 80)          # cost units per ip per day
        self.repeat = repeat or _env("RL_REPEAT", 3)                 # identical message per ip per hour
        self.max_chars = max_chars or _env("RL_MAX_CHARS", 8000)
        self.global_daily = global_daily or _env("RL_GLOBAL_DAILY", 3000)
        self.lock = threading.Lock()
        self.hits = defaultdict(deque)     # ip -> [(t, cost)]
        self.repeats = defaultdict(deque)  # (ip, query) -> [t]
        self.all = deque()                 # [(t, cost)]
        self.sweep_at = 10_000             # repeats keys above this: drop every stale key

    def cost(self, query): return 1 + len(query) // (self.max_chars // 4)

    def check(self, ip, query, now) -> str | None:
        """Return a refusal reason, or None to allow. Counts the request only if allowed.
        The provisional cost is by query length; settle() adds the real cost afterwards."""
        if len(query) > self.max_chars: return "too_long"
        with self.lock:
            self._prune(ip, query, now)
            if sum(c for _, c in self.all) >= self.global_daily: return "global_daily"
            recent = [t for t, _ in self.hits[ip] if t > now - self.burst_window]
            if len(recent) >= self.burst: return "burst"
            if len(self.repeats[ip, query]) >= self.repeat: return "repeat"
            if sum(c for _, c in self.hits[ip]) + self.cost(query) > self.ip_daily: return "ip_daily"
            self.all.append((now, self.cost(query))); self.hits[ip].append((now, self.cost(query))); self.repeats[ip, query].append(now)
            return None

    def settle(self, ip, api_calls, now):
        """Charge what the answer actually cost: one unit per model call beyond the first.
        Spend is driven by thinking and tool rounds, not by query length."""
        extra = max(0, api_calls - 1)
        if not extra: return
        with self.lock:
            self.all.append((now, extra)); self.hits[ip].append((now, extra))

    def _prune(self, ip, query, now):
        day = now - 86400
        _prune(self.all, day, key=lambda x: x[0]); _prune(self.hits[ip], day, key=lambda x: x[0])
        _prune(self.repeats[ip, query], now - 3600)
        for d, k in ((self.hits, ip), (self.repeats, (ip, query))):
            if not d[k]: del d[k]
        if len(self.repeats) > self.sweep_at:  # keys are full query texts; drop stale ones wholesale
            for k in [k for k, dq in self.repeats.items() if not dq or dq[-1] <= now - 3600]: del self.repeats[k]


def _prune(dq, cutoff, key=lambda x: x):
    while dq and key(dq[0]) <= cutoff: dq.popleft()


MESSAGES = {
    "too_long": "That message is too long for Stampy. Please ask a shorter question.",
    "burst": "Too many requests in a minute. Please wait a little and try again.",
    "repeat": "That same message has been sent several times. If Stampy's answer isn't showing, please try rephrasing or come back later.",
    "ip_daily": "Stampy's daily budget for your network is used up. If you are on a shared connection (school, office, VPN) that may include other people's use. Please come back tomorrow.",
    "global_daily": "Stampy is over its daily budget. Please try again tomorrow.",
}
STATUS = {"too_long": 413, "global_daily": 503}


# Cloudflare's published ranges (https://www.cloudflare.com/ips, fetched 2026-09-21).
# chat.stampy.ai is proxied by Cloudflare, but the origin port is also reachable
# directly, so the client-ip header is only believed when the hop came from Cloudflare.
TRUSTED_PROXIES = [ipaddress.ip_network(n) for n in os.environ.get(
    "RL_TRUSTED_PROXIES", ",".join(['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18', '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22', '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22', '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32', '2405:b500::/32', '2405:8100::/32', '2a06:98c0::/29', '2c0f:f248::/32'])).split(",") if n]


def client_ip(request) -> str:
    addr = request.remote_addr or "?"
    try: from_proxy = any(ipaddress.ip_address(addr) in n for n in TRUSTED_PROXIES)
    except ValueError: from_proxy = False
    if not from_proxy: return addr
    return (request.headers.get("CF-Connecting-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or addr)
