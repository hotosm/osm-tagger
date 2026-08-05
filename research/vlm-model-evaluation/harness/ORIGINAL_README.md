# HOT OSM VLM Testing

Vision-language model testing for OpenStreetMap road surface / smoothness classification from street-level imagery (HOT - Humanitarian OpenStreetMap Team).

Compares local VLMs (LLaVA, Qwen2.5-VL) via Ollama against GPT-4o-mini on the same image set.

## Layout

```
old_images/        # curated + screened test set (ready for evaluation)
new_images/        # scratch area for newly downloaded images before review
results/           # CSV outputs (git-ignored)
run_local.py       # Ollama runner (LLaVA / Qwen / any Ollama vision model)
run_api.py         # OpenAI GPT-4o-mini runner
compare.py         # side-by-side comparison of two result CSVs
download_images.py # Mapillary bbox downloader (general)
download_night.py  # Mapillary downloader filtered to night captures
```

## Setup (desktop with GPU)

1. Clone the repo.
2. Install Ollama: https://ollama.com/download
3. Pull models:
   ```bash
   ollama pull llava
   ollama pull qwen2.5vl
   ```
4. Create a `.env` from `.env.example` and fill in keys (only needed for API + downloading):
   ```
   OPENAI_API_KEY=sk-...
   ACCESS_TOKEN_MAP=MLY|...
   ```
5. Install Python deps:
   ```bash
   pip install -r requirements.txt
   ```

## Running the evaluations

```bash
# Local models on the screened image set
python run_local.py llava old_images
python run_local.py qwen2.5vl old_images

# API baseline (optional)
python run_api.py old_images

# Compare any two result CSVs
python compare.py
```

Outputs land in `results/results_local_<model>.csv` and `results/results_api.csv`.

## CSV columns

`image, surface, smoothness, confidence, latency_sec, json_valid, raw_output, correct, notes`

Fill `correct` and `notes` manually during review.

## Image set categories

- **Gravel / dirt** (core failure case): NEPAL_GRAVEL, MONGOLIA_AMBIGUOUS
- **Paved** (asphalt, concrete): ICELAND, NYC, PERU, MADAGASCAR, RWANDA, INDIA, BOLIVIA
- **Cobblestone / pavers**: PARIS, PORTO, EDINBURGH
- **Hallucination tests**: *_NOROAD, *_AERIAL, *_PATH
- **Quality-filter tests**: *_NIGHT, *_WET, *_BLUR
- **Original set**: AFGHAN, BRAZIL, CHAD, IRAN, IRAQ, NIGERIA, SUDAN

## Week 5 evaluation targets

- Hallucination mitigation (add `road_present: yes/no`)
- Gravel-vs-paved accuracy (primary failure mode)
- Strict JSON output (no markdown fences)
- Low-light / blur quality gate
- Numeric confidence + filtering threshold
