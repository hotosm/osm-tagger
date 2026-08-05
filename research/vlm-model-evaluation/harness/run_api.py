"""Vision model road classifier via API.

Providers:
  openai      - GPT-4o-mini        (OPENAI_API_KEY)
  openrouter  - Qwen2.5-VL-7B      (OPENROUTER_API_KEY)

Usage:
  python run_api.py [provider] [folder]

Examples:
  python run_api.py openrouter old_images
  python run_api.py openai old_images

Pipeline per image:
  1. Quality gate  → skip if dark or blurry
  2. VLM call      → structured JSON with road_present + numeric confidence
  3. JSON parsing  → strip markdown fences, fallback regex
  4. Filtering     → reject if road_present=no OR confidence < threshold
"""

import base64
import glob
import json
import os
import re
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

import quality_gate

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.5   # reject classifications below this

PROVIDERS = {
    "openai": {
        "base_url": None,
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "cost_per_image": 0.005,
    },
    # Qwen2.5-VL-7B has no OpenRouter endpoint - using Qwen3-VL-8B (same family,
    # direct successor). This is what produced the existing results_openrouter.csv.
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPEN_ROUTERAPI",
        "model": "qwen/qwen3-vl-8b-instruct",
        "cost_per_image": 0.002,
    },
    # Actual Qwen2.5-VL-7B, served from a Colab notebook via vLLM + ngrok.
    # Set COLAB_BASE_URL to the ngrok URL printed by the notebook (e.g.
    # https://abc123.ngrok-free.app/v1). Model is free; set COLAB_API_KEY to any string.
    "colab": {
        "base_url": os.environ.get("COLAB_BASE_URL"),
        "env_key": "COLAB_API_KEY",
        "model": "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        "cost_per_image": 0.0,
    },
}

PROMPT = """You are an OpenStreetMap road classifier. Respond with ONLY a JSON object - no markdown, no code fences, no extra text.

Step 1 - road_present: Is a drivable road or track the PRIMARY subject?
Set "no" for: aerial/satellite views, construction sites, pedestrian-only footpaths, building interiors, or scenes with no visible road surface.

Step 2 - If road_present is "yes", classify:
surface: one of ["asphalt","concrete","paving_stones","cobblestone","gravel","compacted","dirt","grass","sand","wood","metal","paved","unpaved"]
  GRAVEL TIP: loose stones/aggregate (tan or grey), clearly unpaved - use "gravel".
  DIRT TIP: bare earth/mud with no stones - use "dirt".
  COMPACTED TIP: packed earth or fine gravel, smoother than gravel but still unpaved.
smoothness: one of ["excellent","good","intermediate","bad","very_bad"]

If road_present is "no", set surface and smoothness to null.

confidence: float 0.0–1.0 (your certainty across all fields combined).

Output format (strictly):
{"road_present": "yes" or "no", "surface": "..." or null, "smoothness": "..." or null, "confidence": 0.0}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_images(folder):
    files = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        files.extend(glob.glob(os.path.join(folder, ext)))
    return sorted(files)


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_json(text):
    """Strip markdown fences then parse JSON; regex fallback."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group()), True
        except json.JSONDecodeError:
            pass
    return {}, False


def coerce_confidence(raw):
    """Accept float, int, or legacy strings like 'high'/'medium'/'low'."""
    if raw is None:
        return None
    try:
        val = float(raw)
        return round(max(0.0, min(1.0, val)), 3)
    except (ValueError, TypeError):
        return {"high": 0.85, "medium": 0.6, "low": 0.2}.get(str(raw).lower())


def classify_image(client, model, image_path):
    # --- Quality gate ---
    qg = quality_gate.check(image_path)
    base = {
        "image": os.path.basename(image_path),
        "quality_passed": "yes" if qg["passed"] else "no",
        "quality_reason": qg["reason"],
        "brightness": qg["brightness"],
        "blur_score": qg["blur_score"],
        "correct": "",
        "notes": "",
    }

    if not qg["passed"]:
        return {**base,
                "road_present": "n/a", "surface": "n/a", "smoothness": "n/a",
                "confidence": None, "rejected": "yes", "reject_reason": qg["reason"],
                "latency_sec": 0.0, "json_valid": "n/a", "raw_output": ""}

    # --- VLM call ---
    b64 = encode_image(image_path)
    mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=120,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}},
            ],
        }],
    )
    latency = round(time.time() - start, 2)
    raw = response.choices[0].message.content

    # --- Parse ---
    parsed, valid = parse_json(raw)
    road_present = str(parsed.get("road_present", "")).lower()
    surface = parsed.get("surface") if road_present == "yes" else "none"
    smoothness = parsed.get("smoothness") if road_present == "yes" else "none"
    confidence = coerce_confidence(parsed.get("confidence"))

    # --- Filter ---
    if road_present == "no":
        rejected, reject_reason = "yes", "no_road"
    elif confidence is not None and confidence < CONFIDENCE_THRESHOLD:
        rejected, reject_reason = "yes", "low_confidence"
    else:
        rejected, reject_reason = "no", ""

    return {**base,
            "road_present": road_present or "unknown",
            "surface": surface or "",
            "smoothness": smoothness or "",
            "confidence": confidence,
            "rejected": rejected,
            "reject_reason": reject_reason,
            "latency_sec": latency,
            "json_valid": "yes" if valid else "no",
            "raw_output": raw[:200]}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    provider_name = sys.argv[1] if len(sys.argv) > 1 else "openai"
    if provider_name not in PROVIDERS:
        print(f"Unknown provider '{provider_name}'. Choose: {', '.join(PROVIDERS)}")
        return

    provider = PROVIDERS[provider_name]
    api_key = os.environ.get(provider["env_key"])
    if not api_key:
        print(f"Error: set {provider['env_key']} in your .env file.")
        return
    if provider_name == "colab" and not provider["base_url"]:
        print("Error: set COLAB_BASE_URL in your .env file to the ngrok URL from Colab "
              "(e.g. https://abc123.ngrok-free.app/v1).")
        return

    kwargs = {"api_key": api_key}
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]
    client = OpenAI(**kwargs)
    model = provider["model"]

    folder = sys.argv[2] if len(sys.argv) > 2 else "."
    images = find_images(folder) if os.path.isdir(folder) else [folder]
    if not images:
        print(f"No images found in '{folder}'")
        return

    print(f"Provider : {provider_name}")
    print(f"Model    : {model}")
    print(f"Images   : {len(images)}")
    print(f"Conf thr : {CONFIDENCE_THRESHOLD}\n")

    results = []
    total_start = time.time()

    for i, img in enumerate(images, 1):
        print(f"[{i:>3}/{len(images)}] {os.path.basename(img):<40}", end="", flush=True)
        row = classify_image(client, model, img)
        results.append(row)
        if row["quality_passed"] == "no":
            print(f"SKIPPED ({row['quality_reason']})  brightness={row['brightness']}")
        else:
            print(f"{row['latency_sec']}s  road={row['road_present']}  "
                  f"surface={row['surface']}  conf={row['confidence']}  "
                  f"rejected={row['rejected']}")

    total_time = time.time() - total_start
    df = pd.DataFrame(results)
    os.makedirs("results", exist_ok=True)
    folder_tag = os.path.basename(os.path.normpath(folder)) if os.path.isdir(folder) else "single"
    results_path = os.path.join("results", f"results_{provider_name}_{folder_tag}.csv")
    df.to_csv(results_path, index=False)
    print(f"\nSaved → {results_path}")

    # Summary
    n = len(df)
    quality_fail = (df["quality_passed"] == "no").sum()
    no_road = (df["road_present"] == "no").sum()
    valid_json = (df["json_valid"] == "yes").sum()
    rejected = (df["rejected"] == "yes").sum()
    processed = n - quality_fail
    avg_lat = df[df["quality_passed"] == "yes"]["latency_sec"].mean() if processed else 0

    print("\n--- Summary ---")
    print(f"Total images        : {n}")
    print(f"Quality filtered    : {quality_fail}  (dark/blurry - skipped)")
    print(f"Processed by VLM    : {processed}")
    print(f"road_present = no   : {no_road}  (hallucination guard triggered)")
    print(f"Valid JSON           : {valid_json}/{processed}")
    print(f"Rejected (total)    : {rejected}")
    print(f"Avg latency         : {avg_lat:.2f}s")
    print(f"Total time          : {total_time:.1f}s")
    print(f"Est. cost           : ${n * provider['cost_per_image']:.3f}  "
          f"(${provider['cost_per_image'] * 1000:.2f} per 1000)")


if __name__ == "__main__":
    main()
