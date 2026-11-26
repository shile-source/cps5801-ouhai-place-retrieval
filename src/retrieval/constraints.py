"""Shared deterministic explicit constraints; unknown facts never pass a hard filter."""
from dataclasses import dataclass


def parse_explicit_constraints(value):
    if value is None:return ()
    if not isinstance(value,list) or len(value)>5:
        raise ValueError('At most five explicit source-snapshot constraints are supported')
    output=[]
    for item in value:
        if not isinstance(item,dict) or not {'field','operator','value'}<=set(item) or set(item)-{'field','operator','value','scope'}:
            raise ValueError('Constraint requires field, operator and value only')
        output.append(Constraint(**item))
    return tuple(output)


@dataclass(frozen=True)
class Constraint:
    field: str
    operator: str
    value: str | int
    scope: str = 'source_snapshot_only'

    def __post_init__(self):
        if self.field not in ('name','category','address','seats','holdings'):
            raise ValueError('Unsupported evidence field; do not infer geography/quietness/current operations')
        if self.scope != 'source_snapshot_only':
            raise ValueError('These facts do not establish current or independently verified conditions')
        numeric = self.field in ('seats','holdings')
        if numeric:
            if self.operator not in ('eq','gte','lte') or type(self.value) is not int or self.value<0:
                raise ValueError('Numeric constraint requires a nonnegative integer and supported comparison')
        elif self.operator != 'eq' or not isinstance(self.value,str) or not self.value.strip():
            raise ValueError('Text constraint requires exact nonempty source value')


def assess(facts, constraints):
    """Return met/unmet/unknown, preserving the evidence supporting each decision."""
    checks=[]
    for c in constraints:
        if not isinstance(c,Constraint):
            raise ValueError('Explicit validated constraints required')
        fact=facts.get(c.field,{})
        actual=fact.get('value')
        if fact.get('status')!='supported' or not fact.get('evidence') or actual is None:
            status='unknown'
        else:
            if c.field in ('seats','holdings') and type(actual) is not int:
                raise ValueError('Invalid numeric fact')
            passed = actual==c.value if c.operator=='eq' else actual>=c.value if c.operator=='gte' else actual<=c.value
            status='met' if passed else 'unmet'
        checks.append({'field':c.field,'operator':c.operator,'requested':c.value,
                       'status':status,'source_value':actual,'evidence':fact.get('evidence',[])})
    status='unmet' if any(c['status']=='unmet' for c in checks) else 'unknown' if any(c['status']=='unknown' for c in checks) else 'met'
    return {'status':status,'checks':checks,'scope':'source_snapshot_only'}


def shared_pool(facts_by_id, constraints):
    """Build one common candidate pool before any ranking; no relevance labels."""
    constraints=tuple(constraints)
    decisions={pid:assess(facts,constraints) for pid,facts in facts_by_id.items()}
    return {'eligible_ids':[pid for pid,r in decisions.items() if r['status']=='met'],
            'unknown_ids':[pid for pid,r in decisions.items() if r['status']=='unknown'],
            'unmet_ids':[pid for pid,r in decisions.items() if r['status']=='unmet'],
            'decisions':decisions,'scope':'source_snapshot_only','creates_relevance_grades':False}
