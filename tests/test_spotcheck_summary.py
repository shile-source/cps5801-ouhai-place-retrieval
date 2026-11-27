import hashlib
import json
import pytest
from src.evaluation.assisted_review import AssistedReview
from src.evaluation.spotcheck_summary import summarize


def fixture(tmp_path,grades):
    packet={'purpose':'ai_assisted_development_review_NOT_independent_test','source_bindings':{},
            'items':[{'case_id':str(i),'ai_suggestion':{'grade':g}} for i,g in enumerate(grades)]}
    p=tmp_path/'packet.json';p.write_text(json.dumps(packet),encoding='utf-8')
    (tmp_path/'manifest.json').write_text(json.dumps({'packet_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
    return AssistedReview(tmp_path,tmp_path)


def test_incomplete_or_unlocked_human_sample_cannot_supply_statistics(tmp_path):
    review=fixture(tmp_path,[2,0])
    with pytest.raises(ValueError):summarize(review)
    review.decide('0',0,'synthetic correction','test',True)
    review.decide('1',0,'synthetic agreement','test',True)
    with pytest.raises(ValueError):summarize(review)
    review.finalize();result=summarize(review)
    assert result['numeric_exact_fraction']==.5
    assert result['transition_counts_ai_to_human']['2']['0']==1
    assert result['unreviewed_suggestions_promoted_to_human_labels']==0


def test_unknown_never_becomes_zero_or_numeric_agreement(tmp_path):
    review=fixture(tmp_path,[None,2])
    review.decide('0',None,'synthetic unknown','test',True)
    review.decide('1',None,'synthetic insufficient facts','test',True)
    review.finalize();result=summarize(review)
    assert result['both_numeric_count']==0 and result['numeric_exact_fraction'] is None
    assert result['human_unknown_count']==2
    assert result['all_equal_including_unknown_count']==1
    assert result['full_corpus_relevance_metrics'] is None
