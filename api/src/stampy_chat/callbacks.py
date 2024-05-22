import threading
import traceback
from queue import Queue
from typing import Any, Dict, List, Callable, Iterator

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import BaseMessage

from stampy_chat import logging


logger = logging.getLogger(__name__)


class StampyCallbackHandler(BaseCallbackHandler):

    def on_memory_set_start(self, history: List[dict]) -> None:
        pass

    def on_memory_set_end(self, history: List[dict]) -> None:
        pass

    def on_context_fetch_start(self, input_variables: Dict[str, str]) -> None:
        pass

    def on_context_fetch_end(self, context: List[dict]) -> None:
        pass

    def on_followups_start(self, inputs: Dict[str, Any]) -> None:
        pass

    def on_followups_end(self, followups: List[Dict[str, Any]]) -> None:
        pass


class BroadcastCallbackHandler(StampyCallbackHandler):
    """A callback handler that will broadcast any events to all listeners."""

    def __init__(self, broadcaster, *args, **kwargs) -> None:
        self.broadcaster = broadcaster
        super().__init__(*args, **kwargs)

    def broadcast(self, value: Any) -> None:
        if self.broadcaster:
            self.broadcaster(value and value)

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.broadcast({'state': 'streaming', 'content': token})

    def on_memory_set_start(self, history: List[dict]):
        self.broadcast({'state': 'loading', 'phase': 'history'})

    def on_context_fetch_start(self, input_variables: Dict[str, str]) -> None:
        self.broadcast({'state': 'loading', 'phase': 'context'})

    def on_context_fetch_end(self, context: List[dict]) -> None:
        self.broadcast({'state': 'citations', 'citations': context})
        self.broadcast({'state': 'loading', 'phase': 'prompt'})

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any) -> Any:
        self.broadcast({'state': 'loading', 'phase': 'llm'})

    # def on_llm_end(self, response, **kwargs: Any) -> Any:
    #     self.broadcast({'state': 'done'})

    def on_followups_start(self, inputs: Dict[str, Any]) -> None:
        self.broadcast({'state': 'loading', 'phase': 'followups'})

    def on_followups_end(self, followups: List[Dict[str, Any]]) -> None:
        self.broadcast({'state': 'followups', 'followups': followups})


class LoggerCallbackHandler(StampyCallbackHandler):
    """A callback handler that will collect events and then log it in the database."""

    def __init__(self, session_id=None, query=None, history=None, *args, **kwargs) -> None:
        self.session_id = session_id
        self.query = query
        self.response = None
        self.history = history
        self.context = None
        self.prompt = None
        super().__init__(*args, **kwargs)

    def on_memory_set_start(self, history: List[dict]):
        self.history = history

    def on_context_fetch_end(self, context: List[dict]) -> None:
        self.context = context

    def on_llm_end(self, response, **kwargs: Any) -> Any:
        response = ''.join([gen.text for gen in response.generations[0]])
        logger.interaction(self.session_id, self.query, response, self.history, self.prompt, self.context)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        self.prompt = '\n'.join(prompts)


Callback = Callable[[Any], None]
def stream_callback(function: Callable[[Callback], Any], formatter: Callable[[Any], str] = str) -> Iterator:
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
    threading.Thread(target=error_handler, args=(function, callback,)).start()
    return generate(queue)
