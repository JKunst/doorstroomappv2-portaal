import streamlit as st

# check_password backwards-compat (page 4 importeert 'm hier vandaan)
from auth import check_jwt as check_password  # noqa: F401


@st.dialog("Nieuw per versie van app (Huidige 2.1)")
def release_notes():
    st.markdown("""
    **v2.1** Aanpassingen op 15-05-2026:  \n
    - Geïntegreerd in Bovenbouw-portaal (SSO via Kennisnet).  \n
    - Leerlingnummers worden bij inladen gehasht — niet meer zichtbaar in de UI.  \n

    **v2.0** Aanpassingen op 20-03-2026:  \n
    - Basisschooladvies toegevoegd aan de data (waar beschikbaar).  \n
    - Nieuwe pagina *Basisschooladvies* (pagina 3): transitiepaden met uitsplitsing per basisschooladvies, flexibel aantal jaren vooruit/terug.  \n
    - Filter op *School van herkomst* toegevoegd aan pagina 3 (standaard alle scholen geselecteerd).  \n
    - Pagina 1 uitgebreid: slider voor 1–6 jaar vooruit kijken (was vast 3 jaar), toggle om 1 jaar terug te tonen als prefix in de transitiepaden.  \n
    - Wachtwoordbeveiliging \n
    \n
    v1.2 Aanpassingen flow en opmaak, leesbaarheid.  \n
    v1.1 Aanpassing paginavolgorde, percentages in tabel, filters boven tabellen in 3-jaars vergelijk.  \n
    v1.0 Laatst aangepast 11-12-2025, data validatie heeft plaatsgevonden met Cumlaude percentages, leerlingen naar MBO gelabeld.  \n
    v0.91 Laatst aangepast 9-12-2025, data verbetering voor onduidelijke doorstroomcategorieën (bijv. h4->VAVO), toelichting pagina Analyse gesplitst.  \n
    v0.8 Laatst aangepast 3-12-2025, extra pagina met analyse gesplitst en tekortpunten.  \n
    v0.7 Laatst aangepast 26-11-2025, Eerste pagina om groepen doorstroom te vergelijken.  \n
    """)


@st.dialog("Hulp met filters", width="large")
def filter_helper():
    st.markdown("""
                Als je de filters als volgt instelt, selecteer je de leerlingen (voor het eerst) in havo 4 in schooljaar 2022-2023. Je vergelijkt deze met de leerlingen de doublanten in dat jaar h4_doublure:""")
    st.image("components/input_example.jpg", caption="Voorbeeldinstelling", use_container_width=True)
    st.markdown("""Geeft dit de volgende output""")
    st.image("components/output_example.jpg", caption="Voorbeeldoutput", use_container_width=True)


@st.dialog("Hulp met filters deel 2", width="large")
def filter_helper_2():
    st.markdown("""
                Als je de vervolgens gaat kijken naar de leerlingen met 4-6 tekortpunten""")
    st.image("components/input_example_2.png", caption="Voorbeeldinstelling", use_container_width=True)
    st.markdown("""Geeft dit de volgende stromen (2e plaatje)""")
    st.image("components/output_example_2.png", caption="Doorstroom geselecteerde leerlingen", use_container_width=True)
