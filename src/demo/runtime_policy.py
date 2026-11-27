"""Accept only a recorded successful, changed lifecycle check; keep earlier stops intact."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
JOB=ROOT/'outputs/residency_repair_20261127'
STOP=JOB/'runtime_stop.json'
FILES=('src/demo/server.py','src/demo/runtime_telemetry.py','src/demo/runtime_policy.py',
       'src/demo/encoder_worker.py','src/retrieval/streamed_bge.py','Start-Demo.ps1')


def identity():
    return {'strategy':'streamed_FP16_healthy_idle_release_60_seconds_v1',
            'corpus_sha256':hashlib.sha256((ROOT/'data/clean/activity_review_v0_6_20261126/poi_candidates.json').read_bytes()).hexdigest(),
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
            'c_min_gib':5,'d_min_gib':10,'c_decline_limit_gib':1,'dense_idle_seconds':60}


def validated():
    if STOP.exists():return False
    try:report=json.loads((JOB/'validation.json').read_text(encoding='utf-8'))
    except FileNotFoundError:return False
    return report.get('status')=='passed_two_loads_and_two_healthy_idle_releases' and report.get('identity')==identity()


if __name__=='__main__':
    if not validated():raise SystemExit('No valid changed-configuration repair receipt; no model restart')
    print('Validated changed lifecycle receipt; old failure retained; no newer stop recorded')
