import requests
import json
import re
import logging

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS, cross_origin

from stampy_chat import logging
from stampy_chat.env import FLASK_PORT, SENTRY_API_DSN
from stampy_chat.settings import Settings
from stampy_chat.chat import run_query
from stampy_chat.citations import get_top_k_blocks
from stampy_chat.prompts import inline_all_templates
from stampy_chat.db.session import make_session
from stampy_chat.db.models import Rating
from stampy_chat.citations import Message


# ---------------------------------- web setup ---------------------------------

if SENTRY_API_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.pure_eval import PureEvalIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    sentry_sdk.init(
        dsn=SENTRY_API_DSN,
        traces_sample_rate=1.0,
        integrations=[
            PureEvalIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

# ---------------------------------- sse stuff ---------------------------------


def stream(src):
    yield from (
        "data: " + "\ndata: ".join(message.splitlines()) + "\n\n" for message in src
    )
    yield "event: close\n\n"


# ------------------------------- semantic search ------------------------------


@app.route("/semantic", methods=["POST"])
@cross_origin()
def semantic():
    query = request.json["query"]
    k = request.json.get("k", 20)
    return jsonify(get_top_k_blocks(query, k))


# ------------------------------------ chat ------------------------------------


def clean_history(history: list) -> list:
    """Clean up history, merging consecutive same-role text messages.

    Handles both flat string content and block-structured content (tool_use, tool_result).
    Only merges consecutive same-role messages where both have string content.
    """
    messages = []
    for message in history:
        role = message.get("role")
        content = message.get("content")
        if (
            messages
            and (last := messages[-1])
            and last.get("role") == role
            and isinstance(last.get("content"), str)
            and isinstance(content, str)
        ):
            last["content"] = last["content"] + "\n\n" + content
        else:
            messages.append(dict(message))  # shallow copy
    return messages


@app.route("/chat", methods=["POST"])
@cross_origin()
def chat():
    query = request.json.get("query", None)
    session_id = request.json.get("sessionId")
    history = request.json.get("history", [])
    settings = request.json.get("settings", {})
    followups = request.json.get("followups", True)
    as_stream = request.json.get("stream", True)

    if query is None and history:
        query = history[-1].get("content")
        history = history[:-1]

    history = clean_history(history)

    if not as_stream:
        # Non-streaming: collect full response
        response = ""
        for event in run_query(session_id, query, history, Settings(**settings), followups):
            if event.get("state") == "streaming":
                response += event.get("content", "")
        return jsonify(response)

    def generate():
        for event in run_query(session_id, query, history, Settings(**settings), followups):
            yield json.dumps(event)

    return Response(
        stream_with_context(stream(generate())),
        mimetype="text/event-stream",
    )


# ------------- simplified non-streaming chat for internal testing -------------


@app.route("/chat/<path:param>", methods=["GET"])
@cross_origin()
def chat_simplified(param=""):
    response = ""
    follows = []
    for event in run_query(None, param, [], Settings()):
        if event.get("state") == "streaming":
            response += event.get("content", "")
        elif event.get("state") == "followups":
            follows = event.get("followups", [])
    return jsonify({"response": response, "followups": follows})


# ---------------------- human authored content retrieval ----------------------


@app.route("/human/<id>", methods=["GET"])
@cross_origin()
def human(id):
    r = requests.get(f"https://aisafety.info/questions/{id}")
    logging.info(
        f"clicked followup '{json.loads(r.text)['data']['title']}': https://stampy.ai/?state={id}"
    )
    text = re.sub(
        r'<a href=\\"/\?state=(\d+.*)\\">',
        r'<a href=\"https://aisafety.info/?state=\1\\">',
        r.text,
    )
    return Response(text, mimetype="application/json")


# ------------------------------------------------------------------------------

@app.route("/test-error", methods=["GET"])
@cross_origin()
def test_error():
    return 1/0


@app.route("/ratings", methods=["POST"])
@cross_origin()
def ratings():
    session_id = request.json.get("sessionId")
    settings = request.json.get("settings", {})
    comment = (
        request.json.get("comment") or ""
    ).strip() or None
    score = request.json.get("score")

    if not session_id or score is None:
        return Response('{"error": "missing params}', 400, mimetype="application/json")

    with make_session() as s:
        s.add(
            Rating(
                session_id=session_id,
                score=score,
                settings=json.dumps(settings),
                comment=comment,
            )
        )
        s.commit()

    return jsonify({"status": "ok"})


@app.route("/inline-prompts", methods=["POST"])
@cross_origin()
def inline_prompts():
    settings = request.json.get("settings", {})
    prompts = settings.get("prompts", {})
    inlined_prompts = inline_all_templates(prompts)
    return jsonify(inlined_prompts)


if __name__ == "__main__":
    app.run(debug=True, use_debugger=False, port=FLASK_PORT, host="0.0.0.0")
