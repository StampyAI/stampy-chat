import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    # post request = calculate factorial of passed number
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        # results = embeddings(data['query'])
        results = { 'results'  : 'foo' }
        self.wfile.write(json.dumps(results).encode('utf-8'))

def embeddings(query):

    # write a function here that takes a query, returns a bunch of semantically similar links

    return [ \
        'https://www.lesswrong.com/posts/FinfRNLMfbq5ESxB9/microsoft-research-paper-claims-sparks-of-artificial', \
        'https://www.lesswrong.com/posts/XhfBRM7oRcpNZwjm8/abstracts-should-be-either-actually-short-tm-or-broken-into', \
        'https://www.lesswrong.com/posts/ohXcBjGvazPAxq2ex/continue-working-on-hard-alignment-don-t-give-up'
    ]
