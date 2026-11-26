"""Read existing human logs; calculate only after the whole frozen B sample is handled."""
import csv
from datetime import datetime
import json
from pathlib import Path
from src.evaluation.human_pilot import Pilot,sha
from src.evaluation.second_rater import REFERENCE,SAMPLED_SESSION,SecondRaterPilot
from src.evaluation.sampled_agreement import analyse_sample

ROOT=Path(__file__).resolve().parents[1]


def main():
    a,b=Pilot(REFERENCE),SecondRaterPilot(SAMPLED_SESSION)
    if b.packet['reference_packet_sha256']!=a.manifest['packet_sha256']:
        raise ValueError('Reference packet mismatch')
    if sha(a.path/'human_actions.jsonl')!=b.packet['reference_action_log_sha256']:
        raise ValueError('Published first-rater log changed since sample freeze')
    protected={p:sha(p) for session in (a,b) for p in session.path.glob('*.json*') if p.is_file()}
    report=analyse_sample(b.tasks,a.ratings(),b.ratings())
    report['input_sha256']={str(p.relative_to(ROOT)):h for p,h in protected.items()}
    if any(sha(p)!=h for p,h in protected.items()):
        raise ValueError('Input log changed during read; retry after human work stops; no report published')
    output=ROOT/'outputs'/('sampled_agreement_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir()
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    queue=report['adjudication_queue']
    if queue:
        with (output/'adjudication_blank.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(queue[0]));writer.writeheader();writer.writerows(queue)
    text=('# Supplemental sampled agreement\n\nStatus: '+report['status']+
          f"\n\nSecond rater handled {report['second_handled']}/{report['sample_size']}. "
          'Unknowns are not zero. No final labels were generated.\n')
    (output/'README.md').write_text(text,encoding='utf-8')
    print(json.dumps({'output':str(output),'status':report['status'],'handled':report['second_handled'],'total':report['sample_size']}))


if __name__=='__main__':main()
