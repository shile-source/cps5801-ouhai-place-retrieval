"""Bind audited source facts to one exact corpus; never silently migrate evidence."""
import hashlib
import json
from pathlib import Path


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_bound_facts(binding,corpus,root):
    root=Path(root).resolve();binding=Path(binding)
    spec=json.loads(binding.read_text(encoding='utf-8'))
    if spec.get('scope')!='source_snapshot_only' or digest(corpus)!=spec.get('corpus_sha256'):
        raise ValueError('Facts are not bound to this exact source corpus')
    facts=(root/spec['facts_path']).resolve()
    if not facts.is_relative_to(root) or digest(facts)!=spec.get('facts_sha256'):
        raise ValueError('Fact file changed or is outside the project')
    for relative,expected in spec.get('evidence_sha256',{}).items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or digest(path)!=expected:
            raise ValueError('Bound source evidence changed')
    data=json.loads(facts.read_text(encoding='utf-8'))
    ids={r['poi_id'] for r in json.loads(Path(corpus).read_text(encoding='utf-8'))}
    if set(data)!=ids:raise ValueError('Fact IDs differ from source corpus')
    return data
