# Evidence Aware AI Place Retrieval in Ouhai

**Conference style manuscript for student review, 27 November 2026. Author Shi LeTian.** Public source repository: https://github.com/shile-source/cps5801-ouhai-place-retrieval. This version incorporates the activity catalogue and pending assisted spotcheck. Source reading by the student and human decisions remain separate responsibilities; neither is claimed complete by this draft.

## Abstract

Natural-language place search must distinguish semantic similarity from facts about real destinations. This project implements a source-aware Chinese retrieval prototype with keyword overlap, BM25, a multilingual sentence encoder and BGE-M3, sharing text fields and explicit source constraints. The local development catalogue contains 151 source records across cultural, green-space, commercial, dining, entertainment and sports categories; a separate 114-record OSM-only snapshot supports public reconstruction. Historical evaluation crossed 49 records with eight exposed convenience queries. The original judgments contained 349 numeric grades and 43 unknowns, leaving one eligible named-place query. A later locked author review produced 352 numeric grades and 40 unknowns, excluding every query under the unchanged completeness rule. Consequently no final model-effectiveness winner is supported. A post-publication second-rater audit yielded 94.4% exact agreement on 71 eligible numeric pairs, with linear weighted kappa 0.875; it was not an independent held-out study. For 30 user-submitted requests, conservative assistant-written rules prepared 4,530 development suggestions and a fixed 60-pair human spotcheck, whose results remain pending. Functional checks demonstrate live retrieval and a reduced-memory FP16 application, while reproducibility artifacts preserve provenance, source hashes, saved arithmetic and the boundary between engineering success and unsupported effectiveness claims.

## 1. Research problem and scope

Users may describe a desired place through its name, an intended activity or several preferences. Lexical overlap can identify named entities but may miss natural-language paraphrases; embedding similarity offers a different ranking signal. This motivates a controlled comparison without assuming that a larger semantic model must win. The research question is whether the methods differ in source-text relevance under the same corpus, text fields, queries and evaluation rules. Map display and external routing are application features rather than the central effectiveness outcome.

The original plan aimed at 150–200 places, distinct development and held-out test queries, multiple retrieval methods and independent dual judgments. The evaluated evidence is smaller: 49 evaluated source records, 8 exposed AI-assisted convenience queries and one fully judged eligible query. Later engineering snapshots contain 54, 76 and 151 source records but do not inherit old judgments. They must not be described as an enlarged evaluated benchmark. A source record is not necessarily a unique independently verified real-world entity.

## 1.1. Related work

Lexical and dense retrieval address different representations of relevance. Robertson and Zaragoza [1] describe the probabilistic framework underlying BM25. A lexical baseline remains useful here because proper names and explicitly recorded quantities can be decisive in a small place catalogue. Its inclusion is a control, not an assumption that token overlap captures every activity preference. Sentence-BERT [2] makes independently encoded sentence vectors useful for similarity search. Multilingual knowledge distillation [3] extends sentence representations across languages through paired text. These works motivate reuse of an existing multilingual encoder; no distillation or sentence-encoder training was conducted in this project.

Dense Passage Retrieval [4] demonstrates dual-encoder retrieval in question answering. SimCSE [5] investigates contrastive learning for sentence embeddings, while Contriever [10] studies unsupervised contrastive retrieval and transfer. The present implementation neither retrains those systems nor evaluates their published checkpoints. They provide methodological context for separating representation learning from downstream nearest-neighbour ranking. BGE-M3 [6] supports dense, sparse and multi-vector signals; this implementation uses only the released dense CLS representation. It therefore does not reproduce M3's complete multi-function retrieval system or training results.

Benchmark design is as important as checkpoint choice. MTEB [7] compares embeddings across several task families. MIRACL [8] emphasizes multilingual retrieval with human relevance judgments. MMTEB [9] expands multilingual embedding evaluation, and BEIR [11] tests retrieval across heterogeneous domains. Together they motivate reporting domain, language, task and judgment coverage explicitly. Their published results are not estimates of performance on the current Ouhai source records. The local catalogue, short descriptions and exposed convenience queries are too different to transfer a leaderboard claim. With only one eligible historical query and none after review, this study cannot identify a universal or domain-level winner.

Graded ranking evaluation follows the cumulative-gain perspective of Järvelin and Kekäläinen [12]. A gain-based measure can distinguish moving partially relevant records earlier even when methods share the first highly relevant hit. Its interpretation still depends on the validity and completeness of the underlying judgments. The project therefore reports unknown labels separately and preserves the prespecified exclusion rule after a later review removes the only originally complete query.

Urban applications introduce additional issues beyond textual similarity. ItiNera [13] integrates natural-language urban requests with spatial itinerary optimization. GeoLM [14] connects language and geographical context, and SpaBERT [15] learns geographic entity representations from spatial context. These approaches motivate a clear boundary between retrieving a source record and validating a real-world destination. The current system does not optimize routes, learn spatial embeddings or assert travel feasibility. Its map is a linked source-location display with external map handoff. The contribution is an inspectable small-data prototype and an audit of where its evidence is insufficient, rather than a new embedding architecture or a claim to solve personalized itinerary planning.

## 2. Sources and evidence model

The local mixed snapshots combine Wenzhou public reading-facility records, OpenStreetMap elements and subsequent official-source evidence. Each imported value is associated with source identifiers, dated acquisition information and content hashes. Missing quantities are not inferred from a place name or facility type. The 76-record development evidence audit links all records to source evidence;37 have supported addresses and 22 have supported seat and book counts. Eight potential duplicate pairs remain flagged for identity review.

The source-text task is deliberately narrower than a real-world recommendation guarantee. A recorded opening time does not establish current opening. A park tag does not establish quietness, seating or suitability for study. A way/relation center is a bounding-box center rather than a verified entrance. Some original coordinates are anomalous and were not silently repaired. District identity, point location, present operations and accessibility require further independent verification.

Mixed-source public redistribution compatibility is unresolved. The open reproducibility materials therefore use a separate frozen OSM-only 39-record demonstration under ODbL attribution, without silently replacing the original evaluated dataset. The original mixed-data full retrieval path is conditional on lawful access to its exact historical inputs.

## 2.1. Activity extension and version boundaries

On 26 November, a bounded additional OSM request returned 75 named source elements, bringing the local mixed development catalogue from 76 to 151 records. The 75 additions comprise 2 KTV records, 1 cinema, 2 game-entertainment venues, 7 fitness places, 1 swimming facility, 6 pitches, 2 playgrounds, 5 sports centres, 1 stadium, 5 shopping centres, 8 retail areas, 3 pedestrian areas, 27 restaurants and 5 cafes. These counts describe source categories, not a current business census. Explicit sport tags support basketball and tennis descriptions. A retail land-use tag or pedestrian way does not by itself establish a commercial street, and a playground tag does not prove organized family activities.

The 151-record corpus has 114 explicitly WGS84 OSM source positions. The other 37 records remain searchable without invented map coordinates. Different OSM elements can represent the same physical destination; this expansion does not establish 151 unique independently verified places. Archived raw responses, source tags, acquisition timestamps, query text and SHA256 bindings support reconstruction and source inspection. Existing 49-record judgments remain bound to their original corpus and are not automatically transferred to the expanded catalogue.

For public reproduction, the two newly collected OSM batches also form a separate 114-record OSM-only snapshot with attribution and original responses. This avoids publishing the mixed government/OSM catalogue while its redistribution compatibility is unresolved. The 114-record open demo and the 151-record local product have different purposes and identifiers in the documentation. Running the open demo verifies source reconstruction and application behavior; it does not reproduce the original mixed-data effectiveness experiment or resolve entity identity and present operation.

## 3. Methods and implementation

The unweighted keyword baseline counts distinct shared Jieba tokens, without frequency or IDF weighting. It shares the BM25 tokenizer, uses no stop-word list and retains zero-overlap candidates for complete ordering; ties use the same stable identifier rule. This baseline was added after the original publication, with its definition frozen before supplemental execution.

All retrieval methods concatenate the same nonempty `name`, `category`, `address` and `description` fields in that order. BM25 uses jieba segmentation, k1=1.5, b=0.75 and epsilon=0.25. Dense methods use normalized embeddings and dot-product cosine similarity; ties use stable source-record identifiers. Raw scores from different models are not interpreted as comparable probabilities.

The multilingual encoder is `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, pinned to revision`4328cf26390c98c5e3c738b4460a05b95f4911f5`, with 768-dimensional output and its published mean-pooling configuration. BGE-M3 is pinned to revision`694b61558aea4ae2512ed8d0e189d5cf8adc2259`, with 1024-dimensional dense CLS output. Sparse and multi-vector BGE outputs, hybrid retrieval and new model training are outside the reported implementation. Pretrained model work and installed libraries are attributed rather than presented as student-created algorithms.

The historical research configuration used FP32, batch 4 and maximum length 128; the current map application explicitly uses streamed FP16 as described in Section 7. For the 76-record functional corpus, the maximum observed document token length was 103, with zero truncated documents. A Windows-specific streamed loader instantiates the published backbone and validates tensor names/shapes before assigning original weights to the GPU one tensor at a time. The original pooling/module graph is respected; supported legacy position buffers must match generated buffers exactly. A tiny synthetic CLS numerical check produced identical parameters and vectors, but this is not a complete real-checkpoint equivalence proof. Some ordinary loading strategies and a later supplemental synthetic attempt stopped under unchanged storage guards. The prototype does not automatically retry a stopped model or change system paging.

Hard conditions and soft preferences are treated separately. Explicit, user-confirmed conditions share one candidate pool across methods. Unknown source facts do not pass a hard filter. A limited inspectable rule-based helper proposes supported category and Arabic-integer minimum-count conditions; it does not claim arbitrary natural-language understanding. Preference language and unsupported experiential or real-time requirements are not silently promoted to hard conditions. This new engineering feature does not retrospectively alter the published Pilot protocol.

## 4. Preliminary evaluation protocol

The original packet contained 49 records crossed with 8 queries, covering names, semantic expressions and multiple preferences. Query design and some conversational guidance were AI-assisted and exposed, so this is a convenience Pilot rather than an independent held-out study. Relevance grades were 0,1 or2. Insufficient evidence was stored as unknown instead of grade 0. Numeric thresholds of 40 seats and 12,000 books applied only to the corresponding predefined preference queries.

The original frozen complete-judgment rule excludes any query with unknown candidate grades. nDCG@5 uses exponential gain 2^grade−1. Binary relevance uses grade 2. Precision@3 divides by 3 even when fewer positions are returned. Full MRR requires the entire shared candidate ordering. Recall@5 is defined only with a fully judged candidate pool and a nonempty relevant set. Model comparisons use identical eligible-query intersections.

The user published the original result before adding the second rater. The append-only original log contains 349 numeric judgments and 43 unknowns; its latest 392 judgments include 369 UI-origin entries and 23 user-requested AI-assisted corrections. The frozen version remains locked. This provenance prevents an independent-human-ground-truth claim.

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

The methods agree on the first fully relevant record, explaining their identical MRR, P@3 and Recall@5. Their nDCG differs because they rank partially relevant records differently. The top-five human grades are keyword[2,0,1,1,0], BM25[2,0,0,1,1], multilingual encoder[2,0,0,0,0] and BGE[2,0,0,0,0]. The keyword baseline moves partial gains earlier, whereas the two dense rankings contain no partial gains in positions 2–5. Equal nDCG values for the two dense methods do not imply identical rankings or embeddings. One exposed named query is insufficient to establish which method is best for semantic paraphrases.

### 5.2 Efficiency and loading diagnosis

A separate CPU measurement used all eight frozen queries without requiring relevance completeness, three warm-ups and 30 measured searches per method per query, alternating keyword/BM25 order within repeats. The mean of the eight per-query means was 0.0479 ms for keyword overlap and 0.1101 ms for BM25. These 240 warm observations per method exclude model loading, network and interface time. They are descriptive timings on the author's current computer, with no population-level performance claim.

Earlier model loads triggered the unchanged system-drive decline guard. Code inspection found that parameter-registration interception could allocate a large CPU tensor before replacing it with a meta parameter. The corrected loader constructs on the meta device including buffers, explicitly restores only the standard generated ID buffers, validates the entire checkpoint catalog and copies checkpoint slices of at most 16 MiB to the GPU. Original FP32 learned parameters, published pooling and normalization remain unchanged. A process-level kernel lock prevents concurrent project GPU workers. In the successful 49-record BGE check, C-drive free space decreased by at most 393,216 bytes from its starting value, far below the retained1 GiB decline limit; document token length was at most 96 with no truncation at 128. The earlier failed attempts remain in the audit trail. This successful check is not a guarantee of every future desktop memory state. The reported load time includes the synthetic precheck and should not be interpreted as a standalone BGE cold-load benchmark.

## 6. Supplemental sampled second-rater audit

To reduce participant burden, the user selected a fixed 80-pair audit instead of another 392-pair full pass. Each of the 8 original queries contributes 10 records sampled uniformly without replacement from sorted candidate IDs, using the deterministic seed string`5801:query_id`. Sampling did not use first-rater grades, model rankings or model scores. The full sampled task list and hashes were frozen before the reduced task was used. Each within-query pair has inclusion probability 10/49.

The second person's page stores a separate append-only log, hides the first person's grades and model rankings, and cannot call models or publish effectiveness metrics. It does not prove absence of prior exposure outside the page. All 80 pairs are now handled: 78 numeric second-rater grades and 2 explicit unknowns. Six pairs have an unknown in one or both records and are excluded from numeric agreement. The completed second-rater log has been copied, hashed and locked; no grades were changed after analysis.

Descriptive agreement was calculated on numeric paired judgments, with results independently checked against scikit-learn. The primary UI-origin first-rater subset contains 71 pairs: 67 exact agreements (94.366%), linear weighted kappa 0.8754385965 and quadratic weighted kappa 0.8851132686. A sensitivity group including three additional numeric AI-assisted first-rater corrections contains 74 pairs: 68 exact agreements (91.892%), linear weighted kappa 0.8423855165 and quadratic weighted kappa 0.8648813147. The 80-pair sample also contains one assisted first-rater record among the unknown exclusions. The code preserves unknowns rather than imputing them as zero. Twelve cases—six numeric disagreements and six pairs involving unknowns—were exported for review. The original first rater subsequently completed all 12 in a separate append-only session, with 9 numeric decisions and 3 explicit unknowns, then personally locked that session. Seven decisions differ from the original first-rater entry; four prior unknowns become numeric and one prior numeric grade becomes unknown. No original action log was changed and no consensus labels were automatically generated. These author decisions are not independent third-rater judgments.

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

### Interactive application and operational configuration

The Chinese application links a natural-language search box, four explicit method choices, optional source-based hard conditions, ranked cards, a map and a source-detail dialog. The 151-record local development catalogue covers reading, cultural, green-space, commercial, dining, entertainment and sports categories. OSM nodes and area bounding-box centres have different marker styles. Neither is a verified entrance; 37 records without an established coordinate system are retained only in the list. Photographs and current facility status are not promised. External OSM street tiles failed in the inspected browser, so the application retains markers, lists and external-map links when the street background is unavailable.

The first new FP32 live model load stopped under the unchanged storage guard; its failure is preserved. After explicit authorization, a materially different streamed FP16 check on 76 records completed three queries. The maximum observed C-drive decline was 131,072 bytes. An actual browser BGE request then returned ten source records, with observed model-load and query times of 37,823.9 and 27.8 ms. These are single-run functional observations, not latency benchmarks or numerical-equivalence evidence. FP16 casting can change rankings and is kept separate from the original FP32 research results. The current application uses this explicit reduced-memory configuration, not a silent precision change to historical experiments.

All project models, caches and generated files are directed to D before library imports. Windows-managed paging remains on C after a prior migration was rolled back; placing project files on D does not prevent C paging growth. The application retains C at least 5 GiB, D at least 10 GiB and a maximum observed C decline of 1 GiB as stop conditions. It neither changes system paging nor automatically retries failed model workers. The school NVIDIA RTX A5000 was not tested; actual functional work used a GeForce RTX 4060 Laptop GPU. A5000 execution remains an unverified portability path, not a completed experiment.

A subsequent single live BGE FP16 request on the expanded 151-record catalogue also passed, returning ten newly computed results. Observed model load was 39,224.3 ms and search was 89.0 ms; C free space changed from 8,622,276,608 to 8,622,116,864 bytes across the request. These endpoint snapshots do not represent a continuous memory benchmark. No new relevance judgments or effectiveness metrics were produced.

A later residency check found that the BGE worker had stopped under the retained C-drive-decline guard. The available status does not establish the cause or exact transient minimum. The earlier successful request remains a finite functional result, not proof of sustained availability. No automatic retry or relaxed threshold was applied. Dense inference is currently paused; lexical search and annotation remain available.

### 7.1. New user requests and limited human spotcheck

The user submitted and locked 30 requests and reported personally writing them. The original submission is preserved. Its form declaration that rankings were unseen conflicts with known result exposure in the conversation; independence has not been established. Many requests concern experiential or weakly documented attributes such as quietness, lake views, picnicking, desserts or family activities. These require additional evidence and cannot be assumed true from a place name. Vague preferences such as abundant seats or many books do not inherit the earlier Pilot's fixed numerical thresholds.

For this expanded development task, assistant-written conservative rules generated 4,530 suggestions over 30 requests and 151 records. This was explicit rule execution, not 4,530 independent language-model judgments and not human annotation. The suggestions contain 1,494 grade-0 entries, 6 grade-1 entries, 40 grade-2 entries and 2,990 unknowns. Their distribution reflects the rules and available fields; it does not estimate actual relevance prevalence or retrieval accuracy. Model rankings and original human labels were not used to determine those suggestions.

At the user's request to reduce participant work, two records per query were selected uniformly without replacement from the sorted 151 identifiers, using a fixed query-specific seed. The resulting 60-pair task is independent of suggestion grade and model rank, with per-record inclusion probability 2/151 within a query. The page displays suggestions and source evidence, and records actual human acceptance, correction or unknown with reasons in a separate append-only log. A read-only check on 27 November found one saved human decision out of 60 and an unlocked task; the assisted spotcheck is incomplete. No agreement estimate, acceptance percentage, confidence interval or human-validated effectiveness metric is reported for it. The 4,470 unreviewed suggestions never become human labels. Even a completed 60-pair assisted spotcheck would provide a limited audit of the suggestions, not full independent dual annotation of all pairs or complete-pool nDCG/Recall under the original protocol.

The source candidate is organized into data, retrieval, evaluation, interface, configuration and experiment modules. It provides pinned dependencies and model artifact hashes, no-training instructions, cached-data rebuild commands, expected outputs, tests and source/AI disclosures. The public bundle excludes personal software, credentials, participant action logs and large model weights.

Two reproducibility levels are distinguished. Anonymous saved full rankings and actual grades reproduce the published metric arithmetic without POI text. A frozen OSM response reconstructs the open 39-record BM25 demonstration. Full original 49-record retrieval reproduction still requires exact historical mixed-source inputs and an independently validated environment; the public bundle alone does not establish that end-to-end path. A subsequent isolated CPU environment was created on D using the same Python 3.13.2 and exact requirements fetched from official PyPI. It was verified to exclude user packages and Torch; 332 source-copy tests passed and one historical-data test was explicitly skipped. Saved metrics, kappa, open-data rebuilding and both lexical searches passed in that environment. This establishes fresh CPU installation and those public workflows, not fresh GPU installation, original mixed-source retrieval or school A5000 execution.

The public source repository is https://github.com/shile-source/cps5801-ouhai-place-retrieval. The initial audited release was anonymously downloaded and every included file was hash-checked against the local source candidate. Later releases retain the same verification procedure. The repository contains source, configurations, saved numerical inputs and an openly reconstructible OSM demonstration; the original mixed-source retrieval inputs are conditional as described above.

## 8. Discussion and conclusion

The prototype demonstrates shared-corpus lexical and dense retrieval, explicit source-evidence boundaries and recoverable human annotation. Historical pre-review results cover only one exposed named query. After the author's completed follow-up review, the unchanged completeness rule excludes every query; the revised version therefore cannot establish a ranking-effectiveness advantage for any method. Preserving that failure to support a conclusion is preferable to filling missing evidence or changing the protocol after observing rankings.

Remaining study limits are the non-independent convenience queries, insufficient source evidence for complete judgments, source identity and geographic review, unresolved mixed-data redistribution compatibility and a catalogue whose 151 source records have not been independently established as 150–200 unique places. The review task itself is complete; three reviewed pairs remain unknown rather than being treated as unfinished work. Further independent research would require new source verification and a separately designed evaluation, not retrospective changes to the locked Pilot.

## 9. AI disclosure and author responsibilities

OpenAI Codex/ChatGPT assisted implementation, debugging, source checking, document and slide preparation, development query examples, historical user-requested label corrections and the new explicit suggestion rules. The user performed the original UI grading and the locked follow-up author review; a second participant completed the supplemental 80-pair task. These origins are tracked separately. The new 30-request authorship is user-reported, and the new 60-pair spotcheck remains pending. The assistant did not impersonate a participant, submit human confirmations or claim that unreviewed suggestions were human-authored. Pretrained checkpoints and external libraries are attributed. The student must personally check the cited sources and reported outputs, understand the implementation, and decide whether the manuscript's limited evidence meets the course expectations. AI assistance does not establish that those responsibilities have already been fulfilled.

## References

[1] Robertson, S., and Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in Information Retrieval. https://doi.org/10.1561/1500000019

[2] Reimers, N., and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP-IJCNLP. https://aclanthology.org/D19-1410/

[3] Reimers, N., and Gurevych, I. (2020). Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation. EMNLP. https://aclanthology.org/2020.emnlp-main.365/

[4] Karpukhin, V., et al. (2020). Dense Passage Retrieval for Open-Domain Question Answering. EMNLP. https://aclanthology.org/2020.emnlp-main.550/

[5] Gao, T., Yao, X., and Chen, D. (2021). SimCSE: Simple Contrastive Learning of Sentence Embeddings. EMNLP. https://aclanthology.org/2021.emnlp-main.552/

[6] Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., and Liu, Z. (2024). M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. Findings of ACL. https://aclanthology.org/2024.findings-acl.137/

[7] Muennighoff, N., Tazi, N., Magne, L., and Reimers, N. (2023). MTEB: Massive Text Embedding Benchmark. EACL. https://aclanthology.org/2023.eacl-main.148/

[8] Zhang, X., et al. (2023). MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages. TACL. https://aclanthology.org/2023.tacl-1.63/

[9] Enevoldsen, K., et al. (2025). MMTEB: Massive Multilingual Text Embedding Benchmark. ICLR. https://proceedings.iclr.cc/paper_files/paper/2025/hash/fc0e3f908a2116ba529ad0a1530a3675-Abstract-Conference.html

[10] Izacard, G., et al. (2022). Unsupervised Dense Information Retrieval with Contrastive Learning. TMLR; author manuscript arXiv:2112.09118. https://arxiv.org/abs/2112.09118

[11] Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., and Gurevych, I. (2021). BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models. NeurIPS Datasets and Benchmarks; author manuscript. https://arxiv.org/abs/2104.08663

[12] Järvelin, K., and Kekäläinen, J. (2002). Cumulated Gain-based Evaluation of IR Techniques. ACM Transactions on Information Systems 20(4), 422–446. https://researchportal.tuni.fi/en/publications/cumulated-gain-based-evaluation-of-ir-techniques

[13] Tang, Y., et al. (2024). ItiNera: Integrating Spatial Optimization with Large Language Models for Open-domain Urban Itinerary Planning. EMNLP Industry Track. https://aclanthology.org/2024.emnlp-industry.104/

[14] Li, Z., Zhou, W., Chiang, Y.-Y., and Chen, M. (2023). GeoLM: Empowering Language Models for Geospatially Grounded Language Understanding. EMNLP. https://aclanthology.org/2023.emnlp-main.317/

[15] Li, Z., Kim, J., Chiang, Y.-Y., and Chen, M. (2022). SpaBERT: A Pretrained Language Model from Geographic Data for Geo-Entity Representation. Findings of EMNLP. https://aclanthology.org/2022.findings-emnlp.200/

## Data and software sources

OpenStreetMap contributors, ODbL attribution and terms: https://www.openstreetmap.org/copyright. Wenzhou reading-facility dataset 13759: https://data.wenzhou.gov.cn/jdop_front/detail/data.do?iid=13759. BAAI BGE-M3 model: https://huggingface.co/BAAI/bge-m3. Sentence Transformers multilingual MPNet: https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2. Leaflet 1.9.4 is distributed under BSD-2-Clause with archived provenance. Government/OSM mixed redistribution remains unresolved; only the separate OSM-only snapshot is included in the public data workflow.
