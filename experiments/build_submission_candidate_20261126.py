"""Whitelist-only local source release. Never upload, include apps or copy private logs."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXPERIMENTS=(
    'prepare_open_osm_20261126.py','reproduce_reported_metrics.py','model_artifacts.py',
    'prepare_repro_inputs_20261126.py','check_sampled_agreement.py','bind_review_facts_20261126.py',
    'audit_research_evidence_20261125.py','verify_source_values_20261125.py',
    'prepare_evidence_snapshot_20261125.py','fetch_osm_expansion_20261125.py',
    'build_submission_candidate_20261126.py','run_retrieval_snapshot.py','verify_submission_candidate_20261126.py',
    'finalize_sampled_review_20261126.py','reproduce_agreement_summary.py',
    'run_keyword_supplement_20261126.py','reproduce_keyword_supplement.py',
    'finalize_bge_supplement_20261126.py','reproduce_bge_supplement.py',
    'verify_streamed_equivalence_20261125.py','prepare_adjudication_20261126.py','verify_fresh_cpu_20261126.py',
    'finalize_adjudication_20261126.py','reproduce_review_sensitivity.py',
    'run_ai_query_smoke_20261126.py','prepare_assisted_review_20261126.py',
    'prepare_user30_spotcheck_20261127.py','prepare_open_activity_20261127.py',
    'fetch_activity_places_20261126.py','prepare_activity_snapshot_20261126.py',
    'summarize_spotcheck_20261127.py')
BLOCKED_PARTS={'apps','.venv','.cache','.git','__pycache__','labels','queries'}
TOKEN=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{35,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def main():
    out=ROOT/'outputs'/('submission_candidate_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    destination=out/'CPS5801-Research'
    destination.mkdir(parents=True)
    planned={}
    def add(source,target=None):
        source=Path(source);relative=source.relative_to(ROOT)
        if source.is_symlink() or any(part in BLOCKED_PARTS for part in relative.parts):
            raise ValueError('Excluded or linked release input: '+str(relative))
        if source.stat().st_size>5_000_000:raise ValueError('Unexpected large release input')
        body=source.read_bytes()
        if TOKEN.search(body):raise ValueError('Possible secret in candidate file: '+str(relative))
        planned[str(target or relative).replace('\\','/')]=(source,body)
    for path in (ROOT/'src').rglob('*'):
        if path.is_file() and path.suffix in ('.py','.html') and '__pycache__' not in path.parts:add(path)
    for relative in ('src/demo/map.js','src/demo/map.css','src/demo/vendor/leaflet-1.9.4/leaflet.js',
                     'src/demo/vendor/leaflet-1.9.4/leaflet.css','src/demo/vendor/leaflet-1.9.4/LICENSE',
                     'src/demo/vendor/leaflet-1.9.4/PROVENANCE.json'):
        add(ROOT/relative)
    for path in (ROOT/'tests').glob('*'):
        if path.suffix in ('.py','.js') and path.name not in ('test_storage_monitor.py','test_stage5_study_data.py'):
            add(path)
    for name in EXPERIMENTS:add(ROOT/'experiments'/name)
    for name in ('Start-Project.ps1','Start-Demo.ps1','Start-Second-Rater.ps1','Start-Open-Demo.ps1','Start-Review-Demo.ps1','Start-Adjudication.ps1','Start-Assisted-Review.ps1','Start-Query-Intake.ps1','Start-Spotcheck.ps1','Start-Open-Activity-Demo.ps1',
                 'requirements.txt','requirements-gpu.txt','requirements-encoder.txt','requirements-bge-helper.txt',
                 'pytest.ini','LICENSE','AI_DISCLOSURE.md','THIRD_PARTY_NOTICES.md'):
        add(ROOT/name)
    readme=ROOT/'docs/reproducibility_README.md'
    # The public checkout already has this English document at its root.
    add(readme if readme.is_file() else ROOT/'README.md','README.md')
    add(ROOT/'data/README.md')
    for name in ('research_v0_5_draft.json','model_artifacts.json','retain_runtime_20261125.txt','supplemental_analysis_v1_20261126.json','runtime_recorded_20261126.json','keyword_supplement_v1_20261126.json','completed_pilot_v1_20261126.json','completed_reviewed_pilot_v2_20261126.json'):
        add(ROOT/'configs'/name)
    for name in ('response.json','query.overpassql','request.json'):
        add(ROOT/'data/raw/osm_expansion_20261125_get'/name)
    for path in (ROOT/'data/clean/open_osm_v2_20261126').glob('*.json'):add(path)
    for name in ('response.json','query.overpassql','request.json','copyright.html'):
        add(ROOT/'data/raw/osm_activities_20261126'/name)
    add(ROOT/'data/raw/osm_expansion_20261125_get/copyright.html')
    for path in (ROOT/'data/clean/open_activity_v1_20261127').glob('*.json'):add(path)
    add(ROOT/'configs/references_20261127.json')
    add(ROOT/'results/activity_function_20261127.json')
    for name in ('pilot_metric_inputs.json','three_method_function.json','sampled_agreement_summary.json','keyword_supplement_v1_20261126.json','bge_supplement_v1_20261126.json','post_review_sensitivity_v1_20261126.json'):add(ROOT/'results'/name)
    for name in ('submission_checklist_20261126.md','second_rater_20261125.md','FINAL_REPORT_20261126.md','DEMO_GUIDE_ZH.md','REVIEW_AND_AUDIT_20261126.md'):
        add(ROOT/'docs'/name)
    for name in ('CONFERENCE_PAPER_20261127.md','DEFENSE_NOTES_ZH_20261127.md','REFERENCE_READING_ZH_20261127.md'):
        add(ROOT/'docs'/name)
    manifest={}
    for relative,(source,body) in sorted(planned.items()):
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        if actual!=hashlib.sha256(body).hexdigest():raise ValueError('Copy verification failed')
        manifest[relative]={'sha256':actual,'bytes':len(body)}
    ignore='''__pycache__/
.venv/
.cache/
.pytest_cache/
models/
outputs/
apps/
data/labels/
data/queries/
.env
.env.*
*.key
*.pem
*.partial
'''
    (destination/'.gitignore').write_bytes(ignore.encode('utf-8'))
    manifest['.gitignore']={'sha256':hashlib.sha256(ignore.encode()).hexdigest(),'bytes':len(ignore.encode())}
    (destination/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=out/'CPS5801-Research-source.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(destination.rglob('*')):
            if path.is_file():bundle.write(path,arcname=path.relative_to(out).as_posix())
    receipt={'status':'local_source_candidate_built_NOT_published','directory':str(destination),
             'archive':str(archive),'files':len(manifest),'bytes':sum(x['bytes'] for x in manifest.values()),
             'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
             'private_logs_or_apps_included':False,'model_weights_included':False,
             'mixed_source_database_included':False,'fresh_environment_install_verified':False,
             'public_repository_url':None,'independent_research_complete':False,
             'scope':'saved metric arithmetic and OSM-only demo are reproducible; original mixed retrieval is conditional'}
    (out/'build_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (ROOT/'outputs/latest_submission_candidate_20261126.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
