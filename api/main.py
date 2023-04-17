from flask import Flask, jsonify, request, Response
from flask_cors import CORS, cross_origin
from get_blocks import get_top_k_blocks
from chat import talk_to_robot
import dataclasses
import os
import openai
import pinecone


# ---------------------------------- env setup ---------------------------------


if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_ENV = "us-east1-gcp"
pinecone.init(
    api_key=PINECONE_API_KEY,
    environment=PINECONE_ENV
)
INDEX_NAME = "alignment-search"
index = pinecone.Index(index_name=INDEX_NAME)


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
    return jsonify([dataclasses.asdict(block) for block in get_top_k_blocks(index, query)])


# ------------------------------------ chat ------------------------------------


@app.route('/chat', methods=['POST'])
@cross_origin()
def chat():

    query = request.json['query']
    history = request.json['history']

    return Response(stream(talk_to_robot(index, query, history)), mimetype='text/event-stream')


# ------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=3000)
