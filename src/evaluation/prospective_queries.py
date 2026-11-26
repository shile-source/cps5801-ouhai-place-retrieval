"""Versioned human query drafts; self-reports are not verified provenance."""
import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone


class QueryDraft:
    def __init__(self, directory, corpus):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.log = self.directory / 'draft_history.jsonl'
        self.final = self.directory / 'submission.json'
        self.binding = {'corpus_sha256': hashlib.sha256(Path(corpus).read_bytes()).hexdigest(),
                        'status': 'prospective_intake_pending_review_not_frozen_test',
                        'provenance_verified': False}
        manifest = self.directory / 'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text(encoding='utf-8')) != self.binding:
                raise ValueError('Corpus binding changed; use a new session')
        else:
            with manifest.open('x', encoding='utf-8') as stream:
                json.dump(self.binding, stream, ensure_ascii=False, indent=2)

    def state(self):
        with self.lock:
            draft = {'author_code': '', 'rank_exposure': '', 'ai_use': '', 'queries': [''] * 30}
            if self.log.exists():
                for line in self.log.read_text(encoding='utf-8').splitlines():
                    draft = json.loads(line)['draft']
            return {'draft': draft, 'locked': self.final.exists(), **self.binding}

    def save(self, value, submit=False):
        with self.lock:
            if self.final.exists():
                raise ValueError('本次提交已锁定，不能覆盖')
            if not isinstance(value, dict):
                raise ValueError('需要表单内容')
            queries = value.get('queries')
            if not isinstance(queries, list) or len(queries) != 30 or any(not isinstance(q, str) or len(q) > 500 for q in queries):
                raise ValueError('需要30个文本栏，每栏最多500字')
            draft = {'queries': [q.strip() for q in queries]}
            for key, allowed in [('author_code', None), ('rank_exposure', {'unseen', 'seen', 'unsure', ''}), ('ai_use', {'none', 'used', 'unsure', ''})]:
                item = value.get(key, '')
                if not isinstance(item, str) or len(item) > 80 or (allowed is not None and item not in allowed):
                    raise ValueError('作者信息格式无效')
                draft[key] = item.strip()
            if submit:
                if not all(draft['queries']) or not all(draft[k] for k in ('author_code', 'rank_exposure', 'ai_use')):
                    raise ValueError('请写完30条并填写作者代号和两项声明')
                if len(set(draft['queries'])) != 30:
                    raise ValueError('存在完全重复的请求，请检查')
                if value.get('confirmed') is not True:
                    raise ValueError('请由实际填写人确认提交')
            event = {'time_utc': datetime.now(timezone.utc).isoformat(), 'draft': draft, 'source': 'human_query_intake_ui', 'submitted': submit}
            with self.log.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            if submit:
                with self.final.open('x', encoding='utf-8') as stream:
                    json.dump({**event, **self.binding}, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
            return self.state()
