"""Supplemental paired-rating audit; never adjudicates or fills an unknown grade."""
from collections import Counter
from .metrics import weighted_kappa


def analyse_sample(tasks,first,second):
    tasks=tuple(tuple(pair) for pair in tasks)
    if not tasks or len(tasks)!=len(set(tasks)):
        raise ValueError('A nonempty unique frozen sample is required')
    allowed=set(tasks)
    if set(second)-allowed:
        raise ValueError('Second-rater log contains a pair outside its frozen sample')
    missing=[pair for pair in tasks if pair not in second]
    base={'purpose':'post_publication_sampled_rater_agreement_NOT_full_dual_annotation',
          'sample_size':len(tasks),'second_handled':len(second),'missing_second':len(missing),
          'formal_independent_test_set':False,'unknowns_imputed_as_zero':False}
    if missing:
        return {**base,'status':'awaiting_second_rater_completion','statistics':None,'adjudication_queue':[]}
    groups={'original_human_pairs_only':[],'including_AI_assisted_first_rater_sensitivity':[]}
    exclusions=Counter();queue=[];by_query={}
    for qid,pid in tasks:
        pair=(qid,pid)
        a,b=first.get(pair),second[pair]
        if a is None:
            exclusions['first_missing']+=1
            continue
        for rating in (a,b):
            grade=rating.get('semantic_grade')
            if grade is not None and (type(grade) is not int or grade not in (0,1,2)):
                raise ValueError('Only actual ordinal grades or explicit unknown are accepted')
        av,bv=a['semantic_grade'],b['semantic_grade']
        human=a.get('source')=='user_local_ui'
        counts=by_query.setdefault(qid,Counter(sampled=0,paired_numeric=0,first_assisted=0))
        counts['sampled']+=1
        if not human:counts['first_assisted']+=1
        if av is None or bv is None:
            exclusions['one_or_both_unknown']+=1
        else:
            counts['paired_numeric']+=1
            groups['including_AI_assisted_first_rater_sensitivity'].append((av,bv))
            if human:groups['original_human_pairs_only'].append((av,bv))
        if av is None or bv is None or av!=bv:
            queue.append({'query_id':qid,'poi_id':pid,'first_grade':av,'second_grade':bv,
                          'first_source':a.get('source'),'first_evidence':a.get('evidence',''),
                          'second_evidence':b.get('evidence',''),'first_unknown_reason':a.get('unknown_reason',''),
                          'second_unknown_reason':b.get('unknown_reason',''),
                          'final_grade':None,'decision_reason':'','adjudicator_id':'','adjudicated_at':''})
    stats={}
    for name,rows in groups.items():
        x,y=zip(*rows) if rows else ((),())
        stats[name]={'n':len(rows),'exact_agreement':sum(a==b for a,b in rows)/len(rows) if rows else None,
                     'linear':weighted_kappa(x,y,weights='linear'),
                     'quadratic':weighted_kappa(x,y,weights='quadratic'),
                     'confusion_matrix_0_1_2':[[sum(a==i and b==j for a,b in rows) for j in range(3)] for i in range(3)]}
    return {**base,'status':'completed_supplemental_sample','statistics':stats,
            'exclusions':dict(exclusions),'per_query':{q:dict(v) for q,v in by_query.items()},
            'adjudication_queue':queue,'automatic_final_labels_created':0,
            'limitations':['Second rater added after original model results were published.',
                          'Convenience AI-assisted queries, not independent held-out intents.',
                          'Uniform sampled pairs can be severely label-imbalanced; no complete-query effectiveness claim.',
                          'Kappa is descriptive; overlapping candidates and intents are not independent sampling units.']}
