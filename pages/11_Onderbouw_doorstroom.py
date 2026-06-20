import streamlit as st

st.set_page_config(layout="wide", page_title="Onderbouw doorstroom", page_icon="📈")

import pandas as pd
from auth import check_jwt
from components.data import load_data
from components.styling import apply_styling
from components.dashboard_helpers import (
    categorie_onderbouw, CATS_ONDERBOUW, kale_fase,
    percentages_per_jaar, gebroken_lijngrafiek, geldige_jaargrens,
)

apply_styling()
check_jwt()

st.title("📈 Onderbouw — doorstroom per leerjaar")
st.markdown(
    "Doorstroom en opstroom samengevoegd tot **'Doorgestroomd'** (door naar het "
    "volgende leerjaar of hoger). Die hoge lijn staat in het bovenvlak; doublure, "
    "afstroom en vertrek in het ruime ondervlak. Het lopende schooljaar wordt "
    "weggelaten zodra de doorstroomstatus daar nog niet bekend is."
)

df = load_data()

# Beschikbare onderbouw-fasen per stroom (afhankelijk van wat in de data zit)
STROMEN = {
    "Mavo (t)":  ["t1", "t2", "t3"],
    "Havo (h)":  ["h2", "h3", "h4"],
    "Vwo (v)":   ["v1", "v2", "v3", "v4", "v5"],
    "Brugklas (combi)": ["th1", "th2", "hv1", "hv2"],
}

stroom = st.radio("Kies een stroom", list(STROMEN.keys()), horizontal=True)

aanwezig = sorted(set(kale_fase(df["Leerfase (afk)"]).dropna()) - {"nan"})
fasen = [f for f in STROMEN[stroom] if f in aanwezig]

if not fasen:
    st.info("Geen data voor deze stroom.")
    st.stop()

fase = st.selectbox("Kies een leerjaar", fasen)

jaargrens = geldige_jaargrens(df)
jaren, perc, cnt, tot, overig = percentages_per_jaar(
    df, fase, categorie_onderbouw, CATS_ONDERBOUW,
    drop_laatste_jaar=True, geldige_jaren=jaargrens,
)

fig = gebroken_lijngrafiek(
    jaren, perc, cnt, CATS_ONDERBOUW,
    titel=f"Doorstroom {fase} per schooljaar",
    hoog=(70, 100), laag=(0, 25),
)
st.plotly_chart(fig, width="stretch")

st.caption(
    "Hover voor percentage én absoluut aantal. Alle uitkomsten samen tellen per "
    "jaar op tot 100%. Voor de mavo (t) komt afstroom niet voor — t is het laagste "
    "aangeboden niveau."
)

with st.expander("Wat zit er in 'Onbekend/overig' en 'Opleiding elders/onbekend'?"):
    st.write(
        "**Opleiding elders/onbekend** — leerlingen die in een afgesloten jaar uit "
        "de telling verdwijnen zonder doorstroom- of vertrekstatus, zonder vervolg. "
        "Vermoedelijk tussentijds vertrokken naar een andere school."
    )
    leeg = overig.get("(leeg)", 0)
    st.write(
        f"**Onbekend/overig** — {leeg} records met een lege doorstroomstatus die "
        "niet onder de bovenstaande noemer vallen (meestal het lopende jaar). "
        "Geen echte uitkomst, maar ontbrekende registratie."
    )

with st.expander("Toon tabel met percentages"):
    tabel = pd.DataFrame(perc, index=jaren)
    tabel.index.name = "Schooljaar"
    st.dataframe(tabel.style.format("{:.1f}%"), width="stretch")
