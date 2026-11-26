"""Versioned label overlay; never changes original judgments or imputes unknowns."""
from .metrics import score_query


def analyse_review(query_ids,candidate_ids,original,decisions,rankings):
    query_ids=tuple(query_ids);candidate_ids=tuple(candidate_ids)
    if not query_ids or not candidate_ids or len(set(query_ids))!=len(query_ids) or len(set(candidate_ids))!=len(candidate_ids):
        raise ValueError('Nonempty unique query and candidate IDs required')
    expected={(qid,pid) for qid in query_ids for pid in candidate_ids}
    if set(original)!=expected or not set(decisions)<=expected:
        raise ValueError('Review must use the complete original packet and only its pairs')
    for grade in [*original.values(),*decisions.values()]:
        if grade is not None and (type(grade) is not int or grade not in (0,1,2)):
            raise ValueError('Only ordinal0/1/2 or explicit unknown accepted')
    revised=dict(original);revised.update(decisions)
    coverage=[];evaluations=[]
    for qid in query_ids:
        before={pid:original[qid,pid] for pid in candidate_ids}
        after={pid:revised[qid,pid] for pid in candidate_ids}
        old_unknown=sum(v is None for v in before.values());new_unknown=sum(v is None for v in after.values())
        coverage.append({'query_id':qid,'candidates':len(candidate_ids),'before_unknown':old_unknown,
                         'after_unknown':new_unknown,'eligible_before':old_unknown==0,'eligible_after':new_unknown==0})
        if new_unknown:
            evaluations.append({'query_id':qid,'status':'excluded','reason':'incomplete_candidate_judgments','metrics':None})
        elif qid not in rankings:
            evaluations.append({'query_id':qid,'status':'not_evaluated','reason':'no_preserved_rankings_for_reviewed_query','metrics':None})
        else:
            for method,ranking in rankings[qid].items():
                score=score_query(ranking,after,eligible_ids=candidate_ids,include_recall=True)
                evaluations.append({'query_id':qid,'method':method,**score})
    return {'purpose':'post_publication_first_rater_review_sensitivity_NOT_independent_ground_truth',
            'reviewed_pairs':len(decisions),'numeric_review_decisions':sum(v is not None for v in decisions.values()),
            'unknown_review_decisions':sum(v is None for v in decisions.values()),
            'changed_from_original':sum(original[k]!=v for k,v in decisions.items()),
            'before_numeric':sum(v is not None for v in original.values()),'before_unknown':sum(v is None for v in original.values()),
            'after_numeric':sum(v is not None for v in revised.values()),'after_unknown':sum(v is None for v in revised.values()),
            'eligible_before':[r['query_id'] for r in coverage if r['eligible_before']],
            'eligible_after':[r['query_id'] for r in coverage if r['eligible_after']],
            'coverage':coverage,'evaluations':evaluations,'original_labels_modified':False,
            'unknowns_imputed_as_zero':False,'original_kappa_recomputed_after_review':False},revised
