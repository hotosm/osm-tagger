"""Download street-level road images from Mapillary API for VLM testing.

Reads ACCESS_TOKEN_MAP from .env. Saves images to ./new_images/.

Provenance: every saved image is recorded in ./new_images/manifest.csv with its
Mapillary image ID, creator (for CC-BY-SA attribution), capture time, and the
query bbox. This is what makes a pull reproducible and legally redistributable -
see ../REPRODUCING.md. (The original volunteer runs did NOT record this, which is
why the committed probe set cannot be pinned to exact Mapillary images.)
"""

import csv
import io
import os
import time

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

TOKEN = os.environ.get("ACCESS_TOKEN_MAP")
OUTPUT_DIR = "new_images"
BBOX_RADIUS = 0.02  # degrees, ~2km - small enough to avoid API 500s on dense areas
IMAGES_PER_LOCATION = 3
GRAPH_URL = "https://graph.mapillary.com/images"
MAX_RETRIES = 3
PACE_SECONDS = 1.2

MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.csv")
MANIFEST_FIELDS = [
    "filename", "mapillary_image_id", "creator_username", "creator_id",
    "captured_at", "image_lon", "image_lat",
    "query_bbox_center_lat", "query_bbox_center_lon", "query_bbox_radius_deg",
    "thumb_url", "image_page_url", "license",
]

LOCATIONS = [
    # Fresh alternate locations for edge cases that 500'd previously

    # --- Snow / winter (different cities) ---
    ("YELLOWKNIFE", 62.45, -114.37),
    ("OSLO", 59.91, 10.75),
    ("QUEBEC_CITY", 46.81, -71.21),
    ("HOKKAIDO_RURAL", 43.50, 142.80),

    # --- Wet / coastal ---
    ("VANCOUVER", 49.28, -123.12),
    ("AMSTERDAM_CANALS", 52.37, 4.90),
    ("DUBLIN", 53.35, -6.26),

    # --- Desert / sand (retry alternatives) ---
    ("MOAB_UTAH", 38.57, -109.55),
    ("SANTA_FE", 35.69, -105.94),
    ("ALICE_SPRINGS", -23.70, 133.88),

    # --- Coastal / boardwalk ---
    ("MIAMI_BEACH", 25.79, -80.13),
    ("OCEAN_CITY", 39.28, -74.58),
    ("COPACABANA", -22.97, -43.18),

    # --- Bridges (different ones) ---
    ("MANHATTAN_BRIDGE", 40.71, -73.99),
    ("WILLIAMSBURG_BRIDGE", 40.71, -73.97),
    ("SYDNEY_HARBOUR", -33.85, 151.21),

    # --- Rough / damaged ---
    ("KABUL", 34.53, 69.17),
    ("PORT_AU_PRINCE", 18.54, -72.34),
    ("HAVANA", 23.13, -82.38),
    ("BUCHAREST", 44.44, 26.10),

    # --- Mountain passes (potential gravel) ---
    ("STELVIO_PASS", 46.53, 10.45),
    ("FURKA_PASS", 46.57, 8.42),
    ("TRANSFAGARASAN", 45.60, 24.60),

    # --- Industrial / construction ---
    ("ROTTERDAM_PORT", 51.92, 4.48),
    ("HAMBURG_PORT", 53.54, 9.98),

    # --- Developing-world urban (rough surface expected) ---
    ("JAKARTA", -6.20, 106.82),
    ("NAIROBI", -1.29, 36.82),
    ("ADDIS_ABABA", 9.03, 38.74),
]


def build_bbox(lat, lng, radius=BBOX_RADIUS):
    """Mapillary bbox format: west,south,east,north."""
    return f"{lng - radius},{lat - radius},{lng + radius},{lat + radius}"


def fetch_image_metadata(lat, lng):
    """Fetch with retry on transient 500 errors and timeouts."""
    params = {
        "access_token": TOKEN,
        # id + creator + captured_at + geometry are required for the provenance manifest.
        "fields": "id,thumb_1024_url,geometry,captured_at,creator",
        "bbox": build_bbox(lat, lng),
        "limit": IMAGES_PER_LOCATION,
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(GRAPH_URL, params=params, timeout=45)
            if resp.status_code == 500 and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  [retry {attempt+1}] 500 error - waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except requests.Timeout:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  [retry {attempt+1}] timeout - waiting {wait}s")
                time.sleep(wait)
                continue
            raise
    return []


def download_and_save(url, out_path):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    # Ensure we save as PNG regardless of source format
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(out_path, format="PNG")


def build_manifest_row(fname, item, q_lat, q_lng):
    """One provenance row: enough to re-fetch the exact image and attribute it."""
    geom = (item.get("geometry") or {}).get("coordinates") or [None, None]
    creator = item.get("creator") or {}
    img_id = item.get("id")
    return {
        "filename": fname,
        "mapillary_image_id": img_id,
        "creator_username": creator.get("username", ""),
        "creator_id": creator.get("id", ""),
        "captured_at": item.get("captured_at", ""),
        "image_lon": geom[0],
        "image_lat": geom[1],
        "query_bbox_center_lat": q_lat,
        "query_bbox_center_lon": q_lng,
        "query_bbox_radius_deg": BBOX_RADIUS,
        "thumb_url": item.get("thumb_1024_url", ""),
        "image_page_url": f"https://www.mapillary.com/app/?pKey={img_id}" if img_id else "",
        "license": "CC-BY-SA-4.0",
    }


def write_manifest(manifest):
    if not manifest:
        return
    with open(MANIFEST_PATH, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(manifest)
    print(f"\nProvenance manifest ({len(manifest)} rows) -> {MANIFEST_PATH}")


def process_location(prefix, lat, lng, manifest):
    """Download images for a location; append provenance rows to `manifest`.

    Returns count of images saved."""
    try:
        items = fetch_image_metadata(lat, lng)
    except requests.HTTPError as e:
        print(f"  [WARN] API error for {prefix}: {e}")
        return 0
    except requests.RequestException as e:
        print(f"  [WARN] Network error for {prefix}: {e}")
        return 0

    if not items:
        print(f"  [WARN] No Mapillary coverage for {prefix} ({lat},{lng})")
        return 0

    saved = 0
    for i, item in enumerate(items, 1):
        url = item.get("thumb_1024_url")
        if not url:
            continue
        fname = f"{prefix}_{i}.png"
        out_path = os.path.join(OUTPUT_DIR, fname)
        try:
            download_and_save(url, out_path)
            saved += 1
            print(f"  [OK]   {out_path}")
        except Exception as e:
            print(f"  [FAIL] {prefix}_{i}: {e}")
            continue
        manifest.append(build_manifest_row(fname, item, lat, lng))
    return saved


def main():
    if not TOKEN:
        print("Error: Set ACCESS_TOKEN_MAP in your .env file.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Downloading to ./{OUTPUT_DIR}/\n")

    manifest = []
    counts = {}
    start = time.time()
    for prefix, lat, lng in LOCATIONS:
        print(f"{prefix} @ ({lat}, {lng}):")
        counts[prefix] = process_location(prefix, lat, lng, manifest)
        time.sleep(PACE_SECONDS)

    write_manifest(manifest)

    elapsed = time.time() - start
    total = sum(counts.values())
    print("\n" + "=" * 50)
    print("Download Summary")
    print("=" * 50)
    for prefix, n in counts.items():
        status = "OK" if n > 0 else "EMPTY"
        print(f"  [{status:5}] {prefix:<25} {n} image(s)")
    print("-" * 50)
    print(f"  Total images: {total}")
    print(f"  Locations w/ coverage: {sum(1 for n in counts.values() if n > 0)}/{len(LOCATIONS)}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
