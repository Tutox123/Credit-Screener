"""
Credit RV Screener — Dashboard Streamlit
========================================
Outil de screening de relative value sur l'univers crédit européen.

Encodage visuel:
    - Axe X            : Score de Risque (faible = sûr)
    - Axe Y            : Score de Reward (élevé = attractif)
    - Taille des bulles: Score de Liquidité (plus grand = plus liquide)
    - Forme            : Séniorité (position dans la capital structure)
    - Couleur          : Émetteur (une couleur par émetteur)

Les pondérations peuvent être modifiées en direct via la sidebar
- les scores se recalculent automatiquement.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import copy

from scoring_engine import load_config, score_universe

# ============================================================
# CONFIG STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Credit RV Screener",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent

# ----- Design tokens -----
NAVY = "#0A0E1A"
NAVY_2 = "#111729"
NAVY_3 = "#1A2235"
GOLD = "#C9A961"
GOLD_SOFT = "#B59550"
TEXT_PRIMARY = "#F2F1ED"
TEXT_SECONDARY = "#9CA3B0"
TEXT_MUTED = "#5E6678"
RED = "#D45353"
GREEN = "#5FB37C"
GRID = "#1F2A3F"

# Forme par seniorité
SHAPE_BY_SENIORITY = {
    "Senior Secured": "square",
    "Senior Unsecured": "circle",
    "Tier 2": "diamond",
    "AT1": "triangle-up",
    "Sub Insurance": "pentagon",
}
SENIORITY_LABEL_FR = {
    "Senior Secured": "Senior Sécurisé",
    "Senior Unsecured": "Senior Non-Sécurisé",
    "Tier 2": "Tier 2",
    "AT1": "AT1",
    "Sub Insurance": "Subordonné Assurance",
}
SENIORITY_SYMBOL_UNICODE = {
    "Senior Secured": "■",
    "Senior Unsecured": "●",
    "Tier 2": "◆",
    "AT1": "▲",
    "Sub Insurance": "⬟",
}

# Palette couleurs émetteurs
ISSUER_PALETTE = [
    "#C9A961", "#7BA7BC", "#B47B84", "#8BA888", "#C8917E",
    "#A09BC4", "#D4B26A", "#6FA3A8", "#B58FA8", "#A8B070",
    "#9D7FA3", "#7B96B8", "#C9926E", "#76A88A", "#B47B68",
    "#8E94BC", "#C49A88", "#7CA290", "#B89870", "#A678A0",
    "#D9B36F", "#83B0B6", "#C28C7A", "#94A47F", "#A88BBC",
    "#7AA0A8", "#BC8E70", "#9BAE8B", "#B098C2", "#D2A47F",
    "#85ACB6", "#C49888", "#8FB59B", "#B58AA3", "#7E9DBE",
    "#CFA670",
]

# ============================================================
# STYLES
# ============================================================

CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, sans-serif !important;
    }}
    .stApp {{ background-color: {NAVY}; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {NAVY_2};
        border-right: 1px solid {GRID};
    }}
    [data-testid="stSidebar"] * {{ color: {TEXT_PRIMARY}; }}
    [data-testid="stSidebar"] h3 {{
        color: {GOLD} !important;
        font-size: 0.7rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-top: 1.2rem;
    }}
    [data-testid="stSidebar"] .stSlider label {{
        font-size: 0.78rem !important;
        color: {TEXT_SECONDARY} !important;
    }}

    /* Titres */
    h1, h2, h3, h4 {{ color: {TEXT_PRIMARY}; font-weight: 600; letter-spacing: -0.01em; }}
    h1 {{ font-size: 1.65rem !important; font-weight: 500 !important; }}
    h2 {{ font-size: 1.05rem !important; margin-top: 1rem !important; }}
    h3 {{
        font-size: 0.9rem !important;
        color: {TEXT_SECONDARY} !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 500 !important;
    }}
    p, label, span, div, .stMarkdown {{ color: {TEXT_PRIMARY}; }}

    /* KPI Cards */
    .kpi-card {{
        background: {NAVY_2};
        border: 1px solid {GRID};
        border-radius: 4px;
        padding: 1rem 1.2rem;
        height: 100%;
    }}
    .kpi-label {{
        color: {TEXT_MUTED};
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 500;
        margin-bottom: 0.3rem;
    }}
    .kpi-value {{
        color: {TEXT_PRIMARY};
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 500;
    }}
    .kpi-value-gold {{ color: {GOLD}; }}
    .kpi-subtext {{ color: {TEXT_SECONDARY}; font-size: 0.7rem; margin-top: 0.2rem; }}

    /* Header */
    .header-title {{
        font-size: 1.6rem; font-weight: 500;
        color: {TEXT_PRIMARY}; letter-spacing: -0.01em;
    }}
    .header-subtitle {{
        font-size: 0.7rem; color: {TEXT_MUTED};
        text-transform: uppercase; letter-spacing: 0.15em;
    }}
    .header-version {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem; color: {GOLD};
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; border-bottom: 1px solid {GRID}; background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; color: {TEXT_MUTED};
        font-weight: 500; font-size: 0.85rem;
        padding: 0.7rem 1.2rem;
        border: none; border-bottom: 2px solid transparent;
        margin-bottom: -1px;
    }}
    .stTabs [aria-selected="true"] {{
        color: {GOLD} !important;
        border-bottom-color: {GOLD} !important;
        background: transparent !important;
    }}

    /* Dataframe */
    .stDataFrame {{
        background-color: {NAVY_2} !important;
        border-radius: 4px;
        border: 1px solid {GRID};
    }}

    /* Sliders */
    [data-testid="stSlider"] [role="slider"] {{ background-color: {GOLD}; }}

    /* Multiselect */
    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {NAVY_3} !important;
        color: {TEXT_PRIMARY} !important;
    }}

    /* Expander */
    .streamlit-expanderHeader, [data-testid="stExpander"] summary {{
        background: {NAVY_3} !important;
        color: {TEXT_PRIMARY} !important;
        border-radius: 4px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
    }}
    [data-testid="stExpander"] {{
        border: 1px solid {GRID} !important;
        border-radius: 4px !important;
    }}

    /* Button */
    .stButton button {{
        background: {NAVY_3} !important;
        color: {GOLD} !important;
        border: 1px solid {GOLD} !important;
        font-weight: 500;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    .stButton button:hover {{
        background: {GOLD} !important;
        color: {NAVY} !important;
    }}

    /* Footer */
    .footer {{
        margin-top: 3rem; padding: 1rem 0;
        border-top: 1px solid {GRID};
        text-align: center; color: {TEXT_MUTED};
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.1em;
    }}
    .section-divider {{ border-top: 1px solid {GRID}; margin: 1.5rem 0; }}

    /* Weight sum indicator */
    .weight-sum {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        padding: 0.4rem 0.6rem;
        border-radius: 3px;
        margin-bottom: 0.5rem;
        text-align: center;
    }}
    .weight-sum-ok {{ background: rgba(95, 179, 124, 0.15); color: {GREEN}; border: 1px solid {GREEN}; }}
    .weight-sum-warn {{ background: rgba(212, 83, 83, 0.15); color: {RED}; border: 1px solid {RED}; }}

    /* Hide Streamlit defaults */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

@st.cache_data
def load_inputs():
    return pd.read_csv(BASE_DIR / "inputs.csv")


@st.cache_data
def load_default_cfg():
    return load_config()


df_inputs = load_inputs()
default_cfg = load_default_cfg()


# ============================================================
# HEADER
# ============================================================

col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1:
    st.markdown(f"""
        <div>
            <div class="header-title">CREDIT RV SCREENER</div>
            <div class="header-subtitle">Univers Crédit Européen · Cadre Relative Value</div>
        </div>
    """, unsafe_allow_html=True)
with col_h3:
    st.markdown(f"""
        <div style="text-align: right; padding-top: 0.6rem;">
            <div class="header-version">MÉTHODOLOGIE v1.0</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ============================================================
# SIDEBAR - FILTRES + PONDÉRATIONS
# ============================================================

with st.sidebar:
    st.markdown("### Filtres")

    sectors = st.multiselect(
        "Secteur",
        options=sorted(df_inputs["Sector"].unique()),
        default=sorted(df_inputs["Sector"].unique()),
    )
    seniorities = st.multiselect(
        "Séniorité",
        options=list(SHAPE_BY_SENIORITY.keys()),
        default=list(SHAPE_BY_SENIORITY.keys()),
        format_func=lambda x: SENIORITY_LABEL_FR.get(x, x),
    )
    countries = st.multiselect(
        "Pays",
        options=sorted(df_inputs["Country"].unique()),
        default=sorted(df_inputs["Country"].unique()),
    )
    ratings_order = ["AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-",
                     "BB+","BB","BB-","B+","B","B-","CCC+","CCC","CCC-"]
    available_ratings = [r for r in ratings_order if r in df_inputs["Bond Rating SP"].unique()]
    ratings = st.multiselect("Rating Obligation", options=available_ratings, default=available_ratings)

    st.markdown("### Caractéristiques Obligation")
    mat_min, mat_max = float(df_inputs["Years to Maturity"].min()), float(df_inputs["Years to Maturity"].max())
    maturity_range = st.slider("Maturité (années)", min_value=mat_min, max_value=mat_max,
                                value=(mat_min, mat_max), step=0.5)
    min_amt = float(df_inputs["Amount Outstanding (M)"].min())
    max_amt = float(df_inputs["Amount Outstanding (M)"].max())
    amt_range = st.slider("Encours (€M)", min_value=min_amt, max_value=max_amt,
                           value=(min_amt, max_amt), step=50.0)

    min_liq = st.slider("Liquidité minimale", 0, 100, 0, 5)

    st.markdown("### Affichage")
    show_diagonal = st.checkbox("Afficher la diagonale de fair value", value=True)
    show_labels = st.checkbox("Étiqueter le top 5 RV", value=True)

    # ============================================================
    # PONDÉRATIONS (live editing)
    # ============================================================
    st.markdown("### Pondérations")

    if "cfg_overrides" not in st.session_state:
        st.session_state.cfg_overrides = None

    if st.button("⟲ Reset aux pondérations par défaut", use_container_width=True):
        st.session_state.cfg_overrides = None
        st.rerun()

    # Build a working copy of cfg
    cfg = copy.deepcopy(default_cfg)
    if st.session_state.cfg_overrides:
        # Apply session overrides
        for path, value in st.session_state.cfg_overrides.items():
            keys = path.split(".")
            d = cfg
            for k in keys[:-1]:
                d = d[k]
            d[keys[-1]] = value

    # ---------- RISK SCORE ----------
    with st.expander("◆  Score de Risque - Blocs", expanded=False):
        risk_idio = st.slider("Bloc A · Idiosyncratique (%)",
                              0, 100,
                              int(cfg["risk_score"]["idiosyncratic"]["total"] * 100),
                              step=1, key="r_idio")
        risk_sector = st.slider("Bloc B · Risque Sectoriel (%)",
                                0, 100,
                                int(cfg["risk_score"]["sector_risk"]["total"] * 100),
                                step=1, key="r_sec")
        risk_macro = st.slider("Bloc C · Risque Macro (%)",
                                0, 100,
                                int(cfg["risk_score"]["macro_risk"]["total"] * 100),
                                step=1, key="r_macro")

        risk_total = risk_idio + risk_sector + risk_macro
        cls = "weight-sum-ok" if risk_total == 100 else "weight-sum-warn"
        st.markdown(f'<div class="weight-sum {cls}">Σ = {risk_total}% '
                    f'{"(OK, normalisé)" if risk_total == 100 else "(sera normalisé)"}</div>',
                    unsafe_allow_html=True)

        cfg["risk_score"]["idiosyncratic"]["total"] = risk_idio / 100
        cfg["risk_score"]["sector_risk"]["total"] = risk_sector / 100
        cfg["risk_score"]["macro_risk"]["total"] = risk_macro / 100

    with st.expander("    └ Sous-pondérations · Idiosyncratique", expanded=False):
        c = cfg["risk_score"]["idiosyncratic"]["components"]
        c["bond_rating"] = st.slider("Rating Obligation", 0.0, 0.50, c["bond_rating"], 0.01, format="%.2f")
        c["subordination"] = st.slider("Subordination", 0.0, 0.50, c["subordination"], 0.01, format="%.2f")
        c["leverage"] = st.slider("Levier (ND/EBITDA · CET1 · S2)", 0.0, 0.50, c["leverage"], 0.01, format="%.2f")
        c["duration"] = st.slider("Duration modifiée", 0.0, 0.50, c["duration"], 0.01, format="%.2f")

    with st.expander("    └ Sous-pondérations · Sectoriel", expanded=False):
        c = cfg["risk_score"]["sector_risk"]["components"]
        c["cyclicality"] = st.slider("Cyclicité", 0.0, 0.30, c["cyclicality"], 0.01, format="%.2f")
        c["default_history"] = st.slider("Historique défaut", 0.0, 0.30, c["default_history"], 0.01, format="%.2f")
        c["spread_volatility"] = st.slider("Vol. de spreads", 0.0, 0.30, c["spread_volatility"], 0.01, format="%.2f")

    with st.expander("    └ Sous-pondérations · Macro", expanded=False):
        c = cfg["risk_score"]["macro_risk"]["components"]
        c["geopolitical"] = st.slider("Géopolitique", 0.0, 0.20, c["geopolitical"], 0.01, format="%.2f")
        c["rates_sensitivity"] = st.slider("Sensibilité aux taux", 0.0, 0.20, c["rates_sensitivity"], 0.01, format="%.2f")
        c["fx_exposure"] = st.slider("Exposition FX", 0.0, 0.20, c["fx_exposure"], 0.01, format="%.2f")
        c["regulatory"] = st.slider("Pression réglementaire", 0.0, 0.20, c["regulatory"], 0.01, format="%.2f")

    # ---------- REWARD SCORE ----------
    with st.expander("◆  Score de Reward - Blocs", expanded=False):
        rew_spread = st.slider("Bloc A · Attractivité du Spread (%)",
                                0, 100,
                                int(cfg["reward_score"]["spread_attractiveness"]["total"] * 100),
                                step=1, key="w_spread")
        rew_carry = st.slider("Bloc B · Carry & Roll (%)",
                               0, 100,
                               int(cfg["reward_score"]["carry_and_roll"]["total"] * 100),
                               step=1, key="w_carry")
        rew_growth = st.slider("Bloc C · Croissance Sectorielle (%)",
                                0, 100,
                                int(cfg["reward_score"]["sector_growth_momentum"]["total"] * 100),
                                step=1, key="w_growth")

        rew_total = rew_spread + rew_carry + rew_growth
        cls = "weight-sum-ok" if rew_total == 100 else "weight-sum-warn"
        st.markdown(f'<div class="weight-sum {cls}">Σ = {rew_total}% '
                    f'{"(OK, normalisé)" if rew_total == 100 else "(sera normalisé)"}</div>',
                    unsafe_allow_html=True)

        cfg["reward_score"]["spread_attractiveness"]["total"] = rew_spread / 100
        cfg["reward_score"]["carry_and_roll"]["total"] = rew_carry / 100
        cfg["reward_score"]["sector_growth_momentum"]["total"] = rew_growth / 100

    with st.expander("    └ Sous-pondérations · Spread", expanded=False):
        c = cfg["reward_score"]["spread_attractiveness"]["components"]
        c["z_spread_vs_universe"] = st.slider("Z-Spread vs Univers", 0.0, 0.60, c["z_spread_vs_universe"], 0.01, format="%.2f")
        c["spread_vs_sector"] = st.slider("Pickup vs Secteur", 0.0, 0.60, c["spread_vs_sector"], 0.01, format="%.2f")
        c["spread_vs_rating"] = st.slider("Pickup vs Rating", 0.0, 0.60, c["spread_vs_rating"], 0.01, format="%.2f")

    with st.expander("    └ Sous-pondérations · Carry & Roll", expanded=False):
        c = cfg["reward_score"]["carry_and_roll"]["components"]
        c["running_yield"] = st.slider("Yield courant", 0.0, 0.30, c["running_yield"], 0.01, format="%.2f")
        c["roll_down_1y"] = st.slider("Roll-down 1Y", 0.0, 0.30, c["roll_down_1y"], 0.01, format="%.2f")

    with st.expander("    └ Sous-pondérations · Croissance Sectorielle", expanded=False):
        c = cfg["reward_score"]["sector_growth_momentum"]["components"]
        c["growth_outlook"] = st.slider("Perspective croissance", 0.0, 0.30, c["growth_outlook"], 0.01, format="%.2f")
        c["earnings_revision"] = st.slider("Révisions ROE", 0.0, 0.30, c["earnings_revision"], 0.01, format="%.2f")
        c["spread_momentum_3m"] = st.slider("Momentum spread 3M", 0.0, 0.30, c["spread_momentum_3m"], 0.01, format="%.2f")


# ============================================================
# SCORING LIVE
# ============================================================

@st.cache_data(show_spinner=False)
def cached_score(df, cfg_hash, cfg):
    return score_universe(df, cfg)

# Hash the cfg for caching (avoid recomputing if nothing changed)
import hashlib, json
cfg_str = json.dumps(cfg, sort_keys=True, default=str)
cfg_hash = hashlib.md5(cfg_str.encode()).hexdigest()
df_full = cached_score(df_inputs, cfg_hash, cfg)

# Appliquer les filtres
df = df_full[
    df_full["Sector"].isin(sectors)
    & df_full["Seniority"].isin(seniorities)
    & df_full["Country"].isin(countries)
    & df_full["Bond Rating SP"].isin(ratings)
    & df_full["Years to Maturity"].between(*maturity_range)
    & df_full["Amount Outstanding (M)"].between(*amt_range)
    & (df_full["Liquidity Score"] >= min_liq)
].copy()


# ============================================================
# KPI ROW
# ============================================================

if len(df) == 0:
    st.warning("Aucune obligation ne correspond aux filtres actuels.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Univers Filtré</div>
        <div class="kpi-value">{len(df)}</div>
        <div class="kpi-subtext">sur {len(df_full)} obligations</div>
    </div>""", unsafe_allow_html=True)
with k2:
    avg_z = df["Z-Spread (bps)"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Z-Spread Moyen</div>
        <div class="kpi-value">{avg_z:.0f} <span style="font-size:0.7rem; color:{TEXT_MUTED}">bps</span></div>
        <div class="kpi-subtext">moyenne arithmétique</div>
    </div>""", unsafe_allow_html=True)
with k3:
    avg_ytm = df["YTM (%)"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">YTM Moyen</div>
        <div class="kpi-value">{avg_ytm:.2f}<span style="font-size:0.8rem">%</span></div>
        <div class="kpi-subtext">sur la sélection</div>
    </div>""", unsafe_allow_html=True)
with k4:
    avg_rv = df["RV Score"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Score RV Moyen</div>
        <div class="kpi-value kpi-value-gold">{avg_rv:.2f}</div>
        <div class="kpi-subtext">ratio reward / risque</div>
    </div>""", unsafe_allow_html=True)
with k5:
    total_size = df["Amount Outstanding (M)"].sum() / 1000
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Encours Total</div>
        <div class="kpi-value">€{total_size:.1f}<span style="font-size:0.8rem">Md</span></div>
        <div class="kpi-subtext">montant notionnel</div>
    </div>""", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "◆  Screener RV",
    "▦  Carte Sectorielle",
    "★  Top Picks",
    "◉  Détail Émetteur",
])


# ============================================================
# TAB 1: BUBBLE CHART
# ============================================================
with tab1:
    st.markdown("### Risque vs Reward")

    unique_issuers = sorted(df["Issuer Name"].unique())
    color_map = {iss: ISSUER_PALETTE[i % len(ISSUER_PALETTE)] for i, iss in enumerate(unique_issuers)}

    fig = go.Figure()

    max_liq = df["Liquidity Score"].max() if df["Liquidity Score"].max() > 0 else 100

    for issuer in unique_issuers:
        for sen in df[df["Issuer Name"] == issuer]["Seniority"].unique():
            sub = df[(df["Issuer Name"] == issuer) & (df["Seniority"] == sen)]
            if len(sub) == 0:
                continue
            sub_sizes = (sub["Liquidity Score"] / max_liq * 45 + 10).values

            fig.add_trace(go.Scatter(
                x=sub["Risk Score"],
                y=sub["Reward Score"],
                mode="markers",
                name=issuer,
                legendgroup=issuer,
                showlegend=(sen == sub["Seniority"].iloc[0]),
                marker=dict(
                    size=sub_sizes,
                    symbol=SHAPE_BY_SENIORITY.get(sen, "circle"),
                    color=color_map[issuer],
                    line=dict(width=1.2, color="rgba(255,255,255,0.4)"),
                    opacity=0.85,
                ),
                customdata=np.stack([
                    sub["Issuer Name"], sub["Seniority"], sub["Bond Rating SP"],
                    sub["Z-Spread (bps)"], sub["YTM (%)"], sub["Years to Maturity"],
                    sub["Liquidity Score"], sub["RV Score"], sub["ISIN"],
                    sub["Amount Outstanding (M)"], sub["Mod Duration"],
                ], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                    "<span style='color:#9CA3B0'>ISIN</span> %{customdata[8]}<br>"
                    "<span style='color:#9CA3B0'>Rating</span> %{customdata[2]}  "
                    "<span style='color:#9CA3B0'>Maturité</span> %{customdata[5]:.1f}a  "
                    "<span style='color:#9CA3B0'>Duration</span> %{customdata[10]:.1f}<br>"
                    "<span style='color:#9CA3B0'>Z-Spread</span> %{customdata[3]:.0f} bps  "
                    "<span style='color:#9CA3B0'>YTM</span> %{customdata[4]:.2f}%<br>"
                    "<span style='color:#9CA3B0'>Encours</span> €%{customdata[9]:.0f}M  "
                    "<span style='color:#9CA3B0'>Liquidité</span> %{customdata[6]:.0f}/100<br>"
                    "<b style='color:#C9A961'>Score RV: %{customdata[7]:.2f}</b>"
                    "<extra></extra>"
                ),
            ))

    if show_diagonal and len(df) > 2:
        ref_x = np.linspace(df["Risk Score"].min(), df["Risk Score"].max(), 50)
        z_fit = np.polyfit(df["Risk Score"], df["Reward Score"], 1)
        ref_y = z_fit[0] * ref_x + z_fit[1]
        fig.add_trace(go.Scatter(
            x=ref_x, y=ref_y,
            mode="lines",
            line=dict(color=GOLD, width=1, dash="dot"),
            name="Fair Value",
            hoverinfo="skip",
            showlegend=True,
        ))

    if show_labels:
        top5 = df.nlargest(5, "RV Score")
        for _, row in top5.iterrows():
            fig.add_annotation(
                x=row["Risk Score"], y=row["Reward Score"],
                text=f"<b>{row['Issuer Name'][:14]}</b>",
                showarrow=True, arrowhead=0, arrowsize=0.6, arrowwidth=1, arrowcolor=GOLD,
                ax=18, ay=-18,
                font=dict(size=9, color=GOLD, family="JetBrains Mono"),
                bgcolor="rgba(10,14,26,0.85)",
                bordercolor=GOLD, borderwidth=0.5, borderpad=3,
            )

    fig.update_layout(
        height=620,
        paper_bgcolor=NAVY, plot_bgcolor=NAVY,
        font=dict(family="Inter, sans-serif", color=TEXT_PRIMARY, size=11),
        xaxis=dict(
            title=dict(text="<b>SCORE DE RISQUE</b>", font=dict(size=11, color=TEXT_SECONDARY)),
            gridcolor=GRID, zerolinecolor=GRID,
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
        yaxis=dict(
            title=dict(text="<b>SCORE DE REWARD</b>", font=dict(size=11, color=TEXT_SECONDARY)),
            gridcolor=GRID, zerolinecolor=GRID,
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
        legend=dict(
            title=dict(text="<b>Émetteurs</b>",
                       font=dict(size=10, color=TEXT_SECONDARY)),
            bgcolor="rgba(17,23,41,0.7)",
            bordercolor=GRID, borderwidth=1,
            font=dict(size=9.5), itemsizing="constant",
            x=1.01, y=1, yanchor="top",
        ),
        margin=dict(l=40, r=180, t=10, b=40),
        hoverlabel=dict(
            bgcolor=NAVY_2, bordercolor=GOLD,
            font=dict(family="JetBrains Mono", size=11, color=TEXT_PRIMARY),
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ===== LÉGENDES VISUELLES =====
    st.markdown("### Légendes visuelles")
    leg_cols = st.columns(3)

    with leg_cols[0]:
        st.markdown(f"""
            <div style="background:{NAVY_2}; border:1px solid {GRID}; border-radius:4px; padding:0.8rem 1rem;">
                <div style="color:{TEXT_MUTED}; font-size:0.7rem; text-transform:uppercase;
                     letter-spacing:0.1em; margin-bottom:0.5rem;">FORME · Séniorité</div>
                <div style="line-height: 1.9; font-size: 0.82rem;">
                    <span style="color:{GOLD}; font-size: 1.1rem;">■</span>&nbsp;&nbsp;Senior Sécurisé (SS)<br>
                    <span style="color:{GOLD}; font-size: 1.1rem;">●</span>&nbsp;&nbsp;Senior Non-Sécurisé (SU)<br>
                    <span style="color:{GOLD}; font-size: 1.1rem;">◆</span>&nbsp;&nbsp;Tier 2 (T2)<br>
                    <span style="color:{GOLD}; font-size: 1.1rem;">▲</span>&nbsp;&nbsp;Additional Tier 1 (AT1)<br>
                    <span style="color:{GOLD}; font-size: 1.1rem;">⬟</span>&nbsp;&nbsp;Subordonné Assurance
                </div>
            </div>
        """, unsafe_allow_html=True)

    with leg_cols[1]:
        st.markdown(f"""
            <div style="background:{NAVY_2}; border:1px solid {GRID}; border-radius:4px; padding:0.8rem 1rem;">
                <div style="color:{TEXT_MUTED}; font-size:0.7rem; text-transform:uppercase;
                     letter-spacing:0.1em; margin-bottom:0.5rem;">TAILLE · Score de liquidité</div>
                <div style="line-height: 1.9; font-size: 0.82rem;">
                    <span style="color:{GOLD}; font-size: 0.6rem;">●</span>&nbsp;&nbsp;Petite = peu liquide<br>
                    <span style="color:{GOLD}; font-size: 1.0rem;">●</span>&nbsp;&nbsp;Moyenne = liquidité moyenne<br>
                    <span style="color:{GOLD}; font-size: 1.5rem;">●</span>&nbsp;&nbsp;Grande = très liquide<br>
                    <div style="color:{TEXT_MUTED}; font-size:0.7rem; margin-top:0.4rem;">
                        Composite: encours · bid-ask · jours tradés · volume
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with leg_cols[2]:
        st.markdown(f"""
            <div style="background:{NAVY_2}; border:1px solid {GRID}; border-radius:4px; padding:0.8rem 1rem;">
                <div style="color:{TEXT_MUTED}; font-size:0.7rem; text-transform:uppercase;
                     letter-spacing:0.1em; margin-bottom:0.5rem;">COULEUR · Émetteur</div>
                <div style="line-height: 1.9; font-size: 0.82rem;">
                    Une couleur unique par émetteur,<br>
                    partagée par toutes ses émissions<br>
                    (SU, T2, AT1, etc.).<br>
                    <div style="color:{TEXT_MUTED}; font-size:0.7rem; margin-top:0.4rem;">
                        {len(unique_issuers)} émetteurs · voir légende droite du graphique
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)


# ============================================================
# TAB 2: SECTOR HEATMAP
# ============================================================
with tab2:
    st.markdown("### Spread Médian par Secteur × Séniorité")

    pivot = df.pivot_table(
        values="Z-Spread (bps)", index="Sector", columns="Seniority", aggfunc="median"
    ).round(0)

    seniority_order = ["Senior Secured", "Senior Unsecured", "Tier 2", "Sub Insurance", "AT1"]
    seniority_order = [s for s in seniority_order if s in pivot.columns]
    pivot = pivot[seniority_order]

    # Use French labels
    pivot.columns = [SENIORITY_LABEL_FR.get(c, c) for c in pivot.columns]

    fig2 = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        text=pivot.values, texttemplate="%{text:.0f}",
        textfont=dict(family="JetBrains Mono", size=12, color=TEXT_PRIMARY),
        colorscale=[[0, NAVY_3], [0.5, "#3D4E6E"], [1, GOLD]],
        showscale=True,
        colorbar=dict(
            title=dict(text="Z-Spread<br>(bps)", font=dict(size=10, color=TEXT_SECONDARY)),
            tickfont=dict(family="JetBrains Mono", size=10),
            outlinewidth=0, bgcolor=NAVY_2, len=0.85,
        ),
        hovertemplate="<b>%{y}</b> · %{x}<br>Spread Médian: %{z:.0f} bps<extra></extra>",
    ))
    fig2.update_layout(
        height=400,
        paper_bgcolor=NAVY, plot_bgcolor=NAVY,
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        xaxis=dict(side="top", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(l=140, r=20, t=40, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Agrégats Sectoriels")
    sector_agg = df.groupby("Sector").agg(
        Émetteurs=("Issuer Name", "nunique"),
        Obligations=("ISIN", "count"),
        ZSpreadMoy=("Z-Spread (bps)", "mean"),
        YTMMoy=("YTM (%)", "mean"),
        RisqueMoy=("Risk Score", "mean"),
        RewardMoy=("Reward Score", "mean"),
        LiquiditéMoy=("Liquidity Score", "mean"),
        RVMoy=("RV Score", "mean"),
    ).round(2)
    sector_agg.columns = ["Émetteurs", "Oblig.", "Z-Spread Moy.", "YTM Moy.",
                          "Risque Moy.", "Reward Moy.", "Liquidité Moy.", "RV Moy."]
    st.dataframe(sector_agg, use_container_width=True, height=200)


# ============================================================
# TAB 3: TOP RV PICKS
# ============================================================
with tab3:
    st.markdown("### Meilleures Opportunités Relative Value")

    top_n = st.slider("Afficher le top N", 5, 30, 15, 5)

    cols_show = ["RV Rank", "Issuer Name", "Sector", "Seniority", "Bond Rating SP",
                 "Years to Maturity", "Z-Spread (bps)", "YTM (%)",
                 "Risk Score", "Reward Score", "Liquidity Score", "RV Score"]
    top_df = df.nlargest(top_n, "RV Score")[cols_show].reset_index(drop=True)
    top_df["Seniority"] = top_df["Seniority"].map(lambda s: SENIORITY_LABEL_FR.get(s, s))
    top_df.columns = ["Rang", "Émetteur", "Secteur", "Séniorité", "Rating", "Maturité",
                      "Z-Spread", "YTM", "Risque", "Reward", "Liquidité", "RV"]

    st.dataframe(
        top_df.style.format({
            "Maturité": "{:.1f}a",
            "Z-Spread": "{:.0f}",
            "YTM": "{:.2f}%",
            "Risque": "{:.1f}",
            "Reward": "{:.1f}",
            "Liquidité": "{:.0f}",
            "RV": "{:.2f}",
        }),
        use_container_width=True,
        height=min(560, 45 + top_n * 35),
    )

    st.markdown("### Répartition Sectorielle du Top")
    sector_breakdown = top_df["Secteur"].value_counts().reset_index()
    sector_breakdown.columns = ["Secteur", "Nombre"]
    fig_breakdown = go.Figure(go.Bar(
        x=sector_breakdown["Secteur"],
        y=sector_breakdown["Nombre"],
        marker_color=GOLD,
        text=sector_breakdown["Nombre"],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color=TEXT_PRIMARY),
    ))
    fig_breakdown.update_layout(
        height=300,
        paper_bgcolor=NAVY, plot_bgcolor=NAVY,
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(family="JetBrains Mono", size=10)),
        margin=dict(l=20, r=20, t=20, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig_breakdown, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# TAB 4: ISSUER DETAIL
# ============================================================
with tab4:
    st.markdown("### Analyse Émetteur")
    issuer_pick = st.selectbox("Sélectionner un émetteur", sorted(df["Issuer Name"].unique()))
    iss_df = df[df["Issuer Name"] == issuer_pick]

    if len(iss_df) > 0:
        first_row = iss_df.iloc[0]

        cd1, cd2, cd3, cd4 = st.columns(4)
        with cd1:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-label">Secteur / Sous-Secteur</div>
                <div class="kpi-value" style="font-size:0.9rem;">{first_row['Sector']}</div>
                <div class="kpi-subtext">{first_row['Sub Sector']} · {first_row['Country']}</div>
            </div>""", unsafe_allow_html=True)
        with cd2:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-label">Rating Émetteur</div>
                <div class="kpi-value kpi-value-gold">{first_row['Issuer Rating SP']}</div>
                <div class="kpi-subtext">S&P · {len(iss_df)} émission(s)</div>
            </div>""", unsafe_allow_html=True)
        with cd3:
            if first_row['Sector'] == 'Banks':
                metric_lbl = "Ratio CET1"; metric_val = f"{first_row['CET1 Ratio (%)']:.1f}%"
            elif first_row['Sector'] == 'Insurance':
                metric_lbl = "Solvency II"; metric_val = f"{first_row['Solvency II Ratio (%)']:.0f}%"
            else:
                metric_lbl = "ND / EBITDA"; metric_val = f"{first_row['Net Debt / EBITDA']:.1f}x"
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-label">{metric_lbl}</div>
                <div class="kpi-value">{metric_val}</div>
                <div class="kpi-subtext">indicateur clé</div>
            </div>""", unsafe_allow_html=True)
        with cd4:
            best_rv = iss_df["RV Score"].max()
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-label">Meilleur Score RV</div>
                <div class="kpi-value kpi-value-gold">{best_rv:.2f}</div>
                <div class="kpi-subtext">sur {len(iss_df)} obligation(s)</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("### Stack Obligataire")

        cols = ["ISIN", "Seniority", "Bond Rating SP", "Years to Maturity",
                "Coupon", "Currency", "Amount Outstanding (M)", "Mid Price",
                "YTM (%)", "Z-Spread (bps)", "OAS (bps)", "Mod Duration",
                "Liquidity Score", "Risk Score", "Reward Score", "RV Score"]
        bond_table = iss_df[cols].copy()
        bond_table["Seniority"] = bond_table["Seniority"].map(lambda s: SENIORITY_LABEL_FR.get(s, s))
        bond_table.columns = ["ISIN", "Séniorité", "Rating", "Mat (a)", "Coupon",
                              "Dev.", "Encours", "Prix", "YTM",
                              "Z-Spread", "OAS", "Duration",
                              "Liquidité", "Risque", "Reward", "RV"]
        st.dataframe(
            bond_table.style.format({
                "Mat (a)": "{:.1f}", "Coupon": "{:.2f}%", "Encours": "€{:.0f}M",
                "Prix": "{:.2f}", "YTM": "{:.2f}%", "Z-Spread": "{:.0f}",
                "OAS": "{:.0f}", "Duration": "{:.1f}",
                "Liquidité": "{:.0f}", "Risque": "{:.1f}",
                "Reward": "{:.1f}", "RV": "{:.2f}",
            }),
            use_container_width=True,
            height=min(400, 45 + len(iss_df) * 38),
        )

        st.markdown("### Décomposition des Scores (Moyenne)")
        decomp_cols = st.columns(2)
        with decomp_cols[0]:
            st.markdown("**Composantes Risque**")
            risk_decomp = pd.DataFrame({
                "Composante": ["Idiosyncratique", "Sectoriel", "Macro"],
                "Score": [
                    iss_df["Score: Idiosyncratic Risk"].mean(),
                    iss_df["Score: Sector Risk"].mean(),
                    iss_df["Score: Macro Risk"].mean(),
                ],
            })
            fig_r = go.Figure(go.Bar(
                y=risk_decomp["Composante"], x=risk_decomp["Score"], orientation="h",
                marker_color=RED, text=risk_decomp["Score"].round(1),
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=10, color=TEXT_PRIMARY),
            ))
            fig_r.update_layout(
                height=200,
                paper_bgcolor=NAVY, plot_bgcolor=NAVY,
                font=dict(family="Inter", color=TEXT_PRIMARY, size=10),
                xaxis=dict(range=[0, 100], gridcolor=GRID, tickfont=dict(family="JetBrains Mono", size=9)),
                yaxis=dict(tickfont=dict(size=10)),
                margin=dict(l=10, r=40, t=10, b=20), showlegend=False,
            )
            st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})

        with decomp_cols[1]:
            st.markdown("**Composantes Reward**")
            rew_decomp = pd.DataFrame({
                "Composante": ["Attractivité Spread", "Carry & Roll", "Croissance Sect."],
                "Score": [
                    iss_df["Score: Spread Attractiveness"].mean(),
                    iss_df["Score: Carry & Roll"].mean(),
                    iss_df["Score: Sector Growth"].mean(),
                ],
            })
            fig_w = go.Figure(go.Bar(
                y=rew_decomp["Composante"], x=rew_decomp["Score"], orientation="h",
                marker_color=GREEN, text=rew_decomp["Score"].round(1),
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=10, color=TEXT_PRIMARY),
            ))
            fig_w.update_layout(
                height=200,
                paper_bgcolor=NAVY, plot_bgcolor=NAVY,
                font=dict(family="Inter", color=TEXT_PRIMARY, size=10),
                xaxis=dict(range=[0, 100], gridcolor=GRID, tickfont=dict(family="JetBrains Mono", size=9)),
                yaxis=dict(tickfont=dict(size=10)),
                margin=dict(l=10, r=40, t=10, b=20), showlegend=False,
            )
            st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# FOOTER
# ============================================================

st.markdown(f"""
    <div class="footer">
        CREDIT RV SCREENER · MÉTHODOLOGIE v1.0 · {len(df_full)} OBLIGATIONS · PYTHON / STREAMLIT / PLOTLY
    </div>
""", unsafe_allow_html=True)
