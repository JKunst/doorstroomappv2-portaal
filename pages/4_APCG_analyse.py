import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from components.doorstroom_functions import (
    analyze_next_leerfase,
    analyze_flexible_leerfase_transitions,
    counts_with_percentages,
)
from components.popups import check_password, filter_helper
from components.data import load_data
from components.styling import apply_styling

st.set_page_config(layout="wide", page_title="APCG Analyse", page_icon="🗺️")
apply_styling()
check_password()

# ── Extra CSS voor KPI-tegels ────────────────────────────────────────────────
st.markdown("""
<style>
.kpi-box {
    background: #E8F4F5;
    border-left: 5px solid #0D5259;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.kpi-box.orange { background: #FDF0EA; border-left-color: #E8612A; }
.kpi-label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
             letter-spacing: 0.6px; color: #4A5568; margin-bottom: 0.2rem; }
.kpi-value { font-size: 2rem; font-weight: 800; color: #0D5259; line-height: 1; }
.kpi-value.orange { color: #E8612A; }
.kpi-sub   { font-size: 0.82rem; color: #4A5568; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ── Data laden ───────────────────────────────────────────────────────────────

df = load_data()

apcg_df  = df[df["APCG"] == 1]
niet_df  = df[df["APCG"] == 0]

# ── APCG-postcodes Amersfoort (bron: CBS 2018) ───────────────────────────────
# Gebaseerd op de officiële CBS-lijst "Armoedeprobleemcumulatiegebieden 2018"
# (https://www.cbs.nl/nl-nl/maatwerk/2020/52/armoedeprobleem-cumulatie-gebieden-2018)
# Criteria: hoog aandeel lage inkomens + uitkeringen + niet-westerse achtergrond.

# ── Alle postcodes waar leerlingen vandaan komen ─────────────────────────────
# Bron: dataset. APCG=True = rode stip (CBS 2018 armoedegebied)
APCG_POSTCODES = {1051, 1106, 3764, 3765, 3813, 3814, 3815, 3816}

ALLE_POSTCODES = {
    # postcode: (naam, lat, lon)
    1051: ("Amsterdam West",              52.3720, 4.8590),
    1106: ("Amsterdam Zuidoost",          52.3190, 5.0000),
    3442: ("Woerden",                     52.0880, 4.8880),
    3741: ("Baarn",                       52.2090, 5.2860),
    3742: ("Baarn-Zuid",                  52.1990, 5.2910),
    3751: ("Bunschoten",                  52.2530, 5.3780),
    3752: ("Bunschoten-Oost",             52.2480, 5.3960),
    3762: ("Soest",                       52.1750, 5.3040),
    3763: ("Soest-Noord",                 52.1830, 5.3100),
    3764: ("Soest-Midden",                52.1770, 5.3200),
    3765: ("Soest",                       52.1700, 5.3280),
    3766: ("Soest-Oost",                  52.1650, 5.3340),
    3768: ("Soest-West",                  52.1820, 5.2960),
    3769: ("Soesterberg",                 52.1240, 5.2850),
    3771: ("Barneveld",                   52.1370, 5.5840),
    3781: ("Voorthuizen",                 52.1860, 5.6060),
    3784: ("Terschuur",                   52.1670, 5.5380),
    3791: ("Achterveld",                  52.1410, 5.4920),
    3792: ("Achterveld-Oost",             52.1340, 5.5020),
    3794: ("Stoutenburg-Noord",           52.1570, 5.4670),
    3811: ("Amersfoort Centrum",          52.1561, 5.3878),
    3812: ("Amersfoort Binnenstad-N",     52.1600, 5.3750),
    3813: ("Amersfoort Kruiskamp",        52.1740, 5.3720),
    3814: ("Amersfoort Randenbroek",      52.1540, 5.3980),
    3815: ("Amersfoort Hoogland-W",       52.1670, 5.4180),
    3816: ("Amersfoort Liendert",         52.1620, 5.4100),
    3817: ("Amersfoort Nieuwe Stad",      52.1820, 5.3960),
    3818: ("Amersfoort Vathorst",         52.1950, 5.3870),
    3819: ("Amersfoort Schuilenburg",     52.1680, 5.4030),
    3822: ("Amersfoort Leusderkwartier",  52.1450, 5.4010),
    3823: ("Amersfoort Berg",             52.1390, 5.3820),
    3824: ("Amersfoort De Hoef",          52.1470, 5.3630),
    3825: ("Amersfoort Oost",             52.1660, 5.4350),
    3826: ("Amersfoort Nieuwland",        52.1760, 5.4320),
    3828: ("Amersfoort Vinkenhoef",       52.1870, 5.4280),
    3829: ("Amersfoort Schothorst",       52.1710, 5.3530),
    3831: ("Leusden",                     52.1300, 5.4260),
    3832: ("Leusden-Zuid",                52.1220, 5.4380),
    3833: ("Leusden-West",                52.1160, 5.4150),
    3834: ("Leusden-Centrum",             52.1240, 5.4060),
    3835: ("Leusden Tabaksteeg",          52.1180, 5.4520),
    3836: ("Leusden De Boom",             52.1120, 5.4600),
    3861: ("Nijkerk",                     52.2190, 5.4870),
    3862: ("Nijkerk-Oost",                52.2140, 5.5020),
    3863: ("Nijkerk-Noord",               52.2310, 5.4920),
    3864: ("Hoevelaken",                  52.1990, 5.4510),
    3871: ("Hoevelaken-Noord",            52.2070, 5.4380),
    3925: ("Amersfoort Hoogland",         52.1960, 5.4130),
    3931: ("Woudenberg",                  52.0820, 5.4140),
    3941: ("Doorn",                       52.0330, 5.3500),
    3953: ("Maarsbergen",                 52.0470, 5.3870),
    3981: ("Bunnik",                      52.0660, 5.2070),
    3991: ("Houten",                      52.0230, 5.1670),
    8077: ("Hulshorst / Nunspeet-O",      52.3280, 5.8230),
}

pc_df = pd.DataFrame.from_dict(
    ALLE_POSTCODES, orient="index",
    columns=["Wijk", "lat", "lon"]
).reset_index().rename(columns={"index": "Postcode"})
pc_df["APCG"] = pc_df["Postcode"].isin(APCG_POSTCODES)

# Kaart: sluit Amsterdam en Hulshorst uit (te ver weg voor regionale weergave)
BUITEN_KAART = {1051, 1106, 8077}
pc_map = pc_df[~pc_df["Postcode"].isin(BUITEN_KAART)].copy()
pc_apcg = pc_map[pc_map["APCG"]]
pc_niet  = pc_map[~pc_map["APCG"]]

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="corderius-hero">
    <h1>🗺️ APCG-analyse</h1>
    <p>
        Armoedeprobleemcumulatiegebied (<span class="accent">APCG</span>) — leerlingen
        uit postcodes met een hoog aandeel lage inkomens, uitkeringen en niet-westerse
        achtergrond. Bron: CBS 2018.<br>
        Op deze pagina vergelijken we APCG- en niet-APCG-leerlingen op tekortpunten,
        basisschooladvies, doorstroom en trends over de tijd.
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTIE 1 — KAART + KPI's naast elkaar
# ══════════════════════════════════════════════════════════════════════════════
map_col, kpi_col = st.columns([3, 2], gap="large")

with map_col:
    st.markdown("#### 📍 Herkomst leerlingen — postcodes")
    st.caption("🔴 Rood = APCG-postcode (CBS 2018) · 🔵 Blauwgroen = overige herkomstpostcodes")

    fig_map = go.Figure()

    # Laag 1: niet-APCG postcodes — kleine teal stippen met label
    fig_map.add_trace(go.Scattermapbox(
        lat=pc_niet["lat"].tolist(),
        lon=pc_niet["lon"].tolist(),
        mode="markers+text",
        marker=dict(size=11, color="#0D5259", opacity=0.75),
        text=pc_niet["Postcode"].astype(str).tolist(),
        textposition="top center",
        textfont=dict(size=8, color="#0D5259"),
        customdata=pc_niet[["Postcode", "Wijk"]].values,
        hovertemplate="<b>%{customdata[0]}</b> – %{customdata[1]}<extra></extra>",
        showlegend=True,
        name="Overige herkomst",
    ))

    # Laag 2: APCG postcodes — grotere rode stippen met label
    fig_map.add_trace(go.Scattermapbox(
        lat=pc_apcg["lat"].tolist(),
        lon=pc_apcg["lon"].tolist(),
        mode="markers+text",
        marker=dict(size=17, color="#D62728", opacity=0.92),
        text=pc_apcg["Postcode"].astype(str).tolist(),
        textposition="top center",
        textfont=dict(size=9, color="#D62728"),
        customdata=pc_apcg[["Postcode", "Wijk"]].values,
        hovertemplate="<b>%{customdata[0]}</b> – %{customdata[1]}<extra>APCG</extra>",
        showlegend=True,
        name="APCG-gebied (CBS 2018)",
    ))

    fig_map.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=52.155, lon=5.400),
            zoom=9.8,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=450,
        legend=dict(
            orientation="h", yanchor="bottom", y=0.01,
            xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#0D5259", borderwidth=1,
        ),
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption(
        "Postcodes 1051 (Amsterdam West), 1106 (Amsterdam Zuidoost) en 8077 (Hulshorst) "
        "liggen buiten het kaartbereik en zijn niet weergegeven."
    )

with kpi_col:
    st.markdown("#### 📊 Kerngetallen vergelijking")

    most_recent = df["Schooljaar"].max()
    df_recent   = df[df["Schooljaar"] == most_recent]
    n_apcg_rec  = df_recent[df_recent["APCG"] == 1]["Leerlingnummer"].nunique()
    n_niet_rec  = df_recent[df_recent["APCG"] == 0]["Leerlingnummer"].nunique()
    pct_apcg_rec = round(n_apcg_rec / max(n_apcg_rec + n_niet_rec, 1) * 100, 1)

    gem_tk_apcg = round(apcg_df["Tekortpunten"].mean(), 2)
    gem_tk_niet = round(niet_df["Tekortpunten"].mean(), 2)

    einde_a = apcg_df[apcg_df["Leerfase (afk)"].isin(["Geslaagd","MBO","VO verlater"])]
    einde_n = niet_df[niet_df["Leerfase (afk)"].isin(["Geslaagd","MBO","VO verlater"])]
    dip_a = round(len(einde_a[einde_a["Leerfase (afk)"]=="Geslaagd"]) / max(len(einde_a),1) * 100, 1)
    dip_n = round(len(einde_n[einde_n["Leerfase (afk)"]=="Geslaagd"]) / max(len(einde_n),1) * 100, 1)

    first_year = df["Schooljaar"].min()
    pct_recent = round(df[df["Schooljaar"]==most_recent]["APCG"].mean() * 100, 1)
    pct_first  = round(df[df["Schooljaar"]==first_year]["APCG"].mean() * 100, 1)

    def kpi(label, value, sub, orange=False):
        cls = "orange" if orange else ""
        return f"""
        <div class="kpi-box {cls}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value {cls}">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>"""

    r1a, r1b = st.columns(2)
    with r1a:
        st.markdown(kpi("APCG-leerlingen", f"{n_apcg_rec}",
                        f"{pct_apcg_rec}% · schooljaar {most_recent}", orange=True),
                    unsafe_allow_html=True)
    with r1b:
        st.markdown(kpi("Niet-APCG", f"{n_niet_rec}",
                        f"{100-pct_apcg_rec}% · schooljaar {most_recent}"),
                    unsafe_allow_html=True)

    st.write("")
    r2a, r2b = st.columns(2)
    with r2a:
        st.markdown(kpi("Gem. tekortpunten", gem_tk_apcg, "APCG (alle jaren)", orange=True), unsafe_allow_html=True)
    with r2b:
        st.markdown(kpi("Gem. tekortpunten", gem_tk_niet, "Niet-APCG (alle jaren)"), unsafe_allow_html=True)

    st.write("")
    r3a, r3b = st.columns(2)
    with r3a:
        st.markdown(kpi("Diploma %", f"{dip_a}%", "APCG-leerlingen", orange=True), unsafe_allow_html=True)
    with r3b:
        st.markdown(kpi("Diploma %", f"{dip_n}%", "Niet-APCG"), unsafe_allow_html=True)

    st.write("")
    r4a, r4b = st.columns(2)
    with r4a:
        st.markdown(kpi("APCG-aandeel", f"{pct_first}%", f"schooljaar {first_year}"), unsafe_allow_html=True)
    with r4b:
        st.markdown(kpi("APCG-aandeel", f"{pct_recent}%", f"schooljaar {most_recent}", orange=True), unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTIE 2 — TREND + TEKORTPUNTEN PER LEERFASE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📈 Trends en tekortpunten")
tc1, tc2 = st.columns(2)

with tc1:
    st.markdown("##### APCG-aandeel per schooljaar")
    trend = df.groupby("Schooljaar")["APCG"].mean().reset_index()
    trend["Percentage"] = (trend["APCG"] * 100).round(1)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend["Schooljaar"], y=trend["Percentage"],
        mode="lines+markers",
        line=dict(color="#E8612A", width=3),
        marker=dict(size=8, color="#E8612A"),
        fill="tozeroy", fillcolor="rgba(232,97,42,0.1)",
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        name="APCG %",
    ))
    fig_trend.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=30),
        yaxis=dict(title="% APCG", ticksuffix="%", range=[0, 30]),
        xaxis=dict(title="Schooljaar", dtick=1),
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
    )
    st.plotly_chart(fig_trend, width="stretch")
    st.caption("Het aandeel APCG-leerlingen groeit gestaag: van ~15% naar ~20%.")

with tc2:
    st.markdown("##### Gemiddelde tekortpunten per leerfase")
    leerfases_select = ["h3","h4","h5","v4","v5","v6"]
    tk_a = apcg_df[apcg_df["Leerfase (afk)"].isin(leerfases_select)].groupby("Leerfase (afk)")["Tekortpunten"].mean().reindex(leerfases_select)
    tk_n = niet_df[niet_df["Leerfase (afk)"].isin(leerfases_select)].groupby("Leerfase (afk)")["Tekortpunten"].mean().reindex(leerfases_select)

    fig_tk = go.Figure()
    fig_tk.add_trace(go.Bar(
        x=leerfases_select, y=tk_a.values,
        name="APCG", marker_color="#E8612A",
        hovertemplate="%{x}: %{y:.2f}<extra>APCG</extra>",
    ))
    fig_tk.add_trace(go.Bar(
        x=leerfases_select, y=tk_n.values,
        name="Niet-APCG", marker_color="#0D5259",
        hovertemplate="%{x}: %{y:.2f}<extra>Niet-APCG</extra>",
    ))
    fig_tk.update_layout(
        barmode="group", height=280,
        margin=dict(l=10, r=10, t=10, b=30),
        yaxis=dict(title="Gem. tekortpunten"),
        xaxis=dict(title="Leerfase"),
        legend=dict(orientation="h", yanchor="bottom", y=1),
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
    )
    st.plotly_chart(fig_tk, width="stretch")
    st.caption("APCG-leerlingen in h4/h5 hebben duidelijk hogere tekortpunten dan niet-APCG.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTIE 3 — BSA-VERDELING + EINDUITSTROOM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🎓 Basisschooladvies en einduitstroom")
bc1, bc2 = st.columns(2)

with bc1:
    st.markdown("##### BSA-verdeling APCG vs niet-APCG")
    uniek = df.drop_duplicates("Leerlingnummer")
    bsa_a = uniek[uniek["APCG"]==1]["Basisschooladvies"].value_counts(normalize=True) * 100
    bsa_n = uniek[uniek["APCG"]==0]["Basisschooladvies"].value_counts(normalize=True) * 100
    bsa_cats = bsa_n.index.tolist()

    fig_bsa = go.Figure()
    fig_bsa.add_trace(go.Bar(
        x=bsa_cats, y=[bsa_a.get(c, 0) for c in bsa_cats],
        name="APCG", marker_color="#E8612A",
        hovertemplate="%{x}: %{y:.1f}%<extra>APCG</extra>",
    ))
    fig_bsa.add_trace(go.Bar(
        x=bsa_cats, y=[bsa_n.get(c, 0) for c in bsa_cats],
        name="Niet-APCG", marker_color="#0D5259",
        hovertemplate="%{x}: %{y:.1f}%<extra>Niet-APCG</extra>",
    ))
    fig_bsa.update_layout(
        barmode="group", height=300,
        margin=dict(l=10, r=10, t=10, b=80),
        yaxis=dict(title="% leerlingen", ticksuffix="%"),
        xaxis=dict(tickangle=-30),
        legend=dict(orientation="h", yanchor="bottom", y=1),
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
    )
    st.plotly_chart(fig_bsa, width="stretch")
    st.caption("APCG-leerlingen hebben minder VWO-adviezen en vaker VMBO-adviezen.")

with bc2:
    st.markdown("##### Einduitstroom (Geslaagd / MBO / VO verlater)")
    uitstroom_cats = ["Geslaagd", "MBO", "VO verlater"]
    einde_a = apcg_df[apcg_df["Leerfase (afk)"].isin(uitstroom_cats)]
    einde_n = niet_df[niet_df["Leerfase (afk)"].isin(uitstroom_cats)]
    pct_a = (einde_a["Leerfase (afk)"].value_counts(normalize=True) * 100).reindex(uitstroom_cats, fill_value=0)
    pct_n = (einde_n["Leerfase (afk)"].value_counts(normalize=True) * 100).reindex(uitstroom_cats, fill_value=0)

    fig_uit = go.Figure()
    fig_uit.add_trace(go.Bar(
        x=uitstroom_cats, y=pct_a.values,
        name="APCG", marker_color="#E8612A",
        hovertemplate="%{x}: %{y:.1f}%<extra>APCG</extra>",
        text=pct_a.round(1).astype(str) + "%", textposition="outside",
    ))
    fig_uit.add_trace(go.Bar(
        x=uitstroom_cats, y=pct_n.values,
        name="Niet-APCG", marker_color="#0D5259",
        hovertemplate="%{x}: %{y:.1f}%<extra>Niet-APCG</extra>",
        text=pct_n.round(1).astype(str) + "%", textposition="outside",
    ))
    fig_uit.update_layout(
        barmode="group", height=300,
        margin=dict(l=10, r=10, t=30, b=30),
        yaxis=dict(title="% van einduitstroom", ticksuffix="%", range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1),
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
    )
    st.plotly_chart(fig_uit, width="stretch")
    st.caption("APCG-leerlingen slagen iets minder vaak en verlaten vaker het VO zonder diploma.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTIE 4 — TRANSITIEANALYSE (interactief)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🔍 Interactieve transitieanalyse: APCG vs niet-APCG")
st.caption(
    "Vergelijk de doorstroompatronen van APCG- en niet-APCG-leerlingen voor een "
    "specifieke leerfase en periode."
)

all_schoolyears = sorted(df["Schooljaar"].unique().tolist())
all_leerfases   = sorted(df["Leerfase (afk)"].dropna().unique().tolist())[17:]
all_buckets     = sorted(df["Tekortpunten_Bucket"].dropna().unique().tolist())

ia1, ia2, ia3 = st.columns(3)
with ia1:
    sj_start = st.selectbox("Startjaar:", all_schoolyears, index=5, key="apcg_sj_s")
    sj_eind  = st.selectbox("t/m jaar:", all_schoolyears, index=5, key="apcg_sj_e")
with ia2:
    leerfase = st.selectbox("Leerfase:", all_leerfases, index=4, key="apcg_lf")
    jaren    = st.slider("Jaren vooruit:", 1, 6, 3, key="apcg_jaren")
with ia3:
    buckets  = st.multiselect("Tekortpunten-filter:", all_buckets, default=all_buckets, key="apcg_bk")
    terug    = st.toggle("Toon 1 jaar terug", False, key="apcg_terug")

if sj_start > sj_eind:
    st.error("Startjaar mag niet na eindjaar liggen.")
    st.stop()

with st.spinner("Berekenen..."):
    tr_apcg = analyze_flexible_leerfase_transitions(
        apcg_df, sj_start, sj_eind, leerfase,
        n_years_forward=jaren, include_year_back=terug,
        tekortpunten_bucket_filter=buckets,
    )
    tr_niet = analyze_flexible_leerfase_transitions(
        niet_df, sj_start, sj_eind, leerfase,
        n_years_forward=jaren, include_year_back=terug,
        tekortpunten_bucket_filter=buckets,
    )

ta1, ta2 = st.columns(2)
with ta1:
    st.markdown("**APCG-leerlingen**")
    if not tr_apcg.empty:
        df_a = counts_with_percentages(tr_apcg)
        st.dataframe(df_a, width="stretch")
    else:
        st.info("Geen data voor deze selectie.")

with ta2:
    st.markdown("**Niet-APCG-leerlingen**")
    if not tr_niet.empty:
        df_n = counts_with_percentages(tr_niet)
        st.dataframe(df_n, width="stretch")
    else:
        st.info("Geen data voor deze selectie.")

# Suggesties
with st.expander("💡 Analysesugesties — wat kun je hier onderzoeken?"):
    st.markdown("""
    **1. Kansrijk bevorderen werkt het voor APCG-leerlingen anders?**
    Stel leerfase h4/h5 in voor de jaren 2020–2023 en vergelijk hoe APCG- en
    niet-APCG-leerlingen doorstromen naar h5/Geslaagd of afstromen naar MBO.

    **2. VWO-doorstroom bij gelijke start**
    Stel v4 of v5 in en vergelijk de paden. Zijn de doorstroompercentages
    vergelijkbaar, of vallen APCG-leerlingen vaker af?

    **3. Vroege jaren vs recente jaren**
    Vergelijk 2017–2019 met 2022–2024 voor dezelfde leerfase.
    Verbetert de positie van APCG-leerlingen over de tijd?

    **4. Hoge tekortpunten-groep**
    Filter op buckets 7–9 en 10+. Is het aandeel APCG in deze groep hoger?
    Wat zijn hun doorstroompatronen?
    """)

st.divider()

# ── Navigatie ────────────────────────────────────────────────────────────────
st.markdown("#### Ben je klaar met deze pagina, je kan altijd verder kijken op de andere pagina's.")
nc1, nc2, nc3 = st.columns(3)

with nc1:
    st.markdown("""
    <a class="card-link" href="Analyse_gegroepeerd_naar_tekorten" target="_self">
        <div class="card"><h3>1️⃣ Aantallen en doorstroom</h3>
        <p>Doorstroom per leerfase flexibel vooruit en terug.</p></div>
    </a>""", unsafe_allow_html=True)

with nc2:
    st.markdown("""
    <a class="card-link" href="basisschool_advies" target="_self">
        <div class="card"><h3>3️⃣ Basisschooladvies</h3>
        <p>Transitiepaden uitgesplitst per basisschooladvies.</p></div>
    </a>""", unsafe_allow_html=True)

with nc3:
    st.markdown("""
    <a class="card-link" href="Details_voor_groepen" target="_self">
        <div class="card"><h3>6️⃣ Details voor groepen</h3>
        <p>Leerlingnummers per groep voor data-controle.</p></div>
    </a>""", unsafe_allow_html=True)

st.write("")
st.markdown("""
<a class="card-link" href="/" target="_self">
    <div class="card"><h3>Terug naar start</h3></div>
</a>""", unsafe_allow_html=True)
st.showSidebarNavigation = False
