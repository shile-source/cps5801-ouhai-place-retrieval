"""Serve only the independent query form on loopback; no submission endpoint."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FORM=Path(__file__).resolve().parents[2]/'outputs/independent_study_preparation_20261125/query_author_form.html'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/','/query_author_form.html','/download'):
            self.send_error(404)
            return
        body=FORM.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if self.path=='/download':
            self.send_header('Content-Disposition','attachment; filename="query_author_form.html"')
        self.end_headers()
        self.wfile.write(body)


if __name__=='__main__':
    if not FORM.is_file():
        raise SystemExit('Prepared human query form is missing')
    ThreadingHTTPServer(('127.0.0.1',8769),Handler).serve_forever()
