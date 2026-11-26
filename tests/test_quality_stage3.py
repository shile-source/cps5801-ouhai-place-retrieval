"""所有临时记录均为 synthetic，不能用作真实地点核验证据。"""
import hashlib
import json
from pathlib import Path
import pytest
from src.data.quality import coordinate_status, map_eligible, factual_description, duplicate_review, report
from src.data.scenic_import import read_table, import_local

@pytest.mark.parametrize('lon,lat,status',[(None,None,'missing'),('x',27,'not_numeric'),(float('nan'),27,'not_finite'),(120,91,'outside_global_range'),(120,7.9,'outside_coarse_regional_range'),(120.6,27.9,'plausible_unverified')])
def test_coordinate_cases(lon,lat,status):
    assert coordinate_status(lon,lat)==status

def test_label_does_not_verify_crs():
    assert not map_eligible({'coordinate_source_label':'百度地图经纬度','map_ready':True})

def test_map_requires_evidence():
    r=dict(coordinate_verified=True,district_verified=True,original_crs='WGS84',wgs84_longitude=120.6,wgs84_latitude=27.9,coordinate_conversion_method='identity')
    assert not map_eligible(r)
    r.update(coordinate_verification_evidence=['synthetic'],district_verification_evidence=['synthetic'],crs_evidence=['synthetic'])
    assert map_eligible(r)

def test_description_has_no_experiential_inference():
    e=[dict(poi_id='test',source_field='类型',source_value='模拟城市书房')]
    text,refs=factual_description({'poi_id':'test'},e)
    assert '安静' not in text and '学习' not in text and len(refs)==1

def test_description_conflicts_omitted():
    e=[dict(poi_id='test',source_field='地址',source_value=v) for v in ('模拟甲','模拟乙')]
    assert factual_description({'poi_id':'test'},e)==(None,[])

def test_alias_review_not_auto_merge():
    r=[dict(poi_id='a',name='模拟城市书房',address='甲'),dict(poi_id='b',name='模拟百姓书屋',address='乙')]
    assert duplicate_review(r)[0]['reasons']==['same_name_stem']
    assert len(r)==2

def test_provenance_hash_failure(tmp_path):
    raw=tmp_path/'raw';raw.write_bytes(b'synthetic')
    e=[dict(poi_id='test',source_field='name',source_id='test',source_record_id='1',source_url='synthetic',downloaded_at='synthetic',raw_path=str(raw),raw_sha256='wrong')]
    result=report([dict(poi_id='test',name='模拟')],e,tmp_path)
    assert result['source_backed_records']==0 and result['retrieval_text_ready_records']==0

def manifest():
    return dict(permission_confirmed=True,source_id='synthetic',source_url='synthetic://test',license_notes='test only',license_evidence='synthetic',retrieved_at='2026-10-12',field_mapping={'name':'名称','address':'地址','longitude':'经度','latitude':'纬度','source_record_id':'ID'})

@pytest.mark.parametrize('encoding',['utf-8-sig','gb18030'])
def test_csv_preserved_and_encoding(tmp_path,encoding):
    p=tmp_path/'input.csv';p.write_bytes('ID,名称,地址,经度,纬度\n1,模拟景区,模拟地址,120.6,7.9\n'.encode(encoding))
    original=p.read_bytes()
    r,e,s=import_local(p,manifest(),tmp_path/'out')
    assert p.read_bytes()==original==(tmp_path/'out/original.csv').read_bytes()
    assert s['sha256']==hashlib.sha256(original).hexdigest() and s['coordinate_anomalous_candidates']==1
    assert r[0]['original_crs']=='UNKNOWN' and e[0]['source_rows']==[1]

def test_permission_required(tmp_path):
    with pytest.raises(ValueError):import_local(tmp_path/'none',{},tmp_path/'out')
    assert not (tmp_path/'out').exists()

def test_json_and_xlsx(tmp_path):
    from openpyxl import Workbook
    p=tmp_path/'test.json';p.write_text(json.dumps([{'名称':'模拟'}]),encoding='utf-8')
    assert read_table(p)[0][0]['名称']=='模拟'
    w=Workbook();w.active.append(['名称']);w.active.append(['模拟']);x=tmp_path/'test.xlsx';w.save(x)
    assert read_table(x)[0][0]['名称']=='模拟'

def test_actual_public_xls_dictionary_parser():
    p=Path('data/evidence/stage3/reading_dictionary.xls')
    if not p.is_file():
        pytest.skip('Historical source dictionary is not bundled in the public-source candidate')
    rows,enc,headers=read_table(p)
    assert enc=='binary-xls' and len(rows)==13 and '字段中文名称' in headers

def test_duplicate_headers_rejected(tmp_path):
    p=tmp_path/'a.csv';p.write_text('名称,名称\n模拟,模拟\n',encoding='utf-8')
    with pytest.raises(ValueError):read_table(p)

def test_entity_link_retains_multisource(tmp_path):
    p=tmp_path/'a.json';p.write_text(json.dumps([{'ID':'1','名称':'模拟新名','地址':'模拟','经度':120,'纬度':27}]),encoding='utf-8')
    m=manifest();m.update(entity_links={'1':'old'},entity_link_evidence={'1':'synthetic manual decision'})
    old=[dict(poi_id='old',name='模拟原名',source_ids=['oldsource'],source_record_ids=['1'])]
    old_e=[{'poi_id':'old','source_id':'oldsource','source_field':'名称','source_value':'模拟原名'}]
    r,e,s=import_local(p,m,tmp_path/'out',old,old_e)
    assert len(r)==1 and r[0]['name']=='模拟原名' and len(r[0]['source_observations'])==1
    assert e[0]['poi_id']=='old' and r[0]['source_ids']==['oldsource','synthetic']
    assert old[0]['source_ids']==['oldsource']
    assert json.loads((tmp_path/'out/field_evidence.json').read_text(encoding='utf-8'))[0]==old_e[0]

def test_import_refuses_overwrite(tmp_path):
    out=tmp_path/'out';out.mkdir();(out/'keep').write_text('keep')
    with pytest.raises(FileExistsError):import_local(tmp_path/'none',manifest(),out)
    assert (out/'keep').read_text()=='keep'

def test_conflicting_source_records_reported(tmp_path):
    p=tmp_path/'a.csv';p.write_text('ID,名称,地址,经度,纬度\n1,模拟甲,模拟,120,27\n1,模拟乙,模拟,120,27\n',encoding='utf-8')
    _,_,s=import_local(p,manifest(),tmp_path/'out')
    assert s['invalid_rows'][0]['reason']=='conflicting_source_id'

def test_nonfinite_coordinate_and_raw_separation(tmp_path):
    p=tmp_path/'a.csv';p.write_text('ID,名称,地址,经度,纬度\n1,模拟,模拟,NaN,27\n',encoding='utf-8')
    r,_,s=import_local(p,manifest(),tmp_path/'clean',raw_dir=tmp_path/'raw')
    assert r[0]['longitude']=='NaN' and s['coordinate_anomalous_candidates']==1
    assert Path(r[0]['raw_path']).parent==tmp_path/'raw'
