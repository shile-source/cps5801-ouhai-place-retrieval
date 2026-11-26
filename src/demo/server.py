"""Loopback-only live search API; stdlib HTTP, existing BM25 and local Encoder."""
import argparse
from datetime import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from src.demo.navigation import destination, load_notes

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'data/clean/pilot_mixed_v0_3_osm_20261031/poi_candidates.json'
MODEL_REVISION = '4328cf26390c98c5e3c738b4460a05b95f4911f5'


def map_preview(record):
    """Show only OSM source points, separately from verified entrances."""
    if not record['poi_id'].startswith('osm_node_') or record.get('original_crs') != 'WGS84':
        return None
    lat, lon = record.get('latitude'), record.get('longitude')
    if (type(lat) not in (int, float) or type(lon) not in (int, float)
            or not math.isfinite(lat) or not math.isfinite(lon)
            or not 27 <= lat <= 29 or not 119 <= lon <= 122):
        return None
    return {'latitude': lat, 'longitude': lon, 'status': 'unverified_osm_point'}


def map_location(record):
    """Display OSM nodes or explicitly documented bbox centres, never guessed entrances."""
    point = map_preview(record)
    if point:
        return {**point, 'kind': 'source_node', 'entrance_verified': False}
    if (not record['poi_id'].startswith(('osm_way_', 'osm_relation_'))
            or record.get('coordinate_kind') != 'overpass_bounding_box_center'):
        return None
    point = map_preview(dict(record, poi_id='osm_node_display_validation'))
    return {**point, 'kind': 'bounding_box_center', 'entrance_verified': False,
            'status': 'approximate_source_area_center'} if point else None

class StorageGuardError(RuntimeError):
    pass

def validate_request(value):
    if not isinstance(value, dict) or value.get('method') not in ('keyword','bm25','encoder','bge_m3'):
        raise ValueError('检索方法必须是 keyword、bm25、encoder 或 bge_m3')
    query = value.get('query')
    if not isinstance(query,str) or not query.strip() or len(query) > 500:
        raise ValueError('请输入1–500字的查询')
    return value['method'], query.strip()

class SearchEngine:
    def __init__(self, corpus, run_dir, min_c_gib=5.0, space=None, encoder_enabled=True,allow_bge=False,safe_streaming=False,facts_binding=None):
        from src.data.load_candidates import load_candidates
        from src.retrieval.bm25 import BM25Retriever
        from src.retrieval.keyword import KeywordRetriever
        self.corpus, self.run_dir = Path(corpus), Path(run_dir)
        self.pois = load_candidates(corpus)
        self.records = {row['poi_id']:row for row in json.loads(self.corpus.read_text(encoding='utf-8'))}
        self.bm25 = BM25Retriever(self.pois)
        self.keyword = KeywordRetriever(self.pois)
        self.corpus_hash = hashlib.sha256(self.corpus.read_bytes()).hexdigest()
        self.source_facts=None
        if facts_binding is not None:
            from src.data.fact_store import load_bound_facts
            self.source_facts=load_bound_facts(facts_binding,self.corpus,ROOT)
        self.navigation_notes = load_notes()
        self.min_c_gib = min_c_gib
        self.encoder_enabled = encoder_enabled
        self.allow_bge=allow_bge
        self.safe_streaming=safe_streaming
        self.worker_backend='encoder'
        self.backend_failures={}
        self.reader_thread=None
        self.space = space or (lambda drive: shutil.disk_usage(drive + ':/').free)
        self.lock = threading.Lock()
        self.worker = None
        self.worker_info = None
        self.worker_error = None
        self.messages = queue.Queue()
        self.stderr_handle = None
        self.stop_monitor = threading.Event()
        self.model_baseline = None
        threading.Thread(target=self._monitor,daemon=True).start()

    def storage_guard(self):
        c, d = self.space('C'), self.space('D')
        if c < self.min_c_gib * 1024**3 or d < 10 * 1024**3:
            raise StorageGuardError(f'C盘可用 {c/1024**3:.2f} GiB，模型保护线 {self.min_c_gib:g} GiB；D盘可用 {d/1024**3:.2f} GiB（需≥10）。本次模型操作未完成，不返回静态替代结果。')
        if self.model_baseline and self.model_baseline-c > (0.25 if self.min_c_gib < 5 else 1)*1024**3:
            raise StorageGuardError('模型运行期间C盘空间下降达到保护限额，已停止模型工作器。')

    def _monitor(self):
        while not self.stop_monitor.wait(1):
            worker, backend = self.worker, self.worker_backend
            if worker and worker.poll() is None:
                try:
                    self.storage_guard()
                except StorageGuardError as exc:
                    if self.worker is not worker:
                        continue  # A completed backend switch must not stop its replacement.
                    self.worker_error = str(exc)
                    self.backend_failures[backend]=str(exc)
                    worker.terminate()  # 仅终止本演示自己创建的模型进程。

    def _receive(self, timeout=150):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if self.worker_error:
                raise StorageGuardError(self.worker_error)
            try:
                message = self.messages.get(timeout=0.25)
                if message.get('type') == 'error':
                    raise RuntimeError(message['error'])
                return message
            except queue.Empty:
                if self.worker.poll() is not None:
                    if self.worker_error:
                        raise StorageGuardError(self.worker_error)
                    raise RuntimeError(f'模型工作器退出（exit={self.worker.returncode}），请核对D盘 encoder_stderr.log')
        self.worker.terminate()
        raise RuntimeError('模型响应超过150秒，已停止本次工作器；不会自动重试')

    def _release_worker(self):
        if self.worker and self.worker.poll() is None:
            self.worker.terminate();self.worker.wait(timeout=10)
        if self.reader_thread:
            self.reader_thread.join(timeout=3)
        if self.stderr_handle:
            self.stderr_handle.close()
        self.worker=None;self.worker_info=None;self.worker_error=None;self.stderr_handle=None
        self.reader_thread=None;self.messages=queue.Queue();self.model_baseline=None

    def _load_encoder(self,backend='encoder'):
        if not self.encoder_enabled:
            raise RuntimeError('本服务的模型已暂停；此前保护停止的模型不会自动重试。已保存的实验结果仍可查看。')
        if backend not in ('encoder','bge_m3') or (backend=='bge_m3' and not self.allow_bge):
            raise ValueError('本服务未启用该模型')
        if backend in self.backend_failures:
            raise RuntimeError(self.backend_failures[backend]+'；本模型已停止，未自动重试')
        self.storage_guard()
        if self.worker is not None and self.worker_backend!=backend:
            if self.worker_error or self.worker.poll() is not None:
                self.backend_failures[self.worker_backend]=self.worker_error or '模型工作器已停止'
            self._release_worker()
        if self.worker is not None:
            if self.worker.poll() is not None:
                raise RuntimeError(self.worker_error or '模型工作器已停止；请检查错误，未自动重启')
            return 0.0
        self.model_baseline = self.space('C')
        self.worker_backend=backend
        self.stderr_handle = (self.run_dir / (backend+'_stderr_'+uuid.uuid4().hex[:8]+'.log')).open('x',encoding='utf-8')
        env = dict(os.environ, HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8',
                   PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        if self.safe_streaming:
            env.update(CPS5801_DENSE_LOADER='streamed',CPS5801_BGE_LOADER='streamed',
                       CPS5801_SAFETENSORS_BACKEND='pread',CPS5801_BGE_DIRECT_GPU_LOAD='1',
                       CPS5801_EMBEDDING_PRECISION='float32',CUDA_MODULE_LOADING='LAZY',CUDA_MODULE_DATA_LOADING='LAZY')
        self.worker = subprocess.Popen([sys.executable,'-u','-m','src.demo.encoder_worker',str(self.corpus),backend],
            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr_handle,
            text=True, encoding='utf-8', bufsize=1)
        current_worker,current_messages=self.worker,self.messages
        def reader():
            for line in current_worker.stdout:
                try:
                    current_messages.put(json.loads(line))
                except json.JSONDecodeError:
                    current_messages.put({'type':'error','error':'模型工作器输出格式异常；未使用静态结果'})
        self.reader_thread=threading.Thread(target=reader,daemon=True);self.reader_thread.start()
        self.worker_info = self._receive()
        if self.worker_info.get('type') != 'ready':
            raise RuntimeError('模型工作器未就绪')
        return self.worker_info['load_ms']

    def status(self):
        encoder_state = ('stopped' if self.worker is not None and (self.worker_error or self.worker.poll() is not None)
                         else 'ready' if self.worker_info else 'loading' if self.worker else 'not_loaded')
        if not self.encoder_enabled:
            encoder_state='disabled'
        states={method:('disabled' if not self.encoder_enabled else 'stopped' if method in self.backend_failures
                       else encoder_state if self.worker and self.worker_backend==method else 'not_loaded')
                for method in ('encoder','bge_m3')}
        return {'candidate_count':len(self.pois), 'corpus_sha256':self.corpus_hash,
            'corpus_snapshot': self.corpus.parent.name, 'encoder_state': states['encoder'],
            'live_backend':True, 'saved_results_used':False, 'bm25_ready':True,
            'encoder_ready':states['encoder']=='ready',
            'encoder_error':self.worker_error, 'encoder_min_c_gib':self.min_c_gib,
            'encoder_enabled':self.encoder_enabled,
            'bge_available':self.allow_bge,'dense_states':states,'safe_streaming':self.safe_streaming,
            'explicit_hard_filter_available':self.source_facts is not None,
            'active_dense_backend':self.worker_backend if self.worker and self.worker.poll() is None else None,
            'disk_free_gib':{d:round(self.space(d)/1024**3,2) for d in ('C','D')},
            'model_revision':MODEL_REVISION,
            'model_revisions':{'encoder':MODEL_REVISION,
                               'bge_m3':'694b61558aea4ae2512ed8d0e189d5cf8adc2259'}}

    def places(self):
        fields = ('poi_id', 'name', 'category', 'address', 'description', 'source_url')
        rows = [
            {**{field: record.get(field) or '' for field in fields},
             'map_preview': map_preview(record), 'map_location': map_location(record), 'navigation': destination(record, self.navigation_notes)}
            for record in self.records.values()
        ]
        rows.sort(key=lambda row: (row['name'], row['poi_id']))
        return {'candidate_count': len(rows), 'corpus_sha256': self.corpus_hash,
                'places': rows, 'order': 'name_then_id', 'formal_evaluation_ready': False}

    def search(self, method, query, top_k=5, constraints=None):
        from src.retrieval.bm25 import tokenize
        from src.retrieval.constraints import parse_explicit_constraints,shared_pool
        if method not in ('keyword','bm25','encoder','bge_m3'):raise ValueError('Unknown retrieval method')
        if type(top_k) is not int or not 1 <= top_k <= 1000:
            raise ValueError('top_k必须是1至1000之间的整数')
        explicit=parse_explicit_constraints(constraints)
        pool=None;allowed=None
        if explicit:
            if self.source_facts is None:raise ValueError('本快照尚未绑定筛选证据，不能猜测硬条件')
            pool=shared_pool(self.source_facts,explicit)
            allowed=set(pool['eligible_ids'])
        began = time.perf_counter()
        with self.lock:
            load_ms = 0
            if allowed is not None and not allowed:
                rows=[];search_ms=0.0  # An empty shared pool must not start a GPU worker.
            elif method in ('keyword','bm25'):
                start = time.perf_counter()
                rows = [{'rank':r.rank,'poi_id':r.poi_id,'score':r.score,'model':r.model}
                        for r in (self.keyword if method=='keyword' else self.bm25).search(query,top_k,predicate=(lambda p:p.poi_id in allowed) if allowed is not None else None)]
                search_ms = (time.perf_counter()-start)*1000
            elif method in ('encoder','bge_m3'):
                try:
                    load_ms = self._load_encoder(method)
                    self.storage_guard()
                    request={'query':query,'top_k':min(top_k,len(self.pois))}
                    if allowed is not None:request['eligible_ids']=sorted(allowed)
                    self.worker.stdin.write(json.dumps(request,ensure_ascii=False)+'\n')
                    self.worker.stdin.flush()
                    message = self._receive()
                    if message.get('type') != 'result':
                        raise RuntimeError('模型没有返回检索结果')
                    rows, search_ms = message['rows'], message['search_ms']
                    self.storage_guard()
                except Exception as exc:
                    self.backend_failures[method]=str(exc)
                    if self.worker is not None and self.worker_backend==method:
                        self.worker_error = str(exc)
                        if self.worker.poll() is None:
                            self.worker.terminate()
                    raise
            else:
                raise ValueError('Unknown retrieval method')
            tokens = set(tokenize(query))
            if allowed is not None and any(row['poi_id'] not in allowed for row in rows):
                raise ValueError('Ranking returned a candidate outside the common evidence pool')
            for row in rows:
                source = self.records[row['poi_id']]
                row.update({key:source.get(key) or '' for key in ('name','category','address','description','source_url')})
                row['map_preview'] = map_preview(source)
                row['map_location'] = map_location(source)
                row['navigation'] = destination(source, self.navigation_notes)
                row['matched_tokens'] = sorted(tokens & set(tokenize('\n'.join(row[k] for k in ('name','category','address','description')))))
                row['verification_status'] = '地点区属、位置和当前运营仍待独立核验'
            response = {'request_id':uuid.uuid4().hex[:12], 'executed_at':datetime.now().astimezone().isoformat(),
                'query':query, 'method':method, 'candidate_count':len(self.pois), 'results':rows,
                'load_ms':load_ms, 'search_ms':search_ms, 'elapsed_ms':(time.perf_counter()-began)*1000,
                'corpus_sha256':self.corpus_hash, 'live_computation':True, 'saved_results_used':False,
                'dense_configuration':self.worker_info if method in ('encoder','bge_m3') else None,
                'eligible_candidate_count':len(allowed) if allowed is not None else len(self.pois),
                'hard_filter':({'scope':'source_snapshot_only','constraints':constraints,
                                'eligible_ids':pool['eligible_ids'],'unknown_ids':pool['unknown_ids'],
                                'unmet_ids':pool['unmet_ids'],'creates_relevance_grades':False} if pool else None),
                'warnings':['排序表示文本相关性，不证明费用、开放状态、距离或安静程度。',
                            '只按明确填写的条件筛选来源快照，未知不通过；未从查询自动推断条件。' if explicit else '未应用硬约束过滤。']}
            if '安静' in query or '学习' in query:
                response['warnings'].append('当前数据没有核实“安静/适合学习”，本结果不能证明这些体验属性。')
            if method in ('keyword','bm25') and rows and all(r['score']==0 for r in rows):
                response['warnings'].append('BM25全部得分为0，以下仅按ID打破同分，不是词汇命中。')
            with (self.run_dir/'live_searches.jsonl').open('a',encoding='utf-8') as log:
                log.write(json.dumps(response,ensure_ascii=False,allow_nan=False)+'\n')
            return response

    def close(self):
        self.stop_monitor.set()
        self._release_worker()

def make_handler(engine):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/api/status':
                self.send_json(200,engine.status())
            elif self.path == '/api/places':
                self.send_json(200,engine.places())
            elif self.path in ('/compare','/index.html'):
                body=Path(__file__).with_name('index.html').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src https://www.openstreetmap.org; frame-ancestors 'none'")
                self.end_headers(); self.wfile.write(body)
            elif self.path in ('/','/map','/map.html','/map.js','/map.css',
                                '/vendor/leaflet-1.9.4/leaflet.js','/vendor/leaflet-1.9.4/leaflet.css',
                                '/vendor/leaflet-1.9.4/LICENSE','/vendor/leaflet-1.9.4/PROVENANCE.json'):
                relative = 'map.html' if self.path in ('/','/map','/map.html') else self.path[1:]
                path = Path(__file__).parent / relative
                body = path.read_bytes()
                kinds = {'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8',
                         '.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8'}
                self.send_response(200)
                self.send_header('Content-Type', kinds.get(path.suffix, 'text/plain; charset=utf-8'))
                self.send_header('Content-Length', str(len(body)))
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
                self.end_headers(); self.wfile.write(body)
            else:
                self.send_json(404,{'error':'Not found'})

        def do_POST(self):
            if self.path not in ('/api/search','/api/constraints/propose'):
                self.send_json(404,{'error':'Not found'}); return
            try:
                if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise ValueError('Content-Type must be application/json')
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 8192:
                    raise ValueError('Request size must be 1–8192 bytes')
                body=self.rfile.read(length)
                host=self.headers.get('Host','')
                allowed={f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
                if host not in allowed or self.headers.get('Origin',f'http://{host}') != f'http://{host}':
                    self.send_json(403,{'error':'Only same-origin local requests allowed'}); return
                value=json.loads(body.decode('utf-8'))
                if self.path=='/api/constraints/propose':
                    from src.retrieval.constraint_proposals import propose_constraints
                    if not isinstance(value,dict):raise ValueError('JSON object required')
                    self.send_json(200,propose_constraints(value.get('query')));return
                method, query=validate_request(value)
                self.send_json(200,engine.search(method,query,top_k=value.get('top_k',5),constraints=value.get('constraints')))
            except StorageGuardError as exc:
                self.send_json(409,{'error':str(exc),'code':'STORAGE_GUARD','saved_results_used':False})
            except (ValueError,UnicodeError) as exc:
                self.send_json(400,{'error':str(exc)})
            except Exception as exc:
                self.send_json(500,{'error':str(exc),'saved_results_used':False})
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8767)
    parser.add_argument('--corpus',type=Path,default=CORPUS)
    parser.add_argument('--min-c-gib',type=float,default=5.0)
    parser.add_argument('--disable-encoder',action='store_true',help='Serve BM25/places without permitting a stopped model to restart')
    parser.add_argument('--enable-bge',action='store_true')
    parser.add_argument('--safe-streaming',action='store_true')
    parser.add_argument('--facts-binding',type=Path)
    args=parser.parse_args()
    if not 2 <= args.min_c_gib <= 20:
        raise ValueError('Model C protection threshold must be between 2 and 20 GiB')
    for name in ('TEMP','TMP','TMPDIR','PIP_CACHE_DIR','HF_HOME','HF_HUB_CACHE','TORCH_HOME','CUDA_CACHE_PATH'):
        if not os.environ.get(name,'').lower().startswith(str(ROOT).lower()):
            raise RuntimeError('Use Start-Project.ps1: project temporary/cache paths must be on D')
    run_dir=ROOT / 'outputs' / ('live_demo_'+datetime.now().strftime('%Y%m%d')) / datetime.now().strftime('%H%M%S_%f')
    run_dir.mkdir(parents=True,exist_ok=False)
    corpus=args.corpus.resolve()
    if not corpus.is_relative_to(ROOT / 'data' / 'clean'):
        raise ValueError('Demo corpus must be a project data/clean snapshot')
    engine=SearchEngine(corpus,run_dir,args.min_c_gib,encoder_enabled=not args.disable_encoder,
                        allow_bge=args.enable_bge,safe_streaming=args.safe_streaming,facts_binding=args.facts_binding)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(engine))
    startup={'url':f'http://127.0.0.1:{args.port}/','pid':os.getpid(),'run_dir':str(run_dir),**engine.status()}
    (run_dir/'startup.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(startup,ensure_ascii=False),flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close(); engine.close()

if __name__=='__main__':
    main()
