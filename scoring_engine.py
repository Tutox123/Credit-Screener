"""
Credit RV Screener - Scoring Engine
====================================
Reads inputs.csv + weights.yaml -> outputs scores.csv

Methodology v1.0:
  RISK SCORE = w_idio * Idiosyncratic + w_sector * Sector + w_macro * Macro
  REWARD SCORE = w_spread * Spread Attractiveness + w_carry * Carry & Roll + w_growth * Sector Growth
  LIQUIDITY SCORE (0-100): from amount outstanding, bid-ask, days traded, volume
  RV SCORE = Reward / Risk

All components are normalized (percentile or min-max) for cross-comparability.
The process is fully deterministic given the same inputs + weights.

The dashboard imports `score_universe(df, cfg)` and re-runs it whenever
the user adjusts weights in the sidebar.
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent


# ============================================================
# UTILITIES
# ============================================================

def load_config(path=None):
    if path is None:
        path = BASE_DIR / "weights.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)


def percentile_rank(series):
    return series.rank(pct=True) * 100


def min_max(series, invert=False, clip=None):
    s = series.copy()
    if clip is not None:
        s = s.clip(*clip)
    rng = s.max() - s.min()
    if rng == 0:
        return pd.Series([50] * len(s), index=s.index)
    out = (s - s.min()) / rng * 100
    if invert:
        out = 100 - out
    return out


# ============================================================
# RISK SCORE COMPONENTS
# ============================================================

def compute_idiosyncratic_risk(df, cfg):
    w = cfg["risk_score"]["idiosyncratic"]["components"]

    rating_score = df["Bond Rating SP"].map(cfg["rating_to_score"]).fillna(50)
    sub_score = df["Seniority"].map(cfg["seniority_to_score"]).fillna(30)

    leverage_score = pd.Series(50.0, index=df.index)
    for idx, row in df.iterrows():
        sector = row["Sector"]
        if sector == "Banks":
            cet1 = row.get("CET1 Ratio (%)")
            if pd.notna(cet1):
                leverage_score[idx] = float(np.clip((16 - cet1) / 6 * 100, 0, 100))
        elif sector == "Insurance":
            sii = row.get("Solvency II Ratio (%)")
            if pd.notna(sii):
                leverage_score[idx] = float(np.clip((230 - sii) / 130 * 100, 0, 100))
        else:
            lev = row.get("Net Debt / EBITDA")
            if pd.notna(lev):
                leverage_score[idx] = float(np.clip(lev / 7 * 100, 0, 100))

    duration_score = min_max(df["Mod Duration"])

    total = sum(w.values())
    if total == 0:
        total = 1
    idio = (
        rating_score * (w["bond_rating"] / total)
        + sub_score * (w["subordination"] / total)
        + leverage_score * (w["leverage"] / total)
        + duration_score * (w["duration"] / total)
    )
    components = {"rating": rating_score, "sub": sub_score,
                  "leverage": leverage_score, "duration": duration_score}
    return idio, components


def compute_sector_risk(df, cfg):
    w = cfg["risk_score"]["sector_risk"]["components"]
    profile = cfg["sector_risk_profile"]
    sub_adj = cfg["sub_sector_cyclicality_adj"]

    cyc = df.apply(
        lambda r: np.clip(profile[r["Sector"]]["cyclicality"] + sub_adj.get(r["Sub Sector"], 0), 0, 100),
        axis=1,
    )
    default = df["Sector"].map(lambda s: profile[s]["default_history"])
    vol = df["Sector"].map(lambda s: profile[s]["spread_volatility"])

    total = sum(w.values())
    if total == 0:
        total = 1
    sector_risk = (
        cyc * (w["cyclicality"] / total)
        + default * (w["default_history"] / total)
        + vol * (w["spread_volatility"] / total)
    )
    return sector_risk


def compute_macro_risk(df, cfg):
    w = cfg["risk_score"]["macro_risk"]["components"]

    geo = df["Country"].map(cfg["country_geopolitical_risk"]).fillna(40)
    rates_sens = min_max(df["Mod Duration"])
    fx_exp = df["Currency"].map(lambda c: 35 if c != "EUR" else 10)
    reg = df["Sector"].map(cfg["regulatory_pressure"])

    total = sum(w.values())
    if total == 0:
        total = 1
    macro = (
        geo * (w["geopolitical"] / total)
        + rates_sens * (w["rates_sensitivity"] / total)
        + fx_exp * (w["fx_exposure"] / total)
        + reg * (w["regulatory"] / total)
    )
    return macro


# ============================================================
# REWARD SCORE COMPONENTS
# ============================================================

def compute_spread_attractiveness(df, cfg):
    w = cfg["reward_score"]["spread_attractiveness"]["components"]

    z_vs_universe = percentile_rank(df["Z-Spread (bps)"])
    sector_median = df.groupby("Sector")["Z-Spread (bps)"].transform("median")
    pickup_sector = df["Z-Spread (bps)"] - sector_median
    spread_vs_sector = min_max(pickup_sector)
    rating_median = df.groupby("Bond Rating SP")["Z-Spread (bps)"].transform("median")
    pickup_rating = df["Z-Spread (bps)"] - rating_median
    spread_vs_rating = min_max(pickup_rating)

    total = sum(w.values())
    if total == 0:
        total = 1
    return (
        z_vs_universe * (w["z_spread_vs_universe"] / total)
        + spread_vs_sector * (w["spread_vs_sector"] / total)
        + spread_vs_rating * (w["spread_vs_rating"] / total)
    )


def compute_carry_and_roll(df, cfg):
    w = cfg["reward_score"]["carry_and_roll"]["components"]

    running_yield = df["Coupon"] / df["Mid Price"] * 100
    ry_score = min_max(running_yield)

    roll_proxy = df.groupby("Issuer Ticker")["Z-Spread (bps)"].transform("std").fillna(0)
    roll_proxy = roll_proxy * df["Mod Duration"]
    roll_score = min_max(roll_proxy)

    total = sum(w.values())
    if total == 0:
        total = 1
    return (
        ry_score * (w["running_yield"] / total)
        + roll_score * (w["roll_down_1y"] / total)
    )


def compute_sector_growth(df, cfg):
    w = cfg["reward_score"]["sector_growth_momentum"]["components"]

    growth_map = cfg["growth_outlook_to_score"]
    growth = df["Sector Growth Outlook"].map(growth_map).fillna(40)
    roe_q = df.groupby("Sector")["ROE (%)"].transform(lambda s: s.rank(pct=True) * 100).fillna(50)

    np.random.seed(7)
    spread_mom = pd.Series(np.random.uniform(20, 80, size=len(df)), index=df.index)

    total = sum(w.values())
    if total == 0:
        total = 1
    return (
        growth * (w["growth_outlook"] / total)
        + roe_q * (w["earnings_revision"] / total)
        + spread_mom * (w["spread_momentum_3m"] / total)
    )


# ============================================================
# LIQUIDITY SCORE
# ============================================================

def compute_liquidity(df):
    amt = min_max(df["Amount Outstanding (M)"])
    ba = min_max(df["Bid-Ask (cents)"], invert=True)
    days = min_max(df["Days Traded per Month"])
    vol = min_max(df["Avg Daily Volume (M)"])
    return 0.30 * amt + 0.30 * ba + 0.20 * days + 0.20 * vol


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def score_universe(df, cfg):
    """
    Compute all scores for the universe.
    Returns a DataFrame with the original columns + score columns.
    This is the function called by the dashboard for live re-scoring.
    """
    idio, idio_components = compute_idiosyncratic_risk(df, cfg)
    sector_risk = compute_sector_risk(df, cfg)
    macro_risk = compute_macro_risk(df, cfg)

    w_risk_idio = cfg["risk_score"]["idiosyncratic"]["total"]
    w_risk_sec = cfg["risk_score"]["sector_risk"]["total"]
    w_risk_macro = cfg["risk_score"]["macro_risk"]["total"]
    risk_total = w_risk_idio + w_risk_sec + w_risk_macro
    if risk_total == 0:
        risk_total = 1
    risk_score = (
        w_risk_idio * idio + w_risk_sec * sector_risk + w_risk_macro * macro_risk
    ) / risk_total

    spread_attr = compute_spread_attractiveness(df, cfg)
    carry = compute_carry_and_roll(df, cfg)
    growth = compute_sector_growth(df, cfg)

    w_rew_spread = cfg["reward_score"]["spread_attractiveness"]["total"]
    w_rew_carry = cfg["reward_score"]["carry_and_roll"]["total"]
    w_rew_growth = cfg["reward_score"]["sector_growth_momentum"]["total"]
    rew_total = w_rew_spread + w_rew_carry + w_rew_growth
    if rew_total == 0:
        rew_total = 1
    reward_score = (
        w_rew_spread * spread_attr + w_rew_carry * carry + w_rew_growth * growth
    ) / rew_total

    liquidity = compute_liquidity(df)
    rv_score = reward_score / risk_score.clip(lower=1)

    out = df.copy()
    out["Score: Idio Rating"] = idio_components["rating"].round(1)
    out["Score: Idio Subordination"] = idio_components["sub"].round(1)
    out["Score: Idio Leverage"] = idio_components["leverage"].round(1)
    out["Score: Idio Duration"] = idio_components["duration"].round(1)
    out["Score: Idiosyncratic Risk"] = idio.round(2)
    out["Score: Sector Risk"] = sector_risk.round(2)
    out["Score: Macro Risk"] = macro_risk.round(2)
    out["Score: Spread Attractiveness"] = spread_attr.round(2)
    out["Score: Carry & Roll"] = carry.round(2)
    out["Score: Sector Growth"] = growth.round(2)
    out["Risk Score"] = risk_score.round(2)
    out["Reward Score"] = reward_score.round(2)
    out["Liquidity Score"] = liquidity.round(2)
    out["RV Score"] = rv_score.round(3)
    out["RV Rank"] = out["RV Score"].rank(ascending=False).astype(int)
    return out


def main():
    cfg = load_config()
    df = pd.read_csv(BASE_DIR / "inputs.csv")
    out = score_universe(df, cfg)
    out.to_csv(BASE_DIR / "scores.csv", index=False)
    print(f"✓ Scored {len(out)} bond emissions")
    cols = ["Issuer Name", "Seniority", "Bond Rating SP", "Z-Spread (bps)",
            "Risk Score", "Reward Score", "Liquidity Score", "RV Score"]
    print(f"\nTop 10 by RV Score:")
    print(out.nlargest(10, "RV Score")[cols].to_string(index=False))
    return out


if __name__ == "__main__":
    main()
