"""Check quoted field values against original bytes or clearly marked manual capture."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from src.data.import_reading_pilot import read_archive, normalize
from .prepare_evidence_snapshot_20261125 import NoticeRows

ROOT=Path(__file__).resolve().parents[1]


def main():
    evidence=json.loads((ROOT/'outputs/evidence_audit_20261125/canonical_field_evidence.json').read_text(encoding='utf-8'))
    content={}
    results=[]
    for e in evidence:
        path=(ROOT/e['raw_path']).resolve()
        assert path.is_relative_to(ROOT)
        if path not in content:
            body=path.read_bytes()
            content[path]={'sha':hashlib.sha256(body).hexdigest(),'bytes':body}
        data=content[path]
        assert data['sha']==e['raw_sha256']
        source=e['source_id'];field=e['source_field'];value=str(e.get('source_value',''))
        if source=='wz_reading_13759':
            if 'rows' not in data: data['rows']=read_archive(path)[0]
            matches=[r for r in data['rows'] if r['主键']==e['source_record_id']]
            assert matches and all(normalize(str(r[field]))==normalize(value) for r in matches)
            status='original_archive_field_exact_match'
        elif source.startswith('osm_'):
            if 'elements' not in data:
                data['elements']={f"{r['type']}/{r['id']}":r for r in json.loads(data['bytes'])['elements']}
            row=data['elements'][e['source_record_id']]
            if field.startswith('tags.'): actual=row.get('tags',{}).get(field[5:])
            elif field.startswith('center.'): actual=row.get('center',{}).get(field[7:])
            else: actual=row.get(field)
            assert str(actual)==value
            status='original_osm_field_exact_match'
        elif source=='ouhai_library_notice_20260904':
            if 'table' not in data:
                parser=NoticeRows();parser.feed(data['bytes'].decode('utf-8'))
                data['table']={r[0]:r for r in parser.rows if len(r)==4 and r[0].isdecimal()}
            row=data['table'][e['source_record_id']]
            if field=='类型':
                assert value=='书房书屋（官方名录）' and '书房书屋名称' in data['bytes'].decode('utf-8')
                status='derived_from_explicit_table_context_not_literal_type_column'
            else:
                index={'名称':1,'地址':2,'开放时间':3}[field]
                assert row[index]==value
                status='original_official_table_exact_match'
        elif source=='ouhai_expansion_20261106_manual_capture':
            if 'manual_records' not in data:
                data['manual_records']={'review_'+r['source_id']:r for r in json.loads(data['bytes'])['records']}
            row=data['manual_records'][e['poi_id']]
            key={'名称':'name','类型':'category','地址':'address','开放时间':'opening_hours'}[field]
            assert row[key]==value
            status='manual_capture_field_match_NOT_original_HTTP'
        else:
            raise ValueError('Unimplemented source-value verification; do not silently pass')
        results.append({'poi_id':e['poi_id'],'field':field,'status':status,'raw_sha256':data['sha']})
    summary={'purpose':'source_value_provenance_audit_NOT_real_world_validation',
             'checked_field_entries':len(results),'distinct_evidence_files':len(content),
             'statuses':dict(Counter(r['status'] for r in results)),
             'manual_capture_limitations_retained':True,'new_human_labels':0,
             'derived_official_category_context_not_claimed_literal':True}
    out=ROOT/'outputs/evidence_audit_20261125'
    (out/'source_value_checks.json').write_text(json.dumps({'summary':summary,'checks':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__': main()
