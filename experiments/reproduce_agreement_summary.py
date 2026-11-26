"""Recompute actual aggregate agreement arithmetic; no participant records required."""
import argparse
import json
import math
from pathlib import Path
from src.evaluation.metrics import weighted_kappa

ROOT=Path(__file__).resolve().parents[1]


def reproduce(path):
    report=json.loads(Path(path).read_text(encoding='utf-8'))
    if report.get('purpose')!='post_publication_sampled_agreement_NOT_full_dual_annotation':
        raise ValueError('Unexpected aggregate agreement schema')
    verified={}
    for name,group in report['statistics'].items():
        matrix=group['confusion_matrix_0_1_2']
        if len(matrix)!=3 or any(len(row)!=3 for row in matrix) or any(type(x) is not int or x<0 for row in matrix for x in row):
            raise ValueError('Ordinal3x3 nonnegative integer contingency counts required')
        if sum(sum(row) for row in matrix)!=group['n']:raise ValueError('Paired count differs from contingency table')
        # Expand only the saved aggregate counts for arithmetic, not new human observations.
        pairs=[(i,j) for i,row in enumerate(matrix) for j,count in enumerate(row) for _ in range(count)]
        first,second=zip(*pairs) if pairs else ((),())
        values={weight:weighted_kappa(first,second,weights=weight)['kappa'] for weight in ('linear','quadratic')}
        for weight,actual in values.items():
            expected=group[weight]['kappa']
            if (actual is None)!=(expected is None) or (actual is not None and not math.isclose(actual,expected,abs_tol=1e-12)):
                raise ValueError('Saved kappa differs from aggregate table')
        agreement=sum(matrix[i][i] for i in range(3))/group['n'] if group['n'] else None
        if agreement!=group['exact_agreement']:raise ValueError('Saved exact agreement differs')
        verified[name]={'n':group['n'],'exact_agreement':agreement,'kappa':values}
    return {'status':'aggregate_agreement_arithmetic_reproduced','groups':verified,
            'new_human_labels_created':0,'private_action_logs_required':False,
            'individual_judgment_provenance_reverified':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=ROOT/'results/sampled_agreement_summary.json')
    args=parser.parse_args();print(json.dumps(reproduce(args.input),indent=2))


if __name__=='__main__':main()
