import streamlit as st

st.set_page_config(layout="wide", page_title="Examenresultaten per niveau", page_icon="🎓")

import pandas as pd
from auth import check_jwt
from components.data import load_data
from components.styling import apply_styling
from components.dashboard_helpers import (
    categorie_examen, CATS_EXAMEN, percentages_per_jaar, gebroken_lijngrafiek,
    geldige_jaargrens,
)

apply_styling()
check_jwt()

st.title("🎓 Examenresultaten per niveau")
st.markdown(
    "Slagen en opstromen versus doubleren en uitstroom in de examenklassen, "
    "per cohort. **Geslaagd** en **opgestroomd** zijn samengevoegd tot één lijn; "
    "die staat hoog in het smalle bovenvlak. De overige uitkomsten krijgen het "
    "ruime ondervlak. De y-as is gebroken voor leesbaarheid."
)

df = load_data()
jaargrens = geldige_jaargrens(df)

NIVEAUS = {"Mavo (t4)": "t4", "Havo (h5)": "h5", "Vwo (v6)": "v6"}
keuze = st.radio("Kies een niveau", list(NIVEAUS.keys()), horizontal=True)
fase = NIVEAUS[keuze]

jaren, perc, cnt, tot, overig = percentages_per_jaar(
    df, fase, categorie_examen, CATS_EXAMEN, geldige_jaren=jaargrens
)

fig = gebroken_lijngrafiek(
    jaren, perc, cnt, CATS_EXAMEN,
    titel=f"Examenuitslag {keuze} per schooljaar",
    hoog=(55, 100), laag=(0, 25),
)
st.plotly_chart(fig, width="stretch")

st.caption(
    "Hover voor percentage én absoluut aantal. Het laatste jaar is een prognose "
    "(examens nog niet afgerond); 'Afgewezen' wordt pas vanaf 2022 als status "
    "geregistreerd."
)

# ── Uitleg 'Overig' ──────────────────────────────────────────────────────────
with st.expander("Wat zit er in 'Overig'?"):
    if overig:
        regels = [
            (("nog geen status (lopend jaar)" if k == "(leeg)" else k) + f": {v}")
            for k, v in overig.items()
        ]
        st.write(" · ".join(regels))
    else:
        st.write("Geen records in deze categorie.")
    st.write(
        "Na het apart tellen van opstroom bevat 'Overig' vrijwel alleen leerlingen "
        "zonder ingevulde doorstroomstatus (lopend jaar) en een enkele afstroom — "
        "geen aparte uitkomstcategorie."
    )

# ── Tabel ────────────────────────────────────────────────────────────────────
with st.expander("Toon tabel met percentages"):
    tabel = pd.DataFrame(perc, index=jaren)
    tabel.index.name = "Schooljaar"
    st.dataframe(tabel.style.format("{:.1f}%"), width="stretch")
