"""Local human-only query intake; contains no retrieval or judgment endpoint."""
import json
from pathlib import Path
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from src.evaluation.prospective_queries import QueryDraft

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'data/clean/research_review_v0_5_20261125/poi_candidates.json'
SESSION = ROOT / 'data/queries/prospective_human30_v1_20261126'


def handler(draft):
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, value, kind='application/json; charset=utf-8'):
            body = (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)).encode('utf-8')
            self.send_response(code)
            for key, val in [('Content-Type', kind), ('Content-Length', str(len(body))), ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'no-referrer'), ('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")]:
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)

        def local(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.local():
                self.send(403, {'error': 'Local host required'}); return
            if self.path == '/':
                self.send(200, (ROOT / 'src/demo/prospective_queries.html').read_text(encoding='utf-8'), 'text/html; charset=utf-8')
            elif self.path == '/api/state':
                self.send(200, {**draft.state(), 'request_token': token})
            elif self.path == '/api/catalog':
                records = json.loads(CORPUS.read_text(encoding='utf-8'))
                self.send(200, [{k: r.get(k) for k in ('name', 'category', 'address', 'description')} for r in records])
            else:
                self.send(404, {'error': 'Not found'})

        def do_POST(self):
            if not self.local() or self.headers.get('Origin') != f'http://127.0.0.1:{self.server.server_port}' or not secrets.compare_digest(self.headers.get('X-Query-Token', ''), token):
                self.send(403, {'error': 'Local token and origin required'}); return
            if self.path not in ('/api/draft', '/api/submit'):
                self.send(404, {'error': 'Not found'}); return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 100000 or self.headers.get_content_type() != 'application/json':
                    raise ValueError('Bounded JSON required')
                self.send(200, draft.save(json.loads(self.rfile.read(size)), self.path == '/api/submit'))
            except (ValueError, TypeError) as error:
                self.send(400, {'error': str(error)})

        def log_message(self, *args):
            pass
    return Handler


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8776), handler(QueryDraft(SESSION, CORPUS)))
    print('Human query intake http://127.0.0.1:8776/; no models', flush=True)
    server.serve_forever()
