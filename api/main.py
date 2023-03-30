from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"general kenobi": "hello there"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
