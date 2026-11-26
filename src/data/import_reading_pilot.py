"""Import the approved government reading-space archive without inventing fields."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

SOURCE_ID = 'wz_reading_13759'
SOURCE_URL = 'https://data.wenzhou.gov.cn/jdop_front/detail/data.do?iid=13759'

def normalize(value):
    # 只清理空白和源文件中的转义换行，不补写地点属性。
    return re.sub(r'\s+', ' ', value.replace('\\n', '\n')).strip()

def read_archive(path):
    with ZipFile(path) as archive:
        files = [item for item in archive.infolist() if item.filename.endswith('.csv')]
        if len(files) != 1 or files[0].file_size > 2_000_000:
            raise ValueError('Expected one small CSV member')
        body = archive.read(files[0])
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            text = body.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('Unsupported CSV encoding')
    reader = csv.DictReader(io.StringIO(text))
    required = {'主键','名称','类型','地址','开放时间','百度地图经度','百度地图纬度'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Unexpected source schema')
    return list(reader), body, encoding

def prepare(rows, downloaded_at, raw_path, raw_hash):
    grouped = {}
    for index, row in enumerate(rows, 1):
        if not row['主键'] or not row['名称']:
            raise ValueError('Missing source ID or name')
        key = row['主键']
        if key in grouped:
            if grouped[key]['raw'] != row:
                raise ValueError(f'Conflicting records for ID {key}')
            grouped[key]['rows'].append(index)
        else:
            grouped[key] = {'raw':row,'rows':[index]}
    cleaned, evidence, issues = [], [], []
    for key, group in grouped.items():
        raw = group['raw']
        poi_id = f'{SOURCE_ID}_{key}'
        flags = ['crs_unverified', 'administrative_boundary_not_independently_checked',
                 'description_missing', 'current_operation_not_independently_checked']
        try:
            lon, lat = float(raw['百度地图经度']), float(raw['百度地图纬度'])
            # 宽松区域合理性筛查，仅发现明显异常，不用于确认瓯海行政归属。
            if not (119 <= lon <= 122 and 26 <= lat <= 30):
                flags.append('coordinate_outside_coarse_regional_sanity_box')
                issues.append({'poi_id':poi_id,'name':raw['名称'],'longitude':lon,'latitude':lat,
                               'issue':'coordinate_outside_coarse_regional_sanity_box',
                               'action':'retain source; no guessed correction; withhold map point'})
        except ValueError:
            lon = lat = None
            flags.append('coordinate_not_numeric')
        if '根据' in raw['开放时间']:
            flags.append('opening_hours_not_machine_resolvable')
        record = {
            'poi_id':poi_id,'name':normalize(raw['名称']),'category':normalize(raw['类型']),
            'address':normalize(raw['地址']),'description':None,
            'opening_hours':normalize(raw['开放时间']),'ticket_info':None,
            'original_longitude_text':raw['百度地图经度'],
            'original_latitude_text':raw['百度地图纬度'],
            'longitude':lon,'latitude':lat,'original_crs':'UNKNOWN',
            'coordinate_source_label':'百度地图经度/百度地图纬度',
            'wgs84_longitude':None,'wgs84_latitude':None,
            'district_assertion':'Ouhai source dataset; boundary not independently verified',
            'district_verified':False,'is_synthetic':False,
            'source_ids':[SOURCE_ID],'source_record_ids':[key],
            'source_rows':group['rows'],'source_url':SOURCE_URL,
            'retrieved_at':downloaded_at,'raw_path':raw_path,'raw_sha256':raw_hash,
            'record_status':'source_backed_candidate_pending_geographic_validation',
            'map_ready':False,'quality_flags':flags,
        }
        cleaned.append(record)
        for field, value in raw.items():
            evidence.append({'poi_id':poi_id,'source_field':field,'source_value':value,
                             'source_id':SOURCE_ID,'source_record_id':key,
                             'source_rows':json.dumps(group['rows']),
                             'source_url':SOURCE_URL,'downloaded_at':downloaded_at,
                             'raw_path':raw_path,'raw_sha256':raw_hash})
    report = {'raw_records':len(rows),'unique_source_records':len(cleaned),
              'exact_duplicate_rows_removed':len(rows)-len(cleaned),
              'coordinate_issues':issues,'map_ready_records':0,
              'description_missing_records':len(cleaned),
              'category_counts':{c:sum(r['category']==c for r in cleaned)
                                 for c in sorted({r['category'] for r in cleaned})},
              'dedup_rule':'same source ID AND identical full raw row; conflicts fail',
              'geographic_check':'119<=lon<=122,26<=lat<=30 coarse sanity only; not an administrative boundary',
              'pilot_status':'partial; below 30-50 target; not frozen for evaluation'}
    return cleaned, evidence, report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('output_dir')
    args = parser.parse_args()
    source = Path(args.archive)
    out = Path(args.output_dir)
    if out.exists():
        raise FileExistsError(out)
    meta = json.loads(source.with_suffix(source.suffix+'.metadata.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != meta['sha256']:
        raise ValueError('Raw archive hash mismatch')
    rows, body, encoding = read_archive(source)
    clean, evidence, report = prepare(rows,meta['checked_at'],source.as_posix(),digest)
    report.update(source_encoding=encoding,archive_sha256=digest,downloaded_at=meta['checked_at'])
    out.mkdir(parents=True)
    # 不覆盖压缩包；额外保留成员的原始字节。
    member = source.parent / 'cata_13759_original.csv'
    if member.exists():
        if member.read_bytes() != body:
            raise ValueError('Existing extracted member differs; refusing to overwrite')
    else:
        with member.open('xb') as stream: stream.write(body)
    report['extracted_member_sha256'] = hashlib.sha256(body).hexdigest()
    with (out/'poi_candidates.json').open('x',encoding='utf-8') as stream:
        json.dump(clean,stream,ensure_ascii=False,indent=2)
    for filename, records in [('poi_candidates.csv',clean),('field_evidence.csv',evidence)]:
        with (out/filename).open('x',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v
                             for k,v in record.items()} for record in records)
    with (out/'quality_report.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
