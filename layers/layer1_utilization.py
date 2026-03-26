"""
layer1_utilization.py
---------------------
Layer 1 — Member Over-Utilization

Aggregation : per member_id
Required    : member_id, claimed_amt, accepted_amt

Rules
-----
  l1_high_freq     : visit_count   > Nth percentile
  l1_high_cost     : total_claimed > Nth percentile
  l1_high_avg_cost : avg_claimed (median) > Nth percentile
"""

import pandas as pd

DEFAULT_VISIT_FREQ_PCT    = 90
DEFAULT_TOTAL_CLAIMED_PCT = 90
DEFAULT_AVG_CLAIMED_PCT   = 90


def run(
    df: pd.DataFrame,
    enable: bool           = True,
    visit_freq_pct: int    = DEFAULT_VISIT_FREQ_PCT,
    total_claimed_pct: int = DEFAULT_TOTAL_CLAIMED_PCT,
    avg_claimed_pct: int   = DEFAULT_AVG_CLAIMED_PCT,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    result : DataFrame  — one row per member_id
    thresholds : dict   — {rule_key: (value, pct_or_None, unit)}
    """

    agg = df.groupby("member_id").agg(
        total_claimed  = ("claimed_amt",  "sum"),
        total_accepted = ("accepted_amt", "sum"),
        avg_claimed    = ("claimed_amt",  "median"),
        visit_count    = ("claimed_amt",  "count"),
    ).reset_index()

    agg["total_claimed"]  = agg["total_claimed"].round(2)
    agg["total_accepted"] = agg["total_accepted"].round(2)
    agg["avg_claimed"]    = agg["avg_claimed"].round(2)

    # Member-level overbilling ratio (total claimed vs total accepted)
    agg["overbilling_ratio"] = (
        agg["total_claimed"] / agg["total_accepted"].replace(0, float("nan"))
    ).round(2)

    q = lambda col, pct: float(agg[col].quantile(pct / 100))
    thresh_visit = q("visit_count",   visit_freq_pct)
    thresh_total = q("total_claimed", total_claimed_pct)
    thresh_avg   = q("avg_claimed",   avg_claimed_pct)

    thresholds = {
        "visit_count":   (thresh_visit, visit_freq_pct,    "visits"),
        "total_claimed": (thresh_total, total_claimed_pct, "$"),
        "avg_claimed":   (thresh_avg,   avg_claimed_pct,   "$"),
    }

    if enable:
        agg["l1_high_freq"]     = agg["visit_count"]   > thresh_visit
        agg["l1_high_cost"]     = agg["total_claimed"]  > thresh_total
        agg["l1_high_avg_cost"] = agg["avg_claimed"]    > thresh_avg
    else:
        agg["l1_high_freq"] = agg["l1_high_cost"] = agg["l1_high_avg_cost"] = False

    return agg[[
        "member_id", "total_claimed", "total_accepted", "overbilling_ratio",
        "avg_claimed", "visit_count",
        "l1_high_freq", "l1_high_cost", "l1_high_avg_cost",
    ]], thresholds
