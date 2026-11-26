# Source and dependency attribution

## Data

- OpenStreetMap contributors: [copyright and attribution](https://www.openstreetmap.org/copyright), [Open Database License1.0](https://opendatacommons.org/licenses/odbl/1-0/). The open39-record snapshot is OSM-only; derived database contents retain ODbL and are separate from the software license. The frozen response, query, source timestamp and SHA are included in the open demonstration materials.
- Wenzhou public data, reading facilities dataset13759: [official landing page](https://data.wenzhou.gov.cn/jdop_front/detail/data.do?iid=13759). Original CSV and mixed derived corpora remain local; no blanket redistribution permission is inferred from public access.
- Ouhai District Library, published opening-time notice2026-09-04: [official source](https://lib.ouhai.gov.cn/col/col1258283/art/2026/art_8f9145f0a304439889cf6a79b1322283.html). Recorded times are a dated source statement, not current availability. Source HTML and mixed derived records are not in the public-source candidate.
- Ouhai tourism operator: [source](https://www.ohltjt.com/Art/Art_5/Art_5_185.aspx). Locally captured source profiles are evidence leads, not independently verified current operations or a licensed mixed public database.

## Pretrained models and software

- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3), MIT model-card license; fixed revision in configs. Only dense CLS output is used; sparse/multi-vector functionality and training are not claimed.
- [paraphrase-multilingual-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2), Apache2.0 model-card license; published mean pooling, fixed revision in configs.
- [Sentence Transformers](https://github.com/huggingface/sentence-transformers), [Transformers](https://github.com/huggingface/transformers), [Accelerate](https://github.com/huggingface/accelerate), [safetensors](https://github.com/huggingface/safetensors), [PyTorch](https://github.com/pytorch/pytorch), [jieba](https://github.com/fxsjy/jieba), [rank_bm25](https://github.com/dorianbrown/rank_bm25), NumPy and other pinned distributions are reused as installed dependencies. Their upstream licenses continue to apply; dependency source and binaries are not bundled into the release candidate.

Project wrappers integrate existing APIs. The streamed adapter uses the published backbone/module configuration and original weight tensors, validates all tensor names/shapes, and changes loading/module plumbing rather than retraining. A scoped experimental safe_open integration is identified in `src/retrieval/safetensor_io.py`; it is project code, not an undisclosed on-disk patch to installed libraries. Third-party packages and pretrained models must not be credited as student-created algorithms.

OpenStreetMap embedded pages and external map/route links remain external services. This repository does not claim their map tiles, photos, routing algorithms or place verification as its own output.
# Interactive map frontend

Leaflet 1.9.4 is redistributed under the BSD 2-Clause license. Unmodified JS/CSS, the complete original license and download URLs/SHA256 receipts are in `src/demo/vendor/leaflet-1.9.4/`. Circle-style numbered markers use project code and do not require Leaflet's default marker images. Leaflet is separate from the project's MIT-authored code. Official API: https://leafletjs.com/reference-1.9.4.html .

Optional browser street tiles use https://tile.openstreetmap.org/{z}/{x}/{y}.png, with visible OSM attribution, normal browser caching and origin referrer. No tile proxy, prefetch, offline scrape or bulk downloader is implemented. Users can disable the basemap while retaining local markers. Service availability is not guaranteed. Tile usage policy: https://operations.osmfoundation.org/policies/tiles/ . OSM attribution/data licensing remains separate from Leaflet's software license.

