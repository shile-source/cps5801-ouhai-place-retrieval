"""Descriptive audit of a locked AI-visible human sample, never full-corpus truth."""
from collections import Counter
from src.evaluation.adjudication import digest


def summarize(review):
    state=review.state()
    if not state['locked'] or state['handled']!=state['total']:
        raise ValueError('Human spotcheck must be complete and personally locked before analysis')
    decisions=review.decisions()
    items=review.packet['items']
    pairs=[(item['ai_suggestion']['grade'],decisions[item['case_id']]['grade']) for item in items]
    numeric=[(a,h) for a,h in pairs if a is not None and h is not None]
    exact=sum(a==h for a,h in numeric)
    def label(value):return 'unknown' if value is None else str(value)
    cells=Counter((label(a),label(h)) for a,h in pairs)
    levels=['0','1','2','unknown']
    return {
        'purpose':'descriptive_AI_visible_human_spotcheck_NOT_independent_effectiveness',
        'human_decision_count':len(pairs),'human_unknown_count':sum(h is None for a,h in pairs),
        'ai_unknown_in_sample':sum(a is None for a,h in pairs),'both_numeric_count':len(numeric),
        'numeric_exact_count':exact,'numeric_exact_fraction':exact/len(numeric) if numeric else None,
        'transition_counts_ai_to_human':{a:{h:cells[a,h] for h in levels} for a in levels},
        'numeric_denominator_excludes_either_unknown':True,
        'all_equal_including_unknown_count':sum(a==h for a,h in pairs),
        'source_bindings':review.packet['source_bindings'],
        'packet_sha256':review.manifest['packet_sha256'],
        'decisions_sha256':digest(review.path/'decisions.jsonl'),
        'independently_blind':False,'unknowns_imputed_as_zero':False,
        'unreviewed_suggestions_promoted_to_human_labels':0,
        'full_corpus_relevance_metrics':None,'population_confidence_interval':None,
        'claim_boundary':'Describes only this locked assisted sample; unknown agreement is not proof of relevance or real-world facts.'}
