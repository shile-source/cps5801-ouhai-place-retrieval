"""Recompute every engineering summary from public observations without a model."""
import hashlib
import json
from pathlib import Path
from src.evaluation.public_engineering import summarize

ROOT=Path(__file__).resolve().parents[1]


def main():
    protocol_path=ROOT/'configs/public_functional_study_20261128.json'
    protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
    query_path=ROOT/protocol['query_path'];raw=ROOT/'results/public_engineering_observations_20261128.jsonl'
    queries=json.loads(query_path.read_text(encoding='utf-8'))
    expected=json.loads((ROOT/'results/public_engineering_20261128.json').read_text(encoding='utf-8'))
    if hashlib.sha256(protocol_path.read_bytes()).hexdigest()!=expected['protocol_sha256']:
        raise ValueError('Protocol changed')
    if hashlib.sha256((ROOT/protocol['corpus_path']).read_bytes()).hexdigest()!=protocol['corpus_sha256']:
        raise ValueError('Corpus changed')
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=expected['raw_observations_sha256']:
        raise ValueError('Raw observations changed')
    if hashlib.sha256(query_path.read_bytes()).hexdigest()!=protocol['query_sha256']:
        raise ValueError('Queries changed')
    result=summarize(protocol,queries,[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()])
    if any(expected[key]!=value for key,value in result.items()):raise ValueError('Reported arithmetic does not match observations')
    print(json.dumps({'status':'all_public_engineering_summaries_recomputed','measured_requests':result['measured_requests'],
        'new_model_inference':False,'new_human_labels':0}))


if __name__=='__main__':main()
