"""以下排名/分数完全手工构造，仅验证公式，不是研究实验。"""
import math
import pytest
from src.evaluation.metrics import score_query, evaluate_runs, weighted_kappa, query_bootstrap


def test_hand_calculated_reversed_binary_ranking():
    r = score_query(['b', 'a'], {'a': 2, 'b': 0}, eligible_ids=['a', 'b'], include_recall=True)
    assert r['metrics'] == pytest.approx({'ndcg_at_5': 0.6309297535714575,
        'precision_at_3': 1/3, 'mrr': 0.5, 'recall_at_5': 1.0})


def test_exponential_gain_not_linear_gain():
    r = score_query(['b', 'a'], {'a': 2, 'b': 1}, eligible_ids=['a', 'b'])
    assert r['metrics']['ndcg_at_5'] == pytest.approx((1 + 3*0.6309297535714575)/(3 + 0.6309297535714575))


def test_perfect_graded_ranking():
    grades = {'a': 2, 'b': 1, 'c': 0}
    assert score_query(['a', 'b', 'c'], grades, eligible_ids=list(grades))['metrics']['ndcg_at_5'] == 1.0


def test_binary_threshold_fixed_explicitly():
    grades = {'a': 1, 'b': 0, 'c': 2}
    high = score_query(list(grades), grades, eligible_ids=list(grades))
    inclusive = score_query(list(grades), grades, eligible_ids=list(grades), relevance_threshold=1)
    assert high['metrics']['precision_at_3'] == pytest.approx(1/3)
    assert high['metrics']['mrr'] == pytest.approx(1/3)
    assert inclusive['metrics']['precision_at_3'] == pytest.approx(2/3)
    assert inclusive['metrics']['mrr'] == 1.0
    assert high['metrics']['ndcg_at_5'] == inclusive['metrics']['ndcg_at_5']


@pytest.mark.parametrize('labels', [{}, {'a': 2}, {'a': 2, 'b': None}])
def test_unjudged_never_treated_as_zero(labels):
    r = score_query(['a'], labels, eligible_ids=['a', 'b'], include_recall=True)
    assert r['status'] == 'excluded' and all(x is None for x in r['metrics'].values())


def test_full_mrr_is_not_mrr_at_five():
    candidates = list('abcdef')
    grades = {p: (2 if p == 'f' else 0) for p in candidates}
    top5 = score_query(candidates[:5], grades, eligible_ids=candidates, include_recall=True)
    full = score_query(candidates, grades, eligible_ids=candidates, include_recall=True)
    assert top5['metrics']['mrr'] is None
    assert full['metrics']['mrr'] == pytest.approx(1/6)
    assert full['metrics']['ndcg_at_5'] == full['metrics']['recall_at_5'] == 0


def test_undefined_metrics_not_fabricated_zero():
    r = score_query(['a'], {'a': 0}, eligible_ids=['a'], include_recall=True)
    assert r['metrics'] == {'ndcg_at_5': None, 'precision_at_3': 0, 'mrr': 0, 'recall_at_5': None}
    assert score_query([], {}, eligible_ids=[])['status'] == 'excluded'


def test_empty_return_and_short_return_precision_denominator():
    assert score_query(['a'], {'a': 2}, eligible_ids=['a'])['metrics']['precision_at_3'] == pytest.approx(1/3)
    r = score_query([], {'a': 2}, eligible_ids=['a'])
    assert r['metrics']['ndcg_at_5'] == r['metrics']['precision_at_3'] == 0
    assert r['metrics']['mrr'] is None


@pytest.mark.parametrize('ranking,candidates', [(['a', 'a'], ['a']), (['x'], ['a']), (['a'], ['a', 'a']), ([''], [''])])
def test_invalid_ranking_identity(ranking, candidates):
    with pytest.raises(ValueError):
        score_query(ranking, {'a': 2}, eligible_ids=candidates)


@pytest.mark.parametrize('grade', [-1, 3, True, 1.0, '2', float('nan')])
def test_invalid_grade(grade):
    with pytest.raises(ValueError):
        score_query(['a'], {'a': grade}, eligible_ids=['a'])


@pytest.mark.parametrize('threshold', [0, 3, True, 1.0])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError):
        score_query([], {}, eligible_ids=[], relevance_threshold=threshold)


def specs():
    return {'q1': {'query_type': 'named_lexical', 'is_synthetic': True},
            'q2': {'query_type': 'semantic_paraphrase', 'is_synthetic': True}}


def test_group_macro_and_identical_model_query_set():
    runs = {'synthetic_A': {'q1': ['a', 'b'], 'q2': ['a', 'b']},
            'synthetic_B': {'q1': ['b', 'a'], 'q2': ['a']}}
    labels = {q: {'a': 2, 'b': 0} for q in specs()}
    report = evaluate_runs(runs, specs(), labels, {q: ['a', 'b'] for q in specs()}, purpose='synthetic_test')
    assert report['summary']['overall']['mrr']['query_ids'] == ['q1']
    assert report['summary']['overall']['ndcg_at_5']['n'] == 2
    assert report['summary']['named_lexical']['mrr']['means'] == {'synthetic_A': 1, 'synthetic_B': 0.5}
    assert report['summary']['semantic_paraphrase']['mrr']['n'] == 0


def test_missing_model_run_excludes_for_everyone():
    report = evaluate_runs({'A': {'q1': ['a']}, 'B': {}}, specs(), {}, {}, purpose='synthetic_test')
    assert report['status'] == 'not_evaluated'
    assert all(r['metrics']['precision_at_3'] is None for r in report['per_query'])


def test_draft_and_unknown_hard_conditions_cannot_enter_formal_evaluation():
    query = {'q': {'query_type': 'hard_constraint', 'formal_eligible': False, 'human_review_status': 'pending'}}
    arguments = ({'A': {'q': ['a']}}, query, {'q': {'a': 2}}, {'q': ['a']})
    assert evaluate_runs(*arguments)['status'] == 'not_evaluated'
    query['q'].update(formal_eligible=True, human_review_status='approved', has_hard_constraints=True)
    assert evaluate_runs(*arguments)['per_query'][0]['reasons'] == ['query_not_frozen_test_or_labels_not_adjudicated']
    query['q'].update(split='held_out_test', freeze_id='synthetic_formula_test_only', labels_status='adjudicated')
    result = evaluate_runs(*arguments)
    assert result['per_query'][0]['reasons'] == ['hard_constraint_pool_not_verified']
    query['q']['eligibility_verified'] = True
    assert evaluate_runs(*arguments)['status'] == 'scored'


def test_hard_query_type_does_not_depend_on_optional_flag():
    q = {'q': {'query_type': 'hard_constraint', 'is_synthetic': True}}
    result = evaluate_runs({'A': {'q': ['a']}}, q, {'q': {'a': 2}}, {'q': ['a']}, purpose='synthetic_test')
    assert result['status'] == 'not_evaluated'


def test_real_queries_rejected_in_synthetic_mode():
    with pytest.raises(ValueError):
        evaluate_runs({'A': {}}, {'real': {'query_type': 'named_lexical'}}, {}, {}, purpose='synthetic_test')


def test_unknown_run_query_rejected():
    with pytest.raises(ValueError):
        evaluate_runs({'A': {'unknown': []}}, specs(), {}, {}, purpose='synthetic_test')


@pytest.mark.parametrize('weights,expected', [('linear', 0.25), ('quadratic', 0.5)])
def test_kappa_hand_calculation(weights, expected):
    assert weighted_kappa([0, 1, 2], [0, 2, 1], weights=weights)['kappa'] == pytest.approx(expected)


def test_kappa_matches_existing_sklearn_reference():
    from sklearn.metrics import cohen_kappa_score
    a, b = [0, 0, 1, 1, 2, 2], [0, 1, 1, 2, 2, 0]
    assert weighted_kappa(a, b)['kappa'] == pytest.approx(cohen_kappa_score(a, b, labels=[0, 1, 2], weights='linear'))


def test_kappa_empty_degenerate_and_invalid():
    assert weighted_kappa([], [])['kappa'] is None
    assert weighted_kappa([2, 2], [2, 2])['kappa'] is None
    assert weighted_kappa([0, 1, 2], [0, 1, 2])['kappa'] == 1
    for a, b in [([1], []), ([None], [0]), ([True], [0])]:
        with pytest.raises(ValueError):
            weighted_kappa(a, b)


def test_bootstrap_is_seeded_and_constant_interval_exact():
    result = query_bootstrap({'s1': 0.5, 's2': 0.5}, samples=100)
    assert result['lower'] == result['upper'] == result['mean'] == 0.5
    assert query_bootstrap({'s2': 1, 's1': 0}, samples=100) == query_bootstrap({'s1': 0, 's2': 1}, samples=100)


@pytest.mark.parametrize('values', [{}, {'s': math.nan}, {'s': True}])
def test_bootstrap_invalid(values):
    with pytest.raises(ValueError):
        query_bootstrap(values)
