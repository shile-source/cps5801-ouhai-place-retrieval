"""Separate <=200 local development snapshot, never migrate old judgments."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from src.data.osm_import import build_candidates
from src.data.activity_sources import ACTIVITY_TAGS,enrich_activity
from src.data.evidence_facts import compile_facts
from src.data.fact_store import load_bound_facts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/clean/activity_review_v0_6_20261126'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base=ROOT/'data/clean/research_review_v0_5_20261125/poi_candidates.json'
    records=json.loads(base.read_text(encoding='utf-8'))
    assert sha(base)=='b96ebb2e68a22b4b905e410e2750934edc1737d2f8eb5f49d05992d47da9efe5'
    facts=deepcopy(load_bound_facts(ROOT/'configs/research_v0_5_facts_binding.json',base,ROOT))
    raw=ROOT/'data/raw/osm_activities_20261126'
    meta=json.loads((raw/'request.json').read_text(encoding='utf-8'))
    assert meta['status']=='downloaded_pending_import_and_verification'
    assert sha(raw/'response.json')==meta['sha256']
    assert sha(raw/'copyright.html')==meta['license_evidence_sha256']
    new,evidence,counts=build_candidates(json.loads((raw/'response.json').read_text(encoding='utf-8')),
            meta,max_elements=124,source_id='osm_activities_20261126',category_tags=ACTIVITY_TAGS)
    for record in new:enrich_activity(record)
    ids={r['poi_id'] for r in records}
    additions=[r for r in new if r['poi_id'] not in ids]
    assert all(r['category'] for r in additions)
    addition_ids={r['poi_id'] for r in additions}
    evidence=[e for e in evidence if e['poi_id'] in addition_ids]
    newfacts=compile_facts(additions,evidence,ROOT)
    for r in additions:
        tags=r['source_tags'];supports=[]
        for key,value,label in ACTIVITY_TAGS:
            if tags.get(key)==value:
                supports.extend({'value':r['category'],'source_url':e['source_url'],'source_field':e['source_field'],
                    'raw_path':e['raw_path'],'raw_sha256':e['raw_sha256'],'retrieved_at':e['downloaded_at'],
                    'scope':'source_snapshot_only','derived_by':'explicit_activity_tag_labels_v1'}
                    for e in evidence if e['poi_id']==r['poi_id'] and e['source_field']=='tags.'+key and e['source_value']==value)
        assert supports
        newfacts[r['poi_id']]['category']={'value':r['category'],'status':'supported','evidence':supports,'scope':'source_snapshot_only'}
    facts.update(newfacts);records.extend(additions)
    assert len(records)<=200 and len({r['poi_id'] for r in records})==len(records)
    OUT.mkdir(exist_ok=False)
    for filename,value in [('poi_candidates.json',records),('source_facts.json',facts),('new_field_evidence.json',evidence)]:
        (OUT/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    previous=json.loads((ROOT/'configs/research_v0_5_facts_binding.json').read_text(encoding='utf-8'))
    binding={'scope':'source_snapshot_only','corpus_sha256':sha(OUT/'poi_candidates.json'),
        'facts_path':str((OUT/'source_facts.json').relative_to(ROOT)).replace('\\','/'),
        'facts_sha256':sha(OUT/'source_facts.json'),'evidence_sha256':dict(previous['evidence_sha256']),
        'formal_research_freeze':False}
    binding['evidence_sha256'][meta['raw_path']]=meta['sha256']
    target=ROOT/'configs/activity_v0_6_facts_binding.json'
    with target.open('x',encoding='utf-8') as f:json.dump(binding,f,ensure_ascii=False,indent=2)
    load_bound_facts(target,OUT/'poi_candidates.json',ROOT)
    summary={'source_record_count':len(records),'new_records':len(additions),
        'same_osm_ids_not_added':len(new)-len(additions),'new_category_counts':dict(Counter(r['category'] for r in additions)),
        'all_category_counts':dict(Counter(r['category'] for r in records)),
        'raw_source_counts':counts,'independently_verified_unique_entities':None,
        'current_operations_verified':False,'existing_labels_migrated':False,'models_reencoded':False,
        'mixed_redistribution_status':'pending_compatibility_review_local_development_only',
        'corpus_sha256':binding['corpus_sha256']}
    (OUT/'source_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
