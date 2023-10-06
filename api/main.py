import json
import re

from flask import Flask, jsonify, request, Response
from flask_cors import CORS, cross_origin

from stampy_chat import logging
from stampy_chat.env import FLASK_PORT
from stampy_chat.settings import Settings
from stampy_chat.chat import run_query
from stampy_chat.citations import get_top_k_blocks


# ---------------------------------- web setup ---------------------------------

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# ---------------------------------- sse stuff ---------------------------------

def stream(src):
    yield from ('data: ' + '\ndata: '.join(message.splitlines()) + '\n\n' for message in src)
    yield 'event: close\n\n'

# ------------------------------- semantic search ------------------------------


@app.route('/semantic', methods=['POST'])
@cross_origin()
def semantic():

    query = request.json['query']
    k = request.json.get('k', 20)
    return jsonify(get_top_k_blocks(query, k))



# ------------------------------------ chat ------------------------------------


@app.route('/chat', methods=['POST'])
@cross_origin()
def chat():

    query = request.json.get('query')
    session_id = request.json.get('sessionId')
    history = request.json.get('history', [])
    settings = Settings(**request.json.get('settings', {}))

    return Response(stream(map(json.dumps, run_query(session_id, query, history, settings))), mimetype='text/event-stream')


# ------------- simplified non-streaming chat for internal testing -------------

@app.route('/chat/<path:param>', methods=['GET'])
@cross_origin()
def chat_simplified(param=''):
    res = {}
    for event in run_query(None, param, [], Settings()):
        if event['state'] == 'citations':
            res['citations'] = event['citations']
        elif event['state'] == 'followups':
            res['followups'] = event['followups']
        elif event['state'] == 'streaming':
            res['text'] = res.get('text', '') + event.get('content')

    return jsonify(res)

# ---------------------- human authored content retrieval ----------------------

# act as a proxy, forwarding any requests to /human/<id> to
# https://aisafety.info/questions/<id> in order to get around CORS
@app.route('/human/<id>', methods=['GET'])
@cross_origin()
def human(id):
    import requests
    r = requests.get(f"https://aisafety.info/questions/{id}")
    logging.info(f"clicked followup '{json.loads(r.text)['data']['title']}': https://stampy.ai/?state={id}")

    # run a regex to replace all relative links with absolute links. Just doing
    # a regex for now since we really don't need to parse everything out then
    # re-serialize it for something this simple.
    # <a href=\"/?state=6207&question=What%20is%20%22superintelligence%22%3F\">
    #                               ⬇️
    # <a href=\"https://stampy.ai/?state=6207&question=What%20is%20%22superintelligence%22%3F\">
    text = re.sub(r'<a href=\\"/\?state=(\d+.*)\\">', r'<a href=\"https://aisafety.info/?state=\1\\">', r.text)

    return Response(text, mimetype='application/json')

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=FLASK_PORT)
