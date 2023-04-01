from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from get_blocks import get_top_k_blocks
from chat import talk_to_robot
import dataclasses
import os
import openai
import pickle

# ---------------------------------- env setup ---------------------------------

if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# -------------------------------- load dataset --------------------------------


print('Loading dataset...')
with open('dataset.pkl', 'rb') as f:
    dataset_dict = pickle.load(f)
print('Done!')


# ---------------------------------- web setup ---------------------------------

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


# ------------------------------- semantic search ------------------------------


@app.route('/semantic', methods=['POST'])
@cross_origin()
def semantic():
    query = request.json['query']
    return jsonify([dataclasses.asdict(block) for block in get_top_k_blocks(dataset_dict, query)])


# ------------------------------------ chat ------------------------------------


@app.route('/chat', methods=['POST'])
@cross_origin()
def chat():
    query = request.json['query']

    is_valid, response, context = talk_to_robot(dataset_dict, query)

    if is_valid:
        return jsonify({'response': response, 'citations': [{'title': block.title, 'author': block.author, 'date': block.date, 'url': block.url} for block in context]})
    else:
        return jsonify({'error': response})

# ------------------------------------------------------------------------------

if __name__ == '__main__': app.run(debug=True, port=3000)
