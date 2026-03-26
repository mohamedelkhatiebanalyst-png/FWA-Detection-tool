"""
layer4_clinical.py
------------------
Layer 4 — Clinical Pattern Fraud

Aggregation : per member × provider  and  per member × ICD code
Required    : treatment_doctor, icd_code

Rules
-----
  l4_provider_shopping : member visited distinct_providers > Nth percentile
  l4_doctor_mill       : member saw many different doctors at the SAME provider
                         → max(distinct doctors per provider) > Nth percentile
  l4_icd_shopping      : member claimed the SAME ICD code at many different providers
                         → max(distinct providers per ICD code) > Nth percentile
"""

import pandas as pd

DEFAULT_DISTINCT_PROVIDERS_PCT = 90
DEFAULT_DOCTOR_MILL_PCT        = 90
DEFAULT_ICD_SHOPPING_PCT       = 90


def run(
    df: pd.DataFrame,
    enable: bool                = True,
    distinct_providers_pct: int = DEFAULT_DISTINCT_PROVIDERS_PCT,
    doctor_mill_pct: int        = DEFAULT_DOCTOR_MILL_PCT,
    icd_shopping_pct: int       = DEFAULT_ICD_SHOPPING_PCT,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    result     : DataFrame — one row per member_id
    thresholds : dict      — {rule_key: (value, pct_or_None, unit)}
    """

    # ── Distinct providers per member ────────────────────────────────────────
    prov_counts = (
        df.groupby("member_id")["provider"]
        .nunique()
        .reset_index(name="distinct_providers")
    )
    thresh_prov = float(prov_counts["distinct_providers"].quantile(distinct_providers_pct / 100))

    # ── Doctor mill ──────────────────────────────────────────────────────────
    max_mill = (
        df.groupby(["member_id", "provider"])["treatment_doctor"]
        .nunique()
        .reset_index(name="doctors_at_prov")
        .groupby("member_id")["doctors_at_prov"]
        .max()
        .reset_index(name="max_doctors_at_prov")
    )
    thresh_mill = float(max_mill["max_doctors_at_prov"].quantile(doctor_mill_pct / 100))

    # ── ICD shopping ─────────────────────────────────────────────────────────
    max_icd = (
        df.groupby(["member_id", "icd_code"])["provider"]
        .nunique()
        .reset_index(name="providers_per_icd")
        .groupby("member_id")["providers_per_icd"]
        .max()
        .reset_index(name="max_providers_per_icd")
    )
    thresh_icd = float(max_icd["max_providers_per_icd"].quantile(icd_shopping_pct / 100))

    thresholds = {
        "distinct_providers": (thresh_prov, distinct_providers_pct, "providers"),
        "doctor_mill":        (thresh_mill, doctor_mill_pct,        "doctors/provider"),
        "icd_shopping":       (thresh_icd, icd_shopping_pct,        "providers/ICD"),
    }

    result = (
        prov_counts
        .merge(max_mill, on="member_id", how="left")
        .merge(max_icd,  on="member_id", how="left")
    )

    # ── Apply flags ──────────────────────────────────────────────────────────
    if enable:
        result["l4_provider_shopping"] = result["distinct_providers"]   > thresh_prov
        result["l4_doctor_mill"]       = result["max_doctors_at_prov"]  > thresh_mill
        result["l4_icd_shopping"]      = result["max_providers_per_icd"] > thresh_icd
    else:
        result["l4_provider_shopping"] = False
        result["l4_doctor_mill"]       = False
        result["l4_icd_shopping"]      = False

    return result, thresholds
