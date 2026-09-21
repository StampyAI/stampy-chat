"""A dated index of the corpus's recent high-karma items, appended to the system prompt
so the answering model knows what the last few months looked like before it searches.
It is an index, not a briefing, and the header says so to the reader."""
from datetime import datetime, timedelta
from sqlalchemy import select, func, or_
from stampy_chat.tools import ard_engine, articles

FORUMS = ("lesswrong", "alignmentforum", "eaforum", "blogs")
WINDOW_DAYS, TOP_N, RECENT_DAYS, RECENT_N = 90, 40, 14, 15
TTL = timedelta(hours=1)
_cache = {}

HEADER = """<recent-corpus-brief generated="{date}">
Below are the highest-karma items in your search corpus from the last {window} days
(plus the top of the last {recent} days), one line each, newest first. Read this as an
index of what people were discussing, not as a briefing on what happened:
- It is ranked by forum karma, so it over-represents LessWrong/EA Forum discussion and
  under-represents papers (arxiv ingestion stopped in 2025-04), mainstream news, and
  anything that got little forum attention. Karma measures attention, not importance.
- It is almost certainly missing recent major events: because they are older than
  {window} days, because the corpus discusses them under a name you would not guess
  from a user's question, or because they were never posted to these forums.
- Titles can be claims, jokes, or contested takes; a title is not a fact.
- Items here are not citable: they have no [N] reference until you fetch them with a
  search or get_doc call, which gives them one. Do not cite the brief itself.
Treat absence from this list as no evidence either way. For any question about current
events or "the state of things", search first (lw_af_arxivsafety_recent, then search
with the names you find here), and say plainly what you could not find. Not knowing
something recent is expected and fine to say.
"""


def fetch_rows(now):
    karma = func.json_extract(articles.c.metadata, "$.karma")
    base = (select(articles.c.title, articles.c.url, articles.c.source, articles.c.authors,
                   articles.c.date_published, karma.label("karma"))
            .where(articles.c.source.in_(FORUMS), articles.c.date_published <= now))
    top = base.where(articles.c.date_published > now - timedelta(days=WINDOW_DAYS)).order_by(karma.desc()).limit(TOP_N)
    recent = base.where(articles.c.date_published > now - timedelta(days=RECENT_DAYS)).order_by(karma.desc()).limit(RECENT_N)
    with ard_engine.connect() as conn:
        rows = [dict(r) for q in (top, recent) for r in conn.execute(q).mappings()]
    seen, out = set(), []
    for r in rows:
        if r["url"] not in seen: seen.add(r["url"]); out.append(r)
    return out


def format_brief(rows, now) -> str:
    esc = lambda s: str(s or "").replace("{", "{{").replace("}", "}}")
    lines = [f"- {r['date_published']:%Y-%m-%d} [{r['source']}] {esc(r['title'])} -- {esc(r['authors'])} (karma {r['karma'] or '?'}) {r['url']}"
             for r in sorted(rows, key=lambda r: r["date_published"], reverse=True)]
    head = HEADER.format(date=f"{now:%Y-%m-%d}", window=WINDOW_DAYS, recent=RECENT_DAYS)
    return head + "\n".join(lines) + "\n</recent-corpus-brief>"


def world_brief(now=None) -> str:
    """Cached for TTL; on a DB failure returns the stale copy or an honest empty block."""
    now = now or datetime.now()
    if _cache and now - _cache["at"] < TTL: return _cache["text"]
    try:
        text = format_brief(fetch_rows(now), now)
    except Exception as e:  # the brief is optional; never fail the request over it
        if _cache: return _cache["text"]
        return f'<recent-corpus-brief generated="{now:%Y-%m-%d}">unavailable ({type(e).__name__})</recent-corpus-brief>'
    _cache.update(at=now, text=text)
    return text
