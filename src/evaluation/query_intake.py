"""Human-authored query intake validation, never an automatic test-set approval."""
from collections import Counter

KINDS={'named_lexical','semantic_paraphrase','multi_preference','hard_constraint'}


def validate_intake(value,expected_catalog_sha256):
    if not isinstance(value,dict) or value.get('schema')!='independent_query_intake_v1':
        raise ValueError('Unknown intake schema')
    if value.get('formal_eligible') is not False:
        raise ValueError('Intake cannot declare itself approved/frozen')
    if value.get('is_draft') is not False or value.get('original_authorship_declared') is not True:
        raise ValueError('Complete human authorship declaration required')
    alias=value.get('author_alias')
    if not isinstance(alias,str) or not 1<=len(alias.strip())<=80:
        raise ValueError('Author alias required')
    if type(value.get('prior_ranking_exposure')) is not bool:
        raise ValueError('Explicit exposure self-report required')
    queries=value.get('queries')
    if not isinstance(queries,list) or len(queries)!=12:
        raise ValueError('Expected12 complete query drafts')
    ids,texts=set(),set()
    for q in queries:
        if not isinstance(q,dict) or set(q)!={'query_id','query_type','text'}:
            raise ValueError('Draft query accepts identity/type/text only, not grades or model ranks')
        if not isinstance(q['query_id'],str) or not q['query_id'] or q['query_id'] in ids:
            raise ValueError('Duplicate/empty query ID')
        if q['query_type'] not in KINDS or not isinstance(q['text'],str) or not 1<=len(q['text'].strip())<=300:
            raise ValueError('Invalid type or query text')
        text=q['text'].strip()
        if text in texts: raise ValueError('Duplicate query text; intent review still required')
        ids.add(q['query_id']);texts.add(text)
    if Counter(q['query_type'] for q in queries)!=Counter({k:3 for k in KINDS}):
        raise ValueError('Expected3 drafts per query type')
    binding=value.get('source_catalog_sha256')
    if binding is not None and binding!=expected_catalog_sha256:
        raise ValueError('Source catalog differs; do not silently migrate human queries')
    return {'status':'received_pending_human_evidence_and_intent_review','formal_eligible':False,
            'self_reported_no_prior_rankings':value['prior_ranking_exposure'] is False,
            'independence_verified':False,'query_count':12,
            'catalog_binding':'matches' if binding else 'missing_in_earlier_form_requires_review',
            'requires':['naturalness','source evidence','intent grouping','dev/test separation','protocol freeze']}
