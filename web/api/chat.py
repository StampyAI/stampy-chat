# ---------------------------------- web code ----------------------------------

import json
import dataclasses
from http.server import BaseHTTPRequestHandler

@dataclasses.dataclass
class Block:
    title: str
    author: str
    date: str
    url: str
    tags: str
    text: str

class Encoder(json.JSONEncoder):
    def default(self, o):
        return dataclasses.asdict(o) if dataclasses.is_dataclass(o) else super().default(o)

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        self.wfile.write(f"no, you're a {data['query']}".encode())
