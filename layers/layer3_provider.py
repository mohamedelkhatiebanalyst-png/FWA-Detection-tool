"""
layer3_provider.py
------------------
Layer 3 — Provider Overbilling

Aggregation : per provider, flags joined back to member level
Required    : provider, claimed_amt, accepted_amt

Rules
-----
  l3_provider_overbilling    : provider's claimed/accepted ratio > threshold
  l3_provider_high_rejection : provider's rejection rate > Nth percentile
                               rejection_rate = (claimed - accepted) / claimed
"""

import pandas as pd

DEFAULT_OVERBILLING_RATIO  = 2.0
DEFAULT_REJECTION_RATE_PCT = 90


def run(
    df: pd.DataFrame,
    enable: bool                    = True,
    overbilling_ratio_threshold: float = DEFAULT_OVERBILLING_RATIO,
    rejection_rate_pct: int         = DEFAULT_REJECTION_RATE_PCT,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    result : DataFrame  — one row per member_id
                          includes max_provider_overbilling_ratio (worst provider seen by member)
    thresholds : dict   — {rule_key: (value, pct_or_None, unit)}
    """

    # ── Provider-level aggregation ───────────────────────────────────────────
    prov = df.groupby("provider").agg(
        total_claimed  = ("claimed_amt",  "sum"),
        total_accepted = ("accepted_amt", "sum"),
    ).reset_index()

    prov["prov_overbilling_ratio"] = (
        prov["total_claimed"] / prov["total_accepted"].replace(0, float("nan"))
    ).round(2)

    # Rejection rate: share of claimed amount that was NOT accepted
    prov["prov_rejection_rate"] = (
        (prov["total_claimed"] - prov["total_accepted"]).clip(lower=0)
        / prov["total_claimed"].replace(0, float("nan"))
    ).round(4)

    thresh_rejection = float(prov["prov_rejection_rate"].quantile(rejection_rate_pct / 100))

    thresholds = {
        "provider_overbilling":  (overbilling_ratio_threshold, None,               "× ratio"),
        "provider_rejection":    (thresh_rejection,            rejection_rate_pct, "rejection rate"),
    }

    # ── Provider flags ───────────────────────────────────────────────────────
    if enable:
        prov["l3_prov_overbilling"]    = prov["prov_overbilling_ratio"]  > overbilling_ratio_threshold
        prov["l3_prov_high_rejection"] = prov["prov_rejection_rate"]     > thresh_rejection
    else:
        prov["l3_prov_overbilling"]    = False
        prov["l3_prov_high_rejection"] = False

    # ── Join back to member level ────────────────────────────────────────────
    # A member is flagged if ANY provider they visited was flagged.
    member_prov = df[["member_id", "provider"]].drop_duplicates()
    member_prov = member_prov.merge(
        prov[[
            "provider", "prov_overbilling_ratio",
            "l3_prov_overbilling", "l3_prov_high_rejection",
        ]],
        on="provider", how="left",
    )

    member_flags = (
        member_prov
        .groupby("member_id")
        .agg(
            l3_provider_overbilling    = ("l3_prov_overbilling",    "any"),
            l3_provider_high_rejection = ("l3_prov_high_rejection", "any"),
            max_provider_overbilling_ratio = ("prov_overbilling_ratio", "max"),
        )
        .reset_index()
    )
    member_flags["max_provider_overbilling_ratio"] = (
        member_flags["max_provider_overbilling_ratio"].round(2)
    )

    return member_flags, thresholds
