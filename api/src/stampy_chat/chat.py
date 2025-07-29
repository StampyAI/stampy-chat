import re
from typing import Any, Callable, Optional

from stampy_chat.callbacks import (
    BroadcastCallbackHandler,
    CallbackHandler,
    LoggerCallbackHandler,
)
from stampy_chat.settings import Settings
from stampy_chat.llms import query_llm
from stampy_chat.citations import retrieve_docs, Message
from stampy_chat.prompts import inject_guidance, inject_guidance_hyde
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

    retrieval_query = query
    if settings.enable_hyde:
        hyde_history = inject_guidance_hyde(query, history, settings)
        retrieval_query = query_llm(
            hyde_history,
            settings,
            stream=False,
            max_tokens=settings.hyde_max_tokens,
            thinking_budget=0,
        )
        for call in callbacks:
            call.on_hyde_done(retrieval_query)

    docs = retrieve_docs(retrieval_query, settings)

    for call in callbacks:
        call.on_citations_retrieved(docs)

    prompted_history = inject_guidance(query, history, docs, settings)
    for call in callbacks:
        call.on_prompt(prompted_history, query, history)

    for call in callbacks:
        call.on_llm_start()

    response = ""
    for chunk in query_llm(prompted_history, settings):
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
