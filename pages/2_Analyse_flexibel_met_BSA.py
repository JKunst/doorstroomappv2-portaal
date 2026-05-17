import pandas as pd
import streamlit as st
import numpy as np
import os
from components.doorstroom_functions import (
    analyze_next_leerfase,
    analyze_flexible_transitions,
    counts_with_percentages,
)
from components.popups import *
from components.doorstroom_functions import *
from components.helper import *

# --- Pagina configuratie ---
st.set_page_config(layout="wide", page_title="Flexibel met BSA", page_icon="📊")

from components.data import load_data
from components.styling import apply_styling
apply_styling()

# --- Auth (zelfde als pagina 2) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True

check_password()

# --- Data laden ---

updated_df = load_data()

# --- Opties opbouwen ---
all_schoolyears = sorted(updated_df["Schooljaar"].unique().tolist())

all_leerfases = sorted(updated_df["Leerfase (afk)"].dropna().unique().tolist())
# Verwijder de eerste 8 (zelfde als pagina 2)
all_leerfases = all_leerfases[17:]

all_tekortpunten_buckets = sorted(
    updated_df["Tekortpunten_Bucket"].dropna().unique().tolist()
)

all_bsa = sorted(updated_df["Basisschooladvies"].dropna().unique().tolist())

# --- Pagina header ---
st.subheader("Doorstroom – flexibel vooruit & 1 jaar terug, met Basisschooladvies")
st.text(
    "Gebruik de filters om een groep leerlingen te analyseren. "
    "De rechterkolom is voor de vergelijkingsgroep. "
    "Het Basisschooladvies wordt getoond als uitsplitsing per transitiepad."
)
st.button("ℹ️ Uitleg: Hulp bij filters.", on_click=filter_helper)
st.button("ℹ️ Uitleg: Vervolg filters.", on_click=filter_helper_2)

# --- Globale tijdsinstellingen (gedeeld) ---
st.markdown("#### ⚙️ Tijdsinstellingen (voor beide groepen)")
tcol1, tcol2, tcol3 = st.columns(3)
with tcol1:
    jaren_vooruit = st.slider(
        "Aantal jaren **vooruit** kijken:",
        min_value=1, max_value=6, value=3, step=1,
        help="VWO-leerlingen kunnen tot 6 jaar op school zitten."
    )
with tcol2:
    toon_jaar_terug = st.toggle(
        "Toon 1 jaar **terug** (vorige leerfase als prefix)",
        value=False,
        help="Laat zien vanuit welke leerfase een leerling in de starttase is gekomen."
    )
with tcol3:
    st.markdown("")  # ruimte

st.divider()

# --- Twee kolommen: analyse + vergelijking ---
if updated_df is not None:
    with st.spinner("Berekenen en plaatje maken..."):
        # col1, col2 = st.columns(2)

        # ========== KOLOM 1: ANALYSE GROEP ==========
        # with col1:
            st.subheader("Analyse groep")

            schooljaar_start = st.selectbox(
                "Selecteer start schooljaar:",
                options=all_schoolyears, index=5, key="sj_start_1"
            )
            schooljaar_eind = st.selectbox(
                "Tot en met schooljaar:",
                options=all_schoolyears, index=5, key="sj_eind_1"
            )
            if schooljaar_start > schooljaar_eind:
                st.error("Startjaar mag niet na eindjaar liggen.")
                st.stop()

            leerfase_start = st.selectbox(
                "Selecteer de Leerfase (afk):",
                options=all_leerfases, index=4, key="lf_1"
            )
            selected_buckets = st.multiselect(
                "Filter op tekortpunten (in het startjaar):",
                options=all_tekortpunten_buckets,
                default=all_tekortpunten_buckets,
                key="buckets_1"
            )

            # --- Eenjaars overzicht ---
            progression_percentages = analyze_next_leerfase(
                updated_df,
                schooljaar_start=schooljaar_start,
                schooljaar_eind=schooljaar_eind,
                leerfase_start=leerfase_start,
                tekortpunten_bucket_filter=selected_buckets,
            )
            if not progression_percentages.empty:
                st.write("#### Aantallen en percentages (1 jaar vooruit)")
                st.dataframe(progression_percentages)
            else:
                st.info("Geen leerlingen gevonden voor deze selectie.")

            # --- Flexibele transitietabel met BSA ---
            flex_df = analyze_flexible_transitions(
                updated_df,
                schooljaar_start=schooljaar_start,
                schooljaar_eind=schooljaar_eind,
                leerfase_start=leerfase_start,
                jaren_vooruit=jaren_vooruit,
                toon_jaar_terug=toon_jaar_terug,
                tekortpunten_bucket_filter=selected_buckets,
            )
            if not flex_df.empty:
                richting = (
                    f"1 jaar terug + {jaren_vooruit} jaar vooruit"
                    if toon_jaar_terug
                    else f"{jaren_vooruit} jaar vooruit"
                )
                st.write(f"#### Transitiepaden ({richting}) met Basisschooladvies")
                st.dataframe(
                    flex_df,
                    use_container_width=True,
                    column_config={
                        "Aantal": st.column_config.NumberColumn("Aantal"),
                        "Percentage": st.column_config.TextColumn("Percentage"),
                    },
                )
            else:
                st.info("Geen transities gevonden voor de geselecteerde criteria.")

        # # ========== KOLOM 2: VERGELIJKINGSGROEP ==========
        # with col2:
        #     st.subheader("Vergelijkingsgroep")
        #
        #     schooljaar_start_v = st.selectbox(
        #         "Selecteer start schooljaar (vergelijking):",
        #         options=all_schoolyears, index=5, key="sj_start_2"
        #     )
        #     schooljaar_eind_v = st.selectbox(
        #         "Tot en met schooljaar (vergelijking):",
        #         options=all_schoolyears, index=5, key="sj_eind_2"
        #     )
        #     if schooljaar_start_v > schooljaar_eind_v:
        #         st.error("Startjaar mag niet na eindjaar liggen.")
        #         st.stop()
        #
        #     leerfase_vergelijk = st.selectbox(
        #         "Selecteer de Leerfase (afk.) voor vergelijking:",
        #         options=all_leerfases, index=5, key="lf_2"
        #     )
        #     selected_buckets_v = st.multiselect(
        #         "Filter op tekortpunten (in het startjaar):",
        #         options=all_tekortpunten_buckets,
        #         default=all_tekortpunten_buckets,
        #         key="buckets_2"
        #     )
        #
        #     # --- Eenjaars overzicht vergelijking ---
        #     vergelijk_percentages = analyze_next_leerfase(
        #         updated_df,
        #         schooljaar_start=schooljaar_start_v,
        #         schooljaar_eind=schooljaar_eind_v,
        #         leerfase_start=leerfase_vergelijk,
        #         tekortpunten_bucket_filter=selected_buckets_v,
        #     )
        #     if not vergelijk_percentages.empty:
        #         st.write("#### Vergelijking (1 jaar vooruit)")
        #         st.dataframe(vergelijk_percentages)
        #     else:
        #         st.info("Geen leerlingen gevonden voor deze selectie.")
        #
        #     # --- Flexibele transitietabel met BSA (vergelijking) ---
        #     flex_df_v = analyze_flexible_transitions(
        #         updated_df,
        #         schooljaar_start=schooljaar_start_v,
        #         schooljaar_eind=schooljaar_eind_v,
        #         leerfase_start=leerfase_vergelijk,
        #         jaren_vooruit=jaren_vooruit,
        #         toon_jaar_terug=toon_jaar_terug,
        #         tekortpunten_bucket_filter=selected_buckets_v,
        #     )
        #     if not flex_df_v.empty:
        #         richting = (
        #             f"1 jaar terug + {jaren_vooruit} jaar vooruit"
        #             if toon_jaar_terug
        #             else f"{jaren_vooruit} jaar vooruit"
        #         )
        #         st.write(f"#### Transitiepaden ({richting}) met Basisschooladvies")
        #         st.dataframe(
        #             flex_df_v,
        #             use_container_width=True,
        #             column_config={
        #                 "Aantal": st.column_config.NumberColumn("Aantal"),
        #                 "Percentage": st.column_config.TextColumn("Percentage"),
        #             },
        #         )
        #     else:
        #         st.info("Geen transities gevonden voor de geselecteerde criteria.")

    # --- Toelichting ---
    url = "Details_voor_groepen"
    st.write(
        "Toelichting: als er alleen een leerfase met een aantal staat zonder pijltje, "
        "zijn deze leerlingen in de geselecteerde periode in de geselecteerde leerfase "
        "aangekomen, maar nog niet doorgestroomd. "
        "Zie onderaan op de [pagina Details voor groepen](%s) de tabel met leerlingnummers." % url
    )
else:
    st.error("Data niet geladen. Controleer het bestandspad.")

# --- Navigatiekaarten onderaan ---
st.markdown("#### Ben je klaar met deze pagina, je kan altijd verder kijken op de andere pagina's.")
col3, col4, col5 = st.columns(3)

with col3:
    st.markdown(
        """
        <a class="card-link" href="Analyse_gegroepeerd_naar_tekorten" target="_self">
            <div class="card">
                <h3>1️⃣ Analyse met tekortpunten (3 jaar)</h3>
                <p>De originele pagina met doorstroom 3 jaar vooruit, gegroepeerd naar tekorten.</p>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <a class="card-link" href="Eenjaars_overgangen" target="_self">
            <div class="card">
                <h3>3️⃣ Eenjaars overgangen</h3>
                <p>Eenvoudige weergave van doorstroom met één jaar vooruitkijken.</p>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        """
        <a class="card-link" href="Details_voor_groepen" target="_self">
            <div class="card">
                <h3>4️⃣ Details voor groepen</h3>
                <p>Leerlingnummers per groep om de herkomst van data te controleren.</p>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

st.write("   \n")
st.markdown(
    """
    <a class="card-link" href="/" target="_self">
        <div class="card">
            <h3>Terug naar start</h3>
    </a>
    """,
    unsafe_allow_html=True,
)
st.showSidebarNavigation = False
