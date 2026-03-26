"""
layer5_claim_type.py
--------------------
Layer 5 — Claim Type & Chronic Abuse

Aggregation : per member_id
Required    : claim_form_type, chronic, accident_date

Rules
-----
  l5_duplicate_service_same_day : same claim type submitted >= 2 times on the same day
  l5_inpatient_frequency        : inpatient (hospital) admission count > Nth percentile
  l5_claim_type_diversity       : member uses many distinct claim types > Nth percentile
  l5_chronic_high_ratio         : member's proportion of chronic-flagged claims > Nth percentile
"""

import pandas as pd

DEFAULT_INPATIENT_FREQ_PCT       = 90
DEFAULT_CLAIM_TYPE_DIVERSITY_PCT = 90
DEFAULT_CHRONIC_RATIO_PCT        = 90

INPATIENT_LABEL = "hospital claim form"


def _parse_chronic(val) -> bool:
    """Normalize heterogeneous chronic column values to bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).strip().lower() in ("1", "true", "yes", "y")


def run(
    df: pd.DataFrame,
    enable: bool                  = True,
    inpatient_freq_pct: int       = DEFAULT_INPATIENT_FREQ_PCT,
    claim_type_diversity_pct: int = DEFAULT_CLAIM_TYPE_DIVERSITY_PCT,
    chronic_ratio_pct: int        = DEFAULT_CHRONIC_RATIO_PCT,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    result     : DataFrame — one row per member_id with metric + flag columns
    thresholds : dict      — {rule_key: (value, pct_or_None, unit)}
    """
    members = df["member_id"].unique()
    result  = pd.DataFrame({"member_id": members})

    # ── Rule 1: Duplicate service same day ───────────────────────────────────
    # E.g., 2 lab claims or 2 x-ray claims on the same day — ghost billing signal.
    df_dated = df[["member_id", "accident_date", "claim_form_type"]].copy()
    df_dated["accident_date"] = pd.to_datetime(df_dated["accident_date"], errors="coerce")
    df_dated = df_dated.dropna(subset=["accident_date"])

    max_dup = (
        df_dated.groupby(["member_id", "accident_date", "claim_form_type"])
        .size()
        .reset_index(name="claim_count")
        .groupby("member_id")["claim_count"]
        .max()
        .reset_index(name="max_same_type_same_day")
    )
    result = result.merge(max_dup, on="member_id", how="left")
    result["max_same_type_same_day"] = result["max_same_type_same_day"].fillna(0)

    # ── Rule 2: Inpatient frequency ──────────────────────────────────────────
    # Multiple hospital admissions in the data period is a strong fraud signal.
    inpatient_counts = (
        df[df["claim_form_type"].astype(str).str.strip().str.lower() == INPATIENT_LABEL]
        .groupby("member_id")
        .size()
        .reset_index(name="inpatient_count")
    )
    result = result.merge(inpatient_counts, on="member_id", how="left")
    result["inpatient_count"] = result["inpatient_count"].fillna(0)
    thresh_inpatient = float(result["inpatient_count"].quantile(inpatient_freq_pct / 100))

    # ── Rule 3: Claim type diversity ─────────────────────────────────────────
    # Using an unusually wide variety of service types may indicate benefit exhaustion fraud.
    type_div = (
        df.groupby("member_id")["claim_form_type"]
        .nunique()
        .reset_index(name="distinct_claim_types")
    )
    result = result.merge(type_div, on="member_id", how="left")
    result["distinct_claim_types"] = result["distinct_claim_types"].fillna(0)
    thresh_diversity = float(result["distinct_claim_types"].quantile(claim_type_diversity_pct / 100))

    # ── Rule 4: Chronic claim high ratio ─────────────────────────────────────
    # Abnormally high proportion of chronic-flagged claims may indicate benefit code abuse.
    chronic_ratio = (
        df[["member_id", "chronic"]].copy()
        .assign(chronic_bool=lambda d: d["chronic"].apply(_parse_chronic))
        .groupby("member_id")["chronic_bool"]
        .mean()
        .reset_index(name="chronic_ratio")
    )
    result = result.merge(chronic_ratio, on="member_id", how="left")
    result["chronic_ratio"] = result["chronic_ratio"].fillna(0)
    thresh_chronic = float(result["chronic_ratio"].quantile(chronic_ratio_pct / 100))

    thresholds = {
        "duplicate_service_same_day": (2,                None,                     "claims/type/day"),
        "inpatient_frequency":        (thresh_inpatient, inpatient_freq_pct,       "admissions"),
        "claim_type_diversity":       (thresh_diversity, claim_type_diversity_pct, "types"),
        "chronic_high_ratio":         (thresh_chronic,   chronic_ratio_pct,        "ratio"),
    }

    # ── Apply flags ──────────────────────────────────────────────────────────
    if enable:
        result["l5_duplicate_service_same_day"] = result["max_same_type_same_day"] >= 2
        result["l5_inpatient_frequency"]        = result["inpatient_count"]        > thresh_inpatient
        result["l5_claim_type_diversity"]       = result["distinct_claim_types"]   > thresh_diversity
        result["l5_chronic_high_ratio"]         = result["chronic_ratio"]          > thresh_chronic
    else:
        result["l5_duplicate_service_same_day"] = False
        result["l5_inpatient_frequency"]        = False
        result["l5_claim_type_diversity"]       = False
        result["l5_chronic_high_ratio"]         = False

    return result, thresholds
