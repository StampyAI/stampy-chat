from flask import Flask, jsonify, request, Response
from flask_cors import CORS, cross_origin
from urllib.parse import unquote
import dataclasses
import json
import re

from env import PINECONE_INDEX, log
from get_blocks import get_top_k_blocks
from chat import talk_to_robot, talk_to_robot_simple


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
    k = request.json['k'] if 'k' in request.json else 20
    return jsonify([dataclasses.asdict(block) for block in get_top_k_blocks(PINECONE_INDEX, query, k)])



# ------------------------------------ chat ------------------------------------


@app.route('/chat', methods=['POST'])
@cross_origin()
def chat():

    query = request.json['query']
    mode = request.json['mode']
    history = request.json['history']

    return Response(stream(talk_to_robot(PINECONE_INDEX, query, mode, history, log = log)), mimetype='text/event-stream')


# ------------- simplified non-streaming chat for internal testing -------------

@app.route('/chat/<path:param>', methods=['GET'])
@cross_origin()
def chat_simplified(param=''):
    return Response(talk_to_robot_simple(PINECONE_INDEX, unquote(param)))

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=3001)
