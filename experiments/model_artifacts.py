"""Pinned model acquisition/verification; all paths derived from this checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',choices=['encoder','bge_m3','all'],default='all')
    parser.add_argument('--download',action='store_true',help='Explicitly opt into downloading missing pinned artifacts')
    args=parser.parse_args()
    c_baseline=shutil.disk_usage('C:/').free if os.name=='nt' else None
    def storage_guard():
        if c_baseline is not None:
            current=shutil.disk_usage('C:/').free
            if current<5*1024**3 or c_baseline-current>1024**3:
                raise ValueError('System-drive download protection reached; no automatic retry')
        if shutil.disk_usage(ROOT).free<10*1024**3:
            raise ValueError('Project-drive download protection reached')
    spec=json.loads((ROOT/'configs/model_artifacts.json').read_text(encoding='utf-8'))
    checked=[]
    for key,model in spec['models'].items():
        if args.model not in ('all',key):continue
        directory=(ROOT/model['directory']).resolve()
        if not directory.is_relative_to(ROOT/'models'):raise ValueError('Invalid model destination')
        for row in model['files']:
            target=(directory/row['file']).resolve()
            if not target.is_relative_to(directory):raise ValueError('Invalid model file path')
            if not target.exists() and args.download:
                storage_guard()
                if shutil.disk_usage(ROOT).free<10*1024**3+row['bytes']:
                    raise ValueError('Insufficient project-drive space')
                target.parent.mkdir(parents=True,exist_ok=True)
                partial=target.with_name(target.name+'.partial')
                if partial.exists():raise ValueError('An interrupted partial exists; inspect before retrying')
                url='https://huggingface.co/'+model['id']+'/resolve/'+model['revision']+'/'+row['file']
                with urlopen(Request(url,headers={'User-Agent':'CPS5801-Reproducibility/1'}),timeout=60) as source,partial.open('xb') as output:
                    total=0
                    while block:=source.read(1024*1024):
                        storage_guard()
                        total+=len(block)
                        if total>row['bytes']:raise ValueError('Response exceeds pinned artifact length')
                        output.write(block)
                if partial.stat().st_size!=row['bytes'] or digest(partial)!=row['sha256']:
                    raise ValueError('Pinned download hash mismatch; partial retained')
                partial.rename(target)
            if not target.is_file() or target.stat().st_size!=row['bytes'] or digest(target)!=row['sha256']:
                raise ValueError('Missing or changed model artifact: '+key+'/'+row['file'])
            checked.append(key+'/'+row['file'])
        manifest=directory/'deployment_manifest.json'
        if args.download and not manifest.exists():
            manifest.write_text(json.dumps({'model_id':model['id'],'revision':model['revision'],
                'status':'download_complete_content_verified','files':model['files'],
                'runtime_function_check_completed':False,'source':'configs/model_artifacts.json'},indent=2),encoding='utf-8')
    print(json.dumps({'status':'all_selected_pinned_artifacts_verified','files':len(checked),'models_loaded':False}))


if __name__=='__main__':main()
