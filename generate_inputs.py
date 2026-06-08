"""
Generate realistic credit research input data.
Mirrors the structure of data feeds received from Bloomberg, ICE, Markit.
~75 bond emissions across Banks, Insurance, Corporate IG, and High Yield.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

# ============================================================
# UNIVERSE DEFINITION
# ============================================================
# Each issuer has: ticker, sector, sub-sector, country, base_rating, fundamentals
# Bonds derived from issuers respect seniority hierarchy and rating notching.

ISSUERS = {
    # ===== BANKS =====
    "BNP":   {"name": "BNP Paribas",          "sector": "Banks", "sub_sector": "GSIB",            "country": "FR", "rating": "A+",  "cet1": 13.2, "lev_or_solvency": None,  "roe": 11.2},
    "ACAFP": {"name": "Credit Agricole",      "sector": "Banks", "sub_sector": "GSIB",            "country": "FR", "rating": "A+",  "cet1": 17.5, "lev_or_solvency": None,  "roe": 12.1},
    "SOCGEN":{"name": "Societe Generale",     "sector": "Banks", "sub_sector": "GSIB",            "country": "FR", "rating": "A",   "cet1": 13.1, "lev_or_solvency": None,  "roe": 6.8},
    "DB":    {"name": "Deutsche Bank",        "sector": "Banks", "sub_sector": "GSIB",            "country": "DE", "rating": "A-",  "cet1": 13.6, "lev_or_solvency": None,  "roe": 7.4},
    "SANTAN":{"name": "Santander",            "sector": "Banks", "sub_sector": "GSIB",            "country": "ES", "rating": "A+",  "cet1": 12.8, "lev_or_solvency": None,  "roe": 14.2},
    "INTNED":{"name": "ING Group",            "sector": "Banks", "sub_sector": "GSIB",            "country": "NL", "rating": "A+",  "cet1": 14.1, "lev_or_solvency": None,  "roe": 13.8},
    "UCG":   {"name": "UniCredit",            "sector": "Banks", "sub_sector": "Domestic",        "country": "IT", "rating": "BBB+","cet1": 16.0, "lev_or_solvency": None,  "roe": 17.5},
    "BARC":  {"name": "Barclays",             "sector": "Banks", "sub_sector": "GSIB",            "country": "UK", "rating": "A",   "cet1": 13.8, "lev_or_solvency": None,  "roe": 9.1},
    "HSBC":  {"name": "HSBC Holdings",        "sector": "Banks", "sub_sector": "GSIB",            "country": "UK", "rating": "A+",  "cet1": 15.2, "lev_or_solvency": None,  "roe": 14.6},

    # ===== INSURANCE =====
    "AXA":   {"name": "AXA",                  "sector": "Insurance", "sub_sector": "Life & P&C",  "country": "FR", "rating": "A+",  "cet1": None, "lev_or_solvency": 227, "roe": 14.8},
    "ALVGR": {"name": "Allianz",              "sector": "Insurance", "sub_sector": "Life & P&C",  "country": "DE", "rating": "AA",  "cet1": None, "lev_or_solvency": 209, "roe": 16.2},
    "GASIM": {"name": "Generali",             "sector": "Insurance", "sub_sector": "Life & P&C",  "country": "IT", "rating": "A",   "cet1": None, "lev_or_solvency": 220, "roe": 13.5},
    "AVLN":  {"name": "Aviva",                "sector": "Insurance", "sub_sector": "Life",        "country": "UK", "rating": "A",   "cet1": None, "lev_or_solvency": 203, "roe": 11.2},
    "MUNRE": {"name": "Munich Re",            "sector": "Insurance", "sub_sector": "Reinsurance", "country": "DE", "rating": "AA-", "cet1": None, "lev_or_solvency": 268, "roe": 17.1},
    "ZURNVX":{"name": "Zurich Insurance",     "sector": "Insurance", "sub_sector": "Life & P&C",  "country": "CH", "rating": "AA-", "cet1": None, "lev_or_solvency": 232, "roe": 18.9},

    # ===== CORPORATE IG =====
    "MCFP":  {"name": "LVMH",                 "sector": "Corporate IG", "sub_sector": "Luxury",      "country": "FR", "rating": "A+",  "cet1": None, "lev_or_solvency": 1.1, "roe": 22.3},
    "TTEFP": {"name": "TotalEnergies",        "sector": "Corporate IG", "sub_sector": "Energy",      "country": "FR", "rating": "A",   "cet1": None, "lev_or_solvency": 0.8, "roe": 19.5},
    "SANFP": {"name": "Sanofi",               "sector": "Corporate IG", "sub_sector": "Pharma",      "country": "FR", "rating": "AA",  "cet1": None, "lev_or_solvency": 1.4, "roe": 15.7},
    "EDF":   {"name": "Electricite de France","sector": "Corporate IG", "sub_sector": "Utilities",   "country": "FR", "rating": "BBB", "cet1": None, "lev_or_solvency": 3.8, "roe": 8.2},
    "ENGIFP":{"name": "Engie",                "sector": "Corporate IG", "sub_sector": "Utilities",   "country": "FR", "rating": "BBB+","cet1": None, "lev_or_solvency": 3.1, "roe": 9.6},
    "SU":    {"name": "Schneider Electric",   "sector": "Corporate IG", "sub_sector": "Industrials", "country": "FR", "rating": "A-",  "cet1": None, "lev_or_solvency": 1.6, "roe": 14.2},
    "DG":    {"name": "Vinci",                "sector": "Corporate IG", "sub_sector": "Infrastructure","country": "FR","rating": "A-", "cet1": None, "lev_or_solvency": 2.2, "roe": 13.8},
    "AIFP":  {"name": "Air Liquide",          "sector": "Corporate IG", "sub_sector": "Chemicals",   "country": "FR", "rating": "A",   "cet1": None, "lev_or_solvency": 1.7, "roe": 14.5},
    "ORA":   {"name": "Orange",               "sector": "Corporate IG", "sub_sector": "Telecom",     "country": "FR", "rating": "BBB+","cet1": None, "lev_or_solvency": 2.3, "roe": 7.9},
    "SAP":   {"name": "SAP",                  "sector": "Corporate IG", "sub_sector": "Technology",  "country": "DE", "rating": "A",   "cet1": None, "lev_or_solvency": 1.2, "roe": 16.4},
    "VOLKWAGEN":{"name": "Volkswagen",        "sector": "Corporate IG", "sub_sector": "Autos",       "country": "DE", "rating": "BBB+","cet1": None, "lev_or_solvency": 2.8, "roe": 8.4},

    # ===== HIGH YIELD =====
    "ATCNA": {"name": "Altice France",        "sector": "High Yield", "sub_sector": "Telecom",      "country": "FR", "rating": "CCC+","cet1": None, "lev_or_solvency": 6.5, "roe": -8.1},
    "VERIS": {"name": "Verisure",             "sector": "High Yield", "sub_sector": "Services",     "country": "SE", "rating": "B+",  "cet1": None, "lev_or_solvency": 5.8, "roe": 4.2},
    "IHOVER":{"name": "IHO Verwaltungs",      "sector": "High Yield", "sub_sector": "Autos Suppliers","country": "DE","rating": "BB", "cet1": None, "lev_or_solvency": 4.1, "roe": 6.5},
    "PICARD":{"name": "Picard Groupe",        "sector": "High Yield", "sub_sector": "Retail Food",  "country": "FR", "rating": "B",   "cet1": None, "lev_or_solvency": 5.2, "roe": 3.8},
    "ILDFP": {"name": "Iliad",                "sector": "High Yield", "sub_sector": "Telecom",      "country": "FR", "rating": "BB+", "cet1": None, "lev_or_solvency": 3.6, "roe": 9.2},
    "FAURFP":{"name": "Forvia (Faurecia)",    "sector": "High Yield", "sub_sector": "Autos Suppliers","country": "FR","rating": "BB", "cet1": None, "lev_or_solvency": 3.9, "roe": 5.1},
    "RXLFP": {"name": "Rexel",                "sector": "High Yield", "sub_sector": "Industrials",  "country": "FR", "rating": "BB+", "cet1": None, "lev_or_solvency": 3.2, "roe": 12.4},
    "INEGRP":{"name": "INEOS Group",          "sector": "High Yield", "sub_sector": "Chemicals",    "country": "UK", "rating": "BB-", "cet1": None, "lev_or_solvency": 4.6, "roe": 7.8},
    "LOXAM": {"name": "Loxam",                "sector": "High Yield", "sub_sector": "Services",     "country": "FR", "rating": "B+",  "cet1": None, "lev_or_solvency": 5.1, "roe": 8.6},
    "STONEG":{"name": "Stonegate Pub",        "sector": "High Yield", "sub_sector": "Leisure",      "country": "UK", "rating": "B-",  "cet1": None, "lev_or_solvency": 6.8, "roe": 2.1},
}

# Seniority structures by sector
SENIORITY_BY_SECTOR = {
    "Banks": ["Senior Unsecured", "Tier 2", "AT1"],
    "Insurance": ["Senior Unsecured", "Sub Insurance"],
    "Corporate IG": ["Senior Unsecured"],
    "High Yield": ["Senior Secured", "Senior Unsecured"],
}

# Spread base levels by sector / seniority / rating (mid 2026 realistic)
def base_spread(sector, seniority, rating):
    """Return realistic Z-spread in bps."""
    rating_score = {"AAA": 0, "AA+": 1, "AA": 2, "AA-": 3, "A+": 4, "A": 5, "A-": 6,
                    "BBB+": 7, "BBB": 8, "BBB-": 9, "BB+": 10, "BB": 11, "BB-": 12,
                    "B+": 13, "B": 14, "B-": 15, "CCC+": 16, "CCC": 17}
    rs = rating_score.get(rating, 8)

    if sector == "Banks":
        if seniority == "Senior Unsecured":
            return 60 + rs * 12
        elif seniority == "Tier 2":
            return 180 + rs * 18
        elif seniority == "AT1":
            return 380 + rs * 35
    elif sector == "Insurance":
        if seniority == "Senior Unsecured":
            return 50 + rs * 10
        elif seniority == "Sub Insurance":
            return 200 + rs * 25
    elif sector == "Corporate IG":
        return 55 + rs * 15
    elif sector == "High Yield":
        if seniority == "Senior Secured":
            return 250 + (rs - 10) * 80
        elif seniority == "Senior Unsecured":
            return 350 + (rs - 10) * 110
    return 100

# Notching by seniority (rating step down from issuer rating)
NOTCH = {
    "Senior Secured": +1, "Senior Unsecured": 0, "Tier 2": -2, "AT1": -4, "Sub Insurance": -2,
}

RATINGS_ORDERED = ["AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-",
                   "BB+","BB","BB-","B+","B","B-","CCC+","CCC","CCC-"]

def notch_rating(r, n):
    if r not in RATINGS_ORDERED:
        return r
    idx = RATINGS_ORDERED.index(r)
    new_idx = max(0, min(len(RATINGS_ORDERED) - 1, idx - n))  # n positive = upgrade
    return RATINGS_ORDERED[new_idx]


# ============================================================
# BOND GENERATION
# ============================================================
rows = []
isin_counter = 1000000

today = datetime(2026, 6, 8)

for ticker, info in ISSUERS.items():
    seniorities = SENIORITY_BY_SECTOR[info["sector"]]
    for sen in seniorities:
        # number of bonds per seniority
        n_bonds = 1 if info["sector"] in ["Corporate IG"] else (
                  2 if sen == "Senior Unsecured" and info["sector"] == "Banks" else 1)

        for k in range(n_bonds):
            isin_counter += 1
            isin = f"XS{isin_counter:010d}"

            # Maturity: spread across 2 to 12 years; sub debt tends longer
            base_maturity = {"Senior Secured": 5, "Senior Unsecured": 6, "Tier 2": 9, "AT1": 7, "Sub Insurance": 10}[sen]
            maturity_years = base_maturity + np.random.uniform(-1.5, 2.5) + k * 1.5
            maturity_date = today + timedelta(days=int(maturity_years * 365))

            issue_years_ago = np.random.uniform(0.5, 4.0)
            issue_date = today - timedelta(days=int(issue_years_ago * 365))

            # Bond rating (notched from issuer)
            bond_rating = notch_rating(info["rating"], NOTCH[sen])

            # Spread (noise around base)
            z_spread = base_spread(info["sector"], sen, bond_rating)
            z_spread *= np.random.uniform(0.82, 1.18)
            z_spread = round(z_spread, 1)

            # OAS slightly different (callable bonds especially)
            callable = sen in ["AT1", "Tier 2", "Sub Insurance"] or (info["sector"] == "High Yield" and np.random.random() > 0.4)
            if callable:
                oas = z_spread - np.random.uniform(15, 60)
                next_call_years = np.random.uniform(0.8, 4.0)
                next_call = (today + timedelta(days=int(next_call_years * 365))).strftime("%Y-%m-%d")
            else:
                oas = z_spread - np.random.uniform(0, 8)
                next_call = ""
            oas = round(oas, 1)

            # ASW
            asw = round(z_spread - np.random.uniform(2, 12), 1)
            # G-spread (vs govt curve)
            g_spread = round(z_spread + np.random.uniform(-5, 12), 1)

            # YTM (rough: risk-free ~3% in 2026 + Z-spread/100)
            risk_free = 2.85 + np.random.uniform(-0.15, 0.25)  # approx EUR swap
            ytm = round(risk_free + z_spread / 100, 3)

            # Coupon: usually close to historical YTM at issue
            coupon = round(ytm + np.random.uniform(-1.2, 0.8), 3)
            coupon = max(0.5, coupon)

            # Mid price
            duration = maturity_years * 0.85  # rough
            mid_price = round(100 - (ytm - coupon) * duration + np.random.uniform(-2, 2), 3)

            # Modified Duration
            mod_duration = round(maturity_years * np.random.uniform(0.75, 0.92), 3)
            convexity = round(mod_duration ** 2 * np.random.uniform(0.08, 0.12), 3)

            # Amount issued — varies by issuer size and seniority
            if info["sector"] == "Banks":
                amt = np.random.choice([500, 750, 1000, 1250, 1500, 2000]) if sen != "AT1" else np.random.choice([750, 1000, 1500])
            elif info["sector"] == "Insurance":
                amt = np.random.choice([500, 750, 1000, 1250])
            elif info["sector"] == "Corporate IG":
                amt = np.random.choice([500, 750, 1000, 1500])
            else:  # HY
                amt = np.random.choice([300, 400, 500, 600, 750])
            amt_outstanding = amt * np.random.uniform(0.85, 1.0)

            # Liquidity inputs
            bid_ask = {
                "Senior Unsecured": np.random.uniform(2, 8),
                "Senior Secured": np.random.uniform(15, 50),
                "Tier 2": np.random.uniform(5, 15),
                "AT1": np.random.uniform(15, 40),
                "Sub Insurance": np.random.uniform(8, 25),
            }[sen]
            if info["sector"] == "High Yield":
                bid_ask *= 1.8
            bid_ask = round(bid_ask, 1)

            days_traded = int(np.clip(np.random.normal(
                {"Banks": 18, "Insurance": 14, "Corporate IG": 16, "High Yield": 11}[info["sector"]],
                3), 3, 22))

            avg_daily_vol = round(amt * np.random.uniform(0.002, 0.025), 2)  # M

            # Currency
            ccy = "EUR" if info["country"] != "UK" else np.random.choice(["EUR", "GBP"], p=[0.5, 0.5])
            if info["country"] == "CH":
                ccy = np.random.choice(["EUR", "CHF"], p=[0.7, 0.3])

            rows.append({
                "ISIN": isin,
                "Issuer Ticker": ticker,
                "Issuer Name": info["name"],
                "Sector": info["sector"],
                "Sub Sector": info["sub_sector"],
                "Country": info["country"],
                "Issuer Rating SP": info["rating"],
                "Bond Rating SP": bond_rating,
                "Seniority": sen,
                "Issue Date": issue_date.strftime("%Y-%m-%d"),
                "Maturity Date": maturity_date.strftime("%Y-%m-%d"),
                "Years to Maturity": round(maturity_years, 2),
                "Coupon": coupon,
                "Currency": ccy,
                "Amount Issued (M)": amt,
                "Amount Outstanding (M)": round(amt_outstanding, 1),
                "Callable": "Y" if callable else "N",
                "Next Call Date": next_call,
                "Mid Price": mid_price,
                "YTM (%)": ytm,
                "Z-Spread (bps)": z_spread,
                "OAS (bps)": oas,
                "ASW Spread (bps)": asw,
                "G-Spread (bps)": g_spread,
                "Mod Duration": mod_duration,
                "Convexity": convexity,
                "Bid-Ask (cents)": bid_ask,
                "Days Traded per Month": days_traded,
                "Avg Daily Volume (M)": avg_daily_vol,
                # Fundamentals
                "Net Debt / EBITDA": info["lev_or_solvency"] if info["sector"] not in ["Banks", "Insurance"] else None,
                "CET1 Ratio (%)": info["cet1"],
                "Solvency II Ratio (%)": info["lev_or_solvency"] if info["sector"] == "Insurance" else None,
                "ROE (%)": info["roe"],
                # Sector growth outlook (qualitative -> qualitative-to-numerical)
                "Sector Growth Outlook": {
                    "Technology": "Strong",
                    "Pharma": "Moderate",
                    "Luxury": "Moderate",
                    "Energy": "Mixed",
                    "Utilities": "Stable",
                    "Telecom": "Stable",
                    "Industrials": "Moderate",
                    "Infrastructure": "Stable",
                    "Chemicals": "Mixed",
                    "Autos": "Weak",
                    "Autos Suppliers": "Weak",
                    "Services": "Moderate",
                    "Retail Food": "Stable",
                    "Leisure": "Mixed",
                    "GSIB": "Stable",
                    "Domestic": "Stable",
                    "Life & P&C": "Stable",
                    "Life": "Stable",
                    "Reinsurance": "Moderate",
                }.get(info["sub_sector"], "Moderate"),
            })

df = pd.DataFrame(rows)
df.to_csv("/home/claude/credit_rv_screener/inputs.csv", index=False)
print(f"Generated {len(df)} bond emissions across {df['Sector'].nunique()} sectors")
print(df.groupby("Sector").size())
print("\nSample columns:", list(df.columns))
print(f"\nFirst 3 rows:\n{df.head(3).to_string()}")
