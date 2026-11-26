"""Validate a clean source copy using existing dependencies, without models or labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('candidate',type=Path);args=parser.parse_args()
    candidate=args.candidate.resolve()
    if not candidate.is_relative_to(ROOT/'outputs') or candidate.name!='CPS5801-Research':
        raise ValueError('Only a local generated submission candidate can be validated')
    manifest=json.loads((candidate/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    for relative,item in manifest.items():
        path=(candidate/relative).resolve()
        if not path.is_relative_to(candidate) or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Release file hash mismatch')
    for variable in ('TEMP','TMP','HF_HOME','TORCH_HOME'):
        if not Path(os.environ.get(variable,'')).resolve().is_relative_to(ROOT):
            raise ValueError('Use Start-Project.ps1 to keep validation caches in the project')
    origin_check='import pathlib,src.demo.server,experiments.reproduce_reported_metrics; r=pathlib.Path.cwd(); assert all(pathlib.Path(m.__file__).resolve().is_relative_to(r) for m in (src.demo.server,experiments.reproduce_reported_metrics)); print("candidate_source_origin_verified")'
    steps=[('module_origin',['-c',origin_check]),('tests',['-m','pytest','-q','--tb=short']),
           ('metrics',['-m','experiments.reproduce_reported_metrics']),
           ('agreement',['-m','experiments.reproduce_agreement_summary']),
           ('open_data',['-m','experiments.prepare_open_osm_20261126']),
           ('bm25',['-m','experiments.run_retrieval_snapshot','--method','bm25','--query','公园'])]
    results={}
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(candidate))
    for label,arguments in steps:
        done=subprocess.run([sys.executable,*arguments],cwd=candidate,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
        (candidate.parent/(label+'_verification.log')).write_text(done.stdout+'\n'+done.stderr,encoding='utf-8')
        results[label]={'exit_code':done.returncode}
        if label=='tests':
            counts=re.search(r'(\d+) passed(?:, (\d+) skipped)?',done.stdout)
            if counts:results[label].update(passed=int(counts[1]),skipped=int(counts[2] or 0))
        if done.returncode:raise ValueError('Source candidate verification failed: '+label)
    for relative,item in manifest.items():
        if hashlib.sha256((candidate/relative).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Rebuild changed a frozen release file')
    report={'status':'clean_source_copy_verified_with_existing_dependencies','steps':results,
            'fresh_dependency_install':False,'new_model_inference':False,'new_human_labels':0,
            'source_files_unchanged':True,'public_repository_published':False,
            'scope':'symbolic published metric arithmetic and open OSM data/BM25 workflow; not original mixed retrieval'}
    (candidate.parent/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'directory':str(candidate),**report}))


if __name__=='__main__':main()
