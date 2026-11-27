# Public engineering comparison

A separate experiment makes the application's main comparison reproducible from public inputs. It uses 114 OSM source records, the same four concatenated fields, fixed pretrained weights and three methods: keyword overlap, BM25 and streamed FP16 BGE-M3. This experiment does not reuse or modify the 49-record human labels. Before inference, the corpus and query SHA256 values, method settings and schedule were frozen in `configs/public_functional_study_20261128.json`. The assistant authored 30 development queries: ten exact names selected from unique names in the source corpus, ten activity paraphrases and ten multiple-preference requests. These source-constructed queries are exposed development material, not independent human test requests. The ten exact-name cases refer to source identifiers rather than independently verified physical entities.

The schedule used one BGE cold load, one warm-up per method and five measured repetitions of each query-method pair. Seed 5801 controlled query and method order. Thus 450 measured searches cover 30 distinct requests, rather than 450 independent intents. Each search returned up to five records; all unfiltered searches returned five distinct records. The run used a GeForce RTX 4060 Laptop GPU, approximately 16 GB installed RAM, Windows 11, Python 3.13.2, PyTorch 2.10.0+cu126, Transformers 4.57.6 and Sentence Transformers 5.2.0. BGE used 1024-dimensional normalized dense CLS vectors, batch 4 and maximum length 128. The longest document was 81 tokens, so no document truncated. No local model training occurred, and no A5000 execution is claimed.

Table 5. Public source lookup and warm backend timings

| Method | Median search ms | P95 search ms | Source ID recovery at 1 |
|---|---:|---:|---:|
| Keyword | 0.121 | 0.161 | 10/10 |
| BM25 | 0.237 | 0.332 | 10/10 |
| BGE M3 FP16 | 12.298 | 13.992 | 10/10 |

Table 5 reports actual warm backend measurements and exact identifier lookup on the ten constructed names. All three methods also recovered the reference identifier within five results in all ten cases. Since the query exactly repeats a unique source name, this is a software lookup diagnostic with a lexical advantage built into its construction. It does not measure relevance on paraphrases or preferences and supports no general recommendation-accuracy claim. Identical results are expected to be relatively easy for this small catalogue. The five repetitions returned exactly the same IDs, order and scores for every query-method combination.

The median SearchEngine elapsed values were 0.862 ms for keyword, 0.974 ms for BM25 and 13.703 ms for BGE; corresponding P95 values were 1.010, 1.154 and 15.439 ms. Backend `search_ms` and engine `elapsed_ms` are different intervals. The latter includes model-process communication and result enrichment, but excludes prior filter setup, subsequent log writing, HTTP transport and browser rendering. It is not user-perceived end-to-end latency. BGE's observed cold worker load was 40.585 seconds and its first engine call took 45.703 seconds. Cold startup dominates an occasional desktop search despite the lower warm latency. Repetitions and background machine load are dependencies, so the table is descriptive for this run and has no population confidence interval.

Across all 30 requests, mean top-five Jaccard overlap was 0.7988 for keyword/BM25, 0.2786 for keyword/BGE and 0.3270 for BM25/BGE. Each overlap is the intersection size divided by the union size of the returned identifier sets. This shows that representation changes the candidate set. It cannot tell which set better satisfies a person. Low overlap alone is not evidence that semantic retrieval improved quality. For example, experiential preference wording can induce a plausible semantic match even when the source contains no corresponding facility evidence.

Source coverage explains a major product limit. Names have supported evidence for all 114 records; categories have 113 supported and one conflicting record. Address, seats and holdings are unknown for every public record under the archived field-evidence rules. Six frozen explicit-filter cases were checked with each of the three methods. KTV, pitch, park and mall conditions yielded common pools of 2, 6, 20 and 5 records respectively; the conflicting category did not pass. Seats at least 40 and holdings at least 12,000 both yielded empty pools with 114 unknowns. All 18 checks returned only records in the same supported pool. Empty results demonstrate evidence abstention rather than lack of actual facilities. These checks validate filter behavior, not the truth of current OSM tags.

The experiment preserved 472 public observation rows: one cold call, three warm-ups, 450 measurements and 18 filter checks. The public summary, queries, protocol, facts and original source responses are available without participant logs. `experiments.reproduce_public_engineering_20261128` recomputes the numerical summary without loading a model. A new live run is explicitly bounded to one load with no automatic retry. Both model processes exited after the completed run, and unchanged storage guards remained active. This finite engineering comparison adds reproducible behavior and efficiency evidence; it does not repair the absent independent relevance evaluation.


## Reproduction

The included raw observations reproduce the table without CUDA or model weights:

```powershell
.\Start-Project.ps1 -m experiments.prepare_open_activity_20261127
.\Start-Project.ps1 -m experiments.prepare_public_study_20261128
.\Start-Project.ps1 -m experiments.reproduce_public_engineering_20261128
```

After the README's pinned GPU/model setup, a fresh live run is optional:

```powershell
.\Start-Project.ps1 -u -m experiments.run_public_study_20261128 --fresh-workstation
```

It refuses an existing run claim and never retries a stopped worker. The author's original run claim lives outside the public package. On a new checkout, the runner records observations and `reproduced_summary.json` under `outputs/public_study_20261128`, preserving the shipped paper measurements. Saved arithmetic alone does not revalidate GPU performance. Re-running inference produces new timings, which need not equal the recorded run. No new source fetch, participant form, model training, system change or relaxed guard is needed. The live preflight requires the author's successful lifecycle receipt on the original workstation; a public checkout uses its separate explicit fresh-workstation path and records it without claiming author-workstation repair validation. This public preflight/output routing was added after the recorded run; the executed runner is preserved privately, and the model, timing loop and frozen study protocol were unchanged.
