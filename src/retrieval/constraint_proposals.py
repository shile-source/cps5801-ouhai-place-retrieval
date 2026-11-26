"""Narrow inspectable Chinese proposals; never silently turn preferences into filters."""
import re

CATEGORIES=('城市书房','百姓书屋','图书馆','博物馆','公园')
SOFT=re.compile(r'希望|最好|优先|尽量|偏好|倾向|如果可以')
UNSUPPORTED=re.compile(r'安静|舒适|现在营业|今天开放|今晚开放|最近|步行|免费|门票|距离')


def propose_constraints(query):
    if not isinstance(query,str) or not query.strip() or len(query)>500:
        raise ValueError('请输入1至500字的查询')
    suggestions={};notices=[]
    clauses=re.split(r'[，,。；;！!？?\n]|(?:并且|而且|同时)',query)
    for clause in clauses:
        if not clause.strip():continue
        if SOFT.search(clause) or (SOFT.search(query) and not re.search(r'必须|只找|仅限|一定要',clause)):
            notices.append({'clause':clause,'reason':'soft_preference_not_converted'})
            continue
        if re.search(r'不要|不能|不想|排除|不要求|不必|不一定|无需',clause):
            notices.append({'clause':clause,'reason':'negative_condition_requires_manual_review'})
            continue
        if UNSUPPORTED.search(clause):
            notices.append({'clause':clause,'reason':'unverified_attribute_not_filterable'})
        categories=[name for name in CATEGORIES if name in clause]
        if re.search(r'只找|仅限|必须(?:是|为)',clause) and len(categories)==1:
            suggestions.setdefault('category',set()).add(categories[0])
        for field,label,unit in [('seats',r'座位(?:数)?',r'(?:个)?座位'),
                                 ('holdings',r'藏书(?:量)?',r'(?:册|本)(?:书|藏书)?')]:
            # Numeric Arabic integers only; "more than" is deliberately not treated as >=.
            patterns=[label+r'\s*(?:至少|不少于|>=|≥)\s*(\d{1,6})(?!\d)',
                      r'(?:至少|不少于|>=|≥)\s*(\d{1,6})(?!\d)\s*'+unit]
            for pattern in patterns:
                for value in re.findall(pattern,clause):
                    suggestions.setdefault(field,set()).add(int(value))
    output=[]
    for field,values in suggestions.items():
        if len(values)!=1:
            notices.append({'field':field,'reason':'conflicting_values_require_manual_review'})
            continue
        output.append({'field':field,'operator':'eq' if field=='category' else 'gte','value':next(iter(values))})
    return {'purpose':'inspectable_suggestions_NOT_automatic_filter_execution',
            'constraints':output,'notices':notices,'requires_user_confirmation':True,
            'scope':'source_snapshot_only','models_called':False,
            'coverage':'limited explicit categories and Arabic-integer minimum counts; other conditions need review'}
