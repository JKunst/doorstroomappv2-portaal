"""
styling.py – Gedeelde huisstijl voor de Doorstroomanalyse app.
Gebaseerd op de visuele identiteit van het Corderius College Amersfoort.

Gebruik op elke pagina:
    from components.styling import apply_styling
    apply_styling()
"""
import streamlit as st

# --- Kleurenpalet Corderius ---
TEAL       = "#0D5259"   # Primaire donkerteal (header, knoppen, accenten)
TEAL_LIGHT = "#E8F4F5"   # Zeer lichte teal voor achtergronden
ORANGE     = "#E8612A"   # Warm oranje accent
ORANGE_LIGHT = "#FDF0EA" # Licht oranje voor hover/achtergrond
WHITE      = "#FFFFFF"
GRAY_BG    = "#F4F6F7"   # Secondaire achtergrond
TEXT_DARK  = "#1A1A2E"   # Donkere tekst
TEXT_MID   = "#4A5568"   # Middelgrijze tekst

CSS = f"""
<style>
/* ── Globaal ── */
[data-testid="stAppViewContainer"] {{
    background-color: {WHITE};
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

[data-testid="stSidebar"] {{
    background-color: {TEAL};
}}

[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
}}

/* ── Topbalk ── */
[data-testid="stHeader"] {{
    background-color: {TEAL};
}}

/* ── Kopteksten ── */
h1, h2 {{
    color: {TEAL};
    font-weight: 700;
    letter-spacing: -0.3px;
}}

h3, h4 {{
    color: {TEAL};
    font-weight: 600;
}}

/* ── Subheader (st.subheader) ── */
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {{
    color: {TEAL};
    font-weight: 700;
    border-bottom: 3px solid {ORANGE};
    padding-bottom: 0.3rem;
    margin-bottom: 1rem;
}}

/* ── Primaire knop ── */
.stButton > button {{
    background-color: {TEAL};
    color: {WHITE};
    border: none;
    border-radius: 8px;
    padding: 0.45rem 1.1rem;
    font-weight: 600;
    transition: background 0.2s ease, transform 0.1s ease;
}}

.stButton > button:hover {{
    background-color: {ORANGE};
    transform: translateY(-1px);
}}

/* ── Divider ── */
hr {{
    border: none;
    border-top: 2px solid {TEAL_LIGHT};
    margin: 1.2rem 0;
}}

/* ── Slider ── */
[data-testid="stSlider"] [role="slider"] {{
    background-color: {TEAL} !important;
}}

[data-testid="stSlider"] > div > div > div > div {{
    background: {TEAL} !important;
}}

/* ── Toggle ── */
[data-testid="stToggleSwitch"][aria-checked="true"] > div {{
    background-color: {TEAL} !important;
}}

/* ── Multiselect tags ── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background-color: {TEAL} !important;
    color: {WHITE} !important;
    border-radius: 6px;
}}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {{
    border-color: {TEAL_LIGHT};
    border-radius: 8px;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid {TEAL_LIGHT};
}}

/* ── Info / warning / error ── */
[data-testid="stAlert"] {{
    border-radius: 8px;
}}

/* ── Kaartjes (card grid) ── */
.card-link {{
    text-decoration: none;
}}

.card {{
    padding: 1.4rem 1.6rem;
    border-radius: 14px;
    height: 100%;
    background: {WHITE};
    box-shadow: 0 2px 10px rgba(13,82,89,0.08);
    transition: all 0.22s ease;
    border: 1px solid {TEAL_LIGHT};
    border-top: 4px solid {TEAL};
}}

.card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(13,82,89,0.15);
    border-top-color: {ORANGE};
}}

.card h3 {{
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.05rem;
    font-weight: 700;
    color: {TEAL} !important;
    border-bottom: none !important;
    padding-bottom: 0 !important;
}}

.card p {{
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.45;
    color: {TEXT_MID};
}}

/* ── Hero-banner op startpagina ── */
.corderius-hero {{
    background: linear-gradient(135deg, {TEAL} 0%, #1A7A85 100%);
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.8rem;
    color: {WHITE};
}}

.corderius-hero h1 {{
    color: {WHITE} !important;
    font-size: 1.9rem;
    margin-bottom: 0.4rem;
}}

.corderius-hero p {{
    color: rgba(255,255,255,0.88);
    font-size: 1rem;
    margin: 0;
    line-height: 1.6;
}}

.corderius-hero .accent {{
    color: {ORANGE};
    font-weight: 700;
}}

/* ── Sectielabel (boven de tijdsinstellingen etc.) ── */
.section-label {{
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {TEXT_MID};
    margin-bottom: 0.6rem;
}}

/* ── Footer-kaartje "Terug naar start" ── */
.card.back {{
    border-top-color: {GRAY_BG};
    background: {GRAY_BG};
}}

.card.back h3 {{
    color: {TEXT_MID} !important;
}}
</style>
"""


def apply_styling():
    """Injecteer de Corderius-huisstijl CSS op de huidige pagina."""
    st.markdown(CSS, unsafe_allow_html=True)
