"""
fraud_logic.py
--------------
FWA detection orchestrator.

Calls each detection layer and merges results into a unified member-level
report with a composite fraud score.

Layer 1 — Over-Utilization    : l1_high_freq | l1_high_cost | l1_high_avg_cost
Layer 2 — Temporal Abuse      : l2_burst_claims | l2_same_day_multi_prov | l2_multi_city_same_day | l2_high_monthly_velocity
Layer 3 — Provider Billing    : l3_provider_overbilling | l3_provider_high_rejection
Layer 4 — Clinical Patterns   : l4_provider_shopping | l4_doctor_mill | l4_icd_shopping
Layer 5 — Claim Type/Chronic  : l5_duplicate_service_same_day | l5_inpatient_frequency
                                 l5_claim_type_diversity | l5_chronic_high_ratio

fraud_score   = count of triggered rules (max 16)
is_suspicious = fraud_score >= 2
risk_level    : Low (0–2) · Medium (3–5) · High (6+)
"""

import pandas as pd

from layers.layer1_utilization import run as _run_l1
from layers.layer2_temporal    import run as _run_l2
from layers.layer3_provider    import run as _run_l3
from layers.layer4_clinical    import run as _run_l4
from layers.layer5_claim_type  import run as _run_l5

# Rule registry — insertion order defines display order in the UI.
RULE_LABELS: dict[str, str] = {
    "l1_high_freq":                  "High visit frequency",
    "l1_high_cost":                  "High total claimed",
    "l1_high_avg_cost":              "High avg cost/visit",
    "l2_burst_claims":               "Repeated non-doctor claims within 7 days",
    "l2_same_day_multi_prov":        "Same-day multi-provider (same type)",
    "l2_multi_city_same_day":        "Multi-city visits on same day",
    "l2_high_monthly_velocity":      "High monthly velocity",
    "l3_provider_overbilling":       "Provider overbilling",
    "l3_provider_high_rejection":    "Provider high rejection",
    "l4_provider_shopping":          "Provider shopping",
    "l4_doctor_mill":                "Clinic with unusually high doctor rotation",
    "l4_icd_shopping":               "ICD code shopping",
    "l5_duplicate_service_same_day": "Duplicate service same day",
    "l5_inpatient_frequency":        "High inpatient frequency",
    "l5_claim_type_diversity":       "High claim type diversity",
    "l5_chronic_high_ratio":         "Abnormally high chronic ratio",
}

ALL_RULE_COLS = list(RULE_LABELS.keys())


def detect_fraud(
    df: pd.DataFrame,
    enable_utilization: bool = True,
    enable_temporal:    bool = True,
    enable_provider:    bool = True,
    enable_clinical:    bool = True,
    enable_claim_type:  bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Run all 5 detection layers and return a unified member-level result.

    Parameters
    ----------
    df : Claims DataFrame with normalized internal column names.

    Returns
    -------
    result              : pd.DataFrame — one row per member with metrics, flags, and score
    computed_thresholds : dict         — nested {layer: {rule: (value, pct, unit)}} for the UI
    """
    l1, l1_thresh = _run_l1(df, enable_utilization)
    l2, l2_thresh = _run_l2(df, enable_temporal)
    l3, l3_thresh = _run_l3(df, enable_provider)
    l4, l4_thresh = _run_l4(df, enable_clinical)
    l5, l5_thresh = _run_l5(df, enable_claim_type)

    result = (
        l1
        .merge(l2, on="member_id", how="left")
        .merge(l3, on="member_id", how="left")
        .merge(l4, on="member_id", how="left")
        .merge(l5, on="member_id", how="left")
    )

    # Guarantee all rule columns exist and are boolean
    for col in ALL_RULE_COLS:
        if col not in result.columns:
            result[col] = False
        else:
            result[col] = result[col].fillna(False)

    # Composite fraud score and risk classification
    result["fraud_score"]   = sum(result[col].astype(int) for col in ALL_RULE_COLS)
    result["is_suspicious"] = result["fraud_score"] >= 2
    result["risk_level"]    = pd.cut(
        result["fraud_score"],
        bins=[-1, 1, 4, float("inf")],
        labels=["Low", "Medium", "High"],
    ).astype(str)

    # Plain-text summary of triggered rules
    result["reason"] = result[ALL_RULE_COLS].apply(
        lambda row: " | ".join(RULE_LABELS[c] for c in ALL_RULE_COLS if row[c]) or "—",
        axis=1,
    )

    computed_thresholds = {
        "utilization": l1_thresh,
        "temporal":    l2_thresh,
        "provider":    l3_thresh,
        "clinical":    l4_thresh,
        "claim_type":  l5_thresh,
    }

    base_cols  = ["member_id", "total_claimed", "total_accepted", "overbilling_ratio",
                  "avg_claimed", "visit_count", "distinct_providers"]
    extra_cols = [c for c in [
        "max_provider_overbilling_ratio", "max_doctors_at_prov", "max_providers_per_icd",
        "max_same_type_same_day", "inpatient_count", "distinct_claim_types", "chronic_ratio",
    ] if c in result.columns]
    score_cols = ["fraud_score", "risk_level", "is_suspicious", "reason"]

    ordered = base_cols + extra_cols + ALL_RULE_COLS + score_cols
    return result[[c for c in ordered if c in result.columns]].copy(), computed_thresholds
