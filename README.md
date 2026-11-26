# CPS5801: source-text place retrieval

Public source repository: [shile-source/cps5801-ouhai-place-retrieval](https://github.com/shile-source/cps5801-ouhai-place-retrieval).

This repository implements a Chinese place-search prototype for Ouhai, Wenzhou, comparing BM25, a multilingual Sentence Encoder and BGE-M3 dense retrieval under shared text fields. It uses pretrained inference; **there is no model-training stage or newly trained checkpoint**. The map is an application demonstration, not independent evidence of current operations, entrances or district membership.

## Evidence and scope

**Latest author review:** all 12 follow-up cases are complete and locked (9 numeric, 3 unknown). Applying these separate author decisions leaves 352 numeric and 40 unknown pairs in the revised392-pair packet. No query remains fully judged under the unchanged rule. Consequently this reviewed version reports **no final numeric effectiveness comparison**. The numeric tables below preserve the historical original-label results.

The completed preliminary evaluation used 49 source records and eight AI-assisted convenience queries. Of 392 handled pairs, 349 had numeric grades and 43 were explicitly unknown. The frozen complete-judgment rule admitted **only P02**, a named-place query. Seven queries were excluded rather than treating unknowns as zero. The original packet contains 23 latest judgments from user-requested AI-assisted corrections; it is not independent human ground truth.

| Method | Eligible queries | nDCG@5 | P@3 | Full-ranking MRR | Recall@5 |
|---|---:|---:|---:|---:|---:|
| BM25 | 1 | 0.9241332080 | 0.3333333333 | 1 | 1 |
| Multilingual Sentence Encoder | 1 | 0.7262287618 | 0.3333333333 | 1 | 1 |

These original results do not establish general semantic-search superiority. A separately declared post-publication supplement on the same fully judged P02 query gives keyword overlap nDCG@5 **0.9515234566** and BGE-M3 **0.7262287618**; both P@3=1/3, MRR=1 and Recall@5=1. The original two-method publication remains unchanged. Read `docs/FINAL_REPORT_20261126.md` for results, timing, error analysis and limitations. The later second-rater task is a frozen80-pair sample, ten pairs per query, added after original result publication. All80 are handled (78 numeric,2 unknown). The UI-origin first-rater subset has71 numeric pairs,67 exact agreements (94.4%), linear weighted kappa0.8754 and quadratic weighted kappa0.8851. Including assisted first-rater corrections gives74 numeric pairs,68 exact agreements (91.9%), linear kappa0.8424 and quadratic kappa0.8649. Six unknown pairs are excluded from the original agreement calculation. The resulting12-case queue was subsequently reviewed by the original first rater with access to both opinions; all12 are handled, including3 explicit unknowns. That separate author review is not independent blind adjudication, and pre-review kappa is not recalculated after aligning decisions. This is descriptive sampled consistency evidence, not full dual annotation or a new held-out test. The 76-record development corpus and open 39-record demonstration below are distinct from the 49-record evaluated corpus. The original 150–200-place / held-out-query study plan was not achieved.

## Repository structure

- `src/data`: source import, evidence checks, shared place representation.
- `src/retrieval`: BM25, multilingual dense model, BGE-M3, explicit source constraints.
- `src/evaluation`: strict ranking metrics, weighted kappa, query bootstrap and sampled agreement.
- `src/demo`: local bilingual UI, source-point preview, external route hand-off, separate rater pages.
- `experiments`: bounded acquisition, preprocessing, reproducibility and evaluation entry points.
- `configs`: model identities, exact artifact hashes and experimental drafts.
- `data/raw/osm_expansion_20261125_get`: frozen OSM response, request provenance and query.
- `results`: anonymous inputs sufficient to recompute published metric arithmetic; functional-check evidence.
- `tests`: synthetic functional/regression fixtures. Synthetic fixtures are not research observations.

## Hardware and software

Verified environment: Windows x64, Python 3.13.2, NVIDIA RTX 4060 Laptop GPU with 8GiB VRAM, driver 572.83, Torch 2.10.0+cu126, Transformers 4.57.6, Sentence-Transformers 5.2.0. Versions are pinned in the requirements files. GPU inference uses batch4, max_length128 and FP32. Current 76-record functional inputs had maximum103 document tokens and no truncation; this must be rechecked for changed inputs. The implementation streams original checkpoint tensors to one GPU worker at a time to reduce Windows staging pressure.

The course RTX A5000 is a deployment target, **not a tested device in this submission**. Linux/A5000 installation and inference have not been executed. The checked-in GPU wheel URL is specifically for Windows CPython3.13; use an official platform-appropriate PyTorch build on a different OS and record the resulting environment as a new validation.

## Installation

Clone the public repository, then enter its root:

```powershell
git clone https://github.com/shile-source/cps5801-ouhai-place-retrieval.git
cd cps5801-ouhai-place-retrieval
```

```powershell
py -3.13 -m venv .venv
.\Start-Project.ps1 -m pip install -r requirements.txt
.\Start-Project.ps1 -m pip install -r requirements-gpu.txt
.\Start-Project.ps1 -m pip install -r requirements-encoder.txt -r requirements-bge-helper.txt
.\Start-Project.ps1 -m pip check
```

`Start-Project.ps1` sets caches and temporary directories inside this checkout **before imports**, with process-local thread limits. It does not change system PATH, paging or installed Python. Installation commands describe fresh setup; the author's working environment must not be recreated automatically. GPU requirements are unnecessary for the saved metric-arithmetic check or BM25-only open demonstration.

## Reproduce the published metric arithmetic, without a GPU

```powershell
.\Start-Project.ps1 -m experiments.reproduce_reported_metrics
```

Expected output: `published_metric_arithmetic_reproduced`, two rows with the table values above, one eligible query and seven excluded queries. `results/pilot_metric_inputs.json` uses anonymous symbolic candidate IDs, the complete saved rankings and actual grades. This checks the reported arithmetic; **it is not a rerun of acquisition, encoding or retrieval**. Input corpus/packet/publication hashes link it to the preserved local experiment. No new relevance labels or model outputs are invented.

## Reproduce the supplemental sampled agreement arithmetic

```powershell
.\Start-Project.ps1 -m experiments.reproduce_agreement_summary
```

Expected output: `aggregate_agreement_arithmetic_reproduced`, primary n=71 with linear kappa0.8754385965, sensitivity n=74 with linear kappa0.8423855165. Input is `results/sampled_agreement_summary.json`, containing anonymous3x3 contingency matrices and explicit provenance groups. No participant identities, individual action logs or POI texts are required for this arithmetic check. Both groups were also independently verified with scikit-learn in the local evidence audit. This does not turn the sample into full dual annotation or authenticate participant independence.

## Rebuild and run the open-data demonstration

```powershell
.\Start-Project.ps1 -m experiments.prepare_open_osm_20261126
.\Start-Open-Demo.ps1
```

Open http://127.0.0.1:8774/ on the same machine. Expected corpus size:39 source records, rebuilt from the included frozen response dated2026-11-25. BM25 and browsing are available; models are paused by default. Stop the service before restarting on the same port. Current OSM query results may differ; use the frozen response to reproduce this snapshot. OSM ways/relation centers are bounding-box centers, not verified entrances. No photograph, real-time opening or route completion is guaranteed.

The open OSM data is separate from the mixed government/OSM corpus. Attribution: **© OpenStreetMap contributors**; database license: [ODbL1.0](https://opendatacommons.org/licenses/odbl/1-0/), [source copyright and attribution](https://www.openstreetmap.org/copyright). No government-source texts or private software data are bundled into this open dataset.

## Obtain and verify fixed pretrained models

Model identifiers, revisions, file sizes and hashes are in `configs/model_artifacts.json`:

- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, revision `4328cf26390c98c5e3c738b4460a05b95f4911f5`, 768 dimensions, published mean pooling; [model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2), Apache2.0.
- `BAAI/bge-m3`, revision `694b61558aea4ae2512ed8d0e189d5cf8adc2259`, 1024 dimensions, published CLS pooling, dense only; [model card](https://huggingface.co/BAAI/bge-m3), MIT.

```powershell
.\Start-Project.ps1 -m experiments.model_artifacts --download
.\Start-Project.ps1 -m experiments.model_artifacts
```

Downloading is explicit and potentially several GB. The verifier alone never downloads or loads a model. Failed downloads remain partial and are not automatically retried. Models are not included in the repository. Existing local checks are reported separately from general effectiveness. Never restart a failed model just to bypass a guard.

The explicit snapshot runner defaults to BM25 and can be used without the HTTP interface:

```powershell
.\Start-Project.ps1 -m experiments.run_retrieval_snapshot --method bm25 --query 公园
```

For a separately authorized GPU run on a prepared machine, select `--method encoder` or `--method bge_m3` and add `--allow-model-inference`. The parent supervises only its own worker, retains source/output hashes, enforces system-drive5GiB/project-drive10GiB and1GiB system-drive decline guards, and never retries. No dense run of this new runner or Linux/A5000 validation is claimed. Do not use it to bypass an existing stopped model.

## Original mixed corpus and full local workflow

The exact 49/76-record mixed corpora and source evidence are not bundled for public redistribution: government-source redistribution compatibility remains unresolved. `data/README.md` gives source identifiers, expected hashes, preparation steps and limitations. Public readers can reproduce the saved arithmetic and OSM demonstration; **full original retrieval reproduction remains conditional on lawfully obtaining the exact missing mixed inputs**. Do not claim this conditional path has passed a fresh-clone end-to-end test.

For the author's preserved local workspace only:

```powershell
.\Start-Project.ps1 -m experiments.audit_research_evidence_20261125
.\Start-Project.ps1 -m experiments.bind_review_facts_20261126
.\Start-Review-Demo.ps1
.\Start-Second-Rater.ps1
.\Start-Project.ps1 -m experiments.check_sampled_agreement
```

These commands must not replace or modify frozen labels. The agreement command waits for all80 handled pairs, preserves unknowns, reports human-only and assisted sensitivity groups, and leaves final adjudication blank. The rater page cannot call models or show ranking results. Arbitrary new data do not inherit old human labels.

## Evaluation configuration and limitations

All methods use `name/category/address/description` in the same order. BM25 uses jieba, k1=1.5, b=0.75, epsilon=0.25; ties are resolved by stable POI ID. Dense scores are normalized embedding dot products. Raw scores are not comparable across models. nDCG uses gain2^grade−1; binary relevance threshold2; P@3 divides by3; full MRR requires a full candidate ordering. Unknown grades exclude the query under the original frozen protocol. Shared intersections are used for model comparisons.

Optional **explicitly confirmed hard conditions** use the same eligible pool for every method; unknown source facts do not pass. Soft preferences remain in the query and are not silently converted into filters. The interface does not claim arbitrary natural-language interpretation or independent present-day fact verification.

A limited rule-based helper can suggest explicit category and Arabic-integer minimum-count conditions from Chinese text after a user clicks its control. Suggestions fill visible fields for inspection before retrieval; preference language, conflicting counts, unsupported attributes and unrecognized expressions are not silently resolved. The76-record review interface has an actual browser-checked BM25 example: seats>=40 yields11 source-supported eligible records,54 unknown and11 unmet. No new GPU inference or relevance metric is implied by this application check.

The independent held-out query plan, full data identity/geographic review, broader three-method effectiveness comparison and independent human adjudication are not replaced by test success. A single eligible query cannot support a useful query-bootstrap generalization claim. Code for uncertainty estimation is provided without fabricating a confidence interval for missing experiments.

### Latest local model availability (26 November)

Earlier changed checks stopped under the unchanged system-drive guard. A subsequent authorized material fix constructs all model tensors on the meta device, restores only the standard generated ID buffers and copies checkpoint slices of at most16MiB to the GPU. The synthetic CLS/mean parameter and output equivalence checks passed with zero observed differences. The real original49-record FP32 BGE check then passed: the largest C-drive decline was393,216bytes, with unchanged5GiB/10GiB free-space and1GiB decline limits. The complete P02 ranking was saved and scored separately; no new grades were created. Kernel GPU exclusion remains active. Successful current checks do not guarantee future desktop memory conditions, and a failed future worker still stops without automatic retry.

### Reproduce supplementary metric arithmetic

```powershell
.\Start-Project.ps1 -m experiments.reproduce_keyword_supplement
.\Start-Project.ps1 -m experiments.reproduce_bge_supplement
.\Start-Project.ps1 -m experiments.run_retrieval_snapshot --method keyword --query 公园
```

The first two commands use public anonymous rankings and actual frozen grades. The last runs the new keyword baseline on the open39-record snapshot, without a GPU. These are post-publication exploratory supplements, not an independent held-out test. `configs/keyword_supplement_v1_20261126.json` records the untuned score definition and timing schedule. `results/*supplement*.json` preserve numerical evidence; no source text or participant logs are added.

## Verification, attribution and AI disclosure

```powershell
.\Start-Project.ps1 -m pytest -q
.\Start-Project.ps1 -m pip check
```

See `AI_DISCLOSURE.md` and `THIRD_PARTY_NOTICES.md`. The implementation was developed with substantial AI assistance; submitted teaching-example queries and corrections are disclosed. Students must understand the implementation and explain all reported experiments. Test-generated synthetic grades exist only in tests. Personal files, participant action logs, credentials, installed applications, caches and large model weights must not be published.

## Reproduce the completed author review sensitivity

```powershell
.\Start-Project.ps1 -m experiments.reproduce_review_sensitivity
```

Expected status: `post_review_exclusion_reproduced_without_imputation`. All four saved P02 rankings are excluded because the reviewed judgments include an unknown. There is no numeric post-review effectiveness result. `results/post_review_sensitivity_v1_20261126.json` contains anonymous revised P02 grades and aggregate coverage; personal decision logs and free-text reasons remain private. The original tables and original agreement matrices retain their pre-review versions.

## Fresh CPU environment verification

An isolated D-drive environment was created using the existing Python 3.13.2 and exact `requirements.txt` from official PyPI, with no system-site packages, user packages or Torch. On the audited source snapshot,332 tests passed and1 historical-data test was skipped; saved arithmetic, open39-record rebuilding and actual keyword/BM25 search passed. Later added review-sensitivity checks are separately verified. This is fresh CPU workflow evidence only. It does not validate a fresh CUDA installation, school A5000 or original mixed-data end-to-end retrieval. See `docs/REVIEW_AND_AUDIT_20261126.md` for scope and the source-copy verifier.
