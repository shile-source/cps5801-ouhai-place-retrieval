"""New local review snapshot; original corpora/labels and public-release status untouched."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

from src.data.osm_import import build_candidates
from src.data.evidence_facts import compile_facts
from src.retrieval.constraints import Constraint, shared_pool

ROOT=Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class NoticeRows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag in ('td','th') and self.row is not None: self.cell=[]
    def handle_data(self,text):
        if self.cell is not None: self.cell.append(text)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip()); self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None


def main():
    base=ROOT/'data/clean/pilot_review_v0_4_20261106/poi_candidates.json'
    locked=ROOT/'data/labels/pilot_human_v0_1_20261102'
    protected={str(p):sha(p) for p in [base]+list(locked.glob('*')) if p.is_file()}
    records=json.loads(base.read_text(encoding='utf-8'))
    evidence=json.loads((ROOT/'data/clean/pilot_mixed_v0_3_osm_20261031/field_evidence.json').read_text(encoding='utf-8'))
    raw=ROOT/'data/raw/osm_expansion_20261125_get'
    meta=json.loads((raw/'request.json').read_text(encoding='utf-8'))
    assert meta['status']=='downloaded_pending_import_and_verification'
    assert sha(raw/'response.json')==meta['sha256']
    assert sha(raw/'copyright.html')==meta['license_evidence_sha256']
    meta['raw_path']=str((raw/'response.json').relative_to(ROOT).as_posix())
    fresh,fresh_evidence,osm_counts=build_candidates(json.loads((raw/'response.json').read_text(encoding='utf-8')),
                          meta,max_elements=146,source_id='osm_expansion_20261125')
    existing={r['poi_id']:r for r in records}
    overlap=[]
    new_ids=set()
    for r in fresh:
        if r['poi_id'] in existing:
            overlap.append({'poi_id':r['poi_id'],'old_name':existing[r['poi_id']]['name'],
                            'new_name':r['name'],'new_source_tags':r.get('source_tags'),
                            'status':'same_osm_id_old_snapshot_preserved_pending_review'})
        else:
            records.append(r); new_ids.add(r['poi_id'])
    evidence.extend(e for e in fresh_evidence if e['poi_id'] in new_ids)
    notice=ROOT/'data/raw/ouhai_library_20261125/opening_notice.html'
    notice_meta=json.loads(notice.with_suffix('.html.metadata.json').read_text(encoding='utf-8'))
    assert notice_meta['status']==200 and sha(notice)==notice_meta['sha256']
    parser=NoticeRows(); parser.feed(notice.read_text(encoding='utf-8'))
    rows=[r for r in parser.rows if len(r)==4 and r[0].isdecimal()]
    assert [int(r[0]) for r in rows]==list(range(1,26)), 'Unexpected official table structure'
    name_ids={}
    for r in records: name_ids.setdefault(r['name'],[]).append(r['poi_id'])
    official_crossrefs=[]
    official_added=[]
    for number,name,address,hours in rows:
        reference={'source_row':int(number),'name':name,'address':address,'published_opening_hours':hours,
             'source_url':notice_meta['requested_url'],'source_publication_date':'2026-09-04',
             'raw_path':str(notice.relative_to(ROOT).as_posix()),'raw_sha256':sha(notice),
             'source_table':'瓯海区书房书屋开放时间一览表','current_operation_verified':False,
             'identity_matches_by_exact_name':name_ids.get(name,[]),
             'cross_source_identity_independently_verified':False}
        official_crossrefs.append(reference)
        if name in name_ids:
            continue  # Do not silently merge entities, change old facts, or inflate exact-name repeats.
        pid=f'ouhai_library_notice_20260904_{int(number):02d}'
        record={'poi_id':pid,'name':name,'category':'书房书屋（官方名录）','address':address,
             'description':f'瓯海区图书馆2026年9月4日书房书屋名录记载：名称：{name}；地址：{address}；公布开放时段：{hours}。',
             'opening_hours':hours,'opening_hours_as_of':'2026-09-04','current_operation_verified':False,
             'district_verified':False,'coordinate_verified':False,'map_ready':False,
             'original_crs':'UNKNOWN','longitude':None,'latitude':None,'is_synthetic':False,
             'source_url':notice_meta['requested_url'],'raw_path':reference['raw_path'],'raw_sha256':reference['raw_sha256'],
             'retrieved_at':notice_meta['checked_at'],'source_ids':['ouhai_library_notice_20260904'],
             'source_record_ids':[number],'license':'UNKNOWN','redistribution_status':'local_review_only',
             'record_status':'source_backed_candidate_pending_identity_geography_and_license_review'}
        records.append(record); official_added.append(pid)
        for field,value in [('名称',name),('地址',address),('开放时间',hours),('类型','书房书屋（官方名录）')]:
            evidence.append({'poi_id':pid,'source_field':field,'source_value':value,
                 'source_url':notice_meta['requested_url'],'raw_path':reference['raw_path'],
                 'raw_sha256':reference['raw_sha256'],'source_rows':[int(number)],
                 'downloaded_at':notice_meta['checked_at'],'license':'UNKNOWN'})
    assert len(records)<=200 and len({r['poi_id'] for r in records})==len(records)
    facts=compile_facts(records,evidence,ROOT)
    numeric=[pid for pid,fields in facts.items() if all(fields[f]['status']=='supported' for f in ('seats','holdings'))]
    pool=shared_pool(facts,[Constraint('seats','gte',40),Constraint('holdings','gte',12000)])
    out=ROOT/'data/clean/research_review_v0_5_20261125'
    out.mkdir(exist_ok=False)
    manifest={'purpose':'new_source_evidence_review_NOT_formal_or_approved_benchmark',
              'created_at':datetime.now().astimezone().isoformat(),'base_sha256':protected[str(base)],
              'base_count':54,'osm_source_elements':len(fresh),'new_osm_records':len(new_ids),
              'osm_id_overlaps_preserved':len(overlap),'official_table_rows':len(rows),
              'new_official_name_records':len(official_added),'candidate_records':len(records),
              'category_counts':dict(Counter(r['category'] for r in records)),
              'records_with_supported_seats_and_holdings':len(numeric),
              'independently_verified_unique_entities':None,'formal_evaluation_ready':False,
              'labels_imported_or_created':False,'live_demo_switched':False,
              'redistribution_status':'PENDING mixed-source compatibility; local review only',
              'common_text_fields':['name','category','address','description']}
    for name,value in [('poi_candidates.json',records),('field_evidence.json',evidence),('source_facts.json',facts),
                       ('source_manifest.json',manifest),('official_crossrefs.json',official_crossrefs),
                       ('osm_overlap_review.json',overlap),('quantity_filter_diagnostic.json',pool)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,expected in protected.items(): assert sha(Path(name))==expected
    print(json.dumps(manifest,ensure_ascii=True))


if __name__=='__main__': main()
