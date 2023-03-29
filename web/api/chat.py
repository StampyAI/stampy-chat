# ---------------------------------- web code ----------------------------------

import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        self.wfile.write(chat(data['history'], data['query']).encode('utf-8'))

# ------------------------------- chat gpt stuff -------------------------------

def chat(history, query) -> str:

    # history = [
    #     {'role': 'user', 'content': 'Open the pod bay doors'},
    #     {'role': 'assistant', 'content': 'I'm sorry, Dave. I'm afraid I can't do that.'},
    #     {'role': 'user', 'content': 'Who won the world series in 2020?'},
    #     {'role': 'assistant', 'content': 'The Los Angeles Dodgers won the World Series in 2020.'},
    # ]
    #
    # query = 'Who will win the world series in 2023?'
    #
    # (if you want any system message, add it yourself)

    return "no, you're a " + query

