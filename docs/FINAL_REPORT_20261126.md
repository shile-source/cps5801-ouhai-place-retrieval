# Source-Text Place Retrieval in Ouhai: A Reproducible Prototype and Preliminary Evaluation

**Reviewed Pilot report, 26 November 2026. Author: Shi LeTian.** The original first rater has completed and locked all 12 follow-up cases: 9 numeric decisions and 3 explicit unknowns. This was post-publication author review with access to both prior opinions, not independent third-rater blind annotation. Public source repository: https://github.com/shile-source/cps5801-ouhai-place-retrieval. Implementation and writing assistance are disclosed in `AI_DISCLOSURE.md`.

## Abstract

The completed engineering prototype supports four shared-field retrieval methods, source constraints and a bilingual interface. Final author review demonstrates an important evidence limitation: the reviewed label version has no fully judged query under the unchanged complete-judgment rule, so it supports no final numeric model-effectiveness comparison. The earlier numeric results below are historical results on the preserved original labels.

This project implements a Chinese natural-language place-search prototype using BM25, a multilingual Sentence Encoder and BGE-M3 dense retrieval over shared source-text fields. The user interface separates textual relevance from unverified geographic, operational and experiential claims. A completed preliminary annotation packet covered49 source records and 8 convenience queries. Of392 handled query-record pairs, 349 received numeric relevance grades and 43 were explicitly unknown. Under the frozen complete-judgment protocol, only one named-place query was eligible for effectiveness analysis. BM25 and the multilingual encoder obtained nDCG@5 values of 0.9241 and 0.7262 respectively on that query. These observations do not establish general superiority across query types. A separately declared post-publication supplement added unweighted keyword overlap and BGE-M3 on the same fully judged query, obtaining nDCG@5 of 0.9515 and 0.7262 respectively. The original publication was preserved. These exploratory supplements use the original pre-review labels; they do not supply final post-review effectiveness estimates. An 80-pair supplemental second-rater audit, introduced after initial result publication, was completed. Among 71 numeric pairs whose latest first-rater judgments were UI-origin,67 agreed exactly (94.4%); linear weighted kappa was0.875 and quadratic weighted kappa was0.885. These are descriptive post-publication consistency results, not an independent held-out effectiveness study. Reproduction materials distinguish saved metric arithmetic, an openly redistributable OSM-only demonstration and conditional reconstruction of the original mixed-source experiment.

## 1. Research problem and scope

Users may describe a desired place through its name, an intended activity or several preferences. Lexical overlap can identify named entities but may miss natural-language paraphrases; embedding similarity offers a different ranking signal. This motivates a controlled comparison without assuming that a larger semantic model must win. The research question is whether the methods differ in source-text relevance under the same corpus, text fields, queries and evaluation rules. Map display and external routing are application features rather than the central effectiveness outcome.

The original plan aimed at 150–200 places, distinct development and held-out test queries, multiple retrieval methods and independent dual judgments. The completed evidence is smaller:49 evaluated source records,8 exposed AI-assisted convenience queries and one fully judged eligible query. Later engineering snapshots contain 54 and 76 records but do not inherit old judgments. They must not be described as an enlarged evaluated benchmark. A source record is not necessarily a unique independently verified real-world entity.

## 1.1. Related work

Robertson and Zaragoza's probabilistic relevance framework provides the lexical foundation for the BM25 baseline. Reimers and Gurevych(2020) study multilingual sentence representations through teacher–student transfer across translated sentences; this provides background for using an existing multilingual sentence encoder here, not evidence that the present project performed distillation or reproduced their training. Chen et al.(2024) combine dense, sparse and multi-vector retrieval signals in a self-knowledge-distillation approach for M3-Embedding. The current project intentionally evaluates only the released dense component. Neither paper's benchmark results are transplanted into the local Ouhai task, and using a released checkpoint is distinct from implementing its original training pipeline.

## 2. Sources and evidence model

The local mixed snapshots combine Wenzhou public reading-facility records, OpenStreetMap elements and subsequent official-source evidence. Each imported value is associated with source identifiers, dated acquisition information and content hashes. Missing quantities are not inferred from a place name or facility type. The76-record development evidence audit links all records to source evidence;37 have supported addresses and 22 have supported seat and book counts. Eight potential duplicate pairs remain flagged for identity review.

The source-text task is deliberately narrower than a real-world recommendation guarantee. A recorded opening time does not establish current opening. A park tag does not establish quietness, seating or suitability for study. A way/relation center is a bounding-box center rather than a verified entrance. Some original coordinates are anomalous and were not silently repaired. District identity, point location, present operations and accessibility require further independent verification.

Mixed-source public redistribution compatibility is unresolved. The open reproducibility materials therefore use a separate frozen OSM-only39-record demonstration under ODbL attribution, without silently replacing the original evaluated dataset. The original mixed-data full retrieval path is conditional on lawful access to its exact historical inputs.

## 3. Methods and implementation

The unweighted keyword baseline counts distinct shared Jieba tokens, without frequency or IDF weighting. It shares the BM25 tokenizer, uses no stop-word list and retains zero-overlap candidates for complete ordering; ties use the same stable identifier rule. This baseline was added after the original publication, with its definition frozen before supplemental execution.

All retrieval methods concatenate the same nonempty `name`, `category`, `address` and `description` fields in that order. BM25 uses jieba segmentation, k1=1.5, b=0.75 and epsilon=0.25. Dense methods use normalized embeddings and dot-product cosine similarity; ties use stable source-record identifiers. Raw scores from different models are not interpreted as comparable probabilities.

The multilingual encoder is `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, pinned to revision`4328cf26390c98c5e3c738b4460a05b95f4911f5`, with 768-dimensional output and its published mean-pooling configuration. BGE-M3 is pinned to revision`694b61558aea4ae2512ed8d0e189d5cf8adc2259`, with 1024-dimensional dense CLS output. Sparse and multi-vector BGE outputs, hybrid retrieval and new model training are outside the reported implementation. Pretrained model work and installed libraries are attributed rather than presented as student-created algorithms.

The current local functional configuration uses FP32, batch 4 and maximum length128. For the 76-record functional corpus, the maximum observed document token length was103, with zero truncated documents. A Windows-specific streamed loader instantiates the published backbone and validates tensor names/shapes before assigning original weights to the GPU one tensor at a time. The original pooling/module graph is respected; supported legacy position buffers must match generated buffers exactly. A tiny synthetic CLS numerical check produced identical parameters and vectors, but this is not a complete real-checkpoint equivalence proof. Some ordinary loading strategies and a later supplemental synthetic attempt stopped under unchanged storage guards. The prototype does not automatically retry a stopped model or change system paging.

Hard conditions and soft preferences are treated separately. Explicit, user-confirmed conditions share one candidate pool across methods. Unknown source facts do not pass a hard filter. A limited inspectable rule-based helper proposes supported category and Arabic-integer minimum-count conditions; it does not claim arbitrary natural-language understanding. Preference language and unsupported experiential or real-time requirements are not silently promoted to hard conditions. This new engineering feature does not retrospectively alter the published Pilot protocol.

## 4. Preliminary evaluation protocol

The original packet contained 49 records crossed with 8 queries, covering names, semantic expressions and multiple preferences. Query design and some conversational guidance were AI-assisted and exposed, so this is a convenience Pilot rather than an independent held-out study. Relevance grades were0,1 or2. Insufficient evidence was stored as unknown instead of grade0. Numeric thresholds of 40 seats and 12,000 books applied only to the corresponding predefined preference queries.

The original frozen complete-judgment rule excludes any query with unknown candidate grades. nDCG@5 uses exponential gain2^grade−1. Binary relevance uses grade2. Precision@3 divides by3 even when fewer positions are returned. Full MRR requires the entire shared candidate ordering. Recall@5 is defined only with a fully judged candidate pool and a nonempty relevant set. Model comparisons use identical eligible-query intersections.

The user published the original result before adding the second rater. The append-only original log contains 349 numeric judgments and 43 unknowns; its latest392 judgments include369 UI-origin entries and 23 user-requested AI-assisted corrections. The frozen version remains locked. This provenance prevents an independent-human-ground-truth claim.

## 5. Historical results on original frozen labels

Before follow-up author review, only P02, a named-place query, had complete numeric judgments for all 49 candidates. Seven queries were excluded. The original two evaluated methods returned real complete rankings on the exact frozen corpus, and their metrics were independently recomputed from preserved inputs.

| Method | Eligible queries | nDCG@5 | P@3 | Full MRR | Recall@5 |
|---|---:|---:|---:|---:|---:|
| BM25 | 1 | 0.9241332080 | 0.3333333333 | 1.0000 | 1.0000 |
| Multilingual Encoder | 1 | 0.7262287618 | 0.3333333333 | 1.0000 | 1.0000 |

On this one named query, BM25 ranked the graded gains more effectively within the first 5 positions. The observation does not establish how the methods compare on semantic paraphrases or multi-preference needs, because those queries did not satisfy the inclusion rule. A population-level confidence interval or significance claim is not justified by one eligible intent. The group-bootstrap implementation explicitly withholds an interval for fewer than two independent intent groups.

### 5.1 Post publication supplementary comparison

The keyword definition was declared before this supplemental execution. A changed BGE loader was validated against a synthetic tiny standard model for both CLS and mean pooling; maximum parameter and embedding differences were zero in those checks. This is a loading-equivalence check, not a relevance experiment. BGE then produced a real complete 49-record ranking for the exact P02 text with the same frozen labels and FP32 weights. The original two-method publication and all labels remain unchanged.

| Added method | Eligible queries | nDCG@5 | P@3 | Full MRR | Recall@5 |
|---|---:|---:|---:|---:|---:|
| Unweighted keyword overlap | 1 | 0.9515234566 | 0.3333333333 | 1.0000 | 1.0000 |
| BGE M3 dense CLS | 1 | 0.7262287618 | 0.3333333333 | 1.0000 | 1.0000 |

The methods agree on the first fully relevant record, explaining their identical MRR, P@3 and Recall@5. Their nDCG differs because they rank partially relevant records differently. The top-five human grades are keyword[2,0,1,1,0], BM25[2,0,0,1,1], multilingual encoder[2,0,0,0,0] and BGE[2,0,0,0,0]. The keyword baseline moves partial gains earlier, whereas the two dense rankings contain no partial gains in positions2–5. Equal nDCG values for the two dense methods do not imply identical rankings or embeddings. One exposed named query is insufficient to establish which method is best for semantic paraphrases.

### 5.2 Efficiency and loading diagnosis

A separate CPU measurement used all eight frozen queries without requiring relevance completeness, three warm-ups and 30 measured searches per method per query, alternating keyword/BM25 order within repeats. The mean of the eight per-query means was0.0479 ms for keyword overlap and 0.1101 ms for BM25. These240 warm observations per method exclude model loading, network and interface time. They are descriptive timings on the author's current computer, with no population-level performance claim.

Earlier model loads triggered the unchanged system-drive decline guard. Code inspection found that parameter-registration interception could allocate a large CPU tensor before replacing it with a meta parameter. The corrected loader constructs on the meta device including buffers, explicitly restores only the standard generated ID buffers, validates the entire checkpoint catalog and copies checkpoint slices of at most16 MiB to the GPU. Original FP32 learned parameters, published pooling and normalization remain unchanged. A process-level kernel lock prevents concurrent project GPU workers. In the successful49-record BGE check, C-drive free space decreased by at most393,216 bytes from its starting value, far below the retained1 GiB decline limit; document token length was at most 96 with no truncation at 128. The earlier failed attempts remain in the audit trail. This successful check is not a guarantee of every future desktop memory state. The reported load time includes the synthetic precheck and should not be interpreted as a standalone BGE cold-load benchmark.

## 6. Supplemental sampled second-rater audit

To reduce participant burden, the user selected a fixed80-pair audit instead of another392-pair full pass. Each of the 8 original queries contributes 10 records sampled uniformly without replacement from sorted candidate IDs, using the deterministic seed string`5801:query_id`. Sampling did not use first-rater grades, model rankings or model scores. The full sampled task list and hashes were frozen before the reduced task was used. Each within-query pair has inclusion probability10/49.

The second person's page stores a separate append-only log, hides the first person's grades and model rankings, and cannot call models or publish effectiveness metrics. It does not prove absence of prior exposure outside the page. All 80 pairs are now handled:78 numeric second-rater grades and 2 explicit unknowns. Six pairs have an unknown in one or both records and are excluded from numeric agreement. The completed second-rater log has been copied, hashed and locked; no grades were changed after analysis.

Descriptive agreement was calculated on numeric paired judgments, with results independently checked against scikit-learn. The primary UI-origin first-rater subset contains 71 pairs: 67 exact agreements (94.366%), linear weighted kappa0.8754385965 and quadratic weighted kappa0.8851132686. A sensitivity group including three additional numeric AI-assisted first-rater corrections contains 74 pairs: 68 exact agreements (91.892%), linear weighted kappa0.8423855165 and quadratic weighted kappa0.8648813147. The80-pair sample also contains one assisted first-rater record among the unknown exclusions. The code preserves unknowns rather than imputing them as zero. Twelve cases—six numeric disagreements and six pairs involving unknowns—were exported for review. The original first rater subsequently completed all 12 in a separate append-only session, with 9 numeric decisions and 3 explicit unknowns, then personally locked that session. Seven decisions differ from the original first-rater entry; four prior unknowns become numeric and one prior numeric grade becomes unknown. No original action log was changed and no consensus labels were automatically generated. These author decisions are not independent third-rater judgments.

| First-rater provenance group | Numeric pairs | Exact agreement | Linear weighted kappa | Quadratic weighted kappa |
|---|---:|---:|---:|---:|
| Latest UI-origin judgments only | 71 | 67/71 (94.4%) | 0.8754 | 0.8851 |
| Including assisted corrections, sensitivity | 74 | 68/74 (91.9%) | 0.8424 | 0.8649 |

Both statistic implementations matched to numerical precision. Anonymous contingency matrices are sufficient to reproduce the arithmetic using `experiments.reproduce_agreement_summary`; they do not independently authenticate the original participant actions.

This is post-publication sampled consistency evidence, not a preregistered full dual-annotation study, and its partially sampled candidate pools do not supply complete-query ranking metrics. Query/record dependence, label imbalance and limited sample size constrain interpretation.

## 6.1 Author review and revised eligibility

The review was conducted after model results were published, and the interface allowed inspection of both earlier opinions. It is therefore reported as a versioned author sensitivity analysis. The original labels, original rankings and pre-review kappa statistics are preserved, rather than overwritten or recomputed after aligning opinions.

| Label version | Numeric pairs | Explicit unknowns | Fully judged eligible queries |
|---|---:|---:|---:|
| Original frozen first-rater packet | 349 | 43 | 1 P02 |
| Author review overlay on the same packet | 352 | 40 | 0 |

A previously partially relevant generic-name record under P02 was reviewed as unknown because the source did not establish the specific requested identity. P02 now has one unknown judgment. Every other query also retains at least one unknown. Under the original rule, all eight queries are excluded from post-review effectiveness metrics. In particular, unknown is not relabeled as zero to preserve a desirable sample size. The four saved rankings all return an excluded status against the revised P02 labels. No post-review nDCG, Precision, MRR, Recall, confidence interval, method winner or updated model run is manufactured.

This review improves the record of evidence limitations but does not repair the absent independent held-out design, the original small corpus or unverified source facts. The primary completed outcome is the implemented and reproducible prototype plus an auditable preliminary study whose final evidence is insufficient to answer the comparative effectiveness question.

## 7. Reproducibility and research integrity

The source candidate is organized into data, retrieval, evaluation, interface, configuration and experiment modules. It provides pinned dependencies and model artifact hashes, no-training instructions, cached-data rebuild commands, expected outputs, tests and source/AI disclosures. The public bundle excludes personal software, credentials, participant action logs and large model weights.

Two reproducibility levels are distinguished. Anonymous saved full rankings and actual grades reproduce the published metric arithmetic without POI text. A frozen OSM response reconstructs the open 39-record BM25 demonstration. Full original 49-record retrieval reproduction still requires exact historical mixed-source inputs and an independently validated environment; the public bundle alone does not establish that end-to-end path. A subsequent isolated CPU environment was created on D using the same Python 3.13.2 and exact requirements fetched from official PyPI. It was verified to exclude user packages and Torch; 332 source-copy tests passed and one historical-data test was explicitly skipped. Saved metrics, kappa, open-data rebuilding and both lexical searches passed in that environment. This establishes fresh CPU installation and those public workflows, not fresh GPU installation, original mixed-source retrieval or school A5000 execution.

The public source repository is https://github.com/shile-source/cps5801-ouhai-place-retrieval. The initial audited release was anonymously downloaded and every included file was hash-checked against the local source candidate. Later releases retain the same verification procedure. The repository contains source, configurations, saved numerical inputs and an openly reconstructible OSM demonstration; the original mixed-source retrieval inputs are conditional as described above.

## 8. Discussion and conclusion

The prototype demonstrates shared-corpus lexical and dense retrieval, explicit source-evidence boundaries and recoverable human annotation. Historical pre-review results cover only one exposed named query. After the author's completed follow-up review, the unchanged completeness rule excludes every query; the revised version therefore cannot establish a ranking-effectiveness advantage for any method. Preserving that failure to support a conclusion is preferable to filling missing evidence or changing the protocol after observing rankings.

Remaining study limits are the non-independent convenience queries, insufficient source evidence for complete judgments, source identity and geographic review, unresolved mixed-data redistribution compatibility and a corpus below the original150–200-place objective. The review task itself is complete; three reviewed pairs remain unknown rather than being treated as unfinished work. Further independent research would require new source verification and a separately designed evaluation, not retrospective changes to the locked Pilot.

## References and source links

- Robertson, S., and Zaragoza, H.(2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. [DOI](https://doi.org/10.1561/1500000019).
- Reimers, N., and Gurevych, I.(2020). *Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation*. EMNLP. [Official ACL record](https://aclanthology.org/2020.emnlp-main.365/).
- Chen et al.(2024). *M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation*. Findings of ACL. [Official ACL record](https://aclanthology.org/2024.findings-acl.137/).
- OpenStreetMap contributors. [Copyright, attribution and ODbL](https://www.openstreetmap.org/copyright).
- BAAI. [BGE-M3 official model card and paper/code references](https://huggingface.co/BAAI/bge-m3).
- Sentence Transformers. [Multilingual MPNet official model card and authorship references](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2).
- Wenzhou public data. [Reading-facility dataset13759](https://data.wenzhou.gov.cn/jdop_front/detail/data.do?iid=13759).
- Ouhai District Library. [Opening-time notice,4 September2026](https://lib.ouhai.gov.cn/col/col1258283/art/2026/art_8f9145f0a304439889cf6a79b1322283.html).

Implementation, numerical artifacts and scripts are identified in the public repository. The report makes no claim of teacher approval, independent held-out testing or independent third-rater adjudication.
