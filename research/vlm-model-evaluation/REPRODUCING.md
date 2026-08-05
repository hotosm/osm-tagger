# Reproducing the probe image set

This document explains **what can and cannot be reproduced** about the ~106
Mapillary images behind the committed results, and gives the go-forward process for
building a properly-tracked, attributable set. Read the licensing section before
publishing any imagery.

## The honest state of the original set

The images the volunteer ran are **not exactly recoverable**. Two reasons:

1. **No image IDs were ever recorded.** The original `download_images.py` /
   `download_night.py` requested Mapillary's `id` field but only used the thumbnail
   URL - files were saved as `LOCATION_N.png` and the ID was discarded.
2. **The PNGs carry no metadata.** Images were re-encoded through Pillow, which
   stripped EXIF/text chunks. (Some `old_images` even have a `dpi` tag, i.e. they
   were manual screenshots, not API pulls at all.)

So there is no way to point at the specific Mapillary images that produced
`results/*.csv`. The best that survives is captured in **`provenance.csv`**.

### What `provenance.csv` gives you

One row per committed image, with a `coord_confidence` column:

| `coord_confidence` | count | meaning |
|---|---|---|
| `query-location` | 45 | Filename prefix still maps to a bbox in the current `download_*.py` `LOCATIONS` tables. You can re-query that bbox to get *equivalent* (not identical) images. |
| `city-centroid-approx` | 7 | Prefix matches a city in a script but the script/category doesn't line up; coordinates are a rough city centre only. |
| `unrecorded` | 54 | No coordinates anywhere - mostly the hand-curated `old_images`. Location is only as good as the filename (e.g. `NEPAL_GRAVEL_1`). |

`mapillary_image_id` is `UNRECORDED` for all 106 rows, by definition of the problem
above. Coordinates in `provenance.csv` were resolved by matching each filename prefix
against the `LOCATIONS` tables in the two `download_*.py` scripts.

## Go-forward: building a reproducible, attributable set

The download scripts have been **patched** so this never happens again. Every run
now writes `new_images/manifest.csv` with, per image:

`filename, mapillary_image_id, creator_username, creator_id, captured_at,
image_lon, image_lat, query_bbox_center_lat, query_bbox_center_lon,
query_bbox_radius_deg, thumb_url, image_page_url, license`

That manifest is what a future contributor needs to (a) re-pull the **exact** images
and (b) attribute them correctly.

### 1. Pull a fresh set (records provenance automatically)

```bash
cd harness
cp .env.example .env          # add ACCESS_TOKEN_MAP=MLY|...
pip install -r requirements.txt
python download_images.py     # daytime locations  -> new_images/ + new_images/manifest.csv
python download_night.py      # night captures     -> appends to new_images/manifest.csv
```

Edit the `LOCATIONS` tables in either script to change coverage.

### 2. Re-pull an exact set from a manifest

Because Mapillary thumbnail URLs are short-lived signed URLs, don't trust a stored
`thumb_url` - re-resolve each image by its ID:

```bash
python refetch_from_manifest.py path/to/manifest.csv output_dir/
```

Rows with `mapillary_image_id == UNRECORDED` are skipped - which is why the original
set can't be driven through this path, but any set collected from now on can.

### 3. Re-run the pipeline and score

```bash
# local (Ollama) or via the Colab endpoint / an API provider
python run_local.py qwen2.5vl:7b new_images
python compare.py results/results_local_qwen2.5vl_7b_new_images.csv results/<baseline>.csv
```

## Licensing - required before publishing any imagery

Mapillary imagery is **CC BY-SA 4.0**
([Mapillary help](https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data),
[terms](https://www.mapillary.com/terms)). Redistribution is allowed, but with two
binding obligations:

- **Attribution (BY):** credit the contributor - e.g. *"<image link> by
  <creator_username>, CC-BY-SA 4.0"*. The manifest now captures
  `creator_username` and `image_page_url` for exactly this.
- **ShareAlike (SA):** any published collection/derivative of the *images* must
  itself be CC BY-SA 4.0.

Two ways to package the set, if it is ever published:

- **References only** - publish a table of `mapillary_image_id` + `image_page_url` +
  labels + attribution, and let consumers fetch pixels via
  `refetch_from_manifest.py`. No image files are redistributed, so ShareAlike does
  not extend to the labels.
- **Images included** - redistribute the pixels as a CC BY-SA 4.0 release with
  per-image creator attribution (the manifest captures what is needed).

Faces and license plates are blurred upstream by Mapillary.
