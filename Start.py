import streamlit as st
import st_pages
from components.popups import *
from components.styling import apply_styling
from auth import check_jwt

st.set_page_config(
    page_title="Doorstroomanalyse – Corderius College",
    page_icon="📊",
    layout="wide",
)

apply_styling()
user = check_jwt()

# ── Hero-banner ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="corderius-hero">
    <h1>📊 Doorstroomanalyse</h1>
    <p>
        Verken de doorstroomdata schooljaren 2017–2018 t/m 2024–2025.<br>
        Volg leerlingen van leerfase tot leerfase, vergelijk groepen en ontdek patronen
        in tekortpunten, basisschooladvies en schoolherkomst.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Inleiding ────────────────────────────────────────────────────────────────
st.markdown("""
De **tekortpunten** zijn opgeteld over alle vakken per leerling (eindrapport) en worden
gegroepeerd weergegeven: 0–3 · 4–6 · 7–9 · 10+.
Leerfase-overgangen zijn gebaseerd op de kolom *Leerfase (afk)* in Cumlaude;
doublures zijn herkenbaar aan de toevoeging `_doublure` (bijv. `h4_doublure`).

> **Startvraag:** Hoeveel leerlingen stromen op van H5 naar het VWO?
> Of: wat is het effect van kansrijk bevorderen?
""")

st.markdown("---")
st.markdown("### Kies een analyse")

# ── Rij 1 ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <a class="card-link" href="Analyse_gegroepeerd_naar_tekorten" target="_self">
        <div class="card">
            <h3>1️⃣ Aantallen en doorstroom</h3>
            <p>Onderzoek waar leerlingen naartoe gaan. Flexibel 1–6 jaar vooruit kijken,
            met optie om 1 jaar terug te tonen als context.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <a class="card-link" href="Analyse_flexibel_met_BSA" target="_self">
        <div class="card">
            <h3>2️⃣ Flexibele analyse met BSA</h3>
            <p>Transitiepaden 1–6 jaar vooruit, met uitsplitsing
            per basisschooladvies per transitiepad.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <a class="card-link" href="basisschool_advies" target="_self">
        <div class="card">
            <h3>3️⃣ Basisschooladvies</h3>
            <p>Welke basisschooladviezen hadden leerlingen?
            Filterbaar op school van herkomst.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

st.write("")

# ── Rij 2 ────────────────────────────────────────────────────────────────────
col4, col5, col6, col7 = st.columns(4)

with col4:
    st.markdown("""
    <a class="card-link" href="APCG_analyse" target="_self">
        <div class="card">
            <h3>4️⃣ APCG-analyse</h3>
            <p>Vergelijk leerlingen uit armoedegebieden met de rest.
            Kaart, trends, tekortpunten en doorstroom.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <a class="card-link" href="Analyse_gesplitst" target="_self">
        <div class="card">
            <h3>5️⃣ Doorstroom / afstroom gesplitst</h3>
            <p>Doorstroom uitgesplitst naar doorstroom,
            afstroom of doublure per jaar.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col6:
    st.markdown("""
    <a class="card-link" href="Eenjaars_overgangen" target="_self">
        <div class="card">
            <h3>6️⃣ Eenjaars overgangen</h3>
            <p>Eenvoudige weergave van doorstroom
            met één jaar vooruitkijken.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col7:
    st.markdown("""
    <a class="card-link" href="Details_voor_groepen" target="_self">
        <div class="card">
            <h3>7️⃣ Details voor groepen</h3>
            <p>Per groep de doorstroompaden uitsplitsen om
            de herkomst van data te controleren.</p>
        </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown("---")
st.button("ℹ️ Wat is nieuw in versie 2.0?", on_click=release_notes)

st.showSidebarNavigation = False
st_pages.hide_pages(["1_Analyse_per_leerfase", "3_Analyse_eenjaar_vooruit", "4_Analyse_gesplitst"])
