import streamlit as st

st.set_page_config(layout="wide", page_title="Cohortanalyse per startjaar", page_icon="🧭")

import pandas as pd
import plotly.graph_objects as go
from auth import check_jwt
from components.data import load_data
from components.styling import apply_styling
from components.dashboard_helpers import kale_fase, KLEUREN, geldige_jaargrens

apply_styling()
check_jwt()

st.title("🧭 Cohortanalyse per startjaar")
st.markdown(
    "Volg een startcohort — alle leerlingen die in een bepaald schooljaar in een "
    "voorexamen- of examenfase zaten — naar hun **uiteindelijke uitkomst**. "
    "Zo zie je per cohort welk deel uiteindelijk is geslaagd, afgestroomd, "
    "afgewezen of vertrokken."
)

df = load_data()
df = df.sort_values(["Leerlingnummer", "Schooljaar"])
df["fk"] = kale_fase(df["Leerfase (afk)"])

RES_KLEUR = {
    "Geslaagd": "#0D5259",
    "Afgewezen/VAVO": "#B04A3F",
    "Afgestroomd": "#C98A2B",
    "VO verlater": "#8A6D9C",
    "Elders/onbekend": "#9AA3A2",
    "Nog onderweg/onbekend": "#D9D4C7",
}
RES_VOLGORDE = list(RES_KLEUR.keys())


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


@st.cache_data(show_spinner="Cohort volgen…")
def cohort_resultaten(startfase: str) -> pd.DataFrame:
    """Voor elke leerling in startfase: het eindresultaat (laatste status vanaf cohortjaar)."""
    sel = df[df["fk"] == startfase][["Leerlingnummer", "Schooljaar"]].drop_duplicates()
    lo, hi = geldige_jaargrens(df)
    if lo is not None:
        sel = sel[(sel["Schooljaar"] >= lo) & (sel["Schooljaar"] <= hi)]
    # laatste record per leerling (over de hele historie) — eindstatus
    laatste = df.groupby("Leerlingnummer").last()["Doorstroom"]
    rows = []
    for ln, sj in zip(sel["Leerlingnummer"], sel["Schooljaar"]):
        rows.append({"startjaar": int(sj), "resultaat": eindresultaat(laatste.get(ln))})
    return pd.DataFrame(rows)


STARTFASEN = {
    "Havo voorexamen (h4)": "h4",
    "Vwo voorexamen (v4)": "v4",
    "Mavo voorexamen (t3)": "t3",
    "Havo examen (h5)": "h5",
    "Vwo examen (v6)": "v6",
    "Mavo examen (t4)": "t4",
}

keuze = st.selectbox("Kies een startcohort", list(STARTFASEN.keys()))
fase = STARTFASEN[keuze]

data = cohort_resultaten(fase)
if data.empty:
    st.info("Geen data voor dit cohort.")
    st.stop()

cnt = pd.crosstab(data["startjaar"], data["resultaat"])
for c in RES_VOLGORDE:
    if c not in cnt.columns:
        cnt[c] = 0
cnt = cnt[RES_VOLGORDE]
tot = cnt.sum(axis=1)
perc = cnt.div(tot, axis=0) * 100
jaren = [int(x) for x in cnt.index]

# ── Gestapelde staafgrafiek (100% per cohort) ────────────────────────────────
fig = go.Figure()
for c in RES_VOLGORDE:
    fig.add_trace(go.Bar(
        x=jaren, y=perc[c], name=c, marker_color=RES_KLEUR[c],
        customdata=cnt[c],
        hovertemplate=f"{c}<br>%{{x}}: %{{y:.1f}}%% (%{{customdata}})<extra></extra>",
    ))
fig.update_layout(
    barmode="stack",
    title=f"Eindresultaat per startcohort — {keuze}",
    height=480, plot_bgcolor="white", paper_bgcolor="white",
    yaxis=dict(title="Aandeel van cohort", ticksuffix="%", range=[0, 100]),
    xaxis=dict(title="Startjaar cohort", dtick=1),
    font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(t=60, b=40, l=50, r=20),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Elke balk is één startcohort en telt op tot 100%. Recente cohorten staan nog "
    "deels op 'Nog onderweg' omdat het examen nog moet komen."
)

# ── Focus: geslaagd vs afgestroomd ───────────────────────────────────────────
st.subheader("Geslaagd versus afgestroomd")
st.markdown(
    "Twee lijnen die de kern samenvatten: het percentage dat uiteindelijk **slaagde** "
    "en het percentage dat **afstroomde** (naar een lager niveau)."
)

afgerond = perc[perc.index < cnt.index.max()] if len(cnt) > 1 else perc
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=[int(x) for x in afgerond.index], y=afgerond["Geslaagd"],
    name="Geslaagd", mode="lines+markers",
    line=dict(color=RES_KLEUR["Geslaagd"], width=3),
))
fig2.add_trace(go.Scatter(
    x=[int(x) for x in afgerond.index], y=afgerond["Afgestroomd"],
    name="Afgestroomd", mode="lines+markers",
    line=dict(color=RES_KLEUR["Afgestroomd"], width=3),
))
fig2.update_layout(
    height=380, plot_bgcolor="white", paper_bgcolor="white",
    yaxis=dict(title="% van cohort", ticksuffix="%"),
    xaxis=dict(title="Startjaar cohort", dtick=1),
    font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    margin=dict(t=20, b=40, l=50, r=20),
)
st.plotly_chart(fig2, width="stretch")

with st.expander("Toon tabel"):
    toon = perc.copy()
    toon.index.name = "Startjaar"
    st.dataframe(toon.style.format("{:.1f}%"), width="stretch")
    st.caption(f"Aantallen per cohort: {dict(zip(jaren, [int(x) for x in tot]))}")
