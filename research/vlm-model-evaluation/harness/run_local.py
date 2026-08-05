"""
HOT OSM Road Classification Pipeline - Final
=============================================

Classifies street-level imagery into OpenStreetMap-compatible surface and
smoothness tags using Qwen2.5-VL-7B, served locally via Ollama.

Pipeline stages (applied in order, any stage can reject the image):

    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ 1. Quality   │──▶│ 2. VLM       │──▶│ 3. Parse     │──▶│ 4. Filter &  │
    │    gate      │   │    classify  │   │    response  │   │    emit tags │
    └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
         │ reject            │                                      │ reject
         │  too_dark         │                                      │  no_road
         │  too_blurry       │                                      │  low_confidence
         ▼                   ▼                                      ▼
       CSV row            CSV row                              OSM-ready tags

Every image produces exactly one CSV row, flagged as either:
    - rejected=no  → accepted, ready for OSM write
    - rejected=yes → held back, with a machine-readable reject_reason

Usage:
    python run_local.py [model] [folder]

Examples:
    python run_local.py qwen2.5vl:7b new_images
    python run_local.py llava        old_images
"""

import glob
import json
import os
import re
import sys
import time

import ollama
import pandas as pd

import quality_gate


# =============================================================================
# OSM SCHEMA - final allowed vocabulary for surface & smoothness tags
# =============================================================================
# The VLM is constrained to these values via the prompt. Anything outside this
# set is treated as an invalid output. Lists mirror OSM wiki specs for
# surface=* and smoothness=*.

ALLOWED_SURFACES = [
    "asphalt", "concrete", "paving_stones", "cobblestone",
    "gravel", "compacted", "dirt", "grass", "sand",
    "wood", "metal", "paved", "unpaved",
]

ALLOWED_SMOOTHNESS = [
    "excellent", "good", "intermediate", "bad", "very_bad",
]

REJECT_REASONS = {
    "too_dark":       "Image brightness below quality-gate threshold",
    "too_blurry":     "Image blur score below quality-gate threshold",
    "no_road":        "VLM determined no drivable road is visible",
    "low_confidence": "VLM confidence below CONFIDENCE_THRESHOLD",
}


# =============================================================================
# Configuration
# =============================================================================

CONFIDENCE_THRESHOLD = 0.5       # minimum confidence for an output to reach OSM
DEFAULT_MODEL        = "qwen2.5vl:7b"

PROMPT = f"""You are an OpenStreetMap road classifier. Respond with ONLY a JSON object - no markdown, no code fences, no extra text.

Step 1 - road_present: Is a drivable road or track the PRIMARY subject?
Set "no" for: aerial/satellite views, construction sites, pedestrian-only footpaths, building interiors, or scenes with no visible road surface.

Step 2 - If road_present is "yes", classify:
surface: one of {json.dumps(ALLOWED_SURFACES)}
  GRAVEL TIP: loose stones/aggregate (tan or grey), clearly unpaved - use "gravel".
  DIRT TIP: bare earth/mud with no stones - use "dirt".
  COMPACTED TIP: packed earth or fine gravel, smoother than gravel but still unpaved.
smoothness: one of {json.dumps(ALLOWED_SMOOTHNESS)}

If road_present is "no", set surface and smoothness to null.

confidence: float 0.0–1.0 (your certainty across all fields combined).

Output format (strictly):
{{"road_present": "yes" or "no", "surface": "..." or null, "smoothness": "..." or null, "confidence": 0.0}}"""


# =============================================================================
# Helpers
# =============================================================================

def find_images(folder):
    files = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        files.extend(glob.glob(os.path.join(folder, ext)))
    return sorted(files)


def coerce_confidence(raw):
    """Accept float/int, or legacy strings 'high'/'medium'/'low' from older prompts."""
    if raw is None:
        return None
    try:
        val = float(raw)
        return round(max(0.0, min(1.0, val)), 3)
    except (ValueError, TypeError):
        return {"high": 0.85, "medium": 0.6, "low": 0.2}.get(str(raw).lower())


# =============================================================================
# Stage 1 - Quality gate
# =============================================================================
# Dark or blurry images are the top source of VLM hallucinations: the model
# returns a confident surface label for unreadable pixels. Cheaper and safer
# to reject at the gate than to spend inference and then write garbage to OSM.
# Thresholds live in quality_gate.py, tuned on the Week 5 edge-case set.

def stage_1_quality_gate(image_path):
    qg = quality_gate.check(image_path)
    return {
        "passed":     qg["passed"],
        "reason":     qg["reason"],      # "" if passed, else "too_dark" / "too_blurry"
        "brightness": qg["brightness"],
        "blur_score": qg["blur_score"],
    }


# =============================================================================
# Stage 2 - VLM classification
# =============================================================================
# Qwen2.5-VL-7B won Week 5's head-to-head against LLaVA on surface accuracy
# (especially gravel/compacted/dirt distinctions). Served locally via Ollama:
# no API cost, no rate limits, no image egress - compatible with OSM's manual
# write flow and with humanitarian-data locality requirements.

def stage_2_vlm_classify(model, image_path):
    abs_path = os.path.abspath(image_path)
    start = time.time()
    response = ollama.chat(
        model=model,
        messages=[{
            "role":    "user",
            "content": PROMPT,
            "images":  [abs_path],
        }],
        options={"temperature": 0},   # deterministic outputs for reproducibility
    )
    latency = round(time.time() - start, 2)

    # Ollama's response shape differs across SDK versions.
    try:
        raw = response["message"]["content"]
    except (TypeError, KeyError):
        raw = response.message.content

    return {"raw": raw, "latency_sec": latency}


# =============================================================================
# Stage 3 - Parse response
# =============================================================================
# Even with "no markdown" in the prompt, VLMs occasionally wrap JSON in code
# fences or prepend an explanation. Three fallback levels:
#   (a) strict json.loads on the stripped text
#   (b) json.loads after removing ```json / ``` fences
#   (c) regex-extract the first {...} block and parse that
# If all three fail, we flag json_valid=no and let downstream inspect raw_output.

def stage_3_parse_response(raw_text):
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    try:
        return {"parsed": json.loads(text), "valid": True}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return {"parsed": json.loads(match.group()), "valid": True}
        except json.JSONDecodeError:
            pass
    return {"parsed": {}, "valid": False}


# =============================================================================
# Stage 4 - Filter & emit OSM tags
# =============================================================================
# Rejection rules, applied in order:
#   (a) road_present == "no"           → hallucination guard for non-road scenes
#                                         (aerial views, interiors, footpaths)
#   (b) confidence < CONFIDENCE_THRESHOLD → below 0.5 the model's accuracy
#                                           dropped below acceptable on Week 5;
#                                           rejecting protects OSM tag quality
# Accepted rows carry surface + smoothness in the OSM vocabulary above.
# Rejected rows preserve the raw VLM output in raw_output for later review.

def stage_4_apply_filters(parsed, confidence_threshold):
    road_present = str(parsed.get("road_present", "")).lower()
    surface      = parsed.get("surface")    if road_present == "yes" else "none"
    smoothness   = parsed.get("smoothness") if road_present == "yes" else "none"
    confidence   = coerce_confidence(parsed.get("confidence"))

    if road_present == "no":
        rejected, reason = "yes", "no_road"
    elif confidence is not None and confidence < confidence_threshold:
        rejected, reason = "yes", "low_confidence"
    else:
        rejected, reason = "no", ""

    return {
        "road_present":  road_present or "unknown",
        "surface":       surface or "",
        "smoothness":    smoothness or "",
        "confidence":    confidence,
        "rejected":      rejected,
        "reject_reason": reason,
    }


# =============================================================================
# Orchestrator - run all four stages on a single image
# =============================================================================

def run_pipeline(model, image_path):
    base = {
        "image":          os.path.basename(image_path),
        "quality_passed": "",
        "quality_reason": "",
        "brightness":     None,
        "blur_score":     None,
        "correct":        "",   # reserved for manual ground-truth annotation
        "notes":          "",   # reserved for manual reviewer notes
    }

    # --- Stage 1: quality gate ---
    qg = stage_1_quality_gate(image_path)
    base.update({
        "quality_passed": "yes" if qg["passed"] else "no",
        "quality_reason": qg["reason"],
        "brightness":     qg["brightness"],
        "blur_score":     qg["blur_score"],
    })
    if not qg["passed"]:
        # Skip VLM entirely - return a row rejected by the quality gate.
        return {**base,
                "road_present":  "n/a",
                "surface":       "n/a",
                "smoothness":    "n/a",
                "confidence":    None,
                "rejected":      "yes",
                "reject_reason": qg["reason"],
                "latency_sec":   0.0,
                "json_valid":    "n/a",
                "raw_output":    ""}

    # --- Stage 2: VLM classification ---
    vlm = stage_2_vlm_classify(model, image_path)

    # --- Stage 3: parse response ---
    parsed = stage_3_parse_response(vlm["raw"])

    # --- Stage 4: filter & emit tags ---
    tagged = stage_4_apply_filters(parsed["parsed"], CONFIDENCE_THRESHOLD)

    return {**base,
            **tagged,
            "latency_sec": vlm["latency_sec"],
            "json_valid":  "yes" if parsed["valid"] else "no",
            "raw_output":  vlm["raw"][:200]}


# =============================================================================
# CLI entry point
# =============================================================================

def main():
    model  = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    folder = sys.argv[2] if len(sys.argv) > 2 else "."

    images = find_images(folder)
    if not images:
        print(f"No images found in '{folder}'")
        return

    os.makedirs("results", exist_ok=True)
    safe_model   = model.replace(":", "_").replace("/", "_")
    folder_tag   = os.path.basename(os.path.normpath(folder))
    results_path = os.path.join("results", f"results_local_{safe_model}_{folder_tag}.csv")

    print(f"Model    : {model}")
    print(f"Folder   : {folder}")
    print(f"Images   : {len(images)}")
    print(f"Conf thr : {CONFIDENCE_THRESHOLD}\n")

    results = []
    total_start = time.time()

    for i, img in enumerate(images, 1):
        print(f"[{i:>3}/{len(images)}] {os.path.basename(img):<40}", end="", flush=True)
        try:
            row = run_pipeline(model, img)
        except Exception as e:
            print(f"ERROR: {e}")
            continue
        results.append(row)
        if row["quality_passed"] == "no":
            print(f"SKIPPED ({row['quality_reason']})  brightness={row['brightness']}")
        else:
            print(f"{row['latency_sec']}s  road={row['road_present']}  "
                  f"surface={row['surface']}  conf={row['confidence']}  "
                  f"rejected={row['rejected']}")

    total_time = time.time() - total_start
    df = pd.DataFrame(results)
    df.to_csv(results_path, index=False)
    print(f"\nSaved → {results_path}")

    # --- Summary (matches Week 5/6 precision/coverage reporting format) ---
    n            = len(df)
    quality_fail = (df["quality_passed"] == "no").sum()
    no_road      = (df["road_present"]   == "no").sum()
    valid_json   = (df["json_valid"]     == "yes").sum()
    rejected     = (df["rejected"]       == "yes").sum()
    accepted     = n - rejected
    processed    = n - quality_fail
    avg_lat      = df[df["quality_passed"] == "yes"]["latency_sec"].mean() if processed else 0

    print("\n--- Summary ---")
    print(f"Model               : {model}")
    print(f"Total images        : {n}")
    print(f"Quality filtered    : {quality_fail}  (dark/blurry - skipped)")
    print(f"Processed by VLM    : {processed}")
    print(f"road_present = no   : {no_road}  (hallucination guard triggered)")
    print(f"Valid JSON          : {valid_json}/{processed}")
    print(f"Rejected (total)    : {rejected}")
    print(f"Accepted (OSM-ready): {accepted}")
    print(f"Acceptance rate     : {accepted/n*100:.1f}%" if n else "Acceptance rate     : n/a")
    print(f"Avg latency         : {avg_lat:.2f}s")
    print(f"Total time          : {total_time:.1f}s")


if __name__ == "__main__":
    main()
