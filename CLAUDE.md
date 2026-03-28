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

- `session 137` 2026-03-27: observed stampy-chat MCP server at api/mcp_server.py runs on port 3002 via FastMCP HTTP transport. Uses Pinecone for semantic search (via stampy_chat.citations) and MySQL alignment_research_dataset DB for full-text retrieval. ARD text cleaning imported via importlib.util from ard symlink (bypasses heavy align_data.__init__). ARD MySQL `authors` field is comma-separated string, not list. Article text can be huge (19MB raw); clean_text from ard/align_data/embeddings/clean.py strips base64/SVG/Plotly; 99th percentile cleaned length ~130k chars. `watchexec -w mcp_server.py -r` for dev reload but races on port binding -- use --restart-timeout 2s or kill old process first. (stampy-mcp-architecture).
  ttl: 2
