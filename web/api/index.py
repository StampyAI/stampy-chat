import json
import functools
import time
from http.server import BaseHTTPRequestHandler

@functools.cache
def factorial(n):
    return 1 if n <= 0 else n * factorial(n - 1)

class handler(BaseHTTPRequestHandler):

    # post request = calculate factorial of passed number
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        result = factorial(data['number'])
        self.wfile.write(json.dumps({'result': result}).encode('utf-8'))
