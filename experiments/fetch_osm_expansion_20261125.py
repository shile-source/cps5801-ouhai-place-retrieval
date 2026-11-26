"""Explicitly approved <=200-candidate expansion; one capped OSM request, no retries."""
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/raw/osm_expansion_20261125'
QUERY = '''[out:json][timeout:50];
rel(3289417);map_to_area->.ouhai;
nwr(area.ouhai)["name"]["leisure"="park"];out tags center 55;
nwr(area.ouhai)["name"]["tourism"~"^(attraction|viewpoint)$"];out tags center 55;
nwr(area.ouhai)["name"]["tourism"="museum"];out tags center 18;
nwr(area.ouhai)["name"]["amenity"="library"];out tags center 18;
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mirror',action='store_true',help='Separate manual attempt on provider-documented alternative after upstream502')
    parser.add_argument('--get',action='store_true',help='Separate GET transport diagnostic after failed POST connections')
    args=parser.parse_args()
    output=ROOT/'data/raw/osm_expansion_20261125_mirror' if args.mirror else OUT
    if args.get:
        output=ROOT/'data/raw/osm_expansion_20261125_get'
    boundary = json.loads((ROOT/'data/raw/osm_boundary_20261031/request.json').read_text(encoding='utf-8'))
    assert boundary['boundary_elements'][0]['id'] == 3289417
    assert boundary['boundary_elements'][0]['tags']['name'] == '瓯海区'
    assert shutil.disk_usage('C:/').free >= 5*1024**3
    assert shutil.disk_usage('D:/').free >= 10*1024**3
    output.mkdir(exist_ok=False)
    (output/'query.overpassql').write_text(QUERY,encoding='utf-8')
    meta={'started':datetime.now().astimezone().isoformat(),'endpoint':('https://overpass.private.coffee/api/interpreter' if args.mirror else 'https://overpass-api.de/api/interpreter'),
          'previous_failed_attempt':'data/raw/osm_expansion_20261125/request.json' if args.mirror else None,
          'maximum_elements':146,'maximum_combined_candidates':200,'base_candidate_count':54,
          'license':'ODbL-1.0','attribution':'© OpenStreetMap contributors',
          'license_url':'https://www.openstreetmap.org/copyright', 'automatic_retries':0,
          'approval':'User explicitly approved public-source expansion up to200 candidates,2026-11-25',
          'boundary_review':'OSM relation identity checked; not independent administrative boundary validation',
          'independently_verified_entities':0,'representative_sample':False}
    try:
        with urlopen(Request(meta['license_url'],headers={'User-Agent':'CPS5801-Research/0.3'}),timeout=30) as r:
            license_body=r.read(500001)
            assert len(license_body)<=500000
        (output/'copyright.html').write_bytes(license_body)
        meta['license_evidence_sha256']=hashlib.sha256(license_body).hexdigest()
        request=Request(meta['endpoint']+'?'+urlencode({'data':QUERY}) if args.get else meta['endpoint'],data=None if args.get else urlencode({'data':QUERY}).encode(),headers={
            'User-Agent':'CPS5801-Research/0.3 (approved146element academic snapshot)',
            'Content-Type':'application/x-www-form-urlencoded'})
        meta['transport']='GET' if args.get else 'POST'
        with urlopen(request,timeout=55) as r:
            body=r.read(4_000_001); meta['http_status']=r.status
        assert len(body)<=4_000_000
        (output/'response.json').write_bytes(body)
        parsed=json.loads(body)
        assert not parsed.get('remark'), parsed.get('remark')
        assert len(parsed['elements'])<=146
        meta.update(status='downloaded_pending_import_and_verification',bytes=len(body),
                    sha256=hashlib.sha256(body).hexdigest(),raw_elements=len(parsed['elements']),
                    osm_data_timestamp=parsed.get('osm3s',{}).get('timestamp_osm_base'))
    except Exception as error:
        meta.update(status='stopped_no_automatic_retry',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        meta['finished']=datetime.now().astimezone().isoformat()
        (output/'request.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(meta,ensure_ascii=True),flush=True)


if __name__=='__main__':
    main()
