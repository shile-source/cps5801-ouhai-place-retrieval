import json
from pathlib import Path
from urllib.request import urlopen
import hashlib
from src.demo.server import map_location


def test_map_area_requires_explicit_coordinate_kind_and_wgs84():
    record = {'poi_id': 'osm_way_123', 'original_crs': 'WGS84', 'latitude': 27.98, 'longitude': 120.6}
    assert map_location(record) is None
    record['coordinate_kind'] = 'overpass_bounding_box_center'
    result = map_location(record)
    assert result['kind'] == 'bounding_box_center'
    assert result['entrance_verified'] is False
    assert map_location(record | {'original_crs': 'UNKNOWN'}) is None
    assert map_location(record | {'latitude': 7.9}) is None
    assert map_location(record | {'longitude': float('nan')}) is None
    assert map_location(record | {'poi_id': 'official_123'}) is None


def test_map_node_remains_source_reported_not_verified():
    row = {'poi_id': 'osm_node_123', 'original_crs': 'WGS84', 'latitude': 27.98, 'longitude': 120.6}
    assert map_location(row)['kind'] == 'source_node'
    assert map_location(row)['status'] == 'unverified_osm_point'
    assert map_location(row)['entrance_verified'] is False


def test_vendored_leaflet_bytes_and_license():
    root = Path(__file__).resolve().parents[1] / 'src/demo/vendor/leaflet-1.9.4'
    for name, item in json.loads((root / 'PROVENANCE.json').read_text()).items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == item['sha256']
    assert 'BSD 2-Clause' in (root / 'LICENSE').read_text()
