"""本地官方文件安全导入。没有网络访问，不绕过登录；许可由用户先确认。"""
import argparse
import csv
import hashlib
import io
import json
import math
from copy import deepcopy
from pathlib import Path
from .import_reading_pilot import normalize
from .quality import coordinate_status, duplicate_review

def read_table(path):
    body = Path(path).read_bytes()
    if len(body) > 10_000_000:
        raise ValueError('Small pilot limit: 10 MB')
    if body.startswith(bytes.fromhex('D0CF11E0')):
        import xlrd
        book = xlrd.open_workbook(file_contents=body)
        if book.nsheets != 1:
            raise ValueError('Select a single sheet explicitly before import')
        sheet = book.sheet_by_index(0)
        matrix = [sheet.row_values(i) for i in range(sheet.nrows)]
        encoding = 'binary-xls'
    elif body.startswith(b'PK'):
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(body), read_only=True, data_only=False)
        if len(book.sheetnames) != 1:
            raise ValueError('Expected a single XLSX worksheet')
        matrix = list(book.active.values)
        book.close()
        encoding = 'binary-xlsx'
    else:
        encoding = None
        for enc in ('utf-8-sig', 'gb18030'):
            try:
                text = body.decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                pass
        if encoding is None:
            raise ValueError('Unsupported encoding')
        if text.lstrip().startswith(('[', '{')):
            rows = json.loads(text)
            if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
                raise ValueError('JSON must be a nonempty list of row objects; no guessed nested structure')
            headers = list(dict.fromkeys(k for row in rows for k in row))
            return rows, encoding, headers
        matrix = list(csv.reader(io.StringIO(text)))
    if not matrix:
        raise ValueError('Empty source')
    headers = [str(h).strip() for h in matrix[0]]
    if any(not h for h in headers) or len(set(headers)) != len(headers):
        raise ValueError('Blank or duplicate column names')
    rows = []
    for values in matrix[1:]:
        if len(values) != len(headers):
            raise ValueError('Row width differs from header')
        if any(str(v or '').startswith('=') for v in values):
            raise ValueError('Formula cells require manual review; no formula execution')
        if all(v is None or v == '' for v in values):
            continue
        rows.append(dict(zip(headers, values)))
    return rows, encoding, headers

def import_local(source, manifest, output, existing=None, existing_evidence=None, raw_dir=None):
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError(output)
    required = ('source_id','source_url','license_notes','license_evidence','retrieved_at','field_mapping')
    if manifest.get('permission_confirmed') is not True or any(not manifest.get(k) for k in required):
        raise ValueError('Explicit permission and complete source manifest required')
    if existing and existing_evidence is None:
        raise ValueError('Existing candidates require their field evidence for a merged snapshot')
    rows, encoding, headers = read_table(source)
    if len(rows) > 2000:
        raise ValueError('Small pilot limit: 2000 rows')
    mapping = manifest['field_mapping']
    if not mapping.get('name') or not set(mapping.values()).issubset(headers):
        raise ValueError('Explicit field mapping does not match source columns')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # 原始字节与清洗输出分开；采用 exclusive create，不覆盖输入或历史版本。
    output.mkdir(parents=True)
    raw = (Path(raw_dir) / (digest + source.suffix)) if raw_dir else output / ('original' + source.suffix)
    raw.parent.mkdir(parents=True,exist_ok=True)
    if raw.exists():
        if raw.read_bytes()!=source.read_bytes():
            raise ValueError('Existing raw file differs; refusing to overwrite')
    else:
        with raw.open('xb') as f:f.write(source.read_bytes())
    candidates = deepcopy(existing or [])
    evidence, errors, duplicate_rows, accepted = [], [], 0, 0
    seen = {}
    source_id = manifest['source_id']
    for index, row in enumerate(rows, 1):
        key = str(row.get(mapping.get('source_record_id', ''), '') or f'row_{index}')
        if key in seen:
            if seen[key] != row:
                errors.append({'row':index,'reason':'conflicting_source_id','source_record_id':key})
            else:
                duplicate_rows += 1
                for e in evidence:
                    if e['source_record_id'] == key:
                        e['source_rows'].append(index)
            continue
        seen[key] = row
        record = {f: normalize(str(row.get(col) or '')) for f, col in mapping.items()}
        if not record.get('name'):
            errors.append({'row':index,'reason':'missing_name'})
            continue
        record.update(poi_id=f'{source_id}_{key}', source_ids=[source_id], source_record_ids=[key],
                      original_crs='UNKNOWN', district_verified=False, coordinate_verified=False,
                      map_ready=False, is_synthetic=False, source_url=manifest['source_url'],
                      retrieved_at=manifest['retrieved_at'], raw_path=raw.as_posix(),raw_sha256=digest)
        for axis in ('longitude','latitude'):
            value = record.get(axis)
            record['original_'+axis+'_text'] = value
            try:
                record[axis] = float(value) if value else None
                if isinstance(record[axis], float) and not math.isfinite(record[axis]):
                    record[axis] = value
            except ValueError:
                record[axis] = value  # 保留非数值异常，不猜测修复。
        record['coordinate_status'] = coordinate_status(record.get('longitude'),record.get('latitude'))
        # 多来源实体合并只接受明确的人工映射；同名不自动合并。
        target = manifest.get('entity_links', {}).get(key)
        if target:
            matches = [r for r in candidates if r['poi_id'] == target]
            if len(matches) != 1 or not manifest.get('entity_link_evidence', {}).get(key):
                raise ValueError('Entity link requires an existing target and review evidence')
            merged = matches[0]
            merged.setdefault('source_observations', []).append(record)
            if source_id not in merged['source_ids']:
                merged['source_ids'].append(source_id)
            pid = target
        else:
            pid = record['poi_id']
            if any(r['poi_id'] == pid for r in candidates):
                raise ValueError('Existing source identity collision; review before import')
            candidates.append(record)
        accepted += 1
        for field,value in row.items():
            evidence.append({'poi_id':pid,'source_id':source_id,'source_record_id':key,'source_rows':[index],
                             'source_field':field,'source_value':str(value if value is not None else ''),
                             'source_url':manifest['source_url'],'downloaded_at':manifest['retrieved_at'],
                             'raw_path':raw.as_posix(),'raw_sha256':digest})
    summary = {'raw_records':len(rows),'candidate_records':len(candidates),'invalid_rows':errors,
               'exact_duplicate_rows':duplicate_rows,'encoding':encoding,'columns':headers,'sha256':digest,
               'valid_named_source_rows':accepted,
               'coordinate_anomalous_candidates':sum(coordinate_status(r.get('longitude'),r.get('latitude')) not in ('missing','plausible_unverified') for r in candidates),
               'pending_verification_candidates':sum(not r.get('coordinate_verified') or not r.get('district_verified') for r in candidates),
               'duplicate_review':duplicate_review(candidates)}
    for name, value in [('poi_candidates.json',candidates),('new_field_evidence.json',evidence),('field_evidence.json',deepcopy(existing_evidence or [])+evidence),('import_report.json',summary),('source_manifest.json',manifest)]:
        with (output/name).open('x',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
    return candidates,evidence,summary

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('source');p.add_argument('manifest');p.add_argument('output');p.add_argument('--existing');p.add_argument('--existing-evidence');p.add_argument('--raw-dir',default='data/raw/scenic_imports')
    a=p.parse_args()
    existing=json.loads(Path(a.existing).read_text(encoding='utf-8')) if a.existing else None
    old_evidence=None
    if a.existing_evidence:
        ep=Path(a.existing_evidence)
        if ep.suffix.lower()=='.csv':
            with ep.open(encoding='utf-8-sig') as f:old_evidence=list(csv.DictReader(f))
        else:old_evidence=json.loads(ep.read_text(encoding='utf-8'))
    _,_,summary=import_local(a.source,json.loads(Path(a.manifest).read_text(encoding='utf-8')),a.output,existing,old_evidence,a.raw_dir)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
