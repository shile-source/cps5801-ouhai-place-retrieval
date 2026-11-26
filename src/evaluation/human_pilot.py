"""Single-rater source-text pilot. No automatic grades or formal-study promotion."""
from datetime import datetime
import csv
import hashlib
import json
from pathlib import Path
import random
import threading
from urllib.request import Request, urlopen

from .metrics import score_query

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'data/clean/pilot_mixed_v0_3_osm_20261031/poi_candidates.json'
SESSION = ROOT / 'data/labels/pilot_human_v0_1_20261102'
RULES = ('仅评价来源快照文本对查询的支持，不判断地点现在是否营业或实际位于瓯海。'
         '2=核心需求有充分事实支持；1=有事实支持部分需求；0=有事实可判断不相关。'
         '资料不足不填0，选择“资料不足”并说明原因。多偏好中缺失的数量不当作不满足。'
         '座位较多在本Pilot中约定为>=40，藏书较多为>=12000；这些阈值不是自动标签。'
         '请不查看模型排名。你已看过此前功能示例，因此结果只能作为有暴露限制的单人Pilot。')


def now():
    return datetime.now().astimezone().isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


QUERIES = [
    {'query_id': 'P01', 'query_type': 'named_lexical', 'text': '查找数安港城市书房。',
     'rubric': '核心需求是这个名称对应的记录。名称歧义时暂停判断，不把所有书房当同一实体。'},
    {'query_id': 'P02', 'query_type': 'named_lexical', 'text': '我想找景山城市书房。',
     'rubric': '评价名称是否支持所求记录；不是给所有同类别设施相同分数。'},
    {'query_id': 'P03', 'query_type': 'named_lexical', 'text': '请找龙舟公园城市书房。',
     'rubric': '核心需求是完整名称指向的阅读设施，不是只有“公园”字样的其他记录。'},
    {'query_id': 'P04', 'query_type': 'semantic_paraphrase', 'text': '想找个读书的去处。',
     'rubric': '根据明确的阅读设施类别和来源事实判断，不推断安静程度或当前开放状态。'},
    {'query_id': 'P05', 'query_type': 'semantic_paraphrase', 'text': '我想看看园林绿地类的地点。',
     'rubric': '根据明确的公园等类别及文本判断；不推断步道、景观质量或设施。'},
    {'query_id': 'P06', 'query_type': 'semantic_paraphrase', 'text': '想找与收藏和展示物品相关的场馆。',
     'rubric': '按博物馆等明确类别对概念的支持评价；不推断具体展览或藏品种类。'},
    {'query_id': 'P07', 'query_type': 'multi_preference', 'text': '希望找到座位较多、藏书也较多的阅读点。',
     'rubric': '两个软目标：座位>=40且藏书>=12000。都获支持可2，部分明确获支持可1，明确均不相关可0；缺失事实影响结论时资料不足。'},
    {'query_id': 'P08', 'query_type': 'multi_preference', 'text': '优先看看城市书房，同时希望座位较多。',
     'rubric': '两个软目标：类别为城市书房、座位>=40。未知座位不能假定满足或不满足。'},
]


def prepare(session=SESSION, corpus=CORPUS, *, queries=None):
    session, corpus = Path(session), Path(corpus)
    if session.exists():
        return session  # Never overwrite a human session.
    records = json.loads(corpus.read_text(encoding='utf-8'))
    ids = [r['poi_id'] for r in records]
    if not records or len(ids) != len(set(ids)):
        raise ValueError('Candidate IDs must be unique')
    queries = queries or QUERIES
    if len({q['query_id'] for q in queries}) != len(queries):
        raise ValueError('Query IDs must be unique')
    session.mkdir(parents=True, exist_ok=False)
    (session / 'corpus.json').write_bytes(corpus.read_bytes())
    packet = {'purpose': 'single_rater_preliminary_source_text_relevance', 'created_at': now(),
              'formal_evaluation': False, 'human_reviewed': False, 'rules': RULES,
              'query_design': 'AI-assisted convenience drafts; not independently authored held-out queries',
              'annotator_prior_exposure': True, 'candidate_verification': 'not independently verified',
              'source_corpus_sha256': sha(corpus), 'queries': queries, 'shuffle_seed': 5801,
              'candidate_ids': ids, 'binary_relevance_threshold': 2}
    (session / 'packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    (session / 'manifest.json').write_text(json.dumps({'packet_sha256': sha(session/'packet.json'),
                                                    'corpus_sha256': sha(session/'corpus.json')}, indent=2), encoding='utf-8')
    return session


class Pilot:
    def __init__(self, session=SESSION):
        self.path = Path(session)
        self.lock = threading.RLock()
        self.packet = json.loads((self.path/'packet.json').read_text(encoding='utf-8'))
        self.manifest = json.loads((self.path/'manifest.json').read_text(encoding='utf-8'))
        self.verify()
        self.records = {r['poi_id']: r for r in json.loads((self.path/'corpus.json').read_text(encoding='utf-8'))}
        self.queries = {q['query_id']: q for q in self.packet['queries']}
        self.tasks = []
        for q in self.packet['queries']:
            order = list(self.packet['candidate_ids'])
            random.Random(self.packet['shuffle_seed'] + len(self.tasks)).shuffle(order)
            self.tasks.extend((q['query_id'], p) for p in order)

    def verify(self):
        if sha(self.path/'packet.json') != self.manifest['packet_sha256'] or sha(self.path/'corpus.json') != self.manifest['corpus_sha256']:
            raise ValueError('Frozen Pilot packet changed; stop, do not relabel against changed inputs')

    def events(self):
        file = self.path/'human_actions.jsonl'
        if not file.exists():
            return []
        return [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines() if line.strip()]

    def review(self):
        reviews = [r for r in self.events() if r['action'] == 'human_query_review']
        return reviews[-1] if reviews else None

    def ratings(self):
        ratings = {}
        for event in self.events():
            if event['action'] == 'human_rating':
                ratings[event['query_id'], event['poi_id']] = event
            elif event['action'] == 'assisted_annotation_correction':
                pair = event['query_id'], event['poi_id']
                previous = ratings.get(pair)
                if previous and previous['recorded_at'] == event['supersedes_recorded_at']:
                    ratings[pair] = event
        return ratings

    def append(self, record):
        record.update(recorded_at=now(), packet_sha256=self.manifest['packet_sha256'])
        with (self.path/'human_actions.jsonl').open('a', encoding='utf-8') as file:
            file.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')

    def approve(self, annotator, query_ids, accepted):
        with self.lock:
            self.verify()
            if not isinstance(annotator, str) or not annotator.strip() or len(annotator) > 80:
                raise ValueError('请输入真实评分者署名')
            if accepted is not True or not isinstance(query_ids, list) or set(query_ids) != set(self.queries) or len(query_ids) != len(self.queries):
                raise ValueError('需要人工逐条确认查询及规则；不同意的查询请先反馈修改，不自动批准')
            existing = self.review()
            if existing:
                if existing['annotator'] != annotator.strip():
                    raise ValueError('本版本是单评分者Pilot，不混合不同人标签')
                return
            self.append({'action': 'human_query_review', 'annotator': annotator.strip(),
                         'query_ids': query_ids, 'accepted_rules': True, 'source': 'user_local_ui'})

    def rate(self, qid, pid, grade, reason='', evidence='', notes=''):
        with self.lock:
            self.verify()
            review = self.review()
            if not review:
                raise ValueError('请先人工确认查询与规则')
            if any(e['action']=='pilot_evaluation_published' for e in self.events()):
                raise ValueError('已显示指标，原评分锁定；修改需建立新版本并说明原因，不能按模型表现改分')
            if qid not in self.queries or pid not in self.records:
                raise ValueError('Unknown query/candidate')
            if grade is not None and (type(grade) is not int or grade not in (0, 1, 2)):
                raise ValueError('评分只能0/1/2，资料不足须留空')
            if grade is None and not str(reason).strip():
                raise ValueError('资料不足时请写明缺少什么事实')
            if grade is not None and not str(evidence).strip():
                raise ValueError('请记录本次判断依据的字段或事实')
            if max(len(str(x)) for x in (reason, evidence, notes)) > 2000:
                raise ValueError('输入过长')
            self.append({'action': 'human_rating', 'query_id': qid, 'poi_id': pid,
                         'semantic_grade': grade, 'unknown_reason': str(reason).strip(),
                         'evidence': str(evidence).strip(), 'notes': str(notes).strip(),
                         'annotator': review['annotator'], 'source': 'user_local_ui'})

    def state(self, index=0):
        with self.lock:
            self.verify()
            if type(index) is not int or not 0 <= index < len(self.tasks):
                raise ValueError('Invalid task index')
            ratings = self.ratings()
            qid, pid = self.tasks[index]
            record = self.records[pid]
            # No model/rank/score keys or ranking-dependent order in this payload.
            fact = {k: record.get(k) or '' for k in ('poi_id', 'name', 'category', 'address', 'description', 'source_url')}
            next_unhandled = next((i for i, pair in enumerate(self.tasks) if pair not in ratings), None)
            counts = {q: sum((q, p) in ratings and ratings[q,p]['semantic_grade'] is not None
                             for p in self.records) for q in self.queries}
            return {'purpose': self.packet['purpose'], 'formal_evaluation': False,
                    'packet_sha256': self.manifest['packet_sha256'],
                    'rules': self.packet['rules'], 'queries': list(self.queries.values()),
                    'review': self.review(), 'total': len(self.tasks), 'index': index,
                    'graded': sum(r['semantic_grade'] is not None for r in ratings.values()),
                    'unknown': sum(r['semantic_grade'] is None for r in ratings.values()),
                    'handled': len(ratings), 'next_unhandled': next_unhandled,
                    'query_counts': counts, 'candidate_count': len(self.records),
                    'query': self.queries[qid], 'candidate': fact,
                    'existing': ratings.get((qid,pid)),
                    'field_evidence_ref': 'data/clean/pilot_mixed_v0_3_osm_20261031/field_evidence.json#'+pid}

    def evaluate(self, fetch=None):
        """Actual human grades only. score_query is shared, without faking formal gates."""
        with self.lock:
            self.verify()
            ratings = self.ratings()
            review = self.review()
            if not review:
                raise ValueError('No human query review')
            if len(ratings) != len(self.tasks):
                return {'status':'not_ready','formal_evaluation':False,
                        'message':'请先处理全部配对（可选择资料不足），完成盲标前不显示模型评价结果。',
                        'excluded':[{'query_id':q,'reason':'human_annotation_not_finished'} for q in self.queries]}
            rows, excluded = [], []
            raw_runs = []
            fetch = fetch or self.fetch_live
            for qid, query in self.queries.items():
                judgments = {pid: ratings.get((qid,pid), {}).get('semantic_grade') for pid in self.records}
                if any(g is None for g in judgments.values()):
                    excluded.append({'query_id': qid, 'reason': 'incomplete_or_unknown_human_judgments',
                                     'judged': sum(g is not None for g in judgments.values()), 'required': len(self.records)})
                    continue
                for method in ('bm25', 'encoder'):
                    try:
                        run = fetch(method, query['text'], len(self.records))
                    except Exception as exc:
                        self.append({'action':'evaluation_failed','query_id':qid,'method':method,'error':str(exc)})
                        raise
                    if run.get('corpus_sha256') != self.packet['source_corpus_sha256']:
                        raise ValueError('Ranker corpus differs from frozen Pilot')
                    ranking = [r['poi_id'] for r in run['results']]
                    if len(ranking) != len(self.records) or set(ranking) != set(self.records):
                        raise ValueError('Full common ranking required for MRR')
                    result = score_query(ranking, judgments, eligible_ids=list(self.records), include_recall=True)
                    raw_runs.append({'query_id': qid, 'method': method, 'run': run})
                    rows.append({'query_id': qid, 'query_type': query['query_type'], 'method': method,
                                 **result['metrics']})
            if not rows:
                return {'status': 'not_ready', 'message': '至少一条查询的全部候选需有可判断的人类评分；未知不补0。',
                        'excluded': excluded, 'formal_evaluation': False}
            aggregates = []
            for method in ('bm25', 'encoder'):
                for group in ['all']+sorted({r['query_type'] for r in rows}):
                    selected = [r for r in rows if r['method'] == method and (group == 'all' or r['query_type'] == group)]
                    aggregates.append({'method': method, 'query_type': group, 'query_count': len(selected),
                        **{metric+'_n':sum(r[metric] is not None for r in selected)
                           for metric in ('ndcg_at_5','precision_at_3','mrr','recall_at_5')},
                        **{metric: (sum(r[metric] for r in selected if r[metric] is not None)/sum(r[metric] is not None for r in selected)
                                   if any(r[metric] is not None for r in selected) else None)
                           for metric in ('ndcg_at_5', 'precision_at_3', 'mrr', 'recall_at_5')}})
            result = {'status': 'pilot_scored', 'purpose': self.packet['purpose'], 'formal_evaluation': False,
                      'annotator_count': 1, 'annotator': review['annotator'], 'kappa': None,
                      'limitations': ['single rater; previous example exposure', 'AI-assisted reviewed convenience queries, not held-out',
                                     'unverified candidate records; source-text relevance only', 'no hard constraints or map validation'],
                      'packet_sha256': self.manifest['packet_sha256'], 'actions_sha256': sha(self.path/'human_actions.jsonl'),
                      'per_query': rows, 'summary': aggregates, 'excluded': excluded, 'raw_runs': raw_runs}
            output = self.path / ('evaluation_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
            with output.open('x', encoding='utf-8') as file:
                json.dump(result, file, ensure_ascii=False, indent=2, allow_nan=False)
            # Human-grade-derived tables only; no output is fabricated while
            # annotation is incomplete. Keep every evaluation as a new version.
            columns=['method','query_type','query_count','ndcg_at_5','precision_at_3','mrr','recall_at_5',
                     'ndcg_at_5_n','precision_at_3_n','mrr_n','recall_at_5_n']
            with output.with_suffix('.csv').open('x',encoding='utf-8-sig',newline='') as file:
                writer=csv.DictWriter(file,fieldnames=columns)
                writer.writeheader();writer.writerows(aggregates)
            report=['# Preliminary single-rater source-text relevance pilot','',
                    'These are human-rated convenience-query results, not held-out or independently verified place-recommendation results.',
                    'One rater; earlier example exposure; no inter-rater kappa. Unknown/incomplete queries excluded.','',
                    '| Method | Query type | Queries | nDCG@5 | P@3 | MRR | Recall@5 |',
                    '|---|---|---:|---:|---:|---:|---:|']
            for row in aggregates:
                report.append('| '+' | '.join(str(row[k]) if k in ('method','query_type','query_count') else
                    ('N/A' if row[k] is None else f'{row[k]:.4f}')
                    for k in ('method','query_type','query_count','ndcg_at_5','precision_at_3','mrr','recall_at_5'))+' |')
            report += ['',f'Excluded queries: {len(excluded)}. Per-metric valid query counts, raw rankings and provenance are retained in '+output.name+'.']
            output.with_suffix('.md').write_text('\n'.join(report),encoding='utf-8')
            self.append({'action':'pilot_evaluation_published','output':output.name,
                         'query_ids':sorted({r['query_id'] for r in rows})})
            return result

    @staticmethod
    def fetch_live(method, query, count):
        body = json.dumps({'method': method, 'query': query, 'top_k': count}, ensure_ascii=False).encode()
        request = Request('http://127.0.0.1:8767/api/search', data=body,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=180) as response:
            return json.load(response)
