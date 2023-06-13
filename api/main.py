from flask import Flask, jsonify, request, Response
from flask_cors import CORS, cross_origin
from get_blocks import get_top_k_blocks
from chat import talk_to_robot, talk_to_robot_simple
import dataclasses
import os
import openai
import pinecone
import json
from discord_webhook import DiscordWebhook


# ---------------------------------- env setup ---------------------------------

if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
else:
    print("'api/.env' not found. Rename the 'api/.env.example' file and fill in values.")


OPENAI_API_KEY   = os.environ.get('OPENAI_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
LOGGING_URL      = os.environ.get('LOGGING_URL')
PINECONE_INDEX   = None

openai.api_key = OPENAI_API_KEY # non-optional

# Only init pinecone if we have an env value for it.
if PINECONE_API_KEY is not None and PINECONE_API_KEY != "":

    pinecone.init(
        api_key = PINECONE_API_KEY,
        environment = "us-east1-gcp",
    )

    PINECONE_INDEX = pinecone.Index(index_name="alignment-search")

# log something only if the logging url is set
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
    k = request.json['k'] if 'k' in request.json else 20
    return jsonify([dataclasses.asdict(block) for block in get_top_k_blocks(PINECONE_INDEX, query, k)])



# ------------------------------------ chat ------------------------------------


@app.route('/chat', methods=['POST'])
@cross_origin()
def chat():

    query = request.json['query']
    history = request.json['history']

    return Response(stream(talk_to_robot(PINECONE_INDEX, query, history, log = log)), mimetype='text/event-stream')


# ------------- simplified non-streaming chat for internal testing -------------

@app.route('/chat/<path:param>', methods=['GET'])
@cross_origin()
def chat_simplified(param=''):
    return Response(talk_to_robot_simple(PINECONE_INDEX, param))



# ---------------------- human authored content retrieval ----------------------

# act as a proxy, forwarding any requests to /human/<id> to
# https://aisafety.info/questions/<id> in order to get around CORS
@app.route('/human/<id>', methods=['GET'])
@cross_origin()
def human(id):
    import requests
    r = requests.get(f"https://aisafety.info/questions/{id}")
    log(f"clicked followup '{json.loads(r.text)['data']['title']}': https://stampy.ai/?state={id}")

    return Response(r.text, mimetype='application/json')


# ------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True, port=3000)
