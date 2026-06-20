import streamlit as st

st.set_page_config(layout="wide", page_title="Cohortanalyse per startjaar", page_icon="🧭")

import pandas as pd
import plotly.graph_objects as go
from auth import check_jwt
from components.data import load_data
from components.styling import apply_styling

apply_styling()
check_jwt()

st.title("🧭 Cohortanalyse per startjaar")
st.markdown(
    "Volg een **instroomcohort** — alle leerlingen die zich in een bepaald jaar op "
    "school inschreven — naar hun uiteindelijke uitkomst. Zo zie je per startjaar "
    "welk deel uiteindelijk slaagde, afstroomde, werd afgewezen of vertrok. "
    "Filterbaar op instroomniveau (op basis van het basisschooladvies)."
)

df = load_data()
df = df.sort_values(["Leerlingnummer", "Schooljaar"])

MIN_COHORT = 50

RES_KLEUR = {
    "Geslaagd": "#0D5259",
    "Afgewezen/VAVO": "#B04A3F",
    "Afgestroomd": "#C98A2B",
    "VO verlater": "#8A6D9C",
    "Elders/onbekend": "#9AA3A2",
    "Nog onderweg/onbekend": "#D9D4C7",
}
RES_VOLGORDE = list(RES_KLEUR.keys())


def instroomniveau(advies):
    if pd.isna(advies):
        return "Onbekend"
    a = str(advies)
    if a.startswith("VWO"):
        return "Vwo"
    if a.startswith("HAVO / VWO"):
        return "Havo/vwo"
    if a.startswith("HAVO"):
        return "Havo"
    if "VMBO (g)t / HAVO" in a:
        return "Mavo/havo"
    if a.startswith("VMBO (g)t") or a.startswith("VMBO k / (g)t"):
        return "Mavo"
    if a.startswith("VMBO k") or a.startswith("VMBO b"):
        return "Kader/basis"
    return "Overig"


def eindresultaat(d):
    if d in ("Geslaagd", "Geslaagd (prognose)"):
        return "Geslaagd"
    if d in ("Afgewezen", "Afgewezen (prognose)"):
        return "Afgewezen/VAVO"
    if d == "Afstroom":
        return "Afgestroomd"
    if d == "VO verlater":
        return "VO verlater"
    if d == "Opleiding elders/onbekend":
        return "Elders/onbekend"
    return "Nog onderweg/onbekend"


@st.cache_data(show_spinner="Cohorten samenstellen…")
def cohort_tabel(df: pd.DataFrame) -> pd.DataFrame:
    insch_jaar = pd.to_datetime(df["Inschrijvingsdatum"]).dt.year
    werk = df.assign(_insch=insch_jaar)
    grp = werk.groupby("Leerlingnummer")
    out = pd.DataFrame({
        "startjaar": grp["_insch"].first(),
        "advies": grp["Basisschooladvies"].first(),
        "laatste": grp["Doorstroom"].last(),
    }).reset_index(drop=True)
    out["niveau"] = out["advies"].apply(instroomniveau)
    out["resultaat"] = out["laatste"].apply(eindresultaat)
    return out


basis = cohort_tabel(df)

niveaus_aanwezig = [n for n in
                    ["Vwo", "Havo/vwo", "Havo", "Mavo/havo", "Mavo", "Kader/basis"]
                    if n in set(basis["niveau"])]
keuze_niveau = st.multiselect(
    "Instroomniveau (leeg = alle niveaus samen)",
    options=niveaus_aanwezig,
    default=[],
)

data = basis if not keuze_niveau else basis[basis["niveau"].isin(keuze_niveau)]

cohort_grootte = data["startjaar"].value_counts()
geldige_jaren = sorted(j for j, n in cohort_grootte.items() if n >= MIN_COHORT)
if not geldige_jaren:
    st.info(f"Geen cohorten met minimaal {MIN_COHORT} leerlingen voor deze selectie.")
    st.stop()

data = data[data["startjaar"].isin(geldige_jaren)]

cnt = pd.crosstab(data["startjaar"], data["resultaat"])
for c in RES_VOLGORDE:
    if c not in cnt.columns:
        cnt[c] = 0
cnt = cnt[RES_VOLGORDE]
tot = cnt.sum(axis=1)
perc = cnt.div(tot, axis=0) * 100
jaren = [int(x) for x in cnt.index]

titel_suffix = "alle niveaus" if not keuze_niveau else ", ".join(keuze_niveau)

fig = go.Figure()
for c in RES_VOLGORDE:
    fig.add_trace(go.Bar(
        x=jaren, y=perc[c], name=c, marker_color=RES_KLEUR[c],
        customdata=cnt[c],
        hovertemplate=f"{c}<br>%{{x}}: %{{y:.1f}}%% (%{{customdata}})<extra></extra>",
    ))
fig.update_layout(
    barmode="stack",
    title=f"Eindresultaat per instroomcohort — {titel_suffix}",
    height=480, plot_bgcolor="white", paper_bgcolor="white",
    yaxis=dict(title="Aandeel van cohort", ticksuffix="%", range=[0, 100]),
    xaxis=dict(title="Inschrijvingsjaar", dtick=1),
    font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(t=60, b=40, l=50, r=20),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    f"Elke balk is één instroomcohort (\u2265 {MIN_COHORT} leerlingen) en telt op tot 100%. "
    "Recente cohorten staan nog deels op 'Nog onderweg' omdat hun examen nog moet komen."
)

st.subheader("Geslaagd versus afgestroomd")
st.markdown(
    "Het percentage van elk instroomcohort dat uiteindelijk **slaagde** en het "
    "percentage dat als eindstatus **afstroomde**."
)
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=jaren, y=perc["Geslaagd"], name="Geslaagd", mode="lines+markers",
    line=dict(color=RES_KLEUR["Geslaagd"], width=3),
))
fig2.add_trace(go.Scatter(
    x=jaren, y=perc["Afgestroomd"], name="Afgestroomd", mode="lines+markers",
    line=dict(color=RES_KLEUR["Afgestroomd"], width=3),
))
fig2.update_layout(
    height=380, plot_bgcolor="white", paper_bgcolor="white",
    yaxis=dict(title="% van cohort", ticksuffix="%"),
    xaxis=dict(title="Inschrijvingsjaar", dtick=1),
    font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    margin=dict(t=20, b=40, l=50, r=20),
)
st.plotly_chart(fig2, width="stretch")

with st.expander("Toon tabel met percentages"):
    toon = perc.copy()
    toon.index.name = "Inschrijvingsjaar"
    st.dataframe(toon.style.format("{:.1f}%"), width="stretch")
    st.caption(f"Cohortgrootte: {dict(zip(jaren, [int(x) for x in tot]))}")
