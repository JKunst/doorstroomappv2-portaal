"""
Centrale data-loader. Vervangt de 7x gekopieerde load_data() in elke pagina.

Hasht de Leerlingnummer-kolom bij inladen, zodat:
- Groupby/shift-logica (doorstroom-tracking) blijft werken — IDs zijn nog uniek
- Geen herleidbare nummers in dataframes die de UI ooit zou kunnen tonen
"""
import hashlib
import os

import numpy as np
import pandas as pd
import streamlit as st

DATA_FILE = "updated_df.xlsx"
HASH_SALT = os.environ.get("LEERLING_HASH_SALT", "")


def _hash_id(waarde) -> str:
    """SHA-256 met salt, ingekort tot 12 hex chars — nog ruim genoeg uniek."""
    payload = f"{HASH_SALT}:{waarde}".encode()
    return hashlib.sha256(payload).hexdigest()[:12]


@st.cache_data(show_spinner="Data laden…")
def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_FILE):
        st.error(f"Databestand niet gevonden: {DATA_FILE}")
        st.stop()

    df = pd.read_excel(DATA_FILE)
    df["Schooljaar"] = df["Schooljaar"].astype(int)
    df["Inschrijvingsdatum"] = pd.to_datetime(df["Inschrijvingsdatum"])

    if "Leerlingnummer" in df.columns:
        df["Leerlingnummer"] = df["Leerlingnummer"].map(_hash_id)

    # Tekortpunten-buckets: leerling met 3 tp valt in '0-3', met 4 in '4-6'
    df["Tekortpunten_Bucket"] = pd.cut(
        df["Tekortpunten"],
        bins=[-1, 3, 6, 9, np.inf],
        labels=["0-3", "4-6", "7-9", "10+"],
        right=True,
        include_lowest=True,
    )

    return df
