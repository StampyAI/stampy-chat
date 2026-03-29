# Tool-Based RAG Pipeline

## Context

The stampy chatbot currently uses a fixed retrieval pipeline: optionally generate a HyDE query, run Pinecone vector search, inject retrieved docs into the prompt, then call Claude. This is rigid -- Claude can't refine searches, look up full articles, or browse by metadata.

We have an MCP server (`api/mcp_server.py`) with richer search tools (semantic search, recent search, full doc retrieval, sorted browsing, author listing, tag listing). The goal is to switch the chatbot to use these same tools dynamically via the Anthropic SDK's tool runner, so Claude decides when and what to search.

The model is Claude Opus 4.5 (`claude-opus-4-5-20251101`) with `thinking: {type: "enabled", budget_tokens: N}`.

## Architecture

### Tool Runner with Streaming

Use `client.beta.messages.tool_runner(stream=True, thinking=..., tools=...)`. The streaming tool runner:
- Yields a `BetaMessageStream` per API call in the agentic loop
- After each stream is fully consumed, executes any tool calls from that stream, then yields the next stream
- Manages thinking block passthrough in multi-tool-call conversations

If the tool runner has issues with cache_control placement or streaming bugs, the fallback is a manual agentic loop (~40 lines) with the same tool wrappers and SSE format.

### Tool Definitions as a Shared Module

**New file: `api/src/stampy_chat/tools.py`**

All tool logic moves here from `mcp_server.py`. Each tool function returns `(model_output, ui_output)`:
- `model_output`: formatted string for Claude (same XML format as current MCP tools)
- `ui_output`: structured data for the frontend (Block dicts, article metadata, etc.)

Tools to move (keeping `lw_af_` prefixed names for both MCP and chat -- they're descriptive and Claude handles long tool names fine):
- `lw_af_arxivsafety_search(query, k, filter, snippets_per_doc)` -- semantic search over 25k articles
- `lw_af_arxivsafety_recent(query, days, k, filter, snippets_per_doc)` -- date-filtered search
- `lw_af_arxivsafety_get_doc(id, url, title, max_chars, offset)` -- full article retrieval
- `lw_af_posts_sorted(sort_by, n, author, source, tag, after, before, include)` -- metadata browsing
- `lw_af_authors(n, offset, source, after, before)` -- author listing
- `lw_af_tags()` -- tag listing

All helper functions move too: `_search()`, `_get_article()`, `_browse_stmt()`, `_format_row()`, `_snippet()`, filter helpers (`_convert_date_fields`, `_remap_quality_fields`), sort/blend logic, SQL expressions.

`format_blocks()` moves from `prompts.py` to `tools.py` (it's tool output formatting, not prompt formatting). The import in `mcp_server.py` changes from `stampy_chat.prompts` to `stampy_chat.tools`.

**`api/mcp_server.py`** becomes thin wrappers that import from `tools.py` and discard `ui_output`:
```python
@mcp.tool
def lw_af_arxivsafety_search(...):
    model_output, _ui = tools.search(...)
    return model_output
```

**Tool wrapping for chat** (also in `tools.py`): `make_anthropic_tools(callback)` creates `@beta_tool` wrappers for the tool runner. Each wrapper:
1. Calls the tool function, getting `(model_output, ui_output)`
2. Emits `{"state": "turn", "role": "tool", ...}` via callback as a **side effect**, including both `model_output` and `ui_output`
3. Returns **only `model_output`** (a string) to the tool runner -- the tool runner expects a string return value, not a tuple

Tool discovery is dynamic -- enumerate registered tools at import time, generate Anthropic tool definitions from their metadata (name, description, parameter schema).

### SSE Protocol -- Turn-Based Streaming

The response is a series of turns. Streaming events happen during a turn, then a turn-complete event marks it done.

**Event types:**
```json
{"state": "thinking", "content": "..."}
{"state": "streaming", "content": "..."}
{"state": "turn", "role": "assistant", "content": [...content blocks...]}
{"state": "turn", "role": "tool", "tool": "search", "model_output": "...", "ui_output": [...]}
{"state": "followups", "followups": [...]}
{"state": "done"}
{"state": "error", "error": "..."}
```

**Removed events:**
- `{"state": "citations", ...}` -- citations are in tool result turns
- `{"state": "loading", "phase": "context|prompt"}` -- no separate retrieval phase
- `{"state": "enrich", ...}` -- no HyDE

**Example flow:**
```
{thinking delta}...
{turn complete: assistant (with tool_use block)}
{turn complete: tool (search results)}
{thinking delta}...
{streaming delta}...
{turn complete: assistant (final text)}
{followups}
{done}
```

### Chat Flow Rewrite

**`run_query()` becomes a generator** that yields SSE event dicts directly. This replaces the current callback/Queue/Thread pattern (`stream_callback` in `callbacks.py`, called from `main.py`). The tool runner is already an iterator; `run_query` wraps it as a generator of SSE events. No need for a Queue bridging callbacks to an iterator when the source is already iterable.

```python
def run_query(session_id, query, history, settings, followups=True):
    # 1. Build system prompt + messages (no doc injection)
    # 2. Create tool runner with SSE-emitting wrappers
    # 3. Iterate streams, yield SSE events
    for stream in runner:
        for event in stream:
            # yield thinking/streaming deltas
        # yield assistant turn-complete
        # (tool execution happens here -- wrappers yield tool turn events
        #  via a shared list that run_query checks after each stream)
    # 4. Followups (unchanged)
    yield {"state": "followups", ...}
    yield {"state": "done"}
```

**Side-effect channel for tool turn events**: The tool runner calls tool wrappers between stream iterations. The wrappers can't directly yield into the generator. Instead, they append to a shared list (captured via closure). After each stream completes, `run_query` drains this list and yields the tool turn events before the next stream starts.

**`main.py` changes**: Since `run_query` is now a generator, the `/chat` endpoint simplifies:
```python
@app.route("/chat", methods=["POST"])
def chat():
    # ...parse request...
    def generate():
        for event in run_query(session_id, query, history, settings):
            yield f"data: {json.dumps(event)}\n\n"
        yield "event: close\n\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream")
```

`stream_callback()` and `BroadcastCallbackHandler` become dead code and are removed.

**`clean_history()` in `main.py`** currently merges consecutive same-role messages by concatenating content strings. This will destroy block-structured messages (tool_use, tool_result blocks). It must be updated to handle content-block messages: only merge consecutive same-role messages where content is a plain string, pass through block-structured messages unchanged.

**Removed from chat.py:**
- `generate_hyde()` -- removed
- `retrieve_docs_cached()` -- removed
- `query_llm()` import and calls -- replaced by tool runner
- Callback parameter -- replaced by generator pattern

### History Handling

**Client sends rich history**: Messages contain full content blocks (thinking, text, tool_use, tool_result). This preserves the conversation structure including past searches.

**Server processing on receipt:**
- Strip thinking blocks from all previous assistant turns (avoids signature validation issues and reduces context size)
- Keep tool_use and tool_result blocks intact (structurally required -- tool_use in assistant turn must pair with tool_result in next user turn)
- Wrap only human text messages in `<from-public-user>` tags -- detect by checking if content is a string (human text) vs list of blocks (tool_result)
- Apply prompt injection only to the final user message

**`validate_history()`**: Rework or remove. The client sends the full conversation including tool_use/tool_result turns, which is still role-alternating (assistant with tool_use, user with tool_result) but the content structure is different. May be simplest to remove the validator and let the API reject malformed history.

**Citation reference stability**: Because full tool history is preserved across turns, citation reference numbers from previous searches stay valid. New searches get higher reference numbers (monotonic IDs).

**Cache safety**: `<from-public-user>` wrapping is a pure function of message content. Previous turns form a stable prefix. Injected content (date, mode) goes only on the final user message, after the cache boundary.

**Payload size**: stampy-ui's `makePayload` has a 70KB limit with recursive trimming. Block-structured history with tool results (potentially large search results) may hit this more often. Raise the limit or restructure trimming to drop old tool results while preserving the conversation structure.

### Prompt Changes

**System prompt**: Unchanged (core reference documents stay inline). Good cache_control target.

**Post-message prompt**: Updated to instruct Claude to use search tools rather than assuming docs are pre-injected. Exact wording is a future concern (search quality/serendipity session).

**Removed**: HyDE prompt assembly (`inject_guidance_hyde`), HyDE prompt templates (`hyde_pre_message_prompt`, `hyde_post_message_prompt`). The prompt injection no longer includes `format_blocks(docs)`.

**Token budget calculations**: `Settings.context_tokens`, `Settings.max_response_tokens`, and the token validation in `__init__` are designed around the fixed pipeline where `contextFraction` determines tokens for retrieved docs. With dynamic tool use, Claude manages its own context. These become partially meaningless. Simplify to just use `maxCompletionTokens` directly as `max_tokens` for the tool runner, remove the context/history fraction arithmetic.

### Frontend Changes -- Both Consumers

Both `stampy-ui/app/hooks/useChat.ts` and `web/src/hooks/useSearch.ts` need the same structural changes. Keep implementations converging -- shared types, same SSE handling logic, same component patterns.

**Type changes (both clients):**
```typescript
type ContentBlock =
  | {type: 'text', text: string}
  | {type: 'thinking', thinking: string}
  | {type: 'tool_use', name: string, input: Record<string, any>}
  | {type: 'tool_result', tool: string, ui_output: any}

type AssistantEntry = {
  role: 'assistant'
  blocks: ContentBlock[]
  content: string              // derived: concatenation of text blocks
  citations?: Citation[]       // derived: accumulated from tool_result ui_outputs
  citationsMap?: Map<string, Citation>
  phase?: ChatPhase
  // ...rest unchanged
}
```

**SSE handler changes (both clients):**
- Add `case 'turn'` handler: finalize current streaming accumulator, append blocks, reset for next turn
- Remove `case 'citations'` (stampy-ui, web)
- Remove `case 'enrich'` (web)
- `case 'thinking'`: unchanged in stampy-ui (accumulates text). **web/ needs updating** -- currently just increments a counter (`thinkingCount`), needs to accumulate thinking text like stampy-ui does
- `case 'streaming'`: unchanged (incremental deltas)

**Rendering (both clients):**
All turns from one agentic episode render as one assistant message. Tool calls and results appear as collapsed `<details>` elements inline with text, matching the Anthropic UI style (small grey text with chevron, collapsed by default).

```
 > Thinking                         (collapsed)
 > Lw af arxivsafety search         (collapsed)
 Response text with [1] refs...
 ───────────────────────
 [1] Author - "Title"...            (citations from tool results)
```

Both clients already use or can easily adopt the `<details>` pattern. stampy-ui has it for thinking; web needs it added for both thinking and tool use.

**Rendering order**: Iterate blocks array. Text blocks render as markdown. Thinking blocks render as collapsible. Tool use/result blocks render as collapsible with tool name as summary.

**History sent to server**: Full block-structured turn sequence. Server strips thinking blocks on receipt.

**stampy-ui `Model` type union** (`useChat.ts` lines 68-90): Has hardcoded model strings including non-Anthropic models. Update to match the cleaned-up backend `MODELS`.

### Settings Changes

- Add `anthropic/claude-opus-4-5-20251101` to `MODELS`: `Model(200_000, 20, 4096, ANTHROPIC, "Claude", True, 1024)`
- Remove non-Anthropic models (OpenAI, Google, OpenRouter) from `MODELS`
- Remove `OPENAI`, `GOOGLE`, `OPENROUTER` provider constants
- Remove HyDE settings from `Settings` dataclass (`enable_hyde`, `hyde_max_tokens`)
- Remove HyDE prompt fields from `Prompts` TypedDict and `DEFAULT_PROMPTS`
- Simplify token budget calculations (remove context/history fraction arithmetic)

### Callbacks Changes

**`api/src/stampy_chat/callbacks.py`:**

With `run_query` becoming a generator, `stream_callback()` and `BroadcastCallbackHandler` are no longer needed and are removed.

`LoggerCallbackHandler` needs adapting: currently called via the callback pattern to log interactions to the DB. With the generator pattern, logging moves into `run_query` directly -- log after the tool runner loop completes with the accumulated response text. The logger still stores query, response, history, and context (now: the tool results from the agentic episode rather than the pre-injected Pinecone results).

`on_llm_start`, `on_llm_end`, `on_thinking`, `on_response`, `on_citations_retrieved`, `on_hyde_done` are all removed (the generator pattern replaces them). `on_followups_*` may remain if followup search is still callback-based, or convert to inline code in `run_query`.

### Tool Execution Errors

When a tool function raises an exception (DB connection failure, Pinecone timeout, etc.), the tool runner catches it and sends `is_error: True` in the tool_result. Claude sees the error and can retry, try a different query, or report the failure to the user. No special error handling needed on our side beyond ensuring tool functions raise informative exceptions.

## Files Modified

**Backend (api/):**
- `src/stampy_chat/tools.py` -- NEW: tool definitions, wrapping, all search/browse logic
- `src/stampy_chat/chat.py` -- rewrite run_query as generator using tool runner
- `src/stampy_chat/callbacks.py` -- remove most callback infrastructure, adapt LoggerCallbackHandler
- `src/stampy_chat/prompts.py` -- remove doc injection from inject_guidance, remove inject_guidance_hyde, move format_blocks to tools.py
- `src/stampy_chat/settings.py` -- add opus 4.5, remove non-Anthropic models, remove HyDE settings, simplify token arithmetic
- `src/stampy_chat/llms.py` -- REMOVED (all provider code replaced by tool runner)
- `main.py` -- simplify /chat endpoint (run_query is now a generator), update clean_history for block-structured messages, remove stream_callback usage

**Frontend (stampy-ui/):**
- `app/hooks/useChat.ts` -- turn-based SSE handling, block-structured AssistantEntry, update Model type union, raise/restructure payload size limit
- `app/components/Chatbot/ChatEntry.tsx` -- ToolUse component, block-based rendering

**Frontend (web/):**
- `src/hooks/useSearch.ts` -- same SSE changes as stampy-ui, update thinking to accumulate text (not just count)
- `src/components/assistant.tsx` -- block-based rendering, add thinking + tool use collapsible rendering
- `src/components/citations.tsx` -- citations from tool result ui_outputs
- `src/hooks/useSettings.ts` -- remove HyDE settings, remove non-Anthropic model options, remove HyDE from DEFAULT_PROMPTS
- `src/components/settings.tsx` -- remove HyDE toggle from UI
- `src/types.ts` -- remove HyDE-related types

## Verification

1. **Tool wrapping**: Verify FastMCP tools convert to beta_tool format, return (model_output, ui_output) tuples
2. **Streaming integration**: Run tool runner against real API with search tool, verify SSE event order
3. **curl test**: Hit /chat endpoint, verify turn-based SSE stream format
4. **Both frontends**: Run web/ and stampy-ui/ against updated API, verify collapsible tool use rendering, citation mapping
5. **Multi-turn**: Send follow-up question, verify thinking stripped, tool history preserved, citation references stable
6. **Fallback path**: If tool runner has issues, verify manual loop produces identical SSE stream
7. **Interaction logging**: Verify LoggerCallbackHandler still logs query, response, and context to DB
8. **Error resilience**: Verify tool failures (e.g., Pinecone timeout) surface as Claude explaining the error, not a crash
