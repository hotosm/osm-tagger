"""Download night-time Mapillary images.

Strategy:
  1. Query a bbox for many images (with captured_at timestamps).
  2. Approximate local hour from UTC timestamp + lng-based TZ offset.
  3. Keep only captures in local night hours (19:00–06:00).
  4. After download, verify with PIL average brightness (<80/255).
  5. Reject false positives (e.g. snowy bright night scenes still get filtered).

Output files: new_images/<CITY>_NIGHT_<n>.png

Provenance: accepted images are recorded in new_images/manifest.csv (Mapillary ID,
creator for CC-BY-SA attribution, capture time, query bbox). See ../REPRODUCING.md.
"""

import csv
import io
import os
import time

import requests
from dotenv import load_dotenv
from PIL import Image, ImageStat

load_dotenv()

TOKEN = os.environ.get("ACCESS_TOKEN_MAP")
OUTPUT_DIR = "new_images"
BBOX_RADIUS = 0.03                  # ~3km
LIMIT_PER_LOC = 200                 # fetch many, filter down
MAX_DOWNLOADS_PER_LOC = 3
BRIGHTNESS_THRESHOLD = 85           # 0–255 grayscale avg; lower = darker
GRAPH_URL = "https://graph.mapillary.com/images"

MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.csv")
MANIFEST_FIELDS = [
    "filename", "mapillary_image_id", "creator_username", "creator_id",
    "captured_at", "image_lon", "image_lat",
    "query_bbox_center_lat", "query_bbox_center_lon", "query_bbox_radius_deg",
    "thumb_url", "image_page_url", "license",
]

LOCATIONS = [
    # Dense coverage cities - higher chance of at least some night captures
    ("NYC", 40.75, -73.98),
    ("LONDON", 51.51, -0.12),
    ("PARIS", 48.85, 2.35),
    ("BERLIN", 52.52, 13.40),
    ("TOKYO", 35.68, 139.69),
    ("SEOUL", 37.57, 126.98),
    ("TAIPEI", 25.03, 121.57),
    ("STOCKHOLM", 59.33, 18.07),
    ("MOSCOW", 55.75, 37.62),
    ("PRAGUE", 50.09, 14.42),
    ("MADRID", 40.42, -3.70),
    ("ROME", 41.90, 12.49),
    ("BARCELONA", 41.39, 2.17),
    ("BUENOS_AIRES", -34.60, -58.38),
    ("SYDNEY", -33.87, 151.21),
    ("MELBOURNE", -37.81, 144.96),
    ("BANGKOK", 13.75, 100.50),
    ("MUMBAI", 19.08, 72.88),
    ("SAOPAULO", -23.55, -46.63),
    ("MEXICO_CITY", 19.43, -99.13),
]


def build_bbox(lat, lng, radius=BBOX_RADIUS):
    return f"{lng - radius},{lat - radius},{lng + radius},{lat + radius}"


def estimate_local_hour(captured_at_ms, lng):
    """Rough local hour using longitude-based TZ offset. Ignores DST / political TZs."""
    utc_hour = (captured_at_ms / 1000 / 3600) % 24
    local_hour = (utc_hour + lng / 15.0) % 24
    return local_hour


def is_night_hour(h):
    return h >= 19 or h < 6


def fetch_candidates(lat, lng):
    params = {
        "access_token": TOKEN,
        # id + creator + geometry are required for the provenance manifest.
        "fields": "id,thumb_1024_url,captured_at,geometry,creator",
        "bbox": build_bbox(lat, lng),
        "limit": LIMIT_PER_LOC,
    }
    try:
        resp = requests.get(GRAPH_URL, params=params, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] request failed: {e}")
        return []
    return resp.json().get("data", [])


def avg_brightness(img):
    return ImageStat.Stat(img.convert("L")).mean[0]


def download(url, out_path):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    if img.mode != "RGB":
        img = img.convert("RGB")
    b = avg_brightness(img)
    img.save(out_path, format="PNG")
    return b


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
    items = fetch_candidates(lat, lng)
    if not items:
        print("  no candidates")
        return 0, 0

    # Filter to night-hour timestamps
    night_candidates = []
    for it in items:
        ts = it.get("captured_at")
        url = it.get("thumb_1024_url")
        if not (ts and url):
            continue
        hr = estimate_local_hour(ts, lng)
        if is_night_hour(hr):
            night_candidates.append((it, hr))

    if not night_candidates:
        print(f"  {len(items)} images, 0 in night hours")
        return 0, 0

    print(f"  {len(items)} images, {len(night_candidates)} in night hours - verifying brightness")
    saved = 0
    rejected = 0
    for item, hr in night_candidates:
        if saved >= MAX_DOWNLOADS_PER_LOC:
            break
        fname = f"{prefix}_NIGHT_{saved + 1}.png"
        out_path = os.path.join(OUTPUT_DIR, fname)
        try:
            brightness = download(item["thumb_1024_url"], out_path)
        except Exception as e:
            print(f"  [FAIL] {e}")
            continue
        if brightness > BRIGHTNESS_THRESHOLD:
            os.remove(out_path)
            rejected += 1
            continue
        print(f"  [OK] {out_path}  local_hour={hr:.1f}  brightness={brightness:.0f}")
        saved += 1
        manifest.append(build_manifest_row(fname, item, lat, lng))
    return saved, rejected


def main():
    if not TOKEN:
        print("Error: Set ACCESS_TOKEN_MAP in your .env file.")
        return
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    manifest = []
    total_saved = 0
    total_rejected = 0
    start = time.time()
    print(f"Searching {len(LOCATIONS)} cities for night images...\n")
    for prefix, lat, lng in LOCATIONS:
        print(f"{prefix} @ ({lat}, {lng}):")
        saved, rejected = process_location(prefix, lat, lng, manifest)
        total_saved += saved
        total_rejected += rejected
        time.sleep(0.3)

    write_manifest(manifest)

    elapsed = time.time() - start
    print("\n" + "=" * 50)
    print("Night Download Summary")
    print("=" * 50)
    print(f"  Saved night images: {total_saved}")
    print(f"  Rejected for brightness: {total_rejected}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
