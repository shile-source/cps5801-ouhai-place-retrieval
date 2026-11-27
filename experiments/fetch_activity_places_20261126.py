"""One bounded public request for user-requested missing activity categories."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/osm_activities_20261126'
QUERY = '''[out:json][timeout:50];
rel(3289417);map_to_area->.ouhai;
nwr(area.ouhai)["name"]["amenity"="karaoke_box"];out tags center 10;
nwr(area.ouhai)["name"]["amenity"~"^(cinema|theatre|nightclub)$"];out tags center 6;
nwr(area.ouhai)["name"]["leisure"~"^(amusement_arcade|bowling_alley|water_park)$"];out tags center 8;
nwr(area.ouhai)["name"]["leisure"~"^(sports_centre|stadium|pitch|fitness_centre|swimming_pool|playground)$"];out tags center 44;
nwr(area.ouhai)["name"]["shop"="mall"];out tags center 8;
nwr(area.ouhai)["name"]["landuse"="retail"];out tags center 8;
nwr(area.ouhai)["name"]["highway"="pedestrian"];out tags center 8;
nwr(area.ouhai)["name"]["amenity"~"^(restaurant|cafe|ice_cream)$"];out tags center 32;
'''


def main():
    base = json.loads((ROOT / 'data/clean/research_review_v0_5_20261125/poi_candidates.json').read_text(encoding='utf-8'))
    assert len(base) == 76 and len(base) + 124 <= 200
    assert shutil.disk_usage('C:/').free >= 5 * 1024**3
    assert shutil.disk_usage('D:/').free >= 10 * 1024**3
    OUT.mkdir(exist_ok=False)
    (OUT / 'query.overpassql').write_text(QUERY, encoding='utf-8')
    license_bytes = (ROOT / 'data/raw/osm_expansion_20261125_get/copyright.html').read_bytes()
    (OUT / 'copyright.html').write_bytes(license_bytes)
    meta = {'started': datetime.now().astimezone().isoformat(), 'endpoint': 'https://overpass-api.de/api/interpreter',
            'maximum_elements': 124, 'maximum_combined_candidates': 200, 'base_candidate_count': 76,
            'license': 'ODbL-1.0', 'license_url': 'https://www.openstreetmap.org/copyright',
            'attribution': '© OpenStreetMap contributors', 'automatic_retries': 0,
            'license_evidence_sha256': hashlib.sha256(license_bytes).hexdigest(),
            'license_evidence_reused_from': 'data/raw/osm_expansion_20261125_get/copyright.html',
            'authorization': 'Existing user-authorized public-source expansion up to200 plus explicit request for commercial/leisure/sports categories',
            'district_identity': 'OSM area of relation3289417; not independently verified',
            'transport': 'GET'}
    try:
        url = meta['endpoint'] + '?' + urlencode({'data': QUERY})
        with urlopen(Request(url, headers={'User-Agent': 'CPS5801-Research/0.4 (bounded124 activity sources)'}), timeout=60) as response:
            body = response.read(4_000_001)
            meta['http_status'] = response.status
        if len(body) > 4_000_000:
            raise ValueError('Response exceeds source bound')
        (OUT / 'response.json').write_bytes(body)
        payload = json.loads(body)
        if payload.get('remark') or len(payload['elements']) > 124:
            raise ValueError('Incomplete or excessive bounded response')
        meta.update(status='downloaded_pending_import_and_verification', raw_elements=len(payload['elements']),
                    raw_path=str((OUT / 'response.json').relative_to(ROOT)).replace('\\', '/'),
                    sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                    osm_data_timestamp=payload.get('osm3s', {}).get('timestamp_osm_base'))
    except Exception as error:
        meta.update(status='stopped_no_automatic_retry', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        meta['finished'] = datetime.now().astimezone().isoformat()
        (OUT / 'request.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(meta, ensure_ascii=True))


if __name__ == '__main__':
    main()
