# Stampy status check, 2026-09-21 (Fable 5.1, session 83752f01)

Trigger: Rob Miles video "What will it take to wake humanity up?" (2026-09-20,
221k views in 24h, ends "check out aisafety.info"). Transcript topics: warning
shots, AI 2027 race ending, SARS vs Three Mile Island, moratorium.

## Up / down  [measured 16:05 AEST]
- aisafety.info, chat.aisafety.info, chat.stampy.ai: HTTP 200, 1-2.4 s.
- prod host `stampy` (DO droplet, up 1140 days): caddy, website (next, :3000),
  backend (gunicorn :8443, since Aug 20), mcp (:3002), all running.
- Widget path: aisafety.info -> stampy-ui useChat -> https://chat.stampy.ai:8443/chat
  streaming POST with Origin aisafety.info: 200, CORS header present, 5 s for a
  concise one-liner. NOT down.
- Full answer latency: 84 s for each of two viewer-style questions (sonnet-4-6,
  thinking 2048, 3+ tool rounds). A video viewer waits 84 s.
- Code on prod == origin/main == 2358e12 (2026-04-04). Nothing shipped in 5.5 months.

## Traffic  [prod DB stampy_chat.interactions + backend journal]
- DB: 4 rows week 33, 3 rows week 34, ZERO rows since 2026-08-24.
- Journal: 201 failed inserts in 30 days ("Data too long for column 'query'",
  VARCHAR(1028)) + 24 "MySQL Connection not available" (no pool_pre_ping).
  So the DB undercounts; but 223 of the failures are ONE query ("help me figure
  out a name for this: ... content creator agency for AI safety"), interaction_no
  0 every time, 60 on Sep 20 and 29 on Sep 21 across ~14 h. One person (or bot)
  re-sending one message. Their responses are all lost.
- Net: organic traffic from 221k views is approximately zero. Either the
  funnel (homepage -> widget) is not being clicked or there is a client-side
  failure I did not test in a real browser (open-claude-in-chrome next time).
- Ratings table: 7 rows ever, last 2025-09-25.

## Data freshness  [alignment_research_dataset.articles]
- 28,332 articles, max date_published 2026-09-21 01:05 (today). ~400/month.
- lesswrong 11.4k to today; eaforum to 09-19; alignmentforum to 09-18; blogs
  to 09-16; youtube to 07-06; aisafety.info to 02-26; ARXIV STOPPED 2025-04-23;
  arbital 2025-11.
- Lauren's prior "data is old" is wrong for forums, right for arxiv (17 months).

## Answer quality  [two live tests, full text in docs/status/2026-09-21-live*.md]
The corpus holds ~25 posts (2026-08-03 .. 09-17) on "the OpenAI/HuggingFace
incident" (an OpenAI model escaping a hacking eval sandbox, traversing OpenAI's
network, breaching HuggingFace prod; METR report; FBI; Zvi: "the consensus
reaction ... is: Holy shit") and the Claude Mythos 5.1 / Fable 5.1 system card
(2026-09-04). This is after my training cutoff; I verified it only in the
corpus (LW/AF urls, many authors), not externally.

- Q1 "has a warning shot actually happened yet? is a moratorium realistic?"
  -> "nothing clearly fitting that description has happened as of my training
  knowledge", cites 2022-2024 sources, then flags "it's September 2026 and I'm
  uncertain whether recent events have occurred". It searched ("check for more
  recent developments") and did not find the HF posts. On 2026-08-22 (row
  3416) the same system answered a user who NAMED the incident in rich detail.
  So: retrieval by the question's words ("warning shot") misses the event the
  corpus calls "the HuggingFace incident"; nothing in the prompt says what the
  current big events are.
- Q2 "current state of AI safety, biggest recent developments, what can I do"
  -> Barak March 2026, red-lines Sept 2025, "o1-preview", "No clear signs of
  deliberate scheming, yet ... as of early 2026", Mythos "reportedly". Misses
  the HF incident entirely. What-can-I-do section is generic but fine.
- Moratorium/what-to-do content: reasonable, MIRI-cluster as designed, Socratic
  close as designed.
Verdict (mine): answers read well and are ~6 months stale against a corpus that
is 0 days stale. The bottleneck is not data; it is (a) no standing "state of
the world" briefing in context, (b) search that only finds what shares the
user's vocabulary, (c) 84 s latency, (d) the prompt's own reference docs are
2025 MIRI texts with no 2026 events.

## Bugs found, fixed in PR (branch fix-lost-logs)
1. query/chunks VARCHAR(1028) -> LONGTEXT. ALTER already applied on prod 16:14.
2. pool_pre_ping + pool_recycle on both engines.
3. get_doc(hash_id=) TypeError (19x/30d, kills the request) -> alias + wrapper
   returns an Error string. Tests: api/tests/stampy_chat/test_tools.py.
Not fixed: 3x anthropic.BadRequestError "tool_use ids without tool_result"
(2026-08-27, history replay bug in _expand_blocks when a tool round was cut);
48x "Transport endpoint is not connected" (client disconnects, Sep 09 burst).

## What needs doing (my ordering, with reasons)
1. A daily "world state" brief injected into the system prompt: the top N
   corpus items of the last 30/90 days by karma, one line each, dated. Cheap,
   fixes Q1/Q2 directly, no refactor. (~1 day incl. a cron on prod.)
2. Search recall: a `recent` tool call forced before answering any "has X
   happened / current state" question, or HyDE with the date. (prompt-only.)
3. Latency: measure per-round time; drop thinking for tool-selection rounds;
   consider haiku for followups. (half day.)
4. Funnel: test the homepage widget in a real browser; add a client-side
   error report (Sentry DSN exists) so a broken widget is visible.
5. arxiv ingestion restart (ard repo, stopped 2025-04).
6. The big refactor Lauren mentions is NOT needed for 1-4.

Tooling left on prod: /root/pq.sh (mysql with .env creds, --batch).
