# Evidence aware AI place retrieval in Ouhai

A Chinese place-search prototype with keyword overlap, BM25, multilingual MPNet and BGE-M3. The application connects natural-language requests to ranked source records, source details, map markers and external map handoff. It reuses fixed pretrained models; no new model was trained.

Repository: [shile-source/cps5801-ouhai-place-retrieval](https://github.com/shile-source/cps5801-ouhai-place-retrieval).

## Latest evidence on 28 November 2026

The public package contains a reconstructible **114-record OSM corpus**, a frozen **30-query engineering protocol**, **472 raw observation rows** and scripts that recompute every new result table. Keyword, BM25 and BGE share the same four text fields, identifiers and supported-fact filtering rules. The public engineering experiment used one FP16 BGE load on an RTX 4060 Laptop GPU and completed 450 measured searches plus warm-up, cold-start and filter checks.

| Method | Warm backend median ms | Warm backend P95 ms | Exact source-name lookup first |
|---|---:|---:|---:|
| Keyword | 0.121 | 0.161 | 10/10 |
| BM25 | 0.237 | 0.332 | 10/10 |
| BGE-M3 FP16 | 12.298 | 13.992 | 10/10 |

The ten exact names were selected from unique names in the same source corpus. They are an easy software lookup diagnostic, **not 100% real-user recommendation accuracy**. All 30 queries were assistant-authored development requests, not independent human test queries. Five repeats per query-method pair are dependent observations, not 450 independent intents. BGE cold worker loading took 40.585 s, and the first engine call took 45.703 s. Warm backend timing excludes network and browser rendering. See [the complete study](docs/PUBLIC_ENGINEERING_20261128.md) for engine timing definitions, overlap, source coverage and limitations.

Mean top-five Jaccard overlap was 0.7988 for keyword/BM25, 0.2786 for keyword/BGE and 0.3270 for BM25/BGE. Different result sets do not demonstrate better relevance. All 18 explicit-filter checks used common pools; unknown seats or holdings yielded empty results rather than guessed matches. No new human labels, relevance nDCG/MRR/Recall or general effectiveness winner are produced by this study.

## Public CPU installation and demonstration

Recorded environment: Windows 11, Python **3.13.2**, approximately 16 GB RAM. The CPU path needs no CUDA/model files. Use a project location with sufficient space; the author's workspace is on D. Commands below use project-relative paths. All caches and temporary files are set inside the project before imports by `Start-Project.ps1`, which does not change system PATH or paging.

```powershell
git clone https://github.com/shile-source/cps5801-ouhai-place-retrieval.git
cd cps5801-ouhai-place-retrieval
py -3.13 -m venv .venv
.\Start-Project.ps1 -m pip install -r requirements.txt
.\Start-Project.ps1 -m experiments.prepare_open_activity_20261127
.\Start-Project.ps1 -m experiments.prepare_public_study_20261128
.\Start-Project.ps1 -m experiments.reproduce_public_engineering_20261128
.\Start-Open-Activity-Demo.ps1
```

Open `http://127.0.0.1:8779/` on the same machine. Select BM25 or keyword and try `KTV`, `篮球`, `网球` or `公园`. Expected rebuild: 114 records. Source facts: 114 supported names, 113 supported categories and one conflicting category; addresses, seats and holdings remain unknown for all 114 under the archived evidence rules. This is source coverage, not a current facility census. Rebuilding uses included frozen responses and makes **no new source request**. Stop a demo normally before starting another service on its port.

The earlier 39-record open workflow remains available through `experiments.prepare_open_osm_20261126` and `Start-Open-Demo.ps1` on port 8774. It is a separate historical snapshot.

## Optional GPU and fixed pretrained models

Actual inference used **NVIDIA GeForce RTX 4060 Laptop GPU**, PyTorch 2.10.0+cu126, Transformers 4.57.6, Sentence Transformers 5.2.0, Accelerate 1.12.0 and psutil 7.2.2. Batch size is 4 and maximum length 128. Public BGE documents had maximum 81 tokens and no truncation. The course **RTX A5000 is not tested**. The pinned GPU wheel below targets Windows CPython 3.13; Linux/A5000 needs a separately validated environment. Do not replace the recorded runtime silently.

```powershell
.\Start-Project.ps1 -m pip install -r requirements-gpu.txt
.\Start-Project.ps1 -m pip install -r requirements-encoder.txt
.\Start-Project.ps1 -m pip install -r requirements-bge-helper.txt -c configs/retain_runtime_20261125.txt
.\Start-Project.ps1 -m experiments.model_artifacts --download
.\Start-Project.ps1 -m experiments.model_artifacts
```

Download is explicit and several GB; model weights are excluded from Git. Hashes, expected files, sizes and download source are recorded in `configs/model_artifacts.json`:

- [Multilingual MPNet](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2), revision `4328cf26390c98c5e3c738b4460a05b95f4911f5`, Apache-2.0, mean pooling, 768 dimensions.
- [BGE-M3](https://huggingface.co/BAAI/bge-m3), revision `694b61558aea4ae2512ed8d0e189d5cf8adc2259`, MIT, dense CLS only, 1024 dimensions. Sparse and multi-vector branches are not evaluated.

After installation and artifact verification, this explicit command on a **fresh checkout** runs the frozen engineering schedule with one model load and no automatic retry:

```powershell
.\Start-Project.ps1 -u -m experiments.run_public_study_20261128 --fresh-workstation
```

It writes new observations and a summary under `outputs/public_study_20261128`, preserving the shipped paper results. An existing single-run claim prevents an accidental repeat. A fresh-workstation mode does not assert that the author's lifecycle repair was revalidated on a different machine. The original run used the author's validated repair path; the later public preflight/output-routing change did not alter the model or measured loop. Saved arithmetic is validated in a clean source copy without a model; a fresh-install GPU/A5000 run is not claimed.

For interactive AI on the public corpus, stop the CPU service and run:

```powershell
.\Start-Project.ps1 -m src.demo.server --port 8779 --corpus data/clean/open_activity_v1_20261127/poi_candidates.json --facts-binding configs/open_activity_study_binding_20261128.json --enable-bge --safe-streaming --dense-precision float16 --dense-idle-seconds 60 --stop-checkpoint outputs/open_activity_runtime_stop.json
```

Select BGE explicitly. Healthy models release after 60 idle seconds and load again on the next explicit query. C must have at least 5 GiB free, D at least 10 GiB, and an active model must not cause an observed C decline over 1 GiB. Failed workers stop without automatic retry. Do not erase failure checkpoints to bypass a stop. Project files on D do not prevent Windows paging growth on C. No system/paging/partition change is part of this reproduction. Historical research used FP32; current FP16 can change numerical scores and ranks.

## Human evaluation and source-version boundaries

The local product catalogue contains **151 source records**, covering reading, culture, parks, retail, dining, KTV, cinemas, fitness and sports. It includes 37 mixed government-source records not distributed publicly while redistribution compatibility remains unresolved. `Start-Demo.ps1` therefore requires author-workspace data. Source-record counts do not establish unique independently verified destinations. The public 114-record data are an OSM-only subset, not a transfer of old human labels.

Historical evaluation used 49 records and eight exposed convenience queries. The original 392 decisions comprise 349 numeric grades and 43 unknowns, including 23 disclosed AI-assisted corrections. Only one named query originally qualified under the frozen complete-judgment rule. A locked 12-case author review leaves 352 numeric and 40 unknown judgments, with **zero eligible final queries**. Historical numbers are preserved rather than promoted into a final recommendation-effectiveness claim.

A separate post-publication 80-pair second-rater audit yields 67/71 exact agreements (94.4%) and linear weighted kappa 0.8754385965 on the UI-origin numeric subset. The sensitivity group including assisted corrections has 68/74 exact and kappa 0.8423855165. This sampled audit is not full independent dual annotation. Recompute the anonymized arithmetic without source text or participant logs:

```powershell
.\Start-Project.ps1 -m experiments.reproduce_reported_metrics
.\Start-Project.ps1 -m experiments.reproduce_keyword_supplement
.\Start-Project.ps1 -m experiments.reproduce_bge_supplement
.\Start-Project.ps1 -m experiments.reproduce_agreement_summary
.\Start-Project.ps1 -m experiments.reproduce_review_sensitivity
```

The user's private 30 requests are separate from the new public AI-authored 30 engineering requests. Conservative assistant-written rules generated 4,530 development suggestions over the local151 catalogue, including 2,990 unknowns. A fixed two-record-per-query sample forms a 60-pair assisted human spotcheck. The last read-only check found 1/60 saved and an unlocked task. The 4,470 unreviewed pairs never become human labels. The summary command refuses incomplete/unlocked sessions. No unperformed human action or independent authorship is asserted.

## Implementation and configuration

- `src/data`: OSM import, source SHA bindings, field evidence, category and unknown handling.
- `src/retrieval`: keyword, BM25, dense models, common filters and GPU exclusion.
- `src/evaluation`: ranking arithmetic, sampled agreement, public engineering summaries and spotcheck safeguards.
- `src/demo`: loopback map application and separately protected participant pages.
- `configs`: model hashes, dependency constraints, frozen protocols, queries and source binding.
- `data/raw` and `data/clean`: redistributable OSM responses and reconstructed snapshots.
- `experiments`: preparation, bounded inference and saved-result reproduction commands.
- `results`: numerical evidence and public raw engineering observations.
- `docs`: manuscript, source verification records, defense notes and submission checklist.

All methods concatenate `name`, `category`, `address` and `description` in the same order. Keyword counts distinct shared Jieba tokens; BM25 uses k1=1.5, b=0.75 and epsilon=0.25. Stable source IDs break ties. Dense methods normalize vectors and use dot products. Scores across methods are not comparable probabilities. User-confirmed hard filters apply the same supported-fact pool, while soft preferences stay in the query. The limited condition helper does not claim arbitrary language understanding or current facility verification.

No local training, fine-tuning, train/validation optimization or trained checkpoint is claimed. Pretrained inference, document indexing and evaluation replace the training step for this project. Source-constructed exact-name references are automatic lookup diagnostics, not human grades. No final reviewed nDCG, MRR, Recall or confidence interval is fabricated for missing independent judgments.

## Checks and deliverables

```powershell
.\Start-Project.ps1 -m pytest -q
.\Start-Project.ps1 -m pip check
```

Synthetic fixtures exist only in tests. A clean source copy verifies frozen data reconstruction, all saved arithmetic and tests using existing dependencies. A prior isolated fresh CPU environment verified the historical CPU workflows; this does not assert a new full GPU installation.

Latest manuscript: [Conference paper](docs/CONFERENCE_PAPER_20261128.md). [Chinese defense notes](docs/DEFENSE_NOTES_ZH_20261128.md). [Submission checklist](docs/submission_checklist_20261126.md). The student must personally read and verify the 15 scholarly references, understand the implementation, check the results and defend the work. Teacher approval, course-platform submission and a particular grade are not asserted.

## Data, software and AI attribution

OSM attribution: **© OpenStreetMap contributors**, [copyright and attribution](https://www.openstreetmap.org/copyright), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Raw responses, acquisition requests, evidence and source hashes are included. Follow ODbL obligations for redistribution. Code is licensed separately under `LICENSE`; external software remains under its original terms, including Leaflet BSD-2-Clause.

See `AI_DISCLOSURE.md` and `THIRD_PARTY_NOTICES.md`. Codex/ChatGPT substantially assisted code, study queries, source inspection, tests, documents and slides. Source reading by the assistant does not mean the student read the papers. Credentials, personal applications, participant action logs, private query payloads, caches and model weights are excluded. Photographs, current business status, verified entrances and internal route optimization are outside the demonstrated capability. External street tiles failed in the inspected browser; source cards, markers and external-map links still work when the street background is absent.
