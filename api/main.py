from flask import Flask, jsonify, request, Response
from flask_cors import CORS, cross_origin
from get_blocks import get_top_k_blocks
from chat import talk_to_robot
import dataclasses
import os
import openai
import pinecone
from discord_webhook import DiscordWebhook


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

LOGGING_URL = os.environ.get('LOGGING_URL')

def log(*args, end="\n"):
    message = " ".join([str(arg) for arg in args]) + end
    # print(message)
    if LOGGING_URL is not None and LOGGING_URL != "":
        while len(message) > 2000 - 8:
            m_section, message = message[:2000 - 8], message[2000 - 8:]
            m_section = "```\n" + m_section + "\n```"
            DiscordWebhook(url=LOGGING_URL, content=m_section).execute()
        DiscordWebhook(url=LOGGING_URL, content="```\n" + message + "\n```").execute()

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

    return Response(stream(talk_to_robot(index, query, history, log = log)), mimetype='text/event-stream')


# ------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=3000)
