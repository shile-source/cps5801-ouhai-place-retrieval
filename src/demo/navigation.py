"""Source-reported destination metadata, separate from retrieval and evaluation text."""
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
NOTE = ROOT / 'data/evidence/navigation_review_20261123/panqiao_route_note.json'


def source_url(value):
    if not isinstance(value, str):
        return ''
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:
        return ''


def load_notes():
    if not NOTE.is_file():
        return {}  # Public/source-only checkouts may omit separately reviewed notes.
    note = json.loads(NOTE.read_text(encoding='utf-8'))
    if (note.get('poi_id') != 'wz_reading_13759_37'
            or note.get('name') != '潘桥城市书房'
            or not source_url(note.get('source_url'))
            or urlsplit(note['source_url']).hostname != 'lib.ouhai.gov.cn'
            or not all(isinstance(note.get(k), str) and note[k].strip()
                       for k in ('address', 'publication_date', 'checked_on', 'evidence_locator'))):
        raise ValueError('Invalid navigation evidence note')
    return {note['poi_id']: note}


def map_search_links(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError('Map search requires 1–1000 characters')
    query = query.strip()
    return {
        'baidu': 'https://api.map.baidu.com/place/search?' + urlencode({
            'query': query, 'region': '瓯海区', 'output': 'html', 'src': 'webapp.cps5801.placesearch'}),
        'amap': 'https://uri.amap.com/search?' + urlencode({
            'keyword': '温州市瓯海区 ' + query, 'city': '温州', 'view': 'map', 'src': 'cps5801'}),
    }


def destination(record, notes):
    name = str(record.get('name') or '').strip()
    original_address = str(record.get('address') or '').strip()
    address = '' if original_address in ('未知', 'UNKNOWN') else original_address
    note = notes.get(record['poi_id'])
    # IDs alone cannot attach evidence to a different named entity.
    if note and note['name'] != name:
        note = None
    if note:
        address = note['address']
    return {
        'address': address,
        'snapshot_address': original_address,
        'address_source_url': source_url(note['source_url'] if note else record.get('source_url')),
        'has_supplement': bool(note),
        'source_checked_on': note['checked_on'] if note else record.get('source_checked_on'),
        'publication_date': note['publication_date'] if note else record.get('source_date'),
        'entrance_verified': False,
        'search_links': map_search_links(' '.join(value for value in (name, address) if value)),
    }
