import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import check_jwt
from components.data import load_data
from components.styling import apply_styling


# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Met tekortpunten", page_icon="📈")
apply_styling()
check_jwt()


# ── Analyse: 3-jaars leerfase-transities ─────────────────────────────────────
def analyze_three_year_leerfase_transitions(
    df: pd.DataFrame,
    schooljaar_start: int,
    schooljaar_eind: int,
    leerfase_start: str,
) -> pd.Series:
    """
    Telt 3-jaars leerfase-paden vanuit `leerfase_start`, voor leerlingen
    die in [schooljaar_start, schooljaar_eind] in die leerfase startten.
    Retourneert pad-string (bijv. 'h3 -> h4 -> h5') → aantal leerlingen.
    """
    initial = df[
        (df["Schooljaar"].between(schooljaar_start, schooljaar_eind))
        & (df["Leerfase (afk)"] == leerfase_start)
    ]
    if initial.empty:
        return pd.Series([], dtype=int)

    records = df[df["Leerlingnummer"].isin(initial["Leerlingnummer"].unique())].copy()
    records = records.sort_values(["Leerlingnummer", "Schooljaar"])

    for i in (1, 2, 3):
        records[f"next_leerfase_{i}"] = records.groupby("Leerlingnummer")["Leerfase (afk)"].shift(-i)
        records[f"next_schooljaar_{i}"] = records.groupby("Leerlingnummer")["Schooljaar"].shift(-i)

    starts = records[
        (records["Leerfase (afk)"] == leerfase_start)
        & (records["Schooljaar"].between(schooljaar_start, schooljaar_eind))
    ].copy()
    if starts.empty:
        return pd.Series([], dtype=int)

    starts["Transition"] = starts["Leerfase (afk)"]
    for i in (1, 2, 3):
        cond = (starts[f"next_schooljaar_{i}"] == starts["Schooljaar"] + i) & starts[f"next_leerfase_{i}"].notna()
        for j in range(1, i):
            cond &= starts[f"next_schooljaar_{j}"] == starts["Schooljaar"] + j
        starts["Transition"] = np.where(
            cond,
            starts["Transition"] + " -> " + starts[f"next_leerfase_{i}"],
            starts["Transition"],
        )

    return starts["Transition"].value_counts()


# ── Sankey helpers ───────────────────────────────────────────────────────────
def prepare_sankey_data(transition_counts: pd.Series):
    labels = sorted({step for path in transition_counts.index for step in path.split(" -> ")})
    idx = {label: i for i, label in enumerate(labels)}

    links = []
    for path, count in transition_counts.items():
        steps = path.split(" -> ")
        for a, b in zip(steps, steps[1:]):
            links.append((idx[a], idx[b], count))

    if not links:
        return labels, [], [], []

    df_links = pd.DataFrame(links, columns=["source", "target", "value"])
    df_links = df_links.groupby(["source", "target"], as_index=False)["value"].sum()
    return labels, df_links["source"].tolist(), df_links["target"].tolist(), df_links["value"].tolist()


def plot_sankey_diagram(labels, source, target, value, title):
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels),
        link=dict(source=source, target=target, value=value),
    )])
    fig.update_layout(title_text=title, font_size=10)
    return fig


# ── App ──────────────────────────────────────────────────────────────────────
st.title("Analyse van doorstroom (3-jaar vooruit)")

updated_df = load_data()

# ── Sidebar / filters ────────────────────────────────────────────────────────
st.sidebar.header("Analysis Filters")

all_schoolyears = sorted(updated_df["Schooljaar"].unique().tolist())
schooljaar_start = st.selectbox(
    "Selecteer start schooljaar (kies bijv. 2022 voor schooljaar 2022-2023):",
    options=all_schoolyears,
    index=min(5, len(all_schoolyears) - 1),
)
schooljaar_eind = st.selectbox(
    "Selecteer eind schooljaar:",
    options=all_schoolyears,
    index=min(5, len(all_schoolyears) - 1),
)
if schooljaar_start > schooljaar_eind:
    st.sidebar.error("Start schooljaar kan niet na eind schooljaar liggen.")
    st.stop()

# Filter alleen bovenbouwfases (was: all_leerfases.pop(0) × 8)
EXCLUDE_LEERFASES = {"b1", "b2", "b3", "h3", "v3", "k3", "k4", "mbo"}  # pas aan naar wens
all_leerfases = sorted(
    lf for lf in updated_df["Leerfase (afk)"].dropna().unique()
    if lf.lower() not in EXCLUDE_LEERFASES
)
leerfase_start = st.selectbox("Selecteer de Leerfase (afk):", options=all_leerfases, index=min(4, len(all_leerfases) - 1))
leerfase_vergelijk = st.selectbox("Selecteer de Leerfase (afk) om mee te vergelijken:", options=all_leerfases, index=min(5, len(all_leerfases) - 1))

# ── Main ─────────────────────────────────────────────────────────────────────
st.subheader(
    f"Leerlingen uit '{leerfase_start}' van {schooljaar_start}-{schooljaar_eind + 1} en hun doorstroom"
)
st.write("Selecteer links de schooljaren en leerfase.")

if st.button("Run Analysis"):
    with st.spinner("Analyse uitvoeren…"):
        counts_main = analyze_three_year_leerfase_transitions(
            updated_df, schooljaar_start, schooljaar_eind, leerfase_start
        )
        counts_compare = analyze_three_year_leerfase_transitions(
            updated_df, schooljaar_start, schooljaar_eind, leerfase_vergelijk
        )

    col1, col2 = st.columns(2)
    with col1:
        st.write("### Aantallen")
        if counts_main.empty:
            st.info("Geen transities gevonden voor de geselecteerde criteria.")
        else:
            st.dataframe(counts_main)
    with col2:
        st.write("### Vergelijking")
        if counts_compare.empty:
            st.info("Geen transities gevonden voor de geselecteerde criteria.")
        else:
            st.dataframe(counts_compare)
            st.caption(
                "Toelichting: als er alleen een leerfase met een aantal staat zonder pijltje, "
                "zijn deze leerlingen in de geselecteerde periode in die leerfase aangekomen, "
                "maar nog niet doorgestroomd."
            )

    if not counts_main.empty:
        labels, source, target, value = prepare_sankey_data(counts_main)
        if labels and source:
            fig = plot_sankey_diagram(
                labels, source, target, value,
                title=f"Doorstroom: {leerfase_start} ({schooljaar_start}-{schooljaar_eind})",
            )
            st.write("### Sankey-diagram")
            st.plotly_chart(fig, use_container_width=True)

        st.write("### Details per pad")
        st.dataframe(counts_main.rename("Aantal").reset_index().rename(columns={"index": "Pad"}))

# ── Footer: sidebar verbergen + terug-knop ───────────────────────────────────
st.markdown(
    """<style>[data-testid="collapsedControl"]{display:none}</style>""",
    unsafe_allow_html=True,
)
st.markdown(
    """<a class="card-link" href="/" target="_self"><div class="card"><h3>Terug naar start</h3></div></a>""",
    unsafe_allow_html=True,
)
