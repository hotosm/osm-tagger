# VLM Model Evaluation - Road Surface & Smoothness Classification

**Origin:** Work by the UC Berkeley Code for Good programme, delivered as a
standalone benchmarking repo
([github.com/takenosuke-code/HOT_OSM](https://github.com/takenosuke-code/HOT_OSM)).
This directory is a copy of that work, preserved so it can be picked up and actioned
later.

**Question it addressed:** Can a single small open vision-language model (VLM)
classify OpenStreetMap road `surface` and `smoothness` from street-level imagery, as
an alternative to OSM Tagger's current multi-model setup?

---

## Contents of this directory

```
research/vlm-model-evaluation/
├── README.md                 # this document
├── REPRODUCING.md            # provenance of the image set + how to (re)build it
├── provenance.csv            # per-image origin of the committed probe set (best effort)
├── harness/                  # the evaluation code
│   ├── run_local.py          # Ollama pipeline (Qwen2.5-VL-7B / LLaVA / any Ollama VLM)
│   ├── run_api.py            # OpenAI / OpenRouter / Colab-vLLM pipeline
│   ├── quality_gate.py       # brightness + blur pre-filter
│   ├── compare.py            # side-by-side scorer for two result CSVs
│   ├── colab_qwen_server.ipynb  # serve Qwen2.5-VL-7B on a free Colab T4 (vLLM + ngrok)
│   ├── download_images.py    # Mapillary bbox downloader (day) - writes a manifest
│   ├── download_night.py     # Mapillary downloader, night captures - writes a manifest
│   ├── refetch_from_manifest.py  # re-pull an exact set from a manifest.csv by image ID
│   ├── requirements.txt
│   ├── .env.example
│   └── ORIGINAL_README.md    # the original repo README, verbatim
└── results/                  # raw per-image measurements
    ├── results_colab_new_images.csv   # Qwen2.5-VL-7B (AWQ) on new_images, n=53
    ├── results_openrouter.csv         # Qwen3-VL-8B on old_images, n=53
    └── results_api.csv                # gpt-4o-mini, 1 image
```

The ~106 test images are not committed here (~92 MB of CC-BY-SA Mapillary imagery).
See `REPRODUCING.md` and `provenance.csv` for what is known about them and how to
rebuild the set.

---

## What was delivered

### 1. A probe image set (~106 images)
Images from the Mapillary API, grouped by filename into categories that stress the
classifier:

- **Surface classes:** gravel/dirt, paved (asphalt/concrete), cobblestone/pavers.
- **Hallucination tests:** `*_NOROAD`, `*_AERIAL`, `*_PATH` - no drivable road present.
- **Quality tests:** `*_NIGHT`, `*_WET`, `*_BLUR`.
- Spread across many geographies (Afghanistan, Nepal, Peru, Rwanda, Iceland, NYC,
  mountain passes, ports, and others).

Two sets: `old_images` (hand-screened) and `new_images` (later batch).

### 2. A single-call classification pipeline
`run_local.py` (Ollama) and `run_api.py` (OpenAI / OpenRouter / Colab-hosted vLLM)
run a 4-stage pipeline per image:

```
1. Quality gate  →  2. VLM classify  →  3. Parse JSON  →  4. Filter & emit tags
   (reject dark/blurry)  (Qwen2.5-VL-7B)   (repair fences)   (reject no-road / low-conf)
```

Output is constrained to an OSM-compatible `surface`/`smoothness` vocabulary via the
prompt, with a numeric `confidence` and a `CONFIDENCE_THRESHOLD = 0.5` cutoff. Each
image produces one CSV row marked `rejected=yes/no` with a machine-readable reason.

The four elements added over a plain VLM call: the brightness/blur **quality gate**
(`quality_gate.py`), a **`road_present`** guard for non-road scenes, a **numeric
confidence + threshold** filter, and **strict single-shot JSON** with a 3-level
repair parser.

### 3. A scorer - `compare.py`
Compares two result CSVs: JSON validity, hallucination rate, gravel/unpaved
accuracy, night/blur filter rate, rejection rate, average latency, plus per-category
and per-image breakdowns. Ground truth is inferred from filename keywords.

### 4. A serving recipe - `colab_qwen_server.ipynb`
Serves `Qwen/Qwen2.5-VL-7B-Instruct-AWQ` via vLLM on a free Colab T4, tunneled with
ngrok, so `run_api.py` (provider `colab`) can reach it. This produced
`results_colab_new_images.csv`.

The original repo's stated evaluation targets (from `harness/ORIGINAL_README.md`)
were: hallucination mitigation via `road_present`, gravel-vs-paved accuracy, strict
JSON output, a low-light/blur quality gate, and numeric confidence + threshold.

---

## Results (as measured)

Aggregated from the committed CSVs. No run has human-verified labels, so "accepted"
reflects pipeline behaviour, not measured accuracy.

| Run | Model | Set | Quality-filtered | `road_present`=no | Valid JSON | Accepted | Avg latency |
|-----|-------|-----|------------------|-------------------|------------|----------|-------------|
| `results_colab_new_images.csv` | Qwen2.5-VL-7B (AWQ), Colab T4 | new_images (53) | 0 | 5 | 53/53 | 48 (91%) | ~12.0 s |
| `results_openrouter.csv` | Qwen3-VL-8B | old_images (53) | 12 | 3 | 41/41 | 38 (72%) | ~2.7 s |
| `results_api.csv` | gpt-4o-mini | 1 image | - | - | - | - | - |

- 100% valid JSON on both multi-image runs after the repair parser.
- Quality gate filtered 12/53 on `old_images` (the night/blur members) and 0/53 on
  `new_images` (no dark/blurry members).
- The `road_present` guard fired on no-road scenes (aerial/interior/boardwalk).
- Latency: ~12 s on the shared free Colab T4 vs ~2.7 s via the hosted API endpoint.
- Accepted-surface distribution on `new_images`: asphalt 41, dirt 3, concrete 2,
  wood 2. On `old_images`: asphalt 24, dirt 5, paving_stones 3, paved 3, gravel 2,
  compacted 1.

---

## Limitations of the delivered results

Facts about the repo as delivered, relevant to anyone building on it:

1. **No ground-truth labels were recorded.** The `correct` and `notes` columns are
   present but blank in every CSV. `compare.py`'s accuracy is based on a
   filename-keyword heuristic, not human labels.
2. **The OpenRouter run used a different model.** `run_api.py` notes that
   Qwen2.5-VL-7B has no OpenRouter endpoint and used **Qwen3-VL-8B** instead, so
   `results_openrouter.csv` is not the same model as the local/Colab runs.
3. **No at-scale API baseline.** `results_api.csv` contains one image. Cost figures
   in the code (~$5/1k gpt-4o-mini, ~$2/1k Qwen via OpenRouter, $0 local) are
   estimates in comments, not billed measurements.
4. **Vocabulary differs from the tagger's.** The harness surface list
   (`asphalt, concrete, paving_stones, cobblestone, gravel, compacted, dirt, grass,
   sand, wood, metal, paved, unpaved`) is not identical to the tagger's in
   `tagger/core/tags.py` (which adds `chipseal`, `sett`, `unhewn_cobblestone`,
   `bricks`, `concrete:lanes`, and others).

## Licensing

Mapillary imagery is CC-BY-SA 4.0 (attribution + share-alike). No model was trained
or fine-tuned - Qwen2.5-VL-7B is used off the shelf. Licensing details and the
constraints on publishing the images are in `REPRODUCING.md`.
