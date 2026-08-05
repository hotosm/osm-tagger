"""Compare two model result CSVs side by side.

Usage:
  python compare.py <csv_a> <csv_b>

Examples:
  python compare.py results/results_local_llava.csv results/results_openrouter.csv

Produces:
  - Overall metrics table (JSON validity, hallucination rate, gravel accuracy, etc.)
  - Quality gate summary
  - Per-category accuracy breakdown
  - Full per-image side-by-side table
"""

import os
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Ground-truth category inference from filename
# ---------------------------------------------------------------------------
# Categories and what "correct" means for each:
#   no_road      → road_present should be "no"  (hallucination test)
#   gravel       → surface should be in UNPAVED_SURFACES
#   unpaved      → surface should be in UNPAVED_SURFACES
#   ambiguous    → no hard ground truth; shown for reference
#   night        → quality gate should reject (quality_passed = "no")
#   blur         → quality gate should reject (quality_passed = "no")
#   cobblestone  → surface should be "cobblestone" or "paving_stones"
#   paved        → surface should be in PAVED_SURFACES

UNPAVED_SURFACES = {"gravel", "dirt", "compacted", "unpaved", "sand", "grass"}
PAVED_SURFACES   = {"asphalt", "concrete", "paving_stones", "cobblestone", "paved", "wood", "metal"}
COBBLE_SURFACES  = {"cobblestone", "paving_stones"}

NO_ROAD_KEYWORDS   = ("NOROAD", "AERIAL", "PATH")
GRAVEL_KEYWORDS    = ("GRAVEL", "NEPAL")
UNPAVED_KEYWORDS   = ("UNPAVED", "BRAZIL", "CHAD", "NIGERIA", "SUDAN_UNPAVED")
AMBIGUOUS_KEYWORDS = ("AMBIGUOUS", "MONGOLIA", "SUDAN_AMBIGUOUS")
NIGHT_KEYWORDS     = ("NIGHT",)
BLUR_KEYWORDS      = ("BLUR",)
WET_KEYWORDS       = ("WET",)
COBBLE_KEYWORDS    = ("COBBLESTONE", "COBBLE", "PAVERS", "EDINBURGH", "PARIS", "PORTO")
PAVED_KEYWORDS     = ("PAVED", "ASPHALT", "NYC", "ICELAND", "INDIA", "IRAN", "IRAQ",
                      "RWANDA", "PERU", "MADAGASCAR", "BOLIVIA_PAVED", "AFGHAN")


def categorize(image_name):
    n = image_name.upper()
    if any(k in n for k in NO_ROAD_KEYWORDS):
        return "no_road"
    if any(k in n for k in GRAVEL_KEYWORDS):
        return "gravel"
    if any(k in n for k in UNPAVED_KEYWORDS):
        return "unpaved"
    if any(k in n for k in AMBIGUOUS_KEYWORDS):
        return "ambiguous"
    if any(k in n for k in NIGHT_KEYWORDS):
        return "night"
    if any(k in n for k in BLUR_KEYWORDS):
        return "blur"
    if any(k in n for k in WET_KEYWORDS):
        return "wet"
    if any(k in n for k in COBBLE_KEYWORDS):
        return "cobblestone"
    if any(k in n for k in PAVED_KEYWORDS):
        return "paved"
    return "other"


def is_correct(row, category):
    """Return True/False/None (None = ambiguous/unknown)."""
    if category == "no_road":
        return row.get("road_present") == "no" or row.get("quality_passed") == "no"
    if category in ("gravel", "unpaved"):
        surf = str(row.get("surface", "")).lower()
        return surf in UNPAVED_SURFACES
    if category == "cobblestone":
        surf = str(row.get("surface", "")).lower()
        return surf in COBBLE_SURFACES
    if category == "paved":
        surf = str(row.get("surface", "")).lower()
        return surf in PAVED_SURFACES
    if category in ("night", "blur"):
        return row.get("quality_passed") == "no"
    return None  # ambiguous / wet / other - no hard ground truth


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_csv(path, label):
    if not os.path.exists(path):
        print(f"Missing: {path}")
        sys.exit(1)
    df = pd.read_csv(path)
    df["_label"] = label
    df["_category"] = df["image"].apply(categorize)
    return df


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def pct(num, denom):
    if denom == 0:
        return "n/a"
    return f"{100 * num / denom:.0f}%"


def count_pct(num, denom):
    return f"{num}/{denom} ({pct(num, denom)})"


def hallucination_rate(df):
    """% of no_road images where model hallucinated a road (road_present != 'no')."""
    noroad = df[df["_category"] == "no_road"]
    if noroad.empty:
        return None, 0, 0
    # Hallucinated = said road_present=yes AND quality gate didn't catch it
    hallucinated = noroad[
        (noroad["road_present"] != "no") & (noroad["quality_passed"] != "no")
    ]
    return len(hallucinated) / len(noroad), len(hallucinated), len(noroad)


def gravel_accuracy(df):
    """% of gravel+unpaved images correctly classified as non-paved surface."""
    subset = df[df["_category"].isin(["gravel", "unpaved"])]
    if subset.empty:
        return None, 0, 0
    correct = subset[subset["surface"].str.lower().isin(UNPAVED_SURFACES)]
    return len(correct) / len(subset), len(correct), len(subset)


def quality_filter_rate(df):
    """% of night+blur images caught by quality gate."""
    subset = df[df["_category"].isin(["night", "blur"])]
    if subset.empty:
        return None, 0, 0
    caught = subset[subset["quality_passed"] == "no"]
    return len(caught) / len(subset), len(caught), len(subset)


def json_validity(df):
    valid = (df["json_valid"] == "yes").sum()
    total = len(df[df["quality_passed"] == "yes"])
    return valid, total


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_header(title):
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_overall(df_a, label_a, df_b, label_b):
    print_header("OVERALL METRICS")

    metrics = []

    n_a, n_b = len(df_a), len(df_b)
    metrics.append(("Images", str(n_a), str(n_b)))

    qf_a = (df_a["quality_passed"] == "no").sum()
    qf_b = (df_b["quality_passed"] == "no").sum()
    metrics.append(("Quality filtered", count_pct(qf_a, n_a), count_pct(qf_b, n_b)))

    jv_a, jt_a = json_validity(df_a)
    jv_b, jt_b = json_validity(df_b)
    metrics.append(("Valid JSON", count_pct(jv_a, jt_a), count_pct(jv_b, jt_b)))

    h_a, ha_n, ha_d = hallucination_rate(df_a)
    h_b, hb_n, hb_d = hallucination_rate(df_b)
    metrics.append(("Hallucination rate",
                    f"{count_pct(ha_n, ha_d)} hallucinated" if ha_d else "n/a",
                    f"{count_pct(hb_n, hb_d)} hallucinated" if hb_d else "n/a"))

    g_a, ga_n, ga_d = gravel_accuracy(df_a)
    g_b, gb_n, gb_d = gravel_accuracy(df_b)
    metrics.append(("Gravel/unpaved accuracy",
                    count_pct(ga_n, ga_d) if ga_d else "n/a",
                    count_pct(gb_n, gb_d) if gb_d else "n/a"))

    qr_a, qra_n, qra_d = quality_filter_rate(df_a)
    qr_b, qrb_n, qrb_d = quality_filter_rate(df_b)
    metrics.append(("Night/blur filtered",
                    count_pct(qra_n, qra_d) if qra_d else "n/a",
                    count_pct(qrb_n, qrb_d) if qrb_d else "n/a"))

    rej_a = (df_a["rejected"] == "yes").sum()
    rej_b = (df_b["rejected"] == "yes").sum()
    metrics.append(("Total rejected", count_pct(rej_a, n_a), count_pct(rej_b, n_b)))

    try:
        lat_a = df_a[df_a["quality_passed"] == "yes"]["latency_sec"].astype(float).mean()
        lat_b = df_b[df_b["quality_passed"] == "yes"]["latency_sec"].astype(float).mean()
        metrics.append(("Avg latency (s)", f"{lat_a:.2f}", f"{lat_b:.2f}"))
    except Exception:
        pass

    col_w = 36
    print(f"\n{'Metric':<{col_w}} {label_a:>18} {label_b:>18}")
    print("-" * (col_w + 40))
    for label, va, vb in metrics:
        print(f"{label:<{col_w}} {va:>18} {vb:>18}")


def print_category_breakdown(df_a, label_a, df_b, label_b):
    print_header("PER-CATEGORY ACCURACY")

    categories = ["no_road", "gravel", "unpaved", "paved", "cobblestone", "night", "blur", "ambiguous", "wet"]
    col_w = 14

    print(f"\n{'Category':<14} {'Count_A':>8} {'Correct_A':>10} {'Count_B':>8} {'Correct_B':>10}")
    print("-" * 56)

    for cat in categories:
        rows_a = df_a[df_a["_category"] == cat]
        rows_b = df_b[df_b["_category"] == cat]
        if rows_a.empty and rows_b.empty:
            continue

        correct_a = sum(1 for _, r in rows_a.iterrows() if is_correct(r, cat) is True)
        correct_b = sum(1 for _, r in rows_b.iterrows() if is_correct(r, cat) is True)

        na, nb = len(rows_a), len(rows_b)
        ca_str = count_pct(correct_a, na) if na and is_correct(rows_a.iloc[0], cat) is not None else f"{na} (no GT)"
        cb_str = count_pct(correct_b, nb) if nb and is_correct(rows_b.iloc[0], cat) is not None else f"{nb} (no GT)"

        print(f"{cat:<14} {na:>8} {ca_str:>10} {nb:>8} {cb_str:>10}")


def print_per_image(df_a, label_a, df_b, label_b):
    print_header("PER-IMAGE COMPARISON")

    merged = pd.merge(
        df_a[["image", "_category", "road_present", "surface", "smoothness",
              "confidence", "quality_passed", "rejected", "json_valid"]],
        df_b[["image", "_category", "road_present", "surface", "smoothness",
              "confidence", "quality_passed", "rejected", "json_valid"]],
        on=["image", "_category"], suffixes=(f"_{label_a[:4]}", f"_{label_b[:4]}")
    )

    if merged.empty:
        # Fall back to showing each separately if filenames differ
        print(f"\n  (No matching image names between the two CSVs.)")
        print(f"  {label_a} images: {len(df_a)}")
        print(f"  {label_b} images: {len(df_b)}")
        return

    la, lb = label_a[:4], label_b[:4]
    surf_a = f"surface_{la}"
    surf_b = f"surface_{lb}"
    road_a = f"road_present_{la}"
    road_b = f"road_present_{lb}"
    conf_a = f"confidence_{la}"
    conf_b = f"confidence_{lb}"
    rej_a  = f"rejected_{la}"
    rej_b  = f"rejected_{lb}"

    print(f"\n{'Image':<32} {'Cat':<12} "
          f"{'Road_A':>7} {'Surf_A':<14} {'Conf_A':>7} "
          f"{'Road_B':>7} {'Surf_B':<14} {'Conf_B':>7} "
          f"{'Match':>6}")
    print("-" * 110)

    for _, row in merged.sort_values("_category").iterrows():
        sa = str(row.get(surf_a, ""))
        sb = str(row.get(surf_b, ""))
        ra = str(row.get(road_a, ""))
        rb = str(row.get(road_b, ""))
        ca = row.get(conf_a)
        cb = row.get(conf_b)
        ca_str = f"{float(ca):.2f}" if ca is not None and str(ca) not in ("", "nan", "None") else "?"
        cb_str = f"{float(cb):.2f}" if cb is not None and str(cb) not in ("", "nan", "None") else "?"
        match = "YES" if sa == sb else "no"
        print(f"{row['image']:<32} {row['_category']:<12} "
              f"{ra:>7} {sa:<14} {ca_str:>7} "
              f"{rb:>7} {sb:<14} {cb_str:>7} "
              f"{match:>6}")

    surface_agree = (merged[surf_a] == merged[surf_b]).sum()
    road_agree    = (merged[road_a] == merged[road_b]).sum()
    print("-" * 110)
    print(f"Surface agreement: {count_pct(surface_agree, len(merged))}")
    print(f"Road-present agreement: {count_pct(road_agree, len(merged))}")


def print_hallucination_detail(df_a, label_a, df_b, label_b):
    print_header("HALLUCINATION TEST DETAIL  (no_road images)")

    for df, label in [(df_a, label_a), (df_b, label_b)]:
        subset = df[df["_category"] == "no_road"]
        if subset.empty:
            continue
        print(f"\n  {label}:")
        print(f"  {'Image':<36} {'Quality':>8} {'RoadPresent':>12} {'Surface':<14} {'Rejected':>9}")
        print(f"  {'-'*82}")
        for _, row in subset.iterrows():
            hallu = "HALLUCINATION" if (
                row.get("road_present") not in ("no", "n/a") and
                row.get("quality_passed") != "no"
            ) else "ok"
            print(f"  {row['image']:<36} {str(row.get('quality_passed','?')):>8} "
                  f"{str(row.get('road_present','?')):>12} "
                  f"{str(row.get('surface','?')):<14} "
                  f"{hallu:>9}")


def print_gravel_detail(df_a, label_a, df_b, label_b):
    print_header("GRAVEL / UNPAVED DETECTION DETAIL")

    for df, label in [(df_a, label_a), (df_b, label_b)]:
        subset = df[df["_category"].isin(["gravel", "unpaved"])]
        if subset.empty:
            continue
        print(f"\n  {label}:")
        print(f"  {'Image':<36} {'Cat':<10} {'Surface':<16} {'Correct':>8}")
        print(f"  {'-'*74}")
        for _, row in subset.iterrows():
            surf = str(row.get("surface", "")).lower()
            correct = "YES" if surf in UNPAVED_SURFACES else "WRONG"
            print(f"  {row['image']:<36} {row['_category']:<10} {surf:<16} {correct:>8}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        # Try default paths
        defaults = [
            ("results/results_local_llava.csv",    "LLaVA"),
            ("results/results_openrouter.csv",      "Qwen2.5VL"),
        ]
        existing = [(p, l) for p, l in defaults if os.path.exists(p)]
        if len(existing) < 2:
            print("Usage: python compare.py <csv_a> <csv_b>")
            print("       python compare.py results/results_local_llava.csv results/results_openrouter.csv")
            sys.exit(1)
        path_a, label_a = existing[0]
        path_b, label_b = existing[1]
    else:
        path_a = sys.argv[1]
        path_b = sys.argv[2]
        label_a = os.path.splitext(os.path.basename(path_a))[0].replace("results_", "")
        label_b = os.path.splitext(os.path.basename(path_b))[0].replace("results_", "")

    df_a = load_csv(path_a, label_a)
    df_b = load_csv(path_b, label_b)

    print(f"\nComparing:")
    print(f"  A: {path_a}  [{label_a}]  ({len(df_a)} images)")
    print(f"  B: {path_b}  [{label_b}]  ({len(df_b)} images)")

    print_overall(df_a, label_a, df_b, label_b)
    print_category_breakdown(df_a, label_a, df_b, label_b)
    print_hallucination_detail(df_a, label_a, df_b, label_b)
    print_gravel_detail(df_a, label_a, df_b, label_b)
    print_per_image(df_a, label_a, df_b, label_b)
    print()


if __name__ == "__main__":
    main()
