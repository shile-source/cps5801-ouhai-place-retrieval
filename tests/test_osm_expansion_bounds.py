"""Synthetic import bounds; no real POI data or labels."""
import pytest
from src.data.osm_import import build_candidates


def fixture(n):
    payload={'elements':[{'type':'node','id':i+1,'tags':{'name':f'synthetic{i}','leisure':'park'},'lat':28,'lon':120.6} for i in range(n)]}
    meta={'license':'ODbL-1.0','license_evidence_sha256':'synthetic','sha256':'synthetic',
          'raw_path':'synthetic.json','finished':'2026-01-01','endpoint':'https://example.test'}
    return payload,meta


def test_original_default_still_rejects_above28():
    with pytest.raises(ValueError,match='28'): build_candidates(*fixture(29))


def test_explicit_new_bound_has_its_own_source_id():
    records,evidence,_=build_candidates(*fixture(39),max_elements=146,source_id='synthetic_new')
    assert len(records)==39
    assert all(r['source_ids']==['synthetic_new'] for r in records)
    assert all(e['source_id']=='synthetic_new' for e in evidence)


@pytest.mark.parametrize('limit',[0,201,True,1.5])
def test_invalid_or_unbounded_expansion_rejected(limit):
    with pytest.raises(ValueError): build_candidates(*fixture(1),max_elements=limit)
