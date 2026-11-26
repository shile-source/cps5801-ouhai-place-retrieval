"""Loopback-only human Pilot UI. Never creates automatic human ratings."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from src.evaluation.human_pilot import Pilot, prepare, SESSION


def handler(pilot, *, page_path=None, allow_evaluation=True):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, data):
            body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(body)

        def do_GET(self):
            path=urlparse(self.path)
            try:
                if path.path=='/api/task':
                    self.send(200,pilot.state(int(parse_qs(path.query).get('index',['0'])[0])))
                elif path.path=='/':
                    body=Path(page_path or Path(__file__).with_name('annotation.html')).read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type','text/html; charset=utf-8')
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Cache-Control','no-store')
                    self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
                    self.end_headers();self.wfile.write(body)
                else:self.send(404,{'error':'Not found'})
            except (ValueError,KeyError) as exc:self.send(400,{'error':str(exc)})

        def do_POST(self):
            try:
                host=self.headers.get('Host','')
                valid={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=12000:raise ValueError('Request size invalid')
                body=self.rfile.read(length)
                if host not in valid or self.headers.get('Origin',f'http://{host}')!=f'http://{host}':
                    self.send(403,{'error':'Local same-origin requests only'});return
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
                value=json.loads(body)
                if not isinstance(value,dict):raise ValueError('JSON object required')
                if self.path=='/api/review':
                    pilot.approve(value.get('annotator'),value.get('query_ids'),value.get('accepted_rules'))
                    self.send(200,{'saved':True})
                elif self.path=='/api/rating':
                    if 'grade' not in value:raise ValueError('Explicit human judgment required')
                    pilot.rate(value.get('query_id'),value.get('poi_id'),value['grade'],
                               value.get('reason',''),value.get('evidence',''),value.get('notes',''))
                    self.send(200,{'saved':True})
                elif self.path=='/api/evaluate':
                    if not allow_evaluation:
                        self.send(403,{'error':'本页只收集第二位评分者判断，不调用模型或显示评价结果。'});return
                    # Metrics only; raw model rankings are retained on disk and
                    # intentionally omitted from this blind presentation.
                    result=pilot.evaluate()
                    self.send(200,{k:v for k,v in result.items() if k!='raw_runs'})
                else:self.send(404,{'error':'Not found'})
            except (ValueError,KeyError,TypeError) as exc:self.send(400,{'error':str(exc)})
            except Exception as exc:self.send(500,{'error':str(exc),'note':'未生成或补填任何人类评分；不自动重试模型'})
    return Handler


def main():
    prepare()
    service=ThreadingHTTPServer(('127.0.0.1',8768),handler(Pilot()))
    print(json.dumps({'url':'http://127.0.0.1:8768/','session':str(SESSION),'labels_prefilled':False}),flush=True)
    service.serve_forever()


if __name__=='__main__':main()
