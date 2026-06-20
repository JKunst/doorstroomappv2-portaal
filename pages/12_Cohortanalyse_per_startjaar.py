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
    "Volg een **startcohort** naar de uiteindelijke uitkomst. Het startjaar is het "
    "jaar waarin de leerling in **leerjaar 1** zat (teruggerekend uit leerfase en "
    "schooljaar), zodat zij-instromers in een hoger leerjaar in het juiste cohort "
    "vallen. Filterbaar op instroomniveau (basisschooladvies)."
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


def _is_echte_fase(f):
    """True voor een echte leerfase (t1, h4, v6, ...) en niet een advies-string."""
    return isinstance(f, str) and len(f) >= 2 and f[0] in "thv" and f[-1].isdigit()


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
    """
    Eén rij per leerling met:
    - startjaar: het leerjaar-1-equivalent (schooljaar van eerste echte leerfase
      minus (leerjaar - 1)), zodat zij-instromers correct worden ingedeeld
    - niveau: instroomniveau uit het basisschooladvies
    - resultaat: de uiteindelijke uitkomst (laatste doorstroomstatus)
    """
    fk = df["Leerfase (afk)"].astype(str).str.replace("_doublure", "", regex=False)
    echt = df[fk.map(_is_echte_fase)].copy()
    echt["_fk"] = fk[fk.map(_is_echte_fase)]

    eerste = echt.groupby("Leerlingnummer").agg(
        schooljaar=("Schooljaar", "first"), fase=("_fk", "first")
    )
    eerste["startlj"] = eerste["fase"].str[-1].astype(int)
    eerste["startjaar"] = eerste["schooljaar"] - (eerste["startlj"] - 1)

    advies = df.groupby("Leerlingnummer")["Basisschooladvies"].first()
    laatste = df.groupby("Leerlingnummer")["Doorstroom"].last()

    out = eerste[["startjaar"]].join(advies).join(laatste)
    out["niveau"] = out["Basisschooladvies"].apply(instroomniveau)
    out["resultaat"] = out["Doorstroom"].apply(eindresultaat)
    return out.reset_index(drop=True)


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
    title=f"Eindresultaat per startcohort — {titel_suffix}",
    height=520, plot_bgcolor="white", paper_bgcolor="white",
    yaxis=dict(title="Aandeel van cohort", ticksuffix="%", range=[0, 100]),
    xaxis=dict(title="Startjaar (leerjaar 1)", dtick=1),
    font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
    margin=dict(t=60, b=40, l=50, r=20),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    f"Elke balk is één startcohort (\u2265 {MIN_COHORT} leerlingen) en telt op tot 100%. "
    "Recente cohorten staan nog grotendeels op 'Nog onderweg' omdat hun examen nog moet komen."
)

with st.expander("Toon tabel met percentages"):
    toon = perc.copy()
    toon.index.name = "Startjaar"
    st.dataframe(toon.style.format("{:.1f}%"), width="stretch")
    st.caption(f"Cohortgrootte: {dict(zip(jaren, [int(x) for x in tot]))}")
