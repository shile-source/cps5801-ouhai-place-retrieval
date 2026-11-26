"""Explicitly synthetic metric-artifact checks; actual arithmetic is also run separately."""
import json
import pytest
from experiments.reproduce_reported_metrics import reproduce


def test_synthetic_saved_arithmetic_and_tamper_detection(tmp_path):
    path=tmp_path/'synthetic.json'
    value={'purpose':'published_metric_arithmetic_reproduction_NOT_new_model_inference','query_id':'synthetic',
           'candidate_ids':['a','b'],'judgments':{'a':2,'b':0},
           'runs':[{'method':'synthetic','ranking':['a','b'],'reported_metrics':{'ndcg_at_5':1}}]}
    path.write_text(json.dumps(value))
    assert reproduce(path)['new_inference'] is False
    value['runs'][0]['reported_metrics']['ndcg_at_5']=0
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='differs'):reproduce(path)
