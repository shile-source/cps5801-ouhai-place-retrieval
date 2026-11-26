"""Loopback review UI with request token, append-only decisions and no model route."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit,parse_qs
from src.evaluation.adjudication import Adjudication

ROOT=Path(__file__).resolve().parents[2]


def handler(review,page):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def send(self,code,value,kind='application/json; charset=utf-8'):
            body=value.encode('utf-8') if isinstance(value,str) else json.dumps(value,ensure_ascii=False).encode('utf-8')
            self.send_response(code);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(body)
        def local(self):
            return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if not self.local():self.send(403,{'error':'Local host required'});return
            try:
                url=urlsplit(self.path)
                if url.path=='/':self.send(200,Path(page).read_text(encoding='utf-8'),'text/html; charset=utf-8')
                elif url.path=='/api/state':
                    index=int(parse_qs(url.query).get('index',['0'])[0])
                    self.send(200,{**review.state(index),'request_token':token})
                elif url.path=='/api/export':self.send(200,review.export())
                else:self.send(404,{'error':'Not found'})
            except (ValueError,KeyError) as error:self.send(400,{'error':str(error)})
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.local() or (origin is not None and origin!=f'http://127.0.0.1:{self.server.server_port}') or not secrets.compare_digest(self.headers.get('X-Review-Token',''),token):
                self.send(403,{'error':'Local review token and origin required'});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=20000 or self.headers.get_content_type()!='application/json':raise ValueError('Bounded JSON required')
                value=json.loads(self.rfile.read(size))
                if not isinstance(value,dict):raise ValueError('JSON object required')
                if self.path=='/api/decision':
                    event=review.decide(value['case_id'],value['grade'],value['reason'],value['reviewer'],value.get('confirmed'))
                    self.send(200,{'saved':True,'event':event})
                elif self.path=='/api/finalize':self.send(200,{'locked':True,'summary':review.finalize()})
                else:self.send(404,{'error':'Not found; this review cannot call models or compute metrics'})
            except (ValueError,KeyError,TypeError) as error:self.send(400,{'error':str(error)})
        def log_message(self,*args):pass
    return Handler


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--session',type=Path,required=True);parser.add_argument('--port',type=int,default=8775)
    args=parser.parse_args();path=args.session.resolve()
    if not path.is_relative_to(ROOT/'data/labels'):raise ValueError('Project review session required')
    review=Adjudication(path,ROOT)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(review,ROOT/'src/demo/adjudication.html'))
    print(json.dumps({'url':f'http://127.0.0.1:{args.port}/','total':review.state()['total'],'models_enabled':False}),flush=True)
    server.serve_forever()


if __name__=='__main__':main()
