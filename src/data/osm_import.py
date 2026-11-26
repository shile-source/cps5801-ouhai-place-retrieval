"""小规模 OSM 来源适配；元素身份不等于已核验的独立地点。"""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

from .import_reading_pilot import normalize
from .quality import coordinate_status, duplicate_review, report

CATEGORY_TAGS = (
    ('leisure', 'park', '公园'), ('tourism', 'attraction', '景点'),
    ('tourism', 'museum', '博物馆'), ('tourism', 'viewpoint', '观景点'),
    ('amenity', 'library', '图书馆'),
)
CRS_EVIDENCE = 'https://osmdata.openstreetmap.de/info/projections.html'
CENTER_EVIDENCE = 'https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Print_(out)'

def build_candidates(payload, manifest, *, max_elements=28, source_id='osm_pilot_20261031'):
    """仅将实际标签整理为事实文本，缺失和硬约束资格保持未知。"""
    if manifest.get('license') != 'ODbL-1.0' or not manifest.get('license_evidence_sha256'):
        raise ValueError('OSM license evidence is required')
    if payload.get('remark') or not isinstance(payload.get('elements'), list):
        raise ValueError('Incomplete or invalid Overpass response')
    elements = payload['elements']
    if type(max_elements) is not int or not 1 <= max_elements <= 200:
        raise ValueError('Explicit element bound must be between1 and200')
    if len(elements) > max_elements:
        raise ValueError(f'This import is limited to {max_elements} source elements')
    if not isinstance(source_id,str) or not source_id.strip():
        raise ValueError('Explicit source ID required')
    if not all(manifest.get(key) for key in ('sha256','raw_path','finished','endpoint')):
        raise ValueError('Complete source manifest required')
    records, evidence, seen, errors = [], [], {}, []
    repeated = 0
    for position, element in enumerate(elements, 1):
        kind, osm_id = element.get('type'), element.get('id')
        if kind not in ('node','way','relation') or type(osm_id) is not int or osm_id < 1:
            raise ValueError('Invalid OSM element identity')
        identity = (kind, osm_id)
        if identity in seen:
            if seen[identity] != element:
                raise ValueError('Conflicting records for the same OSM element')
            repeated += 1
            continue  # 只去除完全相同的元素，不合并同名的不同实体。
        seen[identity] = element
        tags = element.get('tags', {})
        if not isinstance(tags, dict) or any(not isinstance(v, str) for v in tags.values()):
            raise ValueError('OSM tags must be string values')
        name_field = 'name:zh' if tags.get('name:zh', '').strip() else 'name'
        name = normalize(tags.get(name_field, ''))
        if not name:
            errors.append({'source_position': position, 'reason':'missing_name'})
            continue
        categories = [(k,v,label) for k,v,label in CATEGORY_TAGS if tags.get(k) == v]
        category = ' / '.join(label for _,_,label in categories)
        address_fields = ['addr:full'] if tags.get('addr:full') else [
            key for key in ('addr:country','addr:province','addr:city','addr:district',
                            'addr:subdistrict','addr:street','addr:housenumber') if tags.get(key)]
        address = ' '.join(normalize(tags[key]) for key in address_fields)
        clauses = [{'text': '名称：' + name, 'source_fields':[name_field]}]
        if categories:
            clauses.append({'text':'类别标签：' + '；'.join(k+'='+v+'（'+label+'）' for k,v,label in categories),
                            'source_fields':[k for k,_,_ in categories]})
        if address:
            clauses.append({'text':'地址标签：' + address, 'source_fields':address_fields})
        description = 'OSM 来源记载：' + '；'.join(c['text'] for c in clauses) + '。'
        coordinates = element if kind == 'node' else element.get('center', {})
        if not isinstance(coordinates, dict):
            raise ValueError('Invalid coordinate object')
        lon, lat = coordinates.get('lon'), coordinates.get('lat')
        # center 是包围盒中心，并非入口或独立测量点，也不保证在多边形内。
        pid = f'osm_{kind}_{osm_id}'
        record = dict(poi_id=pid, name=name, category=category, address=address,
            description=description, description_zh=description,
            description_method='osm_explicit_tag_facts_v1', description_clauses=clauses,
            longitude=lon, latitude=lat, original_longitude_text=str(lon) if lon is not None else '',
            original_latitude_text=str(lat) if lat is not None else '',
            original_crs='WGS84', crs_evidence=[CRS_EVIDENCE],
            coordinate_kind='node_position' if kind == 'node' else 'overpass_bounding_box_center',
            coordinate_kind_evidence=CENTER_EVIDENCE,
            wgs84_longitude=None, wgs84_latitude=None, coordinate_conversion_method=None,
            coordinate_status=coordinate_status(lon,lat), coordinate_verified=False,
            coordinate_verification_evidence=[], district_verified=False,
            district_assertion='Returned by OSM area query for relation 3289417; not independent verification',
            district_verification_evidence=[], operational_status='UNKNOWN',
            opening_hours=tags.get('opening_hours'), ticket_info=tags.get('fee'),
            current_operation_verified=False, map_ready=False, is_synthetic=False,
            source_ids=[source_id], source_record_ids=[f'{kind}/{osm_id}'],
            source_url=f'https://www.openstreetmap.org/{kind}/{osm_id}',
            retrieved_at=manifest['finished'], osm_data_timestamp=payload.get('osm3s',{}).get('timestamp_osm_base'),
            raw_path=manifest['raw_path'], raw_sha256=manifest['sha256'],
            license='ODbL-1.0', attribution='© OpenStreetMap contributors',
            source_tags=deepcopy(tags), entity_identity_verified=False,
            record_status='source_backed_candidate_pending_independent_verification',
            quality_flags=['administrative_boundary_not_independently_checked',
                           'current_operation_not_independently_checked', 'coordinate_not_independently_checked'])
        records.append(record)
        values = [('tags.' + k, v) for k,v in tags.items()]
        values += [('lat' if kind == 'node' else 'center.lat', lat),
                   ('lon' if kind == 'node' else 'center.lon', lon)]
        for field, value in values:
            if value is not None:
                evidence.append(dict(poi_id=pid, source_id=source_id,
                    source_record_id=f'{kind}/{osm_id}', source_rows=[position],
                    source_field=field, source_value=str(value), source_url=record['source_url'],
                    downloaded_at=manifest['finished'], raw_path=manifest['raw_path'],
                    raw_sha256=manifest['sha256'], license='ODbL-1.0'))
    return records, evidence, dict(raw_records=len(elements), unique_osm_elements=len(seen),
        exact_duplicate_elements=repeated, named_candidates=len(records), invalid_rows=errors,
        independent_entities_verified=0, category_counts=dict(Counter(r['category'] or 'UNKNOWN' for r in records)))

def import_osm_pilot(source, metadata, output, root, existing=None, existing_evidence=None):
    root, source, output = Path(root).resolve(), Path(source).resolve(), Path(output)
    if output.exists():
        raise FileExistsError(output)
    if existing is not None and existing_evidence is None:
        raise ValueError('Existing candidates require existing field evidence')
    manifest = deepcopy(metadata)
    if manifest.get('status') != 'downloaded_pending_import_and_verification':
        raise ValueError('Successful bounded download required')
    body = source.read_bytes()
    if hashlib.sha256(body).hexdigest() != manifest.get('sha256'):
        raise ValueError('Raw source SHA256 differs')
    manifest['raw_path'] = source.relative_to(root).as_posix()
    license_path = source.parent / 'copyright.html'
    if hashlib.sha256(license_path.read_bytes()).hexdigest() != manifest.get('license_evidence_sha256'):
        raise ValueError('License evidence SHA256 differs')
    new, evidence, counts = build_candidates(json.loads(body), manifest)
    combined = deepcopy(existing or []) + new
    if len({row['poi_id'] for row in combined}) != len(combined):
        raise ValueError('Candidate ID collision; no automatic merge')
    combined_evidence = deepcopy(existing_evidence or []) + evidence
    quality = report(combined, combined_evidence, root)
    quality['osm_import'] = counts
    quality['independent_unique_entity_count'] = None
    quality['redistribution_status'] = 'PENDING mixed-source license compatibility review; local development only'
    quality['formal_evaluation_ready'] = False
    output.mkdir(parents=True)
    for name, value in (('poi_candidates.json', combined), ('field_evidence.json', combined_evidence),
                        ('quality_report.json', quality), ('source_manifest.json', manifest),
                        ('new_field_evidence.json', evidence), ('osm_candidates.json', new)):
        with (output / name).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    with (output / 'poi_review.csv').open('x', encoding='utf-8-sig', newline='') as handle:
        fields = ('poi_id','name','category','address','source_url','original_crs','coordinate_kind',
                  'coordinate_status','district_verified','coordinate_verified','map_ready')
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(combined)
    return quality
