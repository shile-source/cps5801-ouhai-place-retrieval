"""Verify an isolated, newly installed CPU environment against an audited source copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import re

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True)
    args=parser.parse_args();source=args.candidate.resolve()
    if not source.is_relative_to(ROOT/'outputs') or source.name!='CPS5801-Research':raise ValueError('Audited project source candidate required')
    python=ROOT/'.cache/repro_cpu_env_20261126/Scripts/python.exe'
    if not python.is_file():raise ValueError('Create and install the documented separate CPU environment first')
    manifest=json.loads((source/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    out=ROOT/'outputs/reproducibility_audit_20261126';out.mkdir(exist_ok=True)
    env=dict(os.environ,PYTHONPATH=str(source),PYTHONNOUSERSITE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    code="import sys,site,importlib.util,pathlib; assert pathlib.Path(sys.prefix)==pathlib.Path(sys.argv[1]).parent.parent; assert not site.ENABLE_USER_SITE; assert importlib.util.find_spec('torch') is None; import src.demo.server; assert pathlib.Path(src.demo.server.__file__).resolve().is_relative_to(pathlib.Path.cwd()); print('fresh_CPU_prefix_and_source_verified_no_torch')"
    steps=[('isolation',['-c',code,str(python)]),('pip_check',['-m','pip','check']),
           ('tests',['-m','pytest','-q','--tb=short']),('metrics',['-m','experiments.reproduce_reported_metrics']),
           ('agreement',['-m','experiments.reproduce_agreement_summary']),
           ('keyword_metrics',['-m','experiments.reproduce_keyword_supplement']),
           ('bge_saved_metrics',['-m','experiments.reproduce_bge_supplement']),
           ('review_sensitivity',['-m','experiments.reproduce_review_sensitivity']),
           ('open_data',['-m','experiments.prepare_open_osm_20261126']),
           ('bm25',['-m','experiments.run_retrieval_snapshot','--method','bm25','--query','公园']),
           ('keyword',['-m','experiments.run_retrieval_snapshot','--method','keyword','--query','公园'])]
    report={'scope':'fresh CPU dependencies and public saved arithmetic/open-data lexical workflow; not fresh GPU or original mixed retrieval',
            'fresh_dependency_install':True,'torch_installed':False,'new_model_inference':False,
            'candidate':str(source),'requirements_sha256':hashlib.sha256((source/'requirements.txt').read_bytes()).hexdigest(),
            'steps':{},'status':'running'}
    for name,arguments in steps:
        run=subprocess.run([str(python),*arguments],cwd=source,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
        (out/('fresh_'+name+'.log')).write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
        report['steps'][name]={'exit_code':run.returncode}
        if name=='tests':
            counts=re.search(r'(\d+) passed(?:, (\d+) skipped)?',run.stdout)
            if counts:report['steps'][name].update(passed=int(counts[1]),skipped=int(counts[2] or 0))
        if run.returncode:
            report.update(status='fresh_CPU_check_failed',failed_step=name)
            (out/'fresh_cpu_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            raise RuntimeError('Fresh CPU check failed: '+name+'; inspect preserved log')
    for relative,item in manifest.items():
        if hashlib.sha256((source/relative).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Source file changed')
    report.update(status='fresh_CPU_reproduction_verified',source_files_unchanged=True)
    (out/'fresh_cpu_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
