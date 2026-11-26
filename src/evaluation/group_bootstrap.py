"""Paired intent-group bootstrap; no confidence interval for a single observed intent."""
import math
from statistics import mean
from .metrics import query_bootstrap


def paired_group_bootstrap(first,second,intent_groups,*,samples=2000,seed=5801,confidence=.95):
    if set(first)!=set(second) or set(first)!=set(intent_groups) or not first:
        raise ValueError('Methods and frozen intent mapping must cover the same nonempty query set')
    groups={}
    for qid in sorted(first):
        group=intent_groups[qid]
        if not isinstance(group,str) or not group.strip():raise ValueError('Explicit intent group required')
        for value in (first[qid],second[qid]):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('Finite paired per-query metrics required')
        groups.setdefault(group,[]).append(first[qid]-second[qid])
    differences={g:mean(values) for g,values in groups.items()}
    if len(differences)<2:
        return {'status':'not_estimable','reason':'fewer_than_two_independent_intent_groups',
                'n_groups':len(groups),'n_queries':len(first),'interval':None}
    result=query_bootstrap(differences,samples=samples,seed=seed,confidence=confidence)
    result['n_groups']=result.pop('n_queries')
    result.update(status='computed',n_queries=len(first),
                  unit='frozen independent intent group; group means weighted equally',
                  estimand='first minus second, macro mean of intent-group means',
                  independence_assumption_verified=False)
    return result
