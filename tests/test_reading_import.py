"""Synthetic records test import rules; these are not real POI evidence."""
import pytest
from src.data.import_reading_pilot import prepare

def row(key='test',lat='27.9'):
    return {'主键':key,'名称':'模拟测试书房','类型':'模拟类型','地址':'模拟地址',
            '开放时间':'根据来源安排','百度地图经度':'120.6','百度地图纬度':lat}

def test_exact_duplicate_is_not_two_places():
    records,_,report=prepare([row(),row()],'test','synthetic','test')
    assert len(records)==1 and records[0]['source_rows']==[1,2]
    assert report['exact_duplicate_rows_removed']==1

def test_conflicting_id_is_not_silently_merged():
    with pytest.raises(ValueError):
        prepare([row(),row(lat='27.8')],'test','synthetic','test')

def test_bad_coordinate_is_retained_and_flagged():
    records,_,report=prepare([row(lat='7.9')],'test','synthetic','test')
    assert records[0]['latitude']==7.9
    assert records[0]['wgs84_latitude'] is None
    assert not records[0]['map_ready']
    assert len(report['coordinate_issues'])==1

def test_missing_description_not_invented():
    records,evidence,_=prepare([row()],'test','synthetic','test')
    assert records[0]['description'] is None
    assert records[0]['original_crs']=='UNKNOWN'
    assert any(e['source_field']=='名称' and e['source_value']=='模拟测试书房' for e in evidence)
