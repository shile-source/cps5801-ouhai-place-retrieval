"""Separate post-publication human decisions; immutable source ratings remain untouched."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import threading


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create_session(session,items,bindings,root):
    session,root=Path(session),Path(root).resolve()
    if session.exists():
        current=Adjudication(session,root)
        if current.packet['items']!=items or current.packet['source_bindings']!=bindings:
            raise ValueError('Existing review belongs to different inputs; never overwrite it')
        return current
    if not items or len({x['case_id'] for x in items})!=len(items):
        raise ValueError('Unique nonempty cases required')
    session.mkdir(parents=True,exist_ok=False)
    packet={'purpose':'post_publication_first_rater_adjudication_NOT_independent_blind_labels',
            'created_at':datetime.now().astimezone().isoformat(),
            'original_labels_will_be_modified':False,'items':items,'source_bindings':bindings}
    (session/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    (session/'manifest.json').write_text(json.dumps({'packet_sha256':digest(session/'packet.json')},indent=2),encoding='utf-8')
    return Adjudication(session,root)


class Adjudication:
    def __init__(self,session,root):
        self.path,self.root=Path(session),Path(root).resolve()
        self.lock=threading.RLock()
        self.packet=json.loads((self.path/'packet.json').read_text(encoding='utf-8'))
        self.manifest=json.loads((self.path/'manifest.json').read_text(encoding='utf-8'))
        self.verify()

    def verify(self):
        if digest(self.path/'packet.json')!=self.manifest['packet_sha256']:
            raise ValueError('Review packet changed; stop')
        for relative,expected in self.packet['source_bindings'].items():
            path=(self.root/relative).resolve()
            if not path.is_relative_to(self.root) or digest(path)!=expected:
                raise ValueError('Original evidence or ratings changed; stop')
        marker=self.path/'review_lock.json'
        if marker.exists():
            lock=json.loads(marker.read_text(encoding='utf-8'))
            if digest(self.path/'decisions.jsonl')!=lock['decisions_sha256']:
                raise ValueError('Locked decisions changed; preserve evidence')

    def decisions(self):
        path=self.path/'decisions.jsonl'
        rows={}
        for line in path.read_text(encoding='utf-8').splitlines() if path.exists() else []:
            event=json.loads(line)
            if event['case_id'] not in {x['case_id'] for x in self.packet['items']}:
                raise ValueError('Unknown case in review history')
            rows[event['case_id']]=event
        return rows

    def state(self,index=0):
        with self.lock:
            self.verify();items=self.packet['items']
            if type(index) is not int or not 0<=index<len(items):raise ValueError('Invalid case index')
            decisions=self.decisions()
            return {'purpose':self.packet['purpose'],'total':len(items),'handled':len(decisions),
                    'unknown':sum(v['grade'] is None for v in decisions.values()),'index':index,
                    'item':items[index],'existing':decisions.get(items[index]['case_id']),
                    'next_unhandled':next((i for i,x in enumerate(items) if x['case_id'] not in decisions),None),
                    'locked':(self.path/'review_lock.json').exists(),'original_labels_modified':False}

    def decide(self,case_id,grade,reason,reviewer,confirmed):
        with self.lock:
            self.verify()
            if (self.path/'review_lock.json').exists():raise ValueError('Review locked; create a new version for corrections')
            if case_id not in {x['case_id'] for x in self.packet['items']}:raise ValueError('Unknown case')
            if grade is not None and (type(grade) is not int or grade not in (0,1,2)):
                raise ValueError('Grade must be0/1/2 or explicit unknown')
            if not isinstance(reason,str) or not 2<=len(reason.strip())<=2000:
                raise ValueError('请填写本次判断依据；资料不足时说明缺少什么事实')
            if not isinstance(reviewer,str) or not 1<=len(reviewer.strip())<=80 or any(ord(c)<32 for c in reviewer):
                raise ValueError('请填写你的复核者代号')
            if confirmed is not True:raise ValueError('请确认由你本人依据来源作出本次判断')
            event={'action':'human_adjudication','case_id':case_id,'grade':grade,'reason':reason.strip(),
                   'reviewer':reviewer.strip(),'source':'user_adjudication_ui',
                   'role':'first_rater_post_publication_reviewer','claims_independent_blind_judgment':False,
                   'saved_at':datetime.now().astimezone().isoformat()}
            with (self.path/'decisions.jsonl').open('a',encoding='utf-8',newline='\n') as file:
                file.write(json.dumps(event,ensure_ascii=False)+'\n');file.flush();os.fsync(file.fileno())
            return event

    def finalize(self):
        with self.lock:
            self.verify()
            if (self.path/'review_lock.json').exists():
                summary=self.export()
                if not (self.path/'completed_review.json').exists():
                    (self.path/'completed_review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
                return summary
            rows=self.decisions()
            if len(rows)!=len(self.packet['items']):raise ValueError('请先处理全部复核案例，资料不足也算已处理')
            summary=self.export()
            with (self.path/'review_lock.json').open('x',encoding='utf-8') as file:
                json.dump({'locked_at':datetime.now().astimezone().isoformat(),
                           'decisions_sha256':digest(self.path/'decisions.jsonl'),
                           'packet_sha256':self.manifest['packet_sha256']},file,indent=2)
            (self.path/'completed_review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
            return summary

    def export(self):
        with self.lock:
            self.verify();rows=self.decisions()
            return {'purpose':self.packet['purpose'],'total':len(self.packet['items']),'handled':len(rows),
                    'complete':len(rows)==len(self.packet['items']),
                    'cases':[dict(x,decision=rows.get(x['case_id'])) for x in self.packet['items']],
                    'original_labels_modified':False,'independent_blind_adjudicator':False,
                    'unknowns_imputed_as_zero':False}
