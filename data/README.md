# Data preparation and expected inputs

## Current public OSM activity demonstration

`python -m experiments.prepare_open_activity_20261127` deterministically rebuilds114 source records from the archived39-element and75-element OSM responses. New raw input: `raw/osm_activities_20261126/response.json`, SHA256 `cb09ac68fc9cc1cccbe1b1c9c781fb2c019988257318c602afb3bfc6e4479426`. The accompanying query, request record and copyright evidence retain timestamps, ODbL and attribution. Output: `clean/open_activity_v1_20261127/{poi_candidates,field_evidence,source_manifest}.json`. Source IDs are unique across these two batches; this is not independent physical-entity deduplication. No human labels are created, no new network request is made, and the mixed151 catalogue is not reconstructed by this public path. Run `Start-Open-Activity-Demo.ps1` for CPU lexical search at8779.

## Historical open reproducible demonstration

`raw/osm_expansion_20261125_get/response.json` is the frozen39-element response, SHA256
`90efae32c8e941f38c2ba72439ae75ee20754761d836e6c1dc32787f0ad7d150`.
The matching `query.overpassql` and `request.json` record the Overpass endpoint, relation3289417 area selector, time and bounded acquisition. Source date2026-11-25T10:56:32Z. Query-derived administrative inclusion is not independent geographic verification.

Run `python -m experiments.prepare_open_osm_20261126` from the checkout root, with the documented project environment. Expected output:

```
data/clean/open_osm_v2_20261126/
  poi_candidates.json      # 39 source records, not verified distinct entities
  field_evidence.json
  source_manifest.json
```

Attribution: © OpenStreetMap contributors. Database license: [ODbL1.0](https://opendatacommons.org/licenses/odbl/1-0/); [OSM copyright](https://www.openstreetmap.org/copyright). This dataset contains only OSM-derived database contents and is separately licensed from project software. Missing facts remain missing; source centers are not entrances. No human labels are attached to this demonstration.

## Original local evaluation: conditional full reproduction

The evaluated mixed49-record snapshot is `clean/pilot_mixed_v0_3_osm_20261031/poi_candidates.json`, SHA256
`000f0f988560f4bc1cc195c743b4d0c85016c50d92b25379dc3aaab16daf44fd`.
The later54-record snapshot has SHA256 `acf2b201793d799fb5e2a75688c57ddcd0501580e8259a7356d07a2aa4775e61`.
The later76-record development snapshot has SHA256 `b96ebb2e68a22b4b905e410e2750934edc1737d2f8eb5f49d05992d47da9efe5`.
They must not be substituted for one another or silently assigned the original labels.

Sources include Wenzhou reading-facility dataset13759 ([landing page](https://data.wenzhou.gov.cn/jdop_front/detail/data.do?iid=13759), [CSV endpoint](https://data.wenzhou.gov.cn/jdop_front/resource/data/download.do?fileType=csv&iid=13759)), older/fresh OSM snapshots, manually captured official evidence and a2026 Ouhai library notice. The original saved CSV has SHA256 `c8e8661c9a4539c7bd91b63e0f81ed16d82d142438ad4c2c5e48510a4b986791`; it may no longer match a newly downloaded current file. Stop on a mismatch rather than altering dates, evidence or labels to force reproduction.

Mixed-source public redistribution compatibility is unresolved, so these full corpora/source HTML, private action logs and participant files are excluded from the source-release candidate. Source URLs and identifiers do not guarantee that every historical file remains downloadable without access restrictions. A lawfully obtained copy of all exact original inputs is required for a full acquisition/preprocessing/inference rerun; the public bundle alone cannot reconstruct those missing historical inputs. This is an explicit reproducibility limitation, not a passed fresh-clone test.

With the author's preserved local input tree, source processing is implemented in `experiments/prepare_evidence_snapshot_20261125.py`, `audit_research_evidence_20261125.py`, `verify_source_values_20261125.py` and `bind_review_facts_20261126.py`. These scripts expect recorded evidence and frozen earlier snapshots; inspect their prerequisites before running. The source importer is `src/data/osm_import.py`; field extraction is `src/data/evidence_facts.py`. Text normalization is shared by all retrieval methods.

The original published metric arithmetic can be reproduced without redistributing POI text or participant identifiers using `results/pilot_metric_inputs.json` and `python -m experiments.reproduce_reported_metrics`. This does not replace full retrieval reproduction.

## Human data

The append-only original392-pair session and later80-pair supplemental sample remain separate. Unknowns are never zero. The original scoring version is locked. A new candidate dataset has no automatic right to reuse old judgments. Real participant ratings are not included in the open OSM dataset. Synthetic fixtures remain inside tests and are never concatenated into a real corpus.
