"""Trace every review record to source evidence; keep faults visible, no relabelling."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from src.data.evidence_facts import compile_facts
from src.data.quality import report
from src.retrieval.constraints import Constraint, shared_pool

ROOT=Path(__file__).resolve().parents[1]


def main():
    snapshot=ROOT/'data/clean/research_review_v0_5_20261125'
    records=json.loads((snapshot/'poi_candidates.json').read_text(encoding='utf-8'))
    evidence=json.loads((snapshot/'field_evidence.json').read_text(encoding='utf-8'))
    # Preserve the five earlier hand-captured evidence sources as such; never call them HTTP archives.
    captured=ROOT/'data/evidence/ouhai_expansion_20261106/source_facts.json'
    capture_sha=hashlib.sha256(captured.read_bytes()).hexdigest()
    old=json.loads((ROOT/'data/clean/pilot_review_v0_4_20261106/new_field_evidence.json').read_text(encoding='utf-8'))
    mapping={'name':'名称','category':'类型','address':'地址','opening_hours':'开放时间'}
    for e in old:
        if e['field'] not in mapping:
            continue
        assert e['capture_sha256']==capture_sha
        evidence.append({'poi_id':e['poi_id'],'source_field':mapping[e['field']],
            'source_value':e['value'],'source_url':e['source_url'],'downloaded_at':e['checked_on'],
            'source_id':'ouhai_expansion_20261106_manual_capture','source_record_id':e['poi_id'],
            'raw_path':str(captured.relative_to(ROOT).as_posix()),'raw_sha256':capture_sha,
            'capture_method':'manual_structured_capture_not_original_HTTP','license':'UNKNOWN'})
    for e in evidence:
        if e['poi_id'].startswith('ouhai_library_notice_20260904_'):
            e['source_id']='ouhai_library_notice_20260904';e['source_record_id']=str(e['source_rows'][0])
    facts=compile_facts(records,evidence,ROOT)
    quality=report(records,evidence,ROOT)
    pools={}
    for key,conditions in [('seats40',[Constraint('seats','gte',40)]),
        ('holdings12000',[Constraint('holdings','gte',12000)]),
        ('both_counts',[Constraint('seats','gte',40),Constraint('holdings','gte',12000)]),
        ('city_reading',[Constraint('category','eq','城市书房')])]:
        p=shared_pool(facts,conditions)
        pools[key]={s:len(p[s+'_ids']) for s in ('eligible','unknown','unmet')}
    out=ROOT/'outputs/evidence_audit_20261125'
    out.mkdir(exist_ok=False)
    audit={'purpose':'source_snapshot_coverage_NOT_human_labels_or_current_verification',
        'candidate_records':len(records),'source_backed_records':quality['source_backed_records'],
        'provenance_issue_count':len(quality['provenance_issues']),
        'fact_coverage':{field:dict(Counter(f[field]['status'] for f in facts.values())) for field in ('name','category','address','seats','holdings')},
        'common_filter_counts':pools,'manual_captured_source_records':5,
        'unique_place_count':None,'duplicate_pairs_pending_review':len(quality['duplicate_review']),
        'new_relevance_grades':0,'formal_ready':False}
    for name,value in [('canonical_field_evidence.json',evidence),('source_facts.json',facts),
                       ('quality_report.json',quality),('summary.json',audit)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=True))


if __name__=='__main__': main()
