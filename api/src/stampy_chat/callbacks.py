import threading
import traceback
from queue import Queue
from typing import Any, Callable, Iterator
import pprint

import mysql.connector.errors
from sqlalchemy.exc import DatabaseError

from stampy_chat import logging
from stampy_chat.citations import Block, Message

logger = logging.getLogger(__name__)


class CallbackHandler:
    def on_history(self, history: list[Message]):
        pass

    def on_citations_retrieved(self, citations: list[Block]) -> None:
        pass

    def on_hyde_done(self, hypothetical_document: str) -> None:
        pass

    def on_prompt(self, prompt: list[Message], query: str, history: list[Message]) -> None:
        pass

    def on_llm_start(self) -> Any:
        pass

    def on_thinking(self, thinking: str) -> None:
        pass

    def on_response(self, response: str) -> None:
        pass

    def on_llm_end(self, response, **kwargs: Any) -> Any:
        pass

    def on_followups_start(self, inputs: dict[str, Any]) -> None:
        pass

    def on_followups_end(self, followups: list["Followup"]) -> None:
        pass


class BroadcastCallbackHandler(CallbackHandler):
    """A callback handler that will broadcast any events to all listeners."""

    def __init__(self, broadcaster, *args, **kwargs) -> None:
        self.broadcaster = broadcaster
        super().__init__(*args, **kwargs)

    def broadcast(self, value: Any) -> None:
        if self.broadcaster:
            self.broadcaster(value and value)

    def on_prompt(self, prompt: list[Message], query: str, history: list[Message]) -> None:
        self.broadcast({"state": "prompt", "promptedHistory": prompt})

    def on_response(self, chunk: str) -> None:
        self.broadcast({"state": "streaming", "content": chunk})

    def on_history(self, history: list[Message]):
        self.broadcast({"state": "loading", "phase": "history"})

    def on_context_fetch_start(self, input_variables: dict[str, str]) -> None:
        self.broadcast({"state": "loading", "phase": "context"})

    def on_hyde_done(self, hypothetical_document: str) -> None:
        self.broadcast({"state": "enrich", "phase": "context", "content": hypothetical_document})

    def on_citations_retrieved(self, citations: list[Block]) -> None:
        self.broadcast({"state": "citations", "citations": citations})
        self.broadcast({"state": "loading", "phase": "prompt"})

    def on_llm_start(self) -> Any:
        self.broadcast({"state": "loading", "phase": "llm"})

    def on_thinking(self, thinking: str) -> None:
        self.broadcast({"state": "thinking", "content": thinking})

    def on_followups_start(self, inputs: dict[str, Any]) -> None:
        self.broadcast({"state": "loading", "phase": "followups"})

    def on_followups_end(self, followups: list["Followup"]) -> None:
        self.broadcast({"state": "followups", "followups": followups})


class LoggerCallbackHandler(CallbackHandler):
    """A callback handler that will collect events and then log it in the database."""

    def __init__(
        self, session_id=None, query=None, history=None, *args, **kwargs
    ) -> None:
        self.session_id = session_id
        self.query = query
        self.response = None
        self.history = history
        self.context = None
        self.prompted_history = None
        self.hyde = None
        super().__init__(*args, **kwargs)

    def on_history(self, history: list[Message]):
        self.history = history

    def on_hyde_done(self, hypothetical_document: str) -> None:
        self.hyde = hypothetical_document

    def on_citations_retrieved(self, citations: list[Block]) -> None:
        self.context = citations

    def on_llm_end(self, response: str, **kwargs: Any) -> Any:
        try:
            logger.interaction(
                self.session_id,
                self.query + (f"\n\n(hyde: {self.hyde})" if self.hyde is not None else ""),
                response,
                self.history,
                pprint.pformat(self.prompted_history), # todo: what is logger.interaction?
                self.context,
            )
        except (DatabaseError, mysql.connector.errors.DatabaseError):
            logger.error(traceback.format_exc())

    def on_prompt(self, prompted_history: list[Message], query: str, history: list[Message]) -> None:
        self.prompted_history = prompted_history


Callback = Callable[[Any], None]


def stream_callback(
    function: Callable[[Callback], Any], formatter: Callable[[Any], str] = str
) -> Iterator:
    """Stream the items that are sent via a callback.

    This function expects to get a one argument function that will generate stuff. The
    argument is a callback to add stuff to the response. So put together it should be something
    like:

        def function_that_uses_callbacks(callback):
            ...
            callback("some value")
            callback("some other value")
            ...

        @app.route('/bla')
        def bla():
            return stream_callback(function_that_uses_callbacks)

    Most functions work normally and return (or yield) values that can be normally returned
    from endpoints as Responses. But sometimes there are things (especially async), which
    don't work like that, but communicate back via callbacks, channels etc. This is very much
    not what Flask expects, hence the magic here with Queues and Threads to pretend that a
    function is a yieldable.

    Sending a `None` to the callable will close the iterator.

    :param Callable[[Callback], Any] function: the function that will generate the data
    :param Callable[[Any], str] formatter: an optional formatter of all received messages

    :returns: An iterator will all calls to the `callback` provided to `function`. This is till the first `None`
    """
    queue = Queue()

    def generate(rq: Queue):
        """Tranform a Queue into an iterator.

        This will iterate over items from the Queue until it gets a `None`.
        Items are added in a child thread.
        """
        while (message := rq.get()) is not None:
            yield formatter(message)

    def callback(value: Any):
        """The callback provided to `function`.

        This just adds the values to the queue. This happens in the child thread; they get
        fetched from the queue in the main thread (i.e. the caller of `stream_callback`).
        """
        queue.put(value)

    def error_handler(function, callback):
        """Catch any errors from the `function`, but also make sure the generated iterator gets closed properly."""
        try:
            function(callback)
        except Exception as e:
            logger.error(traceback.format_exc())
            callback(e)

        callback(None)

    # Call the `function` in a child thread - all callback items will be added to the queue and read from
    # this thread, i.e. the one in which `stream_callback` was called
    threading.Thread(
        target=error_handler,
        args=(
            function,
            callback,
        ),
    ).start()
    return generate(queue)
