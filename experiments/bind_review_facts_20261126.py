"""Freeze source fact hashes for explicit application filtering; no research labels."""
import json
from pathlib import Path
from src.data.fact_store import digest,load_bound_facts

ROOT=Path(__file__).resolve().parents[1]


def main():
    corpus=ROOT/'data/clean/research_review_v0_5_20261125/poi_candidates.json'
    facts=ROOT/'outputs/evidence_audit_20261125/source_facts.json'
    values=json.loads(facts.read_text(encoding='utf-8'))
    evidence={}
    for fields in values.values():
        for fact in fields.values():
            for row in fact.get('evidence',[]):
                relative=row['raw_path'];actual=digest(ROOT/relative)
                if actual!=row['raw_sha256']:raise ValueError('Source evidence no longer matches')
                evidence[relative]=actual
    spec={'scope':'source_snapshot_only','corpus_sha256':digest(corpus),
          'facts_path':str(facts.relative_to(ROOT)).replace('\\','/'),'facts_sha256':digest(facts),
          'evidence_sha256':evidence,'formal_research_freeze':False}
    output=ROOT/'configs/research_v0_5_facts_binding.json'
    if output.exists() and json.loads(output.read_text(encoding='utf-8'))!=spec:
        raise ValueError('Existing binding differs; preserve and version instead of overwrite')
    output.write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    loaded=load_bound_facts(output,corpus,ROOT)
    print(json.dumps({'binding':str(output),'candidates':len(loaded),'raw_sources_checked':len(evidence)}))


if __name__=='__main__':main()
