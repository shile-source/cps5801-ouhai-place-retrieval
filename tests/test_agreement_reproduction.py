"""Synthetic aggregate counts only; no genuine participant observations fabricated."""
import json
import pytest
from experiments.reproduce_agreement_summary import reproduce


def test_synthetic_aggregate_arithmetic_and_corruption_detection(tmp_path):
    path=tmp_path/'synthetic.json'
    value={'purpose':'post_publication_sampled_agreement_NOT_full_dual_annotation',
           'statistics':{'synthetic':{'n':2,'confusion_matrix_0_1_2':[[1,0,0],[0,0,0],[0,0,1]],
                                    'exact_agreement':1,'linear':{'kappa':1},'quadratic':{'kappa':1}}}}
    path.write_text(json.dumps(value));assert reproduce(path)['new_human_labels_created']==0
    value['statistics']['synthetic']['n']=3
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='Paired count'):reproduce(path)
