from typing import Any, Callable, Optional

from stampy_chat.callbacks import (
    BroadcastCallbackHandler,
    CallbackHandler,
    LoggerCallbackHandler,
)
from stampy_chat.settings import Settings
from stampy_chat.llms import query_llm
from stampy_chat.citations import retrieve_docs, Message
from stampy_chat.prompts import construct_prompt
from stampy_chat.followups import search_followups, Followup


def run_query(
    session_id: str,
    query: str,
    history: list[Message],
    settings: Settings,
    callback: Optional[Callable[[Any], None]] = None,
    followups=True,
) -> dict[str, str | list[Followup]]:
    """Execute the query.

    :param str query: the phrase that was input by the user
    :param list[Message] history: any previous interactions with the user
    :param Settings settings: the system settings
    :param Callable[[Any], None] callback: an optional callback that will be called at various key parts of the chain
    :returns: the result of the chain
    """
    callbacks: list[CallbackHandler] = [
        LoggerCallbackHandler(session_id=session_id, query=query, history=history)
    ]
    if callback:
        callbacks += [BroadcastCallbackHandler(callback)]

    docs = retrieve_docs(query, history, settings)
    for call in callbacks:
        call.on_citations_retrieved(docs)

    prompt = construct_prompt(query, history, docs, settings)
    for call in callbacks:
        call.on_prompt(prompt, query, history)

    for call in callbacks:
        call.on_llm_start()

    response = ""
    for chunk in query_llm(prompt, settings):
        if chunk["type"] == "thinking":
            for call in callbacks:
                call.on_thinking(chunk["text"])
        elif chunk["type"] == "response":
            response += chunk["text"]
            for call in callbacks:
                call.on_response(chunk["text"])

    for call in callbacks:
        call.on_llm_end(response)

    follows = []
    if followups:
        follows = search_followups(query, response, callbacks)

    print("result", response)

    if callback:
        callback({"state": "done"})
        callback(None)
    return {"response": response, "followups": follows}
