"""
Credit RV Screener — Dashboard Streamlit
========================================
Outil de screening de relative value sur l'univers crédit européen.

Structure:
    - Onglet 1 : Vue d'ensemble (toutes les obligations)
    - Onglets 2-6 : Une bulle chart par type d'émission (séniorité)
    - Onglet 7 : Top Picks (classement RV)

Encodage visuel:
    - Axe X            : Score de Risque (faible = sûr)
    - Axe Y            : Score de Reward (élevé = attractif)
    - Taille des bulles: Score de Liquidité
    - Forme            : Séniorité (uniquement utile en vue d'ensemble)
    - Couleur          : Émetteur (une couleur unique par émetteur)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import copy
import hashlib
import json

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

    /* DataFrame - force readable text colors */
    .stDataFrame, [data-testid="stDataFrame"] {{
        background-color: {NAVY_2} !important;
        border-radius: 4px;
        border: 1px solid {GRID};
    }}
    .stDataFrame [role="row"] {{
        background-color: {NAVY_2} !important;
    }}
    .stDataFrame [role="cell"], .stDataFrame [role="columnheader"] {{
        color: {TEXT_PRIMARY} !important;
        background-color: {NAVY_2} !important;
    }}
    .stDataFrame [role="columnheader"] {{
        color: {GOLD} !important;
        font-weight: 500 !important;
    }}

    /* Sliders */
    [data-testid="stSlider"] [role="slider"] {{ background-color: {GOLD}; }}

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

    /* Footer minimal */
    .footer {{
        margin-top: 3rem; padding: 1rem 0;
        border-top: 1px solid {GRID};
        text-align: center; color: {GOLD};
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.15em;
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
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
  
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

st.markdown('<div class="header-title">CREDIT SCREENER</div>', unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ============================================================
# SIDEBAR - PONDÉRATIONS UNIQUEMENT
# ============================================================

with st.sidebar:
    st.markdown("### Pondérations")
    st.markdown(
        f'<div style="color:{TEXT_MUTED}; font-size:0.7rem; line-height:1.4; '
        f'margin-bottom:1rem;">Ajustez les poids pour recalculer les scores en temps réel.</div>',
        unsafe_allow_html=True,
    )

    advanced = st.toggle("Mode avancé", value=False,
                         help="Affiche les sous-pondérations par composante")

    cfg = copy.deepcopy(default_cfg)

    # ----- SCORE DE RISQUE -----
    st.markdown(
        f'<div style="margin-top:1.4rem; margin-bottom:0.4rem; color:{GOLD}; '
        f'font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.14em;">'
        f'Score de Risque</div>'
        f'<div style="height:1px; background:{GRID}; margin-bottom:0.6rem;"></div>',
        unsafe_allow_html=True,
    )

    risk_idio = st.slider("Idiosyncratique", 0, 100,
                          int(cfg["risk_score"]["idiosyncratic"]["total"] * 100),
                          step=1, key="r_idio")
    risk_sector = st.slider("Sectoriel", 0, 100,
                            int(cfg["risk_score"]["sector_risk"]["total"] * 100),
                            step=1, key="r_sec")
    risk_macro = st.slider("Macro", 0, 100,
                            int(cfg["risk_score"]["macro_risk"]["total"] * 100),
                            step=1, key="r_macro")

    risk_total = risk_idio + risk_sector + risk_macro
    cls = "weight-sum-ok" if risk_total == 100 else "weight-sum-warn"
    st.markdown(f'<div class="weight-sum {cls}">Σ = {risk_total}%</div>',
                unsafe_allow_html=True)

    cfg["risk_score"]["idiosyncratic"]["total"] = risk_idio / 100
    cfg["risk_score"]["sector_risk"]["total"] = risk_sector / 100
    cfg["risk_score"]["macro_risk"]["total"] = risk_macro / 100

    if advanced:
        with st.expander("Détail · Idiosyncratique"):
            c = cfg["risk_score"]["idiosyncratic"]["components"]
            c["bond_rating"] = st.slider("Rating", 0.0, 0.50, c["bond_rating"], 0.01, format="%.2f", key="r_ido_rat")
            c["subordination"] = st.slider("Subordination", 0.0, 0.50, c["subordination"], 0.01, format="%.2f", key="r_ido_sub")
            c["leverage"] = st.slider("Levier", 0.0, 0.50, c["leverage"], 0.01, format="%.2f", key="r_ido_lev")
            c["duration"] = st.slider("Duration", 0.0, 0.50, c["duration"], 0.01, format="%.2f", key="r_ido_dur")

        with st.expander("Détail · Sectoriel"):
            c = cfg["risk_score"]["sector_risk"]["components"]
            c["cyclicality"] = st.slider("Cyclicité", 0.0, 0.30, c["cyclicality"], 0.01, format="%.2f", key="r_sec_cyc")
            c["default_history"] = st.slider("Hist. défaut", 0.0, 0.30, c["default_history"], 0.01, format="%.2f", key="r_sec_def")
            c["spread_volatility"] = st.slider("Vol. spreads", 0.0, 0.30, c["spread_volatility"], 0.01, format="%.2f", key="r_sec_vol")

        with st.expander("Détail · Macro"):
            c = cfg["risk_score"]["macro_risk"]["components"]
            c["geopolitical"] = st.slider("Géopolitique", 0.0, 0.20, c["geopolitical"], 0.01, format="%.2f", key="r_mac_geo")
            c["rates_sensitivity"] = st.slider("Sens. taux", 0.0, 0.20, c["rates_sensitivity"], 0.01, format="%.2f", key="r_mac_rat")
            c["fx_exposure"] = st.slider("FX", 0.0, 0.20, c["fx_exposure"], 0.01, format="%.2f", key="r_mac_fx")
            c["regulatory"] = st.slider("Régulation", 0.0, 0.20, c["regulatory"], 0.01, format="%.2f", key="r_mac_reg")

    # ----- SCORE DE REWARD -----
    st.markdown(
        f'<div style="margin-top:1.6rem; margin-bottom:0.4rem; color:{GOLD}; '
        f'font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.14em;">'
        f'Score de Reward</div>'
        f'<div style="height:1px; background:{GRID}; margin-bottom:0.6rem;"></div>',
        unsafe_allow_html=True,
    )

    rew_spread = st.slider("Attractivité spread", 0, 100,
                            int(cfg["reward_score"]["spread_attractiveness"]["total"] * 100),
                            step=1, key="w_spread")
    rew_carry = st.slider("Carry & Roll", 0, 100,
                           int(cfg["reward_score"]["carry_and_roll"]["total"] * 100),
                           step=1, key="w_carry")
    rew_growth = st.slider("Croissance sectorielle", 0, 100,
                            int(cfg["reward_score"]["sector_growth_momentum"]["total"] * 100),
                            step=1, key="w_growth")

    rew_total = rew_spread + rew_carry + rew_growth
    cls = "weight-sum-ok" if rew_total == 100 else "weight-sum-warn"
    st.markdown(f'<div class="weight-sum {cls}">Σ = {rew_total}%</div>',
                unsafe_allow_html=True)

    cfg["reward_score"]["spread_attractiveness"]["total"] = rew_spread / 100
    cfg["reward_score"]["carry_and_roll"]["total"] = rew_carry / 100
    cfg["reward_score"]["sector_growth_momentum"]["total"] = rew_growth / 100

    if advanced:
        with st.expander("Détail · Spread"):
            c = cfg["reward_score"]["spread_attractiveness"]["components"]
            c["z_spread_vs_universe"] = st.slider("Z-Spread vs Univers", 0.0, 0.60, c["z_spread_vs_universe"], 0.01, format="%.2f", key="w_spr_univ")
            c["spread_vs_sector"] = st.slider("Pickup vs Secteur", 0.0, 0.60, c["spread_vs_sector"], 0.01, format="%.2f", key="w_spr_sec")
            c["spread_vs_rating"] = st.slider("Pickup vs Rating", 0.0, 0.60, c["spread_vs_rating"], 0.01, format="%.2f", key="w_spr_rat")

        with st.expander("Détail · Carry & Roll"):
            c = cfg["reward_score"]["carry_and_roll"]["components"]
            c["running_yield"] = st.slider("Yield courant", 0.0, 0.30, c["running_yield"], 0.01, format="%.2f", key="w_car_yld")
            c["roll_down_1y"] = st.slider("Roll-down", 0.0, 0.30, c["roll_down_1y"], 0.01, format="%.2f", key="w_car_rol")

        with st.expander("Détail · Croissance"):
            c = cfg["reward_score"]["sector_growth_momentum"]["components"]
            c["growth_outlook"] = st.slider("Perspective", 0.0, 0.30, c["growth_outlook"], 0.01, format="%.2f", key="w_gro_out")
            c["earnings_revision"] = st.slider("Révisions ROE", 0.0, 0.30, c["earnings_revision"], 0.01, format="%.2f", key="w_gro_rev")
            c["spread_momentum_3m"] = st.slider("Momentum 3M", 0.0, 0.30, c["spread_momentum_3m"], 0.01, format="%.2f", key="w_gro_mom")

    # ----- RESET -----
    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)
    if st.button("⟲ Reset"):
        for k in list(st.session_state.keys()):
            if k.startswith("r_") or k.startswith("w_"):
                del st.session_state[k]
        st.rerun()

# ============================================================
# SCORING LIVE
# ============================================================
df_full = score_universe(df_inputs, cfg)


# ============================================================
# KPI ROW (univers complet)
# ============================================================

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Univers</div>
        <div class="kpi-value">{len(df_full)}</div>
       <div class="kpi-subtext">obligations - {df_full["Issuer Name"].nunique()} émetteurs</div>
    </div>""", unsafe_allow_html=True)
with k2:
    avg_z = df_full["Z-Spread (bps)"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Z-Spread Moyen</div>
        <div class="kpi-value">{avg_z:.0f} <span style="font-size:0.7rem; color:{TEXT_MUTED}">bps</span></div>
        <div class="kpi-subtext">moyenne arithmétique</div>
    </div>""", unsafe_allow_html=True)
with k3:
    avg_ytm = df_full["YTM (%)"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">YTM Moyen</div>
        <div class="kpi-value">{avg_ytm:.2f}<span style="font-size:0.8rem">%</span></div>
        <div class="kpi-subtext">sur l'univers complet</div>
    </div>""", unsafe_allow_html=True)
with k4:
    avg_rv = df_full["RV Score"].mean()
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Score RV Moyen</div>
        <div class="kpi-value kpi-value-gold">{avg_rv:.2f}</div>
        <div class="kpi-subtext">ratio reward / risque</div>
    </div>""", unsafe_allow_html=True)
with k5:
    total_size = df_full["Amount Outstanding (M)"].sum() / 1000
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Encours Total</div>
        <div class="kpi-value">€{total_size:.1f}<span style="font-size:0.8rem">Md</span></div>
        <div class="kpi-subtext">montant notionnel</div>
    </div>""", unsafe_allow_html=True)


# ============================================================
# FONCTION DE BUBBLE CHART RÉUTILISABLE
# ============================================================

def render_bubble_chart(df_plot, color_map_full, show_shape_legend=True, title=""):
    """
    Génère un bubble chart standardisé.
    - Une trace de DATA par émetteur (avec formes mixtes)
    - Une trace LÉGENDE par émetteur (cercle uniquement, hors graphique)
    Résultat: une seule entrée dans la légende par émetteur, forme cercle.
    """
    if len(df_plot) == 0:
        st.info("Aucune obligation pour cette catégorie.")
        return

    fig = go.Figure()
    max_liq = df_full["Liquidity Score"].max() if df_full["Liquidity Score"].max() > 0 else 100

    unique_issuers = sorted(df_plot["Issuer Name"].unique())

    # Traces de DATA (sans légende - showlegend=False)
    for issuer in unique_issuers:
        df_iss = df_plot[df_plot["Issuer Name"] == issuer]
        sizes = (df_iss["Liquidity Score"] / max_liq * 45 + 10).values
        symbols = df_iss["Seniority"].map(SHAPE_BY_SENIORITY).values

        fig.add_trace(go.Scatter(
            x=df_iss["Risk Score"],
            y=df_iss["Reward Score"],
            mode="markers",
            legendgroup=issuer,
            showlegend=False,
            marker=dict(
                size=sizes,
                symbol=symbols,
                color=color_map_full[issuer],
                line=dict(width=1.2, color="rgba(255,255,255,0.4)"),
                opacity=0.85,
            ),
            customdata=np.stack([
                df_iss["Issuer Name"], df_iss["Seniority"], df_iss["Bond Rating SP"],
                df_iss["Z-Spread (bps)"], df_iss["YTM (%)"], df_iss["Years to Maturity"],
                df_iss["Liquidity Score"], df_iss["RV Score"], df_iss["ISIN"],
                df_iss["Amount Outstanding (M)"], df_iss["Mod Duration"],
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

    # Traces de LÉGENDE (cercle uniforme, une par émetteur)
    for issuer in unique_issuers:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            name=issuer,
            legendgroup=issuer,
            showlegend=True,
            marker=dict(
                size=10,
                symbol="circle",
                color=color_map_full[issuer],
                line=dict(width=1.2, color="rgba(255,255,255,0.4)"),
            ),
            hoverinfo="skip",
        ))

    # Diagonale fair value
    if len(df_plot) > 2:
        ref_x = np.linspace(df_plot["Risk Score"].min(), df_plot["Risk Score"].max(), 50)
        z_fit = np.polyfit(df_plot["Risk Score"], df_plot["Reward Score"], 1)
        ref_y = z_fit[0] * ref_x + z_fit[1]
        fig.add_trace(go.Scatter(
            x=ref_x, y=ref_y,
            mode="lines",
            line=dict(color=GOLD, width=1, dash="dot"),
            name="Fair Value",
            hoverinfo="skip",
            showlegend=True,
        ))

    # Labels top 5
    top5 = df_plot.nlargest(min(5, len(df_plot)), "RV Score")
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
            title=dict(text="<b>Émetteurs</b>", font=dict(size=10, color=TEXT_SECONDARY)),
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

    # Légendes visuelles sous le chart
    if show_shape_legend:
        leg_cols = st.columns(3)
        with leg_cols[0]:
            st.markdown(f"""
                <div style="background:{NAVY_2}; border:1px solid {GRID}; border-radius:4px; padding:0.8rem 1rem;">
                    <div style="color:{TEXT_MUTED}; font-size:0.7rem; text-transform:uppercase;
                         letter-spacing:0.1em; margin-bottom:0.5rem;">FORME · Séniorité</div>
                    <div style="line-height: 1.9; font-size: 0.82rem;">
                        <span style="color:{GOLD}; font-size: 1.1rem;">■</span>&nbsp;&nbsp;Senior Sécurisé<br>
                        <span style="color:{GOLD}; font-size: 1.1rem;">●</span>&nbsp;&nbsp;Senior Non-Sécurisé<br>
                        <span style="color:{GOLD}; font-size: 1.1rem;">◆</span>&nbsp;&nbsp;Tier 2<br>
                        <span style="color:{GOLD}; font-size: 1.1rem;">▲</span>&nbsp;&nbsp;AT1<br>
                        <span style="color:{GOLD}; font-size: 1.1rem;">⬟</span>&nbsp;&nbsp;Subordonné Assurance
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with leg_cols[1]:
            st.markdown(f"""
                <div style="background:{NAVY_2}; border:1px solid {GRID}; border-radius:4px; padding:0.8rem 1rem;">
                    <div style="color:{TEXT_MUTED}; font-size:0.7rem; text-transform:uppercase;
                         letter-spacing:0.1em; margin-bottom:0.5rem;">TAILLE · Liquidité</div>
                    <div style="line-height: 1.9; font-size: 0.82rem;">
                        <span style="color:{GOLD}; font-size: 0.6rem;">●</span>&nbsp;&nbsp;Petite = peu liquide<br>
                        <span style="color:{GOLD}; font-size: 1.0rem;">●</span>&nbsp;&nbsp;Moyenne<br>
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
                        partagée par toutes ses émissions.<br>
                        <div style="color:{TEXT_MUTED}; font-size:0.7rem; margin-top:0.4rem;">
                            Voir légende à droite du graphique
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)


# ============================================================
# COLOR MAP GLOBAL (consistant entre les onglets)
# ============================================================

all_issuers = sorted(df_full["Issuer Name"].unique())
color_map_full = {iss: ISSUER_PALETTE[i % len(ISSUER_PALETTE)] for i, iss in enumerate(all_issuers)}


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "◆  Vue d'Ensemble",
    "■  Senior Sécurisé",
    "●  Senior Non-Sécurisé",
    "◆  Tier 2",
    "▲  AT1",
    "⬟  Sub. Assurance",
    "★  Top Picks",
])


# ============================================================
# TAB 1: VUE D'ENSEMBLE
# ============================================================
with tab1:
    st.markdown("### Univers Complet · Risque vs Reward")
    render_bubble_chart(df_full, color_map_full, show_shape_legend=True)


# ============================================================
# TABS 2-6: UN PAR TYPE D'ÉMISSION
# ============================================================

def render_seniority_tab(tab, seniority_key, title_label):
    with tab:
        df_sub = df_full[df_full["Seniority"] == seniority_key]
        st.markdown(f"### {title_label} · {len(df_sub)} obligations")
        render_bubble_chart(df_sub, color_map_full, show_shape_legend=False)

render_seniority_tab(tab2, "Senior Secured", "Senior Sécurisé")
render_seniority_tab(tab3, "Senior Unsecured", "Senior Non-Sécurisé")
render_seniority_tab(tab4, "Tier 2", "Tier 2")
render_seniority_tab(tab5, "AT1", "Additional Tier 1")
render_seniority_tab(tab6, "Sub Insurance", "Subordonné Assurance")


# ============================================================
# TAB 7: TOP PICKS
# ============================================================
with tab7:
    st.markdown("### Meilleures Opportunités Relative Value")
    top_n = st.slider("Afficher le top N", 5, 30, 15, 5)

    cols_show = ["RV Rank", "Issuer Name", "Sector", "Seniority", "Bond Rating SP",
                 "Years to Maturity", "Z-Spread (bps)", "YTM (%)",
                 "Risk Score", "Reward Score", "Liquidity Score", "RV Score"]
    top_df = df_full.nlargest(top_n, "RV Score")[cols_show].reset_index(drop=True)
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


# ============================================================
# FOOTER MINIMAL
# ============================================================

st.markdown('<div class="footer">V1</div>', unsafe_allow_html=True)
