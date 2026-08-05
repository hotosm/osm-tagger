"""Image quality gate: brightness and blur heuristics.

Runs before the VLM to skip images that are too dark or too blurry.

Thresholds calibrated against old_images dataset:
  BRIGHTNESS_THRESHOLD = 55
    Catches: LONDON_NIGHT_2/3 (44-45), MOSCOW_NIGHT_3 (41), ROME_NIGHT_1/2/3 (47-51),
             SAOPAULO_NIGHT_1/2/3 (20-35), TALLINN_NIGHT (54).
    Passes:  Well-lit night streets (MOSCOW_NIGHT_1/2: 65-75, SEOUL_NIGHT: 65-78)
             - bright enough for the VLM to process.

  BLUR_THRESHOLD = 100
    Catches: CHAD_UNPAVED3 (67), SUDAN_AMBIGUOUS2 (57).
    Passes:  Slightly soft paved roads (IRAN: 189, AFGHAN_PAVED3: 171, ICELAND: 188)
             - still classifiable; false-positive threshold was 200.

To calibrate for a new dataset: python quality_gate.py <folder>
"""

import sys

import numpy as np
from PIL import Image, ImageFilter, ImageStat

BRIGHTNESS_THRESHOLD = 55   # below → dark
BLUR_THRESHOLD = 100        # below → blurry


def check(image_path, brightness_thresh=BRIGHTNESS_THRESHOLD, blur_thresh=BLUR_THRESHOLD):
    """
    Evaluate image quality.

    Returns a dict:
      passed       : bool
      reason       : "ok" | "dark" | "blurry"
      brightness   : float  (mean luminance, 0–255)
      blur_score   : float  (edge variance; higher = sharper)
    """
    img = Image.open(image_path).convert("RGB")
    gray = img.convert("L")

    brightness = ImageStat.Stat(gray).mean[0]
    edges = gray.filter(ImageFilter.FIND_EDGES)
    blur_score = float(np.array(edges, dtype=np.float32).var())

    if brightness < brightness_thresh:
        return {
            "passed": False,
            "reason": "dark",
            "brightness": round(brightness, 1),
            "blur_score": round(blur_score, 1),
        }
    if blur_score < blur_thresh:
        return {
            "passed": False,
            "reason": "blurry",
            "brightness": round(brightness, 1),
            "blur_score": round(blur_score, 1),
        }
    return {
        "passed": True,
        "reason": "ok",
        "brightness": round(brightness, 1),
        "blur_score": round(blur_score, 1),
    }


# ---------------------------------------------------------------------------
# CLI helper: python quality_gate.py <folder>  → print scores for all images
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import glob
    import os

    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = sorted(
        f for ext in ("*.png", "*.jpg", "*.jpeg")
        for f in glob.glob(os.path.join(folder, ext))
    )
    if not paths:
        print(f"No images found in {folder}")
        sys.exit(0)

    print(f"{'Image':<40} {'Brightness':>10} {'Blur':>10} {'Passed':>8} {'Reason':>8}")
    print("-" * 80)
    for p in paths:
        r = check(p)
        name = os.path.basename(p)
        print(f"{name:<40} {r['brightness']:>10.1f} {r['blur_score']:>10.1f} {str(r['passed']):>8} {r['reason']:>8}")
