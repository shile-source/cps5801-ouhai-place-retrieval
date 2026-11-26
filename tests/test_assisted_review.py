import hashlib
import json
import pytest
from src.evaluation.assisted_review import AssistedReview
from experiments.prepare_assisted_review_20261126 import suggest


def review(tmp_path):
    packet = {'purpose': 'ai_assisted_development_review_NOT_independent_test', 'source_bindings': {},
              'items': [{'case_id': 'synthetic-1', 'ai_suggestion': {'grade': 2}}]}
    (tmp_path / 'packet.json').write_text(json.dumps(packet), encoding='utf-8')
    (tmp_path / 'manifest.json').write_text(json.dumps({'packet_sha256': hashlib.sha256((tmp_path / 'packet.json').read_bytes()).hexdigest()}), encoding='utf-8')
    return AssistedReview(tmp_path, tmp_path)


def test_suggestion_never_counts_as_human_confirmation(tmp_path):
    task = review(tmp_path)
    assert task.state()['handled'] == 0
    assert not (tmp_path / 'decisions.jsonl').exists()
    with pytest.raises(ValueError):
        task.decide('synthetic-1', 2, 'synthetic reason', 'synthetic', False)
    assert task.state()['handled'] == 0
    task.decide('synthetic-1', 0, 'synthetic correction', 'synthetic', True)
    row = task.decisions()['synthetic-1']
    assert row['grade'] == 0 and row['source'] == 'assisted_review_user_ui'
    assert row['role'] == 'ai_assisted_human_reviewer_not_independent'
    assert not row['claims_independent_blind_judgment']
    task.finalize()
    with pytest.raises(ValueError):
        task.decide('synthetic-1', 1, 'synthetic changed', 'synthetic', True)
    assert task.export()['human_confirmed_count'] == 1


def test_missing_quantities_and_partial_soft_preferences():
    item = {'name': 'synthetic', 'category': '城市书房', 'address': None, 'description': ''}
    spec = ('soft_preferences', [('category', 'city_reading'), ('seats', 40)])
    assert suggest(item, spec)[0] is None
    item['description'] = '座位数：30'
    assert suggest(item, spec)[0] == 1
    item['description'] = '座位数：40'
    assert suggest(item, spec)[0] == 2


def test_semantic_conjunction_is_not_soft_preference():
    item = {'name': 'synthetic普通公园', 'category': '公园', 'description': ''}
    facts = [('category', '公园'), ('name_contains', '滨水')]
    assert suggest(item, ('semantic', facts))[0] == 0
    assert suggest(item, ('soft_preferences', facts))[0] == 1
