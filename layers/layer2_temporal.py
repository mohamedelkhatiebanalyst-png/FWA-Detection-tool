"""
layer2_temporal.py
------------------
Layer 2 — Temporal Billing Abuse

Aggregation : per member_id × time window
Required    : accident_date, claim_form_type, provider_city

Rules
-----
  l2_burst_claims          : >= N claims within a rolling K-day window
  l2_same_day_multi_prov   : same claim type at >= 2 different providers on the same day
  l2_multi_city_same_day   : visited providers in >= 2 different cities on the same day
  l2_high_monthly_velocity : max claims in any calendar month > Nth percentile
"""

import pandas as pd

DEFAULT_BURST_WINDOW_DAYS = 7
DEFAULT_BURST_MIN_CLAIMS  = 3
DEFAULT_MONTHLY_VEL_PCT   = 90


def run(
    df: pd.DataFrame,
    enable: bool           = True,
    burst_window_days: int = DEFAULT_BURST_WINDOW_DAYS,
    burst_min_claims: int  = DEFAULT_BURST_MIN_CLAIMS,
    monthly_vel_pct: int   = DEFAULT_MONTHLY_VEL_PCT,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    result     : DataFrame — one row per member_id
    thresholds : dict      — {rule_key: (value, pct_or_None, unit)}
    """
    base = pd.DataFrame({"member_id": df["member_id"].unique()})

    df2 = df[["member_id", "provider", "provider_city", "accident_date", "claim_form_type"]].copy()
    df2["accident_date"] = pd.to_datetime(df2["accident_date"], errors="coerce")
    df2 = df2.dropna(subset=["accident_date"])

    # ── Rule 1: Repeated claims in a short window ────────────────────────────
    # Doctor visits are excluded — seeing a doctor multiple times a week is normal.
    # The rule targets non-doctor services (labs, imaging, physio, etc.) only.
    def _max_burst(grp: pd.DataFrame) -> int:
        dates = grp["accident_date"].sort_values().reset_index(drop=True)
        max_count = 1
        for i in range(len(dates)):
            cutoff = dates[i] + pd.Timedelta(days=burst_window_days)
            count = int(((dates >= dates[i]) & (dates <= cutoff)).sum())
            if count > max_count:
                max_count = count
        return max_count

    df_burst = df2[df2["claim_form_type"].str.lower() != "doctor visit"]
    burst_counts = (
        df_burst.groupby("member_id")
        .apply(_max_burst)
        .reset_index(name="max_burst")
    )

    # ── Rule 2: Same-day multi-provider (type-aware) ─────────────────────────
    # Visiting a doctor AND a lab on the same day is normal.
    # Visiting two different labs on the same day is suspicious.
    same_day_max = (
        df2.groupby(["member_id", "accident_date", "claim_form_type"])["provider"]
        .nunique()
        .reset_index(name="providers_same_type_on_day")
        .groupby("member_id")["providers_same_type_on_day"]
        .max()
        .reset_index(name="max_providers_on_day")
    )

    # ── Rule 3: Multi-city same day ──────────────────────────────────────────
    # A member appearing at providers in 2+ different cities on the same day
    # is physically implausible and a strong fraud indicator.
    multi_city = (
        df2.groupby(["member_id", "accident_date"])["provider_city"]
        .nunique()
        .reset_index(name="cities_on_day")
        .groupby("member_id")["cities_on_day"]
        .max()
        .reset_index(name="max_cities_on_day")
    )

    # ── Rule 4: Monthly velocity ─────────────────────────────────────────────
    df2["year_month"] = df2["accident_date"].dt.to_period("M")
    monthly_max = (
        df2.groupby(["member_id", "year_month"])
        .size()
        .reset_index(name="monthly_claims")
        .groupby("member_id")["monthly_claims"]
        .max()
        .reset_index(name="max_monthly_claims")
    )

    thresh_monthly = float(monthly_max["max_monthly_claims"].quantile(monthly_vel_pct / 100))

    thresholds = {
        "burst_claims":        (burst_min_claims, None,            f"claims/{burst_window_days}d window"),
        "same_day_multi_prov": (2,                None,            "providers/day"),
        "multi_city_same_day": (2,                None,            "cities/day"),
        "monthly_velocity":    (thresh_monthly,   monthly_vel_pct, "claims/month"),
    }

    # ── Apply flags ──────────────────────────────────────────────────────────
    if enable:
        burst_counts["l2_burst_claims"]         = burst_counts["max_burst"] >= burst_min_claims
        same_day_max["l2_same_day_multi_prov"]  = same_day_max["max_providers_on_day"] >= 2
        multi_city["l2_multi_city_same_day"]    = multi_city["max_cities_on_day"] >= 2
        monthly_max["l2_high_monthly_velocity"] = monthly_max["max_monthly_claims"] > thresh_monthly
    else:
        burst_counts["l2_burst_claims"]         = False
        same_day_max["l2_same_day_multi_prov"]  = False
        multi_city["l2_multi_city_same_day"]    = False
        monthly_max["l2_high_monthly_velocity"] = False

    result = (
        base
        .merge(burst_counts[["member_id", "l2_burst_claims"]],         on="member_id", how="left")
        .merge(same_day_max[["member_id", "l2_same_day_multi_prov"]],  on="member_id", how="left")
        .merge(multi_city[["member_id", "l2_multi_city_same_day"]],    on="member_id", how="left")
        .merge(monthly_max[["member_id", "l2_high_monthly_velocity"]], on="member_id", how="left")
    )
    flag_cols = ["l2_burst_claims", "l2_same_day_multi_prov", "l2_multi_city_same_day", "l2_high_monthly_velocity"]
    result[flag_cols] = result[flag_cols].fillna(False)

    return result, thresholds
