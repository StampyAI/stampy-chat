import requests
import json
import re

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS, cross_origin

from stampy_chat import logging
from stampy_chat.env import FLASK_PORT, SENTRY_API_DSN
from stampy_chat.settings import Settings
from stampy_chat.chat import run_query
from stampy_chat.callbacks import stream_callback
from stampy_chat.citations import get_top_k_blocks
from stampy_chat.prompts import inline_all_templates
from stampy_chat.db.session import make_session
from stampy_chat.db.models import Rating
from stampy_chat.citations import Message


# ---------------------------------- web setup ---------------------------------

if SENTRY_API_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.pure_eval import PureEvalIntegration
    sentry_sdk.init(
        dsn=SENTRY_API_DSN,
        # Add data like request headers and IP for users,
        traces_sample_rate=1.0,
        integrations=[
            PureEvalIntegration(),
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


def clean_history(history: list[Message]) -> list[Message]:
    messages: list[Message] = []
    for message in history:
        role = message.get("role")
        content = message.get("content")
        if messages and (last := messages[-1]) and last.get("role") == role:
            last["content"] = last["content"] + "\n\n" + content
        else:
            messages.append(Message(role=role, content=content))
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

    def formatter(item):
        if isinstance(item, Exception):
            item = {"state": "error", "error": str(item)}
        return json.dumps(item)

    def run(callback):
        return run_query(
            session_id, query, history, Settings(**settings), callback, followups
        )

    if not as_stream:
        return jsonify(run(None)["response"])

    return Response(
        stream_with_context(stream(stream_callback(run, formatter))),
        mimetype="text/event-stream",
    )


# ------------- simplified non-streaming chat for internal testing -------------


@app.route("/chat/<path:param>", methods=["GET"])
@cross_origin()
def chat_simplified(param=""):
    res = run_query(None, param, [], Settings())
    res = jsonify({k: v for k, v in res.items() if k in ["response", "followups"]})
    return Response(res, mimetype="application/json")


# ---------------------- human authored content retrieval ----------------------


# act as a proxy, forwarding any requests to /human/<id> to
# https://aisafety.info/questions/<id> in order to get around CORS
@app.route("/human/<id>", methods=["GET"])
@cross_origin()
def human(id):
    r = requests.get(f"https://aisafety.info/questions/{id}")
    logging.info(
        f"clicked followup '{json.loads(r.text)['data']['title']}': https://stampy.ai/?state={id}"
    )

    # run a regex to replace all relative links with absolute links. Just doing
    # a regex for now since we really don't need to parse everything out then
    # re-serialize it for something this simple.
    # <a href=\"/?state=6207&question=What%20is%20%22superintelligence%22%3F\">
    #                               ⬇️
    # <a href=\"https://stampy.ai/?state=6207&question=What%20is%20%22superintelligence%22%3F\">
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
    ).strip() or None  # only save strings if not empty
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
    app.run(debug=True, port=FLASK_PORT)
