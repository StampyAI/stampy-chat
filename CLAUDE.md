in api/, use pipenv to run python commands. otherwise, `python` doesn't exist, `python3` isn't in venv.



Code style:
- prefer putting sufficiently-short single-line if statements on the same line:

    if x: a()
    else: b()
    if condition(long_parameter=foo.bar().baz() + foo.bar(depth=-1).baz(herp="derp")):
        a()
    else:
        b()

- Judiciously use short names to ease human typing, unless readability suffers. one or two acronym names per file is ok. Prefer single word names where possible.
- Don't try/except unless the error needs handling. For errors that will stop the program, just let it crash. Rare, world-stopping-anyway error handling isn't usually worth the readability cost.
- Prefer maintainability where possible
- Mildly prefer procedural over object oriented, use functional tools when they makes things more readable.

Refactoring:

- After growing code in a few rounds to get things working, follow up by looking for ways to increase maintainability. Design a bit, then try some code, then refactor - no need to be perfect first try, but do clean up from the experimentation
- When refactoring aim both to reduce size of a changeset, and to reduce complexity of individual parts.
- When refactoring, prefer compression-oriented programming: generally don't extract something unless it's done two to three times or is a naturally-separable concern.

Python tools:

- tests are `cd api && pipenv run pytest`.
- tests have low coverage, we'd like to fix this over time

Javascript tools - excerpt from web/package.json:
```
{
  ...
  "scripts": {
    "build": "next build",
    "lint": "tsc && npm run prettier && npm run eslint",
    "lint:fix": "tsc && npm run prettier:fix && npm run eslint:fix"
    ...
  },
  ...
}
```


## Living Memory

- `session ?` 2026-04-01: observed Anthropic SDK BetaStreamingToolRunner yields BetaMessageStream per API call. Tool execution happens BETWEEN stream iterations (after one stream is consumed, before next yields). Tool wrapper side effects (appending to a shared list) fire during this gap. Must drain tool events BEFORE streaming the next turn, not after -- otherwise tool results appear after the next turn's content. generate_tool_call_response() + append_messages() caused duplicate tool execution with streaming runner; removed in favor of letting the runner auto-handle. cache_control on tool results needs revisiting., With streaming tool runner: drain tool side-effect events at START of each iteration (from previous turn's execution). Don't use generate_tool_call_response with streaming runner until verified it doesn't double-execute. content_block_stop events have no .delta attribute -- handle separately from content_block_delta. (tool-runner-streaming-architecture).
  ttl: 13
- `session ?` 2026-04-01: observed Major refactor in progress: stampy-chat switched from fixed RAG pipeline (HyDE->Pinecone->inject docs->Claude) to dynamic tool-based RAG using Anthropic SDK tool runner. tools.py extracted from mcp_server.py, returns (model_output, ui_output) tuples. chat.py run_query is now a generator yielding SSE events. llms.py deleted, callbacks.py gutted, settings.py cleaned (Anthropic-only models). Both web/ and stampy-ui/ frontends updated with turn-based SSE protocol and block-based rendering. Spec at docs/superpowers/specs/2026-03-30-tool-based-rag-design.md. Working on jj change vvwsn, prior change tntms. Remaining: tool input JSON now captured, tool_use+tool_result merged in UI, friendly names added. Still needs prompt tuning, cache_control re-add, and stampy-ui testing polish., Continue from current jj change. Core architecture works -- streaming + thinking + tool use all functional. Key remaining items: (1) prompt needs updating to instruct Claude to use tools rather than assuming injected docs, (2) cache_control on tool results needs a working approach (generate_tool_call_response didn't work with streaming), (3) UI polish for tool display styling, (4) web/ frontend testing. (tool-based-rag-refactor-state).
  ttl: 4
- `session 156` 2026-04-02: observed added, observed jj creates divergent changes when a commit is merged into main via PR -- the original change ID exists both locally and in main's history. `jj rebase -s children -d main` then `jj abandon --ignore-immutable "divergent/N::"` cleans it up. `jj op restore` is the escape hatch when abandon/rebase goes wrong. Key: use `jj op log` to find the last good state before attempting fixes. (jj-divergent-changes-from-merged-prs).
  ttl: 1
