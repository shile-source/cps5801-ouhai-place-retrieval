"""Rebuild a separate OSM-only demonstration, never the mixed research corpus."""
import hashlib
import json
from pathlib import Path
from src.data.osm_import import build_candidates

ROOT=Path(__file__).resolve().parents[1]


def main():
    raw=ROOT/'data/raw/osm_expansion_20261125_get'
    body=(raw/'response.json').read_bytes()
    meta=json.loads((raw/'request.json').read_text(encoding='utf-8'))
    if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Original OSM response changed')
    meta['raw_path']='data/raw/osm_expansion_20261125_get/response.json'
    records,evidence,counts=build_candidates(json.loads(body),meta,max_elements=146,source_id='open_osm_20261125')
    out=ROOT/'data/clean/open_osm_v2_20261126'
    values={'poi_candidates.json':records,'field_evidence.json':evidence,
            'source_manifest.json':{'license':'ODbL-1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
              'attribution':'© OpenStreetMap contributors','source_url':'https://www.openstreetmap.org/copyright',
              'source_sha256':meta['sha256'],'source_date':meta['osm_data_timestamp'],
              'source_element_count':len(records),'independently_verified_unique_entities':None,
              'purpose':'open_data_functional_demonstration_NOT_reported_49_record_experiment',
              'labels_created':0,'import_counts':counts}}
    out.mkdir(exist_ok=True)
    for name,value in values.items():
        text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        target=out/name
        if target.exists() and target.read_bytes()!=text.encode('utf-8'):
            raise ValueError('Open snapshot changed; create a new version instead')
        target.write_bytes(text.encode('utf-8'))
    print(json.dumps({'output':str(out),'records':len(records),'mixed_sources':False,'new_human_labels':0}))


if __name__=='__main__':main()
