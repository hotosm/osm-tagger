"""Re-download an image set from a provenance manifest.csv.

Given a manifest produced by download_images.py / download_night.py (columns
include `filename` and `mapillary_image_id`), this re-fetches each exact image
from the Mapillary Graph API by ID and saves it under the original filename.

Mapillary thumbnail URLs are short-lived signed URLs, so we resolve a fresh
`thumb_1024_url` per image ID at fetch time rather than trusting the stored URL.

Usage:
  python refetch_from_manifest.py <manifest.csv> [output_dir]

Requires ACCESS_TOKEN_MAP in .env. Rows with mapillary_image_id == UNRECORDED are
skipped (the original volunteer set has no IDs - see ../REPRODUCING.md).
"""

import csv
import io
import os
import sys
import time

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

TOKEN = os.environ.get("ACCESS_TOKEN_MAP")
GRAPH_URL = "https://graph.mapillary.com/images/{id}"


def resolve_thumb_url(image_id):
    resp = requests.get(
        GRAPH_URL.format(id=image_id),
        params={"access_token": TOKEN, "fields": "thumb_1024_url"},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json().get("thumb_1024_url")


def save_png(url, out_path):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(out_path, format="PNG")


def main():
    if not TOKEN:
        print("Error: set ACCESS_TOKEN_MAP in your .env file.")
        return
    if len(sys.argv) < 2:
        print("Usage: python refetch_from_manifest.py <manifest.csv> [output_dir]")
        return

    manifest_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "refetched_images"
    os.makedirs(out_dir, exist_ok=True)

    with open(manifest_path) as fh:
        rows = list(csv.DictReader(fh))

    saved = skipped = failed = 0
    for row in rows:
        fname = row.get("filename", "")
        image_id = (row.get("mapillary_image_id") or "").strip()
        if not image_id or image_id.upper() == "UNRECORDED":
            print(f"  [SKIP] {fname}: no image ID recorded")
            skipped += 1
            continue
        out_path = os.path.join(out_dir, fname)
        try:
            url = resolve_thumb_url(image_id)
            if not url:
                raise ValueError("no thumb_1024_url returned")
            save_png(url, out_path)
            print(f"  [OK]   {out_path}  (id={image_id})")
            saved += 1
        except Exception as e:
            print(f"  [FAIL] {fname} (id={image_id}): {e}")
            failed += 1
        time.sleep(0.3)  # be polite to the API

    print("\n" + "=" * 50)
    print(f"Re-fetched: {saved}   Skipped (no ID): {skipped}   Failed: {failed}")
    print(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
