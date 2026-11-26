"""Source-snapshot facts only; not present-day operational/geographic verification."""
from collections import defaultdict
import hashlib
from pathlib import Path

ALIASES = {'名称':'name', '类型':'category', '座位数':'seats', '藏书量':'holdings', '地址':'address',
           'tags.name':'name', 'tags.name:zh':'name', 'tags.addr:full':'address'}
TAG_CATEGORY = {('tags.leisure','park'):'公园', ('tags.tourism','museum'):'博物馆',
                ('tags.tourism','attraction'):'景点', ('tags.tourism','viewpoint'):'观景点',
                ('tags.amenity','library'):'图书馆'}


def compile_facts(records, evidence, root):
    """Accept only field-level evidence whose original bytes still match their hash."""
    root = Path(root).resolve()
    ids = [r['poi_id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate record ID')
    by_record = {pid:defaultdict(list) for pid in ids}
    checked = {}
    for row in evidence:
        pid = row.get('poi_id')
        if pid not in by_record:
            raise ValueError('Evidence for unknown record')
        field = ALIASES.get(row.get('source_field'))
        value = row.get('source_value')
        if (row.get('source_field'), value) in TAG_CATEGORY:
            field, value = 'category', TAG_CATEGORY[row['source_field'], value]
        if not field:
            continue
        relative, expected = row.get('raw_path'), row.get('raw_sha256')
        if not relative or not expected or not row.get('source_url'):
            raise ValueError('Incomplete source evidence')
        path = (root/relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Evidence path outside project')
        if path not in checked:
            checked[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        if checked[path] != expected:
            raise ValueError('Source content hash mismatch')
        if field in ('seats','holdings'):
            if not isinstance(value,str) or not value.strip().isdecimal():
                continue
            value = int(value.strip())
        elif not isinstance(value,str) or not value.strip():
            continue
        else:
            value = value.strip()
        by_record[pid][field].append({'value':value,'source_url':row['source_url'],
             'source_field':row['source_field'],'raw_path':relative,'raw_sha256':expected,
             'retrieved_at':row.get('downloaded_at'),'scope':'source_snapshot_only'})
    facts = {}
    for pid, fields in by_record.items():
        facts[pid] = {}
        for field in ('name','category','address','seats','holdings'):
            supports = fields.get(field,[])
            values = {s['value'] for s in supports}
            facts[pid][field] = {'value':next(iter(values)) if len(values)==1 else None,
                'status':('supported' if len(values)==1 else 'conflicting' if values else 'unknown'),
                'evidence':supports,'scope':'source_snapshot_only'}
    return facts
