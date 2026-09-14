import pandas as pd
import plotly.graph_objects as go
from components.doorstroom_functions import *
from components.popups import *
import streamlit as st

st.set_page_config(layout="wide", page_title="Met tekortpunten", page_icon="📈")
from components.data import load_data
from components.styling import apply_styling
apply_styling()

# --- Streamlit App Layout ---

check_password()

# --- Data Loading ---

updated_df = load_data()

# --- Sidebar for Filters ---

# Schooljaar_start and Schooljaar_eind
all_schoolyears = sorted(updated_df['Schooljaar'].unique().tolist())
if len(all_schoolyears) > 1:
    default_schooljaar_start_idx = 0  # First year
    default_schooljaar_end_idx = min(2, len(all_schoolyears) - 1)  # Third year, or last if fewer than 3
else:
    default_schooljaar_start_idx = 0
    default_schooljaar_end_idx = 0

# Leerfase_start
all_leerfases = sorted(updated_df['Leerfase (afk)'].dropna().unique().tolist())
all_leerfases = all_leerfases[17:]
all_tekortpunten_buckets = sorted(updated_df['Tekortpunten_Bucket'].dropna().unique().tolist())

# --- Main Content ---

st.subheader("De doorstroom – flexibel vooruit en terug")

st.text("Gebruik onderstaande filters om een groep leerlingen te onderzoeken. De filters aan de rechterkant zijn voor de tweede groep om mee te vergelijken.")
st.button(
    "ℹ️ Uitleg: Hulp bij filters.",
    on_click=filter_helper
)
st.button(
    "ℹ️ Uitleg: Vervolg filters.",
    on_click=filter_helper_2
)

# --- Gedeelde tijdsinstellingen ---
st.markdown("#### ⚙️ Tijdsinstellingen (voor beide groepen)")
tcol1, tcol2 = st.columns(2)
with tcol1:
    jaren_vooruit = st.slider(
        "Aantal jaren **vooruit** kijken:",
        min_value=1, max_value=6, value=3, step=1,
        help="VWO-leerlingen kunnen tot 6 jaar op school zitten.",
        key="jaren_vooruit_p1"
    )
with tcol2:
    toon_jaar_terug = st.toggle(
        "Toon 1 jaar **terug** (vorige leerfase als prefix)",
        value=False,
        help="Laat zien vanuit welke leerfase een leerling in de startleerfase is gekomen.",
        key="jaar_terug_p1"
    )
st.divider()

if True:
    if updated_df is not None:
        with st.spinner("Berekenen en plaatje maken..."):

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Analyse groep")
                schooljaar_start = st.selectbox(
                    "Selecteer start schooljaar data (kies bijv. 2022 en 2022 voor schooljaar 2022-2023, of 2022 2023 voor schooljaren 2022 augustus-2024 juli):",
                    options=all_schoolyears,
                    index=5
                )
                schooljaar_eind = st.selectbox(
                    "Tot schooljaar:",
                    options=all_schoolyears,
                    index=5
                )

                if schooljaar_start > schooljaar_eind:
                    st.sidebar.error("Start Schooljaar cannot be after End Schooljaar.")
                    st.stop()
                leerfase_start = st.selectbox(
                    "Selecteer de Leerfase (afk):",
                    options=all_leerfases,
                    index=4
                )

                # Tekortpunten_Bucket filter

                selected_tekortpunten_buckets = st.multiselect(
                    "Selecteer de filter op tekortpunten (In het Startjaar):",
                    options=all_tekortpunten_buckets,
                    default=all_tekortpunten_buckets  # Default to all selected
                )
                progression_percentages = analyze_next_leerfase(
                    updated_df,
                    schooljaar_start=schooljaar_start,
                    schooljaar_eind=schooljaar_eind,
                    leerfase_start=leerfase_start,
                    tekortpunten_bucket_filter=selected_tekortpunten_buckets

                )
                flex_transition_counts = analyze_flexible_leerfase_transitions(
                    updated_df,
                    schooljaar_start=schooljaar_start,
                    schooljaar_eind=schooljaar_eind,
                    leerfase_start=leerfase_start,
                    n_years_forward=jaren_vooruit,
                    include_year_back=toon_jaar_terug,
                    tekortpunten_bucket_filter=selected_tekortpunten_buckets
                )
                if not flex_transition_counts.empty:
                    st.write("#### Aantallen en percentages")
                    st.dataframe(progression_percentages)
                    examenklas_noot(leerfase_start)
                    df_flex = counts_with_percentages(flex_transition_counts)
                    richting = (
                        f"1 jaar terug + {jaren_vooruit} jaar vooruit"
                        if toon_jaar_terug else f"{jaren_vooruit} jaar vooruit"
                    )
                    st.write(f"#### Stromen ({richting})")
                    st.dataframe(df_flex)

                else:
                    st.info("No transitions found for the selected criteria.")
            with col2:
                st.subheader("Vergelijkingsgroep")
                schooljaar_start_vergelijk = st.selectbox(
                    "Selecteer ook alle filters voor de groep waarmee je wil vergelijken. ________________________________________________",
                    options=all_schoolyears,
                    index=5,
                    key=1
                )
                schooljaar_eind_vergelijk = st.selectbox(
                    "Tot schooljaar:",
                    options=all_schoolyears,
                    index=5,
                    key=2
                )

                leerfase_vergelijk = st.selectbox(
                    "Selecteer de Leerfase (afk) om mee te vergelijken:",
                    options=all_leerfases,
                    index=5
                )

                selected_tekortpunten_buckets_vergelijk = st.multiselect(
                    "Selecteer de filter op tekortpunten (In het Startjaar):",
                    options=all_tekortpunten_buckets,
                    default=all_tekortpunten_buckets,  # Default to all selected
                    key=6
                )
                flex_transition_counts_vergelijk = analyze_flexible_leerfase_transitions(
                    updated_df,
                    schooljaar_start=schooljaar_start_vergelijk,
                    schooljaar_eind=schooljaar_eind_vergelijk,
                    leerfase_start=leerfase_vergelijk,
                    n_years_forward=jaren_vooruit,
                    include_year_back=toon_jaar_terug,
                    tekortpunten_bucket_filter=selected_tekortpunten_buckets_vergelijk
                )
                vergelijk_percentages = analyze_next_leerfase(
                    updated_df,
                    schooljaar_start=schooljaar_start_vergelijk,
                    schooljaar_eind=schooljaar_eind_vergelijk,
                    leerfase_start=leerfase_vergelijk,
                    tekortpunten_bucket_filter=selected_tekortpunten_buckets_vergelijk

                )
                if not flex_transition_counts_vergelijk.empty:
                    st.write("#### Vergelijking")
                    st.dataframe(vergelijk_percentages)

                    df_flex_vergelijk = counts_with_percentages(
                        flex_transition_counts_vergelijk
                    )
                    richting = (
                        f"1 jaar terug + {jaren_vooruit} jaar vooruit"
                        if toon_jaar_terug else f"{jaren_vooruit} jaar vooruit"
                    )
                    st.write(f"#### Stromen ({richting})")
                    st.dataframe(df_flex_vergelijk)

                else:
                    st.info("No transitions found for the selected criteria.")
            url = "Details_voor_groepen"
            st.write(
                "Toelichting: als er alleen een leerfase met een aantal staat zonder pijltje. Dan zijn deze leerlingen "
                "in de geselecteerde periode in de geselecteerde leerfase aangekomen, maar nog niet doorgestroomd. "
                "Bijvoorbeeld als je jaren 2023-2024 selecteerd dan zijn er in 2024 leerlingen in H4 gestart, maar "
                "zonder data van 2025-2026 zijn deze leerlingen nog niet doorgestroomd. Zie onderaan op de [pagina Details voor groepen](%s) de tabel met leerlingnummers voor meer inzicht." % url)

            # if not three_year_transition_counts.empty:
            #     # Generate Sankey Diagram
            #     labels, source, target, value = prepare_sankey_data(three_year_transition_counts)
            #     if labels and source and target and value:
            #         title_str = f"Student Progression: {leerfase_start} ({schooljaar_start}-{schooljaar_eind})"
            #         if selected_tekortpunten_buckets:
            #             title_str += f" (Tekortpunten: {', '.join(selected_tekortpunten_buckets)})"
            #
            #         fig = plot_sankey_diagram(labels, source, target, value,
            #                                   title=title_str)
            #         st.write("### Sankey Diagram")
            #         st.plotly_chart(fig, width="stretch")
            #     else:
            #         st.warning("Not enough data to generate a Sankey diagram for the selected filters.")
            # else:
            #     st.info("No transitions found for the selected criteria.")
    else:
        st.error("Data not loaded. Please check the file path and data content.")
st.markdown("#### Ben je klaar met deze pagina, je kan altijd verder kijken op de andere pagina's.")
col3, col4, col5 = st.columns(3)

with col3:
    st.markdown(
        """
        <a class="card-link" href="Analyse_gesplitst" target="_self">
            <div class="card">
                <h3>2️⃣ Analyse doorstroom / afstroom</h3>
                <p>
                    Doorstroom in de volgende drie jaar,
                    gesplitst naar doorstroom, afstroom of doublure.
                </p>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        """
        <a class="card-link" href="Eenjaars_overgangen" target="_self">
            <div class="card">
                <h3>3️⃣ Eenjaars overgangen</h3>
                <p>
                    Eenvoudige weergave van doorstroom
                    met één jaar vooruitkijken.
                </p>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

with col5:
    st.markdown(
        """
        <a class="card-link" href="Details_voor_groepen" target="_self">
            <div class="card">
                <h3>4️⃣ Details voor groepen</h3>
                <p>
                    Leerlingnummers per groep om
                    de herkomst van data te controleren.
                </p>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )
st.write("   \n")
st.markdown(
        """
        <a class="card-link" href="/" target="_self">
            <div class="card">
                <h3>Terug naar start</h3>
        </a>
        """,
        unsafe_allow_html=True
    )
st.showSidebarNavigation = False