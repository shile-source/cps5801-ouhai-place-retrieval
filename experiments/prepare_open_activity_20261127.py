"""Deterministically rebuild 114 OSM records without the private mixed corpus."""
import hashlib
import json
from pathlib import Path
from src.data.osm_import import build_candidates
from src.data.activity_sources import ACTIVITY_TAGS, enrich_activity

ROOT = Path(__file__).resolve().parents[1]


def main():
    records, evidence, sources = [], [], []
    for name, maximum, tags in [('osm_expansion_20261125_get',146,None),('osm_activities_20261126',124,ACTIVITY_TAGS)]:
        raw=ROOT/'data/raw'/name
        meta=json.loads((raw/'request.json').read_text(encoding='utf-8'))
        body=(raw/'response.json').read_bytes()
        if hashlib.sha256(body).hexdigest()!=meta['sha256']:
            raise ValueError('Frozen source hash mismatch')
        meta['raw_path']=str((raw/'response.json').relative_to(ROOT)).replace('\\','/')
        rows, fields, counts=build_candidates(json.loads(body),meta,max_elements=maximum,source_id=name,category_tags=tags)
        if tags:
            for row in rows:enrich_activity(row)
        records.extend(rows);evidence.extend(fields)
        sources.append({'raw_path':meta['raw_path'],'sha256':meta['sha256'],'count':len(rows),'import_counts':counts})
    if len({r['poi_id'] for r in records})!=len(records):
        raise ValueError('Duplicate OSM identifiers require a new reviewed snapshot')
    out=ROOT/'data/clean/open_activity_v1_20261127'
    out.mkdir(parents=True,exist_ok=True)
    values={'poi_candidates.json':records,'field_evidence.json':evidence,'source_manifest.json':{
        'license':'ODbL-1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'attribution':'© OpenStreetMap contributors','source_url':'https://www.openstreetmap.org/copyright',
        'source_record_count':len(records),'sources':sources,'mixed_sources':False,
        'independently_verified_unique_entities':None,'current_operations_verified':False,
        'purpose':'OSM_only_activity_functional_demo_NOT_the_mixed_151_or_original_49_experiment','labels_created':0}}
    for name,value in values.items():
        body=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        path=out/name
        if path.exists() and path.read_bytes()!=body:raise ValueError('Use a new version for changed data')
        path.write_bytes(body)
    print(json.dumps({'records':len(records),'directory':str(out),'new_human_labels':0}))


if __name__=='__main__':main()
