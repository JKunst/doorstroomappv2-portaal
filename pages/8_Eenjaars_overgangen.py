import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
from components.helper import *

# Mount Google Drive (if running in Colab, this will prompt authentication)
# In a local Streamlit environment, ensure the file path is accessible.
# drive.mount('/content/drive')

# --- Functions (copied from notebook) ---

def _get_leerfase_numeric_value(leerfase_str):
    """
    Assigns a numerical value to each 'Leerfase (afk)' for comparison.

    Args:
        leerfase_str (str): The 'Leerfase (afk)' string.

    Returns:
        float: A numerical representation of the leerfase, or np.nan if not recognized.
    """
    if pd.isna(leerfase_str):
        return np.nan

    leerfase_str = str(leerfase_str).strip()

    # Handle terminal statuses
    if leerfase_str == 'Geslaagd':
        return 100.0  # High value for successful completion
    elif leerfase_str in ['VO verlater', 'Afstroom', 'Afgewezen']:
        return 0.0    # Low value for non-progression/failure

    # Handle 'doublure' by stripping it for the core comparison logic
    original_leerfase = leerfase_str
    if '_doublure' in leerfase_str:
        leerfase_str = leerfase_str.replace('_doublure', '')

    # Handle 'v', 'h', 't' levels
    if leerfase_str.startswith('t') and leerfase_str[1:].isdigit():
        return 10 + int(leerfase_str[1:])
    elif leerfase_str.startswith('hv') and leerfase_str[2:].isdigit():
        return 15 + int(leerfase_str[2:])
    elif leerfase_str.startswith('h') and leerfase_str[1:].isdigit():
        return 20 + int(leerfase_str[1:])
    elif leerfase_str.startswith('v') and leerfase_str[1:].isdigit():
        return 30 + int(leerfase_str[1:])

    return np.nan # Return NaN for unknown patterns

def analyze_next_leerfase(df, schooljaar_start, schooljaar_eind, leerfase_start, tekortpunten_bucket_filter=None, leerfase_vergelijk=None):
    """
    Analyzes one-year student progression from a specific 'Leerfase (afk)'
    within a school year range, categorizing into 'Doublure', 'Doorstroom',
    'Afstroom', or 'Other', and calculating percentages and counts.

    Args:
        df (pd.DataFrame): The input DataFrame, sorted by 'Leerlingnummer' and 'Schooljaar'.
                           Must contain 'Leerlingnummer', 'Schooljaar', 'Leerfase (afk)',
                           'Leerfase (afk) vorig schooljaar', and 'Tekortpunten_Bucket' columns.
        schooljaar_start (int): The starting school year (inclusive) for the analysis.
        schooljaar_eind (int): The ending school year (inclusive) for the analysis.
        leerfase_start (str): The specific 'Leerfase (afk)' from which to track transitions.
        tekortpunten_bucket_filter (list, optional): A list of 'Tekortpunten_Bucket' categories to filter.
                                                   Defaults to None (all buckets).
        leerfase_vergelijk (str, optional): A specific 'Leerfase (afk)' to compare against.
                                            If provided, will specifically track progression to this phase.

    Returns:
        tuple: A tuple containing two pd.Series:
               - progression_percentages (pd.Series): Percentages of progression categories.
               - progression_counts (pd.Series): Absolute counts of progression categories.
               Returns (pd.Series([], dtype=float), pd.Series([], dtype=int)) if no students match the criteria.
    """
    # 1. Filter students who were in the leerfase_start within the specified year range.
    initial_phase_students_df = df[
        (df['Schooljaar'] >= schooljaar_start) &
        (df['Schooljaar'] <= schooljaar_eind) &
        (df['Leerfase (afk)'] == leerfase_start)
    ].copy()

    # Apply tekortpunten_bucket_filter if provided
    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        initial_phase_students_df = initial_phase_students_df[
            initial_phase_students_df['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)
        ]

    relevant_leerlingnummers = initial_phase_students_df['Leerlingnummer'].unique()

    if len(relevant_leerlingnummers) == 0:
        return pd.Series([], dtype=float), pd.Series([], dtype=int)

    # 2. Get ALL records for these relevant students to track their next year's phase
    student_records = df[df['Leerlingnummer'].isin(relevant_leerlingnummers)].copy()
    student_records = student_records.sort_values(by=['Leerlingnummer', 'Schooljaar'])

    # Calculate the next 'Leerfase (afk)' for each student
    student_records['next_leerfase'] = student_records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-1)
    student_records['next_schooljaar'] = student_records.groupby('Leerlingnummer')['Schooljaar'].shift(-1)

    # Filter to get only the transitions from leerfase_start in the specified school years
    # and only for the immediate next school year.
    transitions_df = student_records[
        (student_records['Leerfase (afk)'] == leerfase_start) &
        (student_records['Schooljaar'] >= schooljaar_start) &
        (student_records['Schooljaar'] <= schooljaar_eind) &
        (student_records['next_schooljaar'] == student_records['Schooljaar'] + 1)
    ].copy()

    # Make sure Leerfase (afk) vorig schooljaar is valid before comparison for doublure
    transitions_df['Leerfase (afk) vorig schooljaar_clean'] = transitions_df['Leerfase (afk) vorig schooljaar'].apply(lambda x: str(x).replace('_doublure', '') if pd.notna(x) else np.nan)

    # Remove _doublure from leerfase_start for comparison
    leerfase_start_clean = str(leerfase_start).replace('_doublure', '')

    def categorize_progression(row):
        current_phase = row['Leerfase (afk)']
        next_phase = row['next_leerfase']

        if pd.isna(next_phase):
            return 'No Data (Dropout/Missing)' # Handle cases where next phase is missing

        # Specific comparison for leerfase_vergelijk if provided
        if leerfase_vergelijk and next_phase == leerfase_vergelijk:
            return f'To {leerfase_vergelijk}'

        # Priority 1: Doublure detection
        if '_doublure' in str(next_phase) and str(next_phase).replace('_doublure', '') == leerfase_start_clean:
            return 'Doublure'

        # Clean next_phase for numeric comparison
        next_phase_clean = str(next_phase).replace('_doublure', '')

        # Priority 2: Terminal statuses
        if next_phase_clean == 'Geslaagd':
            return 'Doorstroom' # Geslaagd is always a positive progression
        elif next_phase_clean in ['VO verlater', 'Afstroom', 'Afgewezen']:
            return 'Afstroom' # These are definitive negative outcomes

        # Priority 3: Numeric comparison for v/h/t levels
        current_numeric = _get_leerfase_numeric_value(current_phase)
        next_numeric = _get_leerfase_numeric_value(next_phase_clean)

        if pd.isna(current_numeric) or pd.isna(next_numeric):
            return 'Other' # Cannot compare if numeric values are unknown

        if next_numeric > current_numeric:
            return 'Doorstroom'
        elif next_numeric < current_numeric:
            return 'Afstroom'
        elif next_numeric == current_numeric:
            # If numeric values are the same but not a _doublure and not a terminal status,
            # it implies staying in the same level without explicitly being a doublure, which is 'Other'
            return 'Other'

        return 'Other' # Default for any uncaught cases

    if transitions_df.empty:
        return pd.Series([], dtype=float), pd.Series([], dtype=int)

    transitions_df['Progression'] = transitions_df.apply(categorize_progression, axis=1)

    # Calculate percentages
    total_students = len(transitions_df)
    if total_students == 0:
        return pd.Series([], dtype=float), pd.Series([], dtype=int)

    progression_counts = transitions_df['Progression'].value_counts()
    progression_percentages = (progression_counts / total_students) * 100

    # Ensure all categories are present, even if 0% or 0 count
    all_categories = ['Doorstroom', 'Afstroom', 'Doublure', 'Other', 'No Data (Dropout/Missing)']
    if leerfase_vergelijk:
        all_categories.append(f'To {leerfase_vergelijk}')

    for category in all_categories:
        if category not in progression_percentages.index:
            progression_percentages[category] = 0.0
        if category not in progression_counts.index:
            progression_counts[category] = 0

    return progression_percentages.sort_index(), progression_counts.sort_index()

# --- Streamlit App Layout ---
st.set_page_config(layout="wide")
from components.data import load_data
from components.styling import apply_styling
apply_styling()

st.title("Student Leerfase Progression Analysis (One-Year Transitions)") # Updated Title

check_password()

# --- Data Loading ---

updated_df = load_data()

# --- Sidebar for Filters ---
st.sidebar.header("Analysis Filters")

# Schooljaar_start and Schooljaar_eind
all_schoolyears = sorted(updated_df['Schooljaar'].unique().tolist())
if len(all_schoolyears) > 1:
    default_schooljaar_start_idx = 0  # First year
    default_schooljaar_end_idx = min(2, len(all_schoolyears) - 1)  # Third year, or last if fewer than 3
else:
    default_schooljaar_start_idx = 0
    default_schooljaar_end_idx = 0

schooljaar_start = st.selectbox(
    "Selecteer start schooljaar data (kies bijv. 2022 voor schooljaar 2022-2023):",
    options=all_schoolyears,
    index=5
)
schooljaar_eind = st.selectbox(
    "Select eind schooljaar:",
    options=all_schoolyears,
    index=5
)

if schooljaar_start > schooljaar_eind:
    st.sidebar.error("Start Schooljaar cannot be after End Schooljaar.")
    st.stop()

# Leerfase_start
all_leerfases = sorted(updated_df['Leerfase (afk)'].replace({'_doublure': ''}, regex=True).dropna().unique().tolist())
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
leerfase_start = st.selectbox(
    "Selecteer de Leerfase (afk):",
    options=all_leerfases,
    index=5
)

# Tekortpunten_Bucket filter
all_tekortpunten_buckets = sorted(updated_df['Tekortpunten_Bucket'].dropna().unique().tolist())
selected_tekortpunten_buckets = st.sidebar.multiselect(
    "Selecteer de filter op tekortpunten (In het Startjaar):",
    options=all_tekortpunten_buckets,
    default=all_tekortpunten_buckets  # Default to all selected
)

vergelijk_start = st.selectbox(
    "Vergelijkperiode start schooljaar data:",
    options=all_schoolyears,
    index=default_schooljaar_start_idx
)
vergelijk_eind = st.selectbox(
    "Vergelijkperiode eind schooljaar:",
    options=all_schoolyears,
    index=default_schooljaar_end_idx
)

if vergelijk_start > vergelijk_eind:
    st.sidebar.error("Start Schooljaar cannot be after End Schooljaar.")
    st.stop()

leerfase_vergelijk = st.selectbox(
    "Selecteer de Leerfase (afk) om mee te vergelijken:",
    options=all_leerfases,
    index=5
)
vergelijk_tekortpunten_buckets = st.multiselect(
    "Selecteer tekortpunten (In het Startjaar) om mee te vergelijken:",
    options=all_tekortpunten_buckets,
    default=all_tekortpunten_buckets  # Default to all selected
)

# --- Main Content ---
st.subheader(f"Een jaar vooruit ({schooljaar_start}-{schooljaar_eind})") # Updated Subheader

if st.button("Run Analysis"):
    if updated_df is not None:
        with st.spinner("Running analysis and generating results..."):
            # Call the one-year progression analysis function
            progression_percentages, progression_counts = analyze_next_leerfase(
                updated_df,
                schooljaar_start=schooljaar_start,
                schooljaar_eind=schooljaar_eind,
                leerfase_start=leerfase_start,
                tekortpunten_bucket_filter=selected_tekortpunten_buckets
            )
            vergelijk_percentages, vergelijk_counts = analyze_next_leerfase(
                updated_df,
                schooljaar_start=vergelijk_start,
                schooljaar_eind=vergelijk_eind,
                leerfase_start=leerfase_vergelijk,
                tekortpunten_bucket_filter=vergelijk_tekortpunten_buckets
            )
            col1, col2 = st.columns(2)
            with col1:
                if not progression_percentages.empty:

                    st.write(f"### Eenjaars percentages {leerfase_start}") # Updated Heading
                    st.dataframe(progression_percentages.reset_index().rename(columns={'index': 'Progression Category', 0: 'Percentage (%)'}))

                    st.write(f"### Eenjaars aantallen {leerfase_start}") # New Heading for counts
                    st.dataframe(progression_counts.reset_index().rename(columns={'index': 'Progression Category', 0: 'Count'}))
                else:
                    st.info("No transitions found for the selected criteria.")
            with col2:
                if not vergelijk_percentages.empty:

                    st.write(f"### Vergeleken met {leerfase_vergelijk} percentages")  # Updated Heading
                    st.dataframe(vergelijk_percentages.reset_index().rename(
                        columns={'index': 'Progression Category', 0: 'Percentage (%)'}))

                    st.write(f"### Eenjaars aantallen {leerfase_vergelijk}")  # New Heading for counts
                    st.dataframe(
                        vergelijk_counts.reset_index().rename(columns={'index': 'Progression Category', 0: 'Count'}))
                else:
                    st.info("No transitions found for the selected criteria.")
    else:
        st.error("Data not loaded. Please check the file path and data content.")
st.markdown(
        """
        <a class="card-link" href="/" target="_self">
            <div class="card">
                <h3>Terug naar start</h3>
        </a>
        """,
        unsafe_allow_html=True
    )