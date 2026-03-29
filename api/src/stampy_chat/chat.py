"""Chat pipeline using Anthropic tool runner with streaming."""

import datetime
import json
import traceback
from typing import Generator

import anthropic
import mysql.connector.errors
from sqlalchemy.exc import DatabaseError

from stampy_chat import logging
from stampy_chat.settings import Settings, MODELS
from stampy_chat.citations import Message
from stampy_chat.prompts import format_history, truncate_history, format_prompts
from stampy_chat.tools import make_anthropic_tools
from stampy_chat.followups import multisearch_authored
from stampy_chat.env import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

def _max_ref_in_history(history: list[Message]) -> int:
    """Find highest citation reference id in history's tool_result ui_output.

    Scans for: history[i]["content"][j] where j is a tool_result block,
    then j["ui_output"][k]["reference"] for the max integer.

    >>> _max_ref_in_history([{"content": [
    ...     {"type": "tool_result", "ui_output": [
    ...         {"reference": "3", "title": "x"},
    ...         {"reference": "7", "title": "y"},
    ...     ]}
    ... ]}])
    7
    >>> _max_ref_in_history([{"content": "just a string"}])
    0
    >>> _max_ref_in_history([{"content": [{"type": "text", "text": "no tools"}]}])
    0
    """
    max_ref = 0
    for msg in history:
        content = msg.get("content", "")
        if not isinstance(content, list): continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result": continue
            ui = block.get("ui_output")
            if not isinstance(ui, list): continue
            for item in ui:
                ref = item.get("reference") if isinstance(item, dict) else None
                if ref is not None:
                    try: max_ref = max(max_ref, int(ref))
                    except (ValueError, TypeError): pass
    return max_ref


def run_query(
    session_id: str,
    query: str,
    history: list[Message],
    settings: Settings,
    followups=True,
) -> Generator[dict, None, None]:
    """Execute a query using the Anthropic tool runner with streaming.

    history is the client's format -- assistant turns have flat block lists:
      [{"role": "assistant", "content": [
          {"type": "text", "text": "..."},
          {"type": "tool_use", "id": "toolu_x", "name": "...", "input": {...}},
          {"type": "tool_result", "tool_use_id": "toolu_x",
           "model_output": "<xml>...</xml>",
           "ui_output": [{"reference": "1", "title": "...", ...}, ...]},
          {"type": "text", "text": "..."},
       ]}, ...]

    Yields SSE event dicts (consumed by both frontends):
      {"state": "thinking", "content": "..."}
      {"state": "streaming", "content": "..."}
      {"state": "turn", "role": "assistant", "content": [
          {"type": "text", "text": "..."},
          {"type": "tool_use", "id": "toolu_x", "name": "...", "input": {...}},
       ]}
      {"state": "turn", "role": "tool",
       "tool": "lw_af_arxivsafety_search", "tool_use_id": "toolu_x",
       "model_output": "<xml>...</xml>",
       "ui_output": [{"reference": "1", "title": "...", ...}, ...]}
      {"state": "followups", "followups": [...]}
      {"state": "done"}
    """
    # Build system prompt
    vals = dict(
        modelname=settings.model_given_name,
        date=datetime.datetime.now().strftime("%B %d, %Y"),
        message_id=0,
    )
    system = format_prompts(settings.system_prompt, vals)
    history_instruction = format_prompts(settings.history_prompt, vals)
    system = system + "\n\n" + history_instruction

    # Format history: strip thinking, preserve tool_use/tool_result, wrap human text
    messages = format_history(query, history, settings, vals)

    # Build tool runner
    tool_events = []  # side-effect channel for tool turn events
    start_id = _max_ref_in_history(history) + 1
    tools = make_anthropic_tools(tool_events, start_id)

    model_info = MODELS[settings.model]
    thinking_budget = settings.thinking_budget
    thinking_params = {}
    if model_info.can_think and thinking_budget > 0:
        thinking_budget = max(model_info.min_think, thinking_budget)
        thinking_params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    runner = client.beta.messages.tool_runner(
        model=settings.model_id,
        max_tokens=settings.max_response_tokens,
        stream=True,
        tools=tools,
        system=system,
        messages=messages,
        **thinking_params,
    )

    # Iterate streams, yield SSE events
    response_text = ""
    turn_num = 0
    tool_names_used = []  # for logging which tools were called
    prev_tool_use_ids = []  # tool_use IDs from previous turn, for pairing with tool_results
    try:
        for message in runner:
            turn_num += 1

            # Drain tool events from PREVIOUS turn's tool execution.
            # Tool wrappers append here during execution between stream iterations.
            # Assert: tool_events should only have items from the previous turn's tools.
            if tool_events:
                n = len(tool_events)
                logger.info(f"[turn {turn_num}] draining {n} tool events from previous turn")
                for i, te in enumerate(tool_events):
                    if i < len(prev_tool_use_ids):
                        te["tool_use_id"] = prev_tool_use_ids[i]
                    tool_names_used.append(te["tool"])
                    logger.info(f"  tool event: {te['tool']}")
                    yield te
                tool_events.clear()

            turn_content = []
            logger.info(f"[turn {turn_num}] stream started")

            for event in message:
                if event.type == "content_block_start":
                    block_type = event.content_block.type
                    logger.info(f"[turn {turn_num}] block_start: {block_type}")
                    if block_type == "thinking":
                        turn_content.append({"type": "thinking", "thinking": ""})
                    elif block_type == "text":
                        turn_content.append({"type": "text", "text": ""})
                    elif block_type == "tool_use":
                        turn_content.append({
                            "type": "tool_use",
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input": {},
                        })
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        yield {"state": "thinking", "content": event.delta.thinking}
                        if turn_content and turn_content[-1]["type"] == "thinking":
                            turn_content[-1]["thinking"] += event.delta.thinking
                    elif event.delta.type == "text_delta":
                        yield {"state": "streaming", "content": event.delta.text}
                        response_text += event.delta.text
                        if turn_content and turn_content[-1]["type"] == "text":
                            turn_content[-1]["text"] += event.delta.text
                    elif event.delta.type == "input_json_delta":
                        if turn_content and turn_content[-1]["type"] == "tool_use":
                            turn_content[-1].setdefault("_input_json", "")
                            turn_content[-1]["_input_json"] += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if turn_content and turn_content[-1]["type"] == "tool_use":
                        raw = turn_content[-1].pop("_input_json", "{}")
                        try: turn_content[-1]["input"] = json.loads(raw)
                        except (json.JSONDecodeError, ValueError): turn_content[-1]["input"] = {"_raw": raw}

            # Clean up any _input_json keys left by abnormal stream termination
            for block in turn_content:
                block.pop("_input_json", None)

            block_types = [b["type"] for b in turn_content]
            logger.info(f"[turn {turn_num}] stream done, blocks: {block_types}")

            prev_tool_use_ids = [b["id"] for b in turn_content if b.get("type") == "tool_use"]
            yield {"state": "turn", "role": "assistant", "content": turn_content}

        # Drain any remaining tool events from the last turn
        for i, te in enumerate(tool_events):
            if i < len(prev_tool_use_ids):
                te["tool_use_id"] = prev_tool_use_ids[i]
            tool_names_used.append(te["tool"])
            yield te
        tool_events.clear()

    except Exception as e:
        logger.error(f"Error in run_query: {e}", exc_info=True)
        yield {"state": "error", "error": str(e)}
        return

    # Log interaction (tools used replaces old prompted_history/context logging)
    try:
        tools_summary = ", ".join(tool_names_used) if tool_names_used else "(no tools)"
        logger.interaction(session_id, query, response_text, history, tools_summary, [])
    except (DatabaseError, mysql.connector.errors.DatabaseError):
        logger.error(traceback.format_exc())

    # Followups
    if followups:
        follows = multisearch_authored([query, response_text])
        yield {"state": "followups", "followups": follows}

    yield {"state": "done"}
