import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

EXAMENFASES = ("t4", "h5", "v6")


def examenklas_noot(leerfase_start):
    """Toon bij een examenklas waarom geslaagden in de eenjaars-tabel ontbreken."""
    if str(leerfase_start).replace("_doublure", "") in EXAMENFASES:
        st.caption(
            "Let op: geslaagde leerlingen hebben in de data geen rij voor het volgende "
            "schooljaar en ontbreken daarom in deze eenjaars-tabel — die toont alleen "
            "doublures, afgewezenen en overstappers. Slagingspercentages staan op de "
            "pagina Examenresultaten per niveau."
        )


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
    'Afstroom', or 'Other', and calculating percentages, counts, and listing student IDs.

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
        tuple: A tuple containing two pd.Series and one dict:
               - progression_percentages (pd.Series): Percentages of progression categories.
               - progression_counts (pd.Series): Absolute counts of progression categories.
               - progression_students_by_category (dict): Dictionary where keys are categories and values are lists of Leerlingnummers.
               Returns (pd.Series([], dtype=float), pd.Series([], dtype=int), {}) if no students match the criteria.
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
        return pd.DataFrame(columns=['Aantallen', 'Percentage'])

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
        return pd.DataFrame(columns=['Aantallen', 'Percentage'])

    transitions_df['Progression'] = transitions_df.apply(categorize_progression, axis=1)

    # Calculate percentages and counts
    total_students = len(transitions_df)
    if total_students == 0:
        return pd.DataFrame(columns=['Aantallen', 'Percentage'])

    progression_counts = transitions_df['Progression'].value_counts()
    progression_percentages = (progression_counts / total_students) * 100

    # Create dictionary of Leerlingnummers by progression category
    progression_students_by_category = transitions_df.groupby('Progression')['Leerlingnummer'].unique().apply(list).to_dict()

    # Ensure all categories are present, even if 0% or 0 count
    all_categories = ['Doorstroom', 'Afstroom', 'Doublure', 'Other', 'No Data (Dropout/Missing)']
    if leerfase_vergelijk:
        all_categories.append(f'To {leerfase_vergelijk}')

    for category in all_categories:
        if category not in progression_percentages.index:
            progression_percentages[category] = 0.0
        if category not in progression_counts.index:
            progression_counts[category] = 0
        if category not in progression_students_by_category:
            progression_students_by_category[category] = []
    #progression_counts=pd.DataFrame(progression_counts)
    #progression_counts.rename(columns={'count': 'aantallen'}, inplace=True))
    result = pd.concat([progression_counts, progression_percentages], axis=1)
    result.columns = ['Aantallen','Percentage']
    result["Percentage"]=result["Percentage"].round(0).astype(int)
    result["Percentage"] = result["Percentage"].astype(str) + "%"
    return result.sort_index()#, progression_counts.sort_index(), progression_students_by_category

def analyze_three_year_leerfase_transitions(df, schooljaar_start, schooljaar_eind, leerfase_start,
                                            leerlingnummer_filter=None, tekortpunten_bucket_filter=None):
    """
    Analyzes 'Leerfase (afk)' transitions for students over three consecutive school years.
    Shows up to three transitions, even if fewer are available consecutively.

    Args:
        df (pd.DataFrame): The input DataFrame, expected to be sorted by 'Leerlingnummer' and 'Schooljaar'.
                           It must contain 'Leerlingnummer', 'Schooljaar', and 'Leerfase (afk)' columns.
        schooljaar_start (int): The starting school year (inclusive) for the analysis.
        schooljaar_eind (int): The ending school year (inclusive) for the analysis.
        leerfase_start (str): The specific 'Leerfase (afk)' from which to track transitions.
        leerlingnummer_filter (int or list, optional): A single 'Leerlingnummer' or a list of 'Leerlingnummer's
                                                       to filter the analysis. Defaults to None (all students).
        tekortpunten_bucket_filter (list, optional): A list of 'Tekortpunten_Bucket' categories to filter.
                                                   Defaults to None (all buckets).

    Returns:
        pd.Series: A Series with three-year transition strings as index and counts as values.
                   (e.g., "v5 -> v6", "v5 -> v6 -> Geslaagd", or "v5 -> v5_doublure").
    """
    # Filter students who were in the leerfase_start within the specified year range.
    initial_phase_students_df = df[
        (df['Schooljaar'] >= schooljaar_start) &
        (df['Schooljaar'] <= schooljaar_eind) &
        (df['Leerfase (afk)'] == leerfase_start)
        ].copy()  # Use .copy() to avoid SettingWithCopyWarning

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        initial_phase_students_df = initial_phase_students_df[
            initial_phase_students_df['Leerlingnummer'].isin(leerlingnummer_filter)
        ]

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        initial_phase_students_df = initial_phase_students_df[
            initial_phase_students_df['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)
        ]

    # Get unique Leerlingnummer's from the filtered initial phase students
    relevant_leerlingnummers = initial_phase_students_df['Leerlingnummer'].unique()

    if len(relevant_leerlingnummers) == 0:
        # st.warning(f"No students found in '{leerfase_start}' between {schooljaar_start}-{schooljaar_eind} (or matching filter).")
        return pd.Series([], dtype=int)

    # Get ALL records for these relevant students.
    student_records = df[df['Leerlingnummer'].isin(relevant_leerlingnummers)].copy()
    student_records = student_records.sort_values(by=['Leerlingnummer', 'Schooljaar'])

    # Calculate the next two 'Leerfase (afk)' and 'Schooljaar' for each student
    student_records['next_leerfase_1'] = student_records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-1)
    student_records['next_schooljaar_1'] = student_records.groupby('Leerlingnummer')['Schooljaar'].shift(-1)
    student_records['next_leerfase_2'] = student_records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-2)
    student_records['next_schooljaar_2'] = student_records.groupby('Leerlingnummer')['Schooljaar'].shift(-2)
    student_records['next_leerfase_3'] = student_records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-3)
    student_records['next_schooljaar_3'] = student_records.groupby('Leerlingnummer')['Schooljaar'].shift(-3)

    # Filter for starting points within the specified range
    transitions_df = student_records[
        (student_records['Leerfase (afk)'] == leerfase_start) &
        (student_records['Schooljaar'] >= schooljaar_start) &
        (student_records['Schooljaar'] <= schooljaar_eind)
        ].copy()

    # Apply tekortpunten_bucket_filter to the starting points again if specified
    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        transitions_df = transitions_df[
            transitions_df['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)
        ]

    if transitions_df.empty:
        # st.warning(f"No starting points found from '{leerfase_start}' between {schooljaar_start}-{schooljaar_eind} (or matching filter).")
        return pd.Series([], dtype=int)

    # Initialize the transition string with the starting phase and its bucket
    transitions_df['Transition'] = transitions_df['Leerfase (afk)'] + ' [' + transitions_df[
        'Tekortpunten_Bucket'].astype(str) + ']'

    # Conditionally add the first transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) & (
            transitions_df['next_leerfase_1'].notna())&
        (transitions_df['next_leerfase_1'] != "Doorstroom")
        ,
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_1'],
        transitions_df['Transition']
    )

    # Conditionally add the second transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) &
        (transitions_df['next_schooljaar_2'] == transitions_df['Schooljaar'] + 2) &
        (transitions_df['next_leerfase_2'].notna())&
        (transitions_df['next_leerfase_2'] != "Doorstroom")
        ,
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_2'],
        transitions_df['Transition']
    )

    # Conditionally add the third transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) &
        (transitions_df['next_schooljaar_2'] == transitions_df['Schooljaar'] + 2) &
        (transitions_df['next_schooljaar_3'] == transitions_df['Schooljaar'] + 3) &
        (transitions_df['next_leerfase_3'].notna())&
        (transitions_df['next_leerfase_3'] != "Doorstroom")
        ,
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_3'],
        transitions_df['Transition']
    )

    # Aantal the occurrences of each unique transition
    transition_counts = transitions_df['Transition'].value_counts()

    return transition_counts

def counts_with_percentages(transition_counts: pd.Series) -> pd.DataFrame:
    """
    Zet een Series met aantallen om naar een DataFrame met aantallen + percentages
    """
    total = transition_counts.sum()

    df_out = (
        transition_counts
        .rename("Aantal")
        .to_frame()
    )

    df_out["Percentage"] = (df_out["Aantal"] / total * 100).round(0).astype(int)
    df_out["Percentage"] = df_out["Percentage"].astype(str) + "%"
    return df_out


def prepare_sankey_data(transition_counts):
    """
    Processes transition counts to prepare data for a Sankey diagram.

    Args:
        transition_counts (pd.Series): A Series where the index contains transition strings
                                       (e.g., 'h3 -> h4 -> Geslaagd') and values are the counts.

    Returns:
        tuple: A tuple containing four lists: (labels, source, target, value)
               - labels (list): Unique node labels.
               - source (list): Source node indices for links.
               - target (list): Target node indices for links.
               - value (list): Values (counts) for links.
    """
    all_labels = []
    for transition_string in transition_counts.index:
        # Split on ' -> ' to get individual nodes
        steps = transition_string.split(' -> ')
        all_labels.extend(steps)

    # Remove duplicates and sort for consistent node ordering
    labels = sorted(list(set(all_labels)))

    # Create a mapping from label to its index
    label_to_index = {label: i for i, label in enumerate(labels)}

    source = []
    target = []
    value = []

    for transition_string, Aantal in transition_counts.items():
        steps = transition_string.split(' -> ')
        for i in range(len(steps) - 1):
            step_current = steps[i]
            step_next = steps[i + 1]

            # Get indices for source and target
            source_index = label_to_index[step_current]
            target_index = label_to_index[step_next]

            source.append(source_index)
            target.append(target_index)
            value.append(Aantal)

    # Aggregate values for identical source-target links
    sankey_links_df = pd.DataFrame({
        'source': source,
        'target': target,
        'value': value
    })

    # Group by source and target and sum the values
    aggregated_links = sankey_links_df.groupby(['source', 'target'])['value'].sum().reset_index()

    return labels, aggregated_links['source'].tolist(), aggregated_links['target'].tolist(), aggregated_links[
        'value'].tolist()


def plot_sankey_diagram(labels, source, target, value, title="Doorstroom leerlingen (3-jaar vooruit)"):
    """
    Generates an interactive Sankey diagram.

    Args:
        labels (list): Unique node labels.
        source (list): Source node indices for links.
        target (list): Target node indices for links.
        value (list): Values (counts) for links.
        title (str): Title for the Sankey diagram.

    Returns:
        go.Figure: A Plotly Figure object representing the Sankey diagram.
    """
    fig = go.Figure(data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                # color=["blue", "blue", "red", "red", ...] # Example: assign colors to nodes
            ),
            link=dict(
                source=source,  # indices correspond to labels, e.g. 0 = 'A', 1 = 'B', 2 = 'C'
                target=target,
                value=value,
                # color=["rgba(0,0,255,0.2)", ...] # Example: assign colors to links
            )
        )
    ])

    fig.update_layout(title_text=title, font_size=10)
    # fig.show() # In Streamlit, use st.plotly_chart(fig)
    return fig



def analyze_flexible_leerfase_transitions(
    df,
    schooljaar_start,
    schooljaar_eind,
    leerfase_start,
    n_years_forward=3,
    include_year_back=False,
    leerlingnummer_filter=None,
    tekortpunten_bucket_filter=None,
):
    """
    Analyzeert 'Leerfase (afk)' transities voor leerlingen over een flexibel aantal
    schooljaren (1-6 jaar vooruit, optioneel 1 jaar terug).

    Args:
        df (pd.DataFrame): De input DataFrame gesorteerd op 'Leerlingnummer' en 'Schooljaar'.
        schooljaar_start (int): Beginjaar (inclusief) voor de analyse.
        schooljaar_eind (int): Eindjaar (inclusief) voor de analyse.
        leerfase_start (str): De startleerfase van waaruit gevolgd wordt.
        n_years_forward (int): Aantal jaren vooruit (1 t/m 6).
        include_year_back (bool): Als True, ook leerfase van 1 jaar eerder tonen.
        leerlingnummer_filter: Optioneel filter op leerlingnummers.
        tekortpunten_bucket_filter (list): Optioneel filter op tekortpunten-buckets.

    Returns:
        pd.Series: Transition-string als index, aantallen als waarden.
    """
    n_years_forward = max(1, min(6, n_years_forward))

    # --- Filter startpunten ---
    initial_df = df[
        (df['Schooljaar'] >= schooljaar_start) &
        (df['Schooljaar'] <= schooljaar_eind) &
        (df['Leerfase (afk)'] == leerfase_start)
    ].copy()

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        initial_df = initial_df[initial_df['Leerlingnummer'].isin(leerlingnummer_filter)]

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        initial_df = initial_df[initial_df['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)]

    relevant_ids = initial_df['Leerlingnummer'].unique()
    if len(relevant_ids) == 0:
        return pd.Series([], dtype=int)

    # --- Haal alle records op voor deze leerlingen ---
    records = df[df['Leerlingnummer'].isin(relevant_ids)].copy()
    records = records.sort_values(by=['Leerlingnummer', 'Schooljaar'])

    # Shifts vooruit
    for i in range(1, n_years_forward + 1):
        records[f'next_leerfase_{i}'] = records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-i)
        records[f'next_schooljaar_{i}'] = records.groupby('Leerlingnummer')['Schooljaar'].shift(-i)

    # Shift 1 jaar terug
    if include_year_back:
        records['prev_leerfase'] = records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(1)
        records['prev_schooljaar'] = records.groupby('Leerlingnummer')['Schooljaar'].shift(1)

    # --- Filter op startpunten ---
    trans = records[
        (records['Leerfase (afk)'] == leerfase_start) &
        (records['Schooljaar'] >= schooljaar_start) &
        (records['Schooljaar'] <= schooljaar_eind)
    ].copy()

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        trans = trans[trans['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)]

    if trans.empty:
        return pd.Series([], dtype=int)

    # --- Bouw Transition-string op ---
    # Optioneel: voeg 1 jaar terug toe als prefix
    if include_year_back:
        trans['Transition'] = np.where(
            (trans['prev_schooljaar'] == trans['Schooljaar'] - 1) &
            trans['prev_leerfase'].notna(),
            trans['prev_leerfase'] + ' -> ',
            '(geen data) -> '
        )
        trans['Transition'] = (
            trans['Transition'] +
            trans['Leerfase (afk)'] +
            ' [' + trans['Tekortpunten_Bucket'].astype(str) + ']'
        )
    else:
        trans['Transition'] = (
            trans['Leerfase (afk)'] +
            ' [' + trans['Tekortpunten_Bucket'].astype(str) + ']'
        )

    # Voeg jaren vooruit toe
    for i in range(1, n_years_forward + 1):
        cond = trans[f'next_schooljaar_{i}'] == trans['Schooljaar'] + i
        # Controleer ook dat alle tussenliggende jaren aanwezig zijn
        for j in range(1, i):
            cond = cond & (trans[f'next_schooljaar_{j}'] == trans['Schooljaar'] + j)
        cond = cond & trans[f'next_leerfase_{i}'].notna()
        cond = cond & (trans[f'next_leerfase_{i}'] != 'Doorstroom')

        trans['Transition'] = np.where(
            cond,
            trans['Transition'] + ' -> ' + trans[f'next_leerfase_{i}'],
            trans['Transition']
        )

    transition_counts = trans['Transition'].value_counts()
    return transition_counts


def analyze_flexible_without_basisschooladvies(
        df,
        schooljaar_start,
        schooljaar_eind,
        leerfase_start,
        n_years_forward=3,
        include_year_back=False,
        leerlingnummer_filter=None,
        tekortpunten_bucket_filter=None,
):
    """
    Analyzeert 'Leerfase (afk)' transities voor leerlingen over een flexibel aantal
    schooljaren (1-6 jaar vooruit, optioneel 1 jaar terug).

    Args:
        df (pd.DataFrame): De input DataFrame gesorteerd op 'Leerlingnummer' en 'Schooljaar'.
        schooljaar_start (int): Beginjaar (inclusief) voor de analyse.
        schooljaar_eind (int): Eindjaar (inclusief) voor de analyse.
        leerfase_start (str): De startleerfase van waaruit gevolgd wordt.
        n_years_forward (int): Aantal jaren vooruit (1 t/m 6).
        include_year_back (bool): Als True, ook leerfase van 1 jaar eerder tonen.
        leerlingnummer_filter: Optioneel filter op leerlingnummers.
        tekortpunten_bucket_filter (list): Optioneel filter op tekortpunten-buckets.

    Returns:
        pd.Series: Transition-string als index, aantallen als waarden.
    """
    n_years_forward = max(1, min(6, n_years_forward))

    # --- Filter startpunten ---
    initial_df = df[
        (df['Schooljaar'] >= schooljaar_start) &
        (df['Schooljaar'] <= schooljaar_eind) &
        (df['Leerfase (afk)'] == leerfase_start)
        ].copy()

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        initial_df = initial_df[initial_df['Leerlingnummer'].isin(leerlingnummer_filter)]

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        initial_df = initial_df[initial_df['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)]

    relevant_ids = initial_df['Leerlingnummer'].unique()
    if len(relevant_ids) == 0:
        return pd.Series([], dtype=int)

    # --- Haal alle records op voor deze leerlingen ---
    records = df[df['Leerlingnummer'].isin(relevant_ids)].copy()
    records = records.sort_values(by=['Leerlingnummer', 'Schooljaar'])

    # Shifts vooruit
    for i in range(1, n_years_forward + 1):
        records[f'next_leerfase_{i}'] = records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(-i)
        records[f'next_schooljaar_{i}'] = records.groupby('Leerlingnummer')['Schooljaar'].shift(-i)

    # Shift 1 jaar terug
    if include_year_back:
        records['prev_leerfase'] = records.groupby('Leerlingnummer')['Leerfase (afk)'].shift(1)
        records['prev_schooljaar'] = records.groupby('Leerlingnummer')['Schooljaar'].shift(1)

    # --- Filter op startpunten ---
    trans = records[
        (records['Leerfase (afk)'] == leerfase_start) &
        (records['Schooljaar'] >= schooljaar_start) &
        (records['Schooljaar'] <= schooljaar_eind)
        ].copy()

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        trans = trans[trans['Tekortpunten_Bucket'].isin(tekortpunten_bucket_filter)]

    if trans.empty:
        return pd.Series([], dtype=int)

    # --- Bouw Transition-string op ---
    # Optioneel: voeg 1 jaar terug toe als prefix
    if include_year_back:
        trans['Transition'] = np.where(
            (trans['prev_schooljaar'] == trans['Schooljaar'] - 1) &
            trans['prev_leerfase'].notna(),
            trans['prev_leerfase'] + ' -> ',
            '(geen data) -> '
        )
        trans['Transition'] = (
                trans['Transition'] +
                trans['Leerfase (afk)']
        )
    else:
        trans['Transition'] = (
                trans['Leerfase (afk)']
        )

    # Voeg jaren vooruit toe
    for i in range(1, n_years_forward + 1):
        cond = trans[f'next_schooljaar_{i}'] == trans['Schooljaar'] + i
        # Controleer ook dat alle tussenliggende jaren aanwezig zijn
        for j in range(1, i):
            cond = cond & (trans[f'next_schooljaar_{j}'] == trans['Schooljaar'] + j)
        cond = cond & trans[f'next_leerfase_{i}'].notna()
        cond = cond & (trans[f'next_leerfase_{i}'] != 'Doorstroom')

        trans['Transition'] = np.where(
            cond,
            trans['Transition'] + ' -> ' + trans[f'next_leerfase_{i}'],
            trans['Transition']
        )

    transition_counts = trans['Transition'].value_counts()
    return transition_counts


def analyze_flexible_transitions(
    df,
    schooljaar_start,
    schooljaar_eind,
    leerfase_start,
    jaren_vooruit=3,
    toon_jaar_terug=False,
    tekortpunten_bucket_filter=None,
    leerlingnummer_filter=None,
):
    """
    Analyseert leerfase-transities voor 1 t/m 6 jaar vooruit en optioneel 1 jaar terug.
    Retourneert een DataFrame met aantallen, percentages én een uitsplitsing per Basisschooladvies.

    Args:
        df: Volledige DataFrame (gesorteerd op Leerlingnummer + Schooljaar).
        schooljaar_start / schooljaar_eind: Bereik van startjaren.
        leerfase_start: Leerfase waaruit gevolgd wordt.
        jaren_vooruit: 1–6 jaar vooruit kijken.
        toon_jaar_terug: Voeg het vorige jaar (Leerfase (afk) vorig schooljaar) toe als prefix.
        tekortpunten_bucket_filter: Optioneel filter op Tekortpunten_Bucket.
        leerlingnummer_filter: Optioneel filter op Leerlingnummer(s).

    Returns:
        pd.DataFrame met kolommen: Transitie, Aantal, Percentage, en één kolom per BSA-waarde.
    """
    # --- 1. Startselectie ---
    mask = (
        (df["Schooljaar"] >= schooljaar_start)
        & (df["Schooljaar"] <= schooljaar_eind)
        & (df["Leerfase (afk)"] == leerfase_start)
    )
    start_df = df[mask].copy()

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        start_df = start_df[start_df["Leerlingnummer"].isin(leerlingnummer_filter)]

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        start_df = start_df[start_df["Tekortpunten_Bucket"].isin(tekortpunten_bucket_filter)]

    relevant_ids = start_df["Leerlingnummer"].unique()
    if len(relevant_ids) == 0:
        return pd.DataFrame()

    # --- 2. Alle records voor deze leerlingen ---
    rec = df[df["Leerlingnummer"].isin(relevant_ids)].copy()
    rec = rec.sort_values(["Leerlingnummer", "Schooljaar"])

    # Shift: toekomst jaar 1..N
    for i in range(1, jaren_vooruit + 1):
        rec[f"next_lf_{i}"] = rec.groupby("Leerlingnummer")["Leerfase (afk)"].shift(-i)
        rec[f"next_sj_{i}"] = rec.groupby("Leerlingnummer")["Schooljaar"].shift(-i)

    # --- 3. Filter op startpunten ---
    trans = rec[
        (rec["Leerfase (afk)"] == leerfase_start)
        & (rec["Schooljaar"] >= schooljaar_start)
        & (rec["Schooljaar"] <= schooljaar_eind)
    ].copy()

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        trans = trans[trans["Tekortpunten_Bucket"].isin(tekortpunten_bucket_filter)]

    if trans.empty:
        return pd.DataFrame()

    # --- 4. Bouw transitie-string ---
    # Optioneel: prefix met vorig jaar
    if toon_jaar_terug:
        prev_lf = trans["Leerfase (afk) vorig schooljaar"].fillna("onbekend").astype(str)
        trans["Transitie"] = prev_lf + " -> " + trans["Leerfase (afk)"]
    else:
        trans["Transitie"] = trans["Leerfase (afk)"]

    # Voeg bucket toe
    trans["Transitie"] = (
        trans["Transitie"] #+ " [" + trans["Tekortpunten_Bucket"].astype(str) + "]"
    )

    # Voeg jaren vooruit toe
    for i in range(1, jaren_vooruit + 1):
        sj_ok = trans[f"next_sj_{i}"] == trans["Schooljaar"] + i
        lf_ok = trans[f"next_lf_{i}"].notna() & (trans[f"next_lf_{i}"] != "Doorstroom")
        can_extend = sj_ok & lf_ok

        # Mag alleen uitbreiden als vorige stap ook aanwezig was (aaneengesloten reeks)
        if i > 1:
            prev_ok = trans[f"next_sj_{i-1}"] == trans["Schooljaar"] + (i - 1)
            can_extend = can_extend & prev_ok

        trans["Transitie"] = np.where(
            can_extend,
            trans["Transitie"] + " -> " + trans[f"next_lf_{i}"],
            trans["Transitie"],
        )

    # --- 5. Aggregatie ---
    total = len(trans)
    counts = trans["Transitie"].value_counts().rename("Aantal").to_frame()
    counts["Percentage"] = (counts["Aantal"] / total * 100).round(1).astype(str) + "%"

    # --- 6. Basisschooladvies uitsplitsing per transitie ---
    bsa_col = "Basisschooladvies"
    if bsa_col in trans.columns:
        bsa_pivot = (
            trans.groupby("Transitie")[bsa_col]
            .value_counts()
            .unstack(fill_value=0)
        )
        # Sorteer BSA-kolommen alfabetisch
        bsa_pivot = bsa_pivot.reindex(sorted(bsa_pivot.columns), axis=1)
        result = counts.join(bsa_pivot, how="left")
    else:
        result = counts

    return result

def analyze_flexible_transitions_small(
        df,
        schooljaar_start,
        schooljaar_eind,
        leerfase_start,
        jaren_vooruit=3,
        toon_jaar_terug=False,
        tekortpunten_bucket_filter=None,
        leerlingnummer_filter=None,
):
    """
    Analyseert leerfase-transities voor 1 t/m 6 jaar vooruit en optioneel 1 jaar terug.
    Retourneert een DataFrame met aantallen, percentages én een uitsplitsing per Basisschooladvies.

    Args:
        df: Volledige DataFrame (gesorteerd op Leerlingnummer + Schooljaar).
        schooljaar_start / schooljaar_eind: Bereik van startjaren.
        leerfase_start: Leerfase waaruit gevolgd wordt.
        jaren_vooruit: 1–6 jaar vooruit kijken.
        toon_jaar_terug: Voeg het vorige jaar (Leerfase (afk) vorig schooljaar) toe als prefix.
        tekortpunten_bucket_filter: Optioneel filter op Tekortpunten_Bucket.
        leerlingnummer_filter: Optioneel filter op Leerlingnummer(s).

    Returns:
        pd.DataFrame met kolommen: Transitie, Aantal, Percentage, en één kolom per BSA-waarde.
    """
    # --- 1. Startselectie ---
    mask = (
            (df["Schooljaar"] >= schooljaar_start)
            & (df["Schooljaar"] <= schooljaar_eind)
            & (df["Leerfase (afk)"] == leerfase_start)
    )
    start_df = df[mask].copy()

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        start_df = start_df[start_df["Leerlingnummer"].isin(leerlingnummer_filter)]

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        start_df = start_df[start_df["Tekortpunten_Bucket"].isin(tekortpunten_bucket_filter)]

    relevant_ids = start_df["Leerlingnummer"].unique()
    if len(relevant_ids) == 0:
        return pd.DataFrame()

    # --- 2. Alle records voor deze leerlingen ---
    rec = df[df["Leerlingnummer"].isin(relevant_ids)].copy()
    rec = rec.sort_values(["Leerlingnummer", "Schooljaar"])

    # Shift: toekomst jaar 1..N
    for i in range(1, jaren_vooruit + 1):
        rec[f"next_lf_{i}"] = rec.groupby("Leerlingnummer")["Leerfase (afk)"].shift(-i)
        rec[f"next_sj_{i}"] = rec.groupby("Leerlingnummer")["Schooljaar"].shift(-i)

    # --- 3. Filter op startpunten ---
    trans = rec[
        (rec["Leerfase (afk)"] == leerfase_start)
        & (rec["Schooljaar"] >= schooljaar_start)
        & (rec["Schooljaar"] <= schooljaar_eind)
        ].copy()

    if tekortpunten_bucket_filter is not None and len(tekortpunten_bucket_filter) > 0:
        trans = trans[trans["Tekortpunten_Bucket"].isin(tekortpunten_bucket_filter)]

    if trans.empty:
        return pd.DataFrame()

    # --- 4. Bouw transitie-string ---
    # Optioneel: prefix met vorig jaar
    if toon_jaar_terug:
        prev_lf = trans["Leerfase (afk) vorig schooljaar"].fillna("onbekend").astype(str)
        trans["Transitie"] = prev_lf + " -> " + trans["Leerfase (afk)"]
    else:
        trans["Transitie"] = trans["Leerfase (afk)"]

    # Voeg bucket toe
    trans["Transitie"] = (
            trans["Transitie"]
    )

    # Voeg jaren vooruit toe
    for i in range(1, jaren_vooruit + 1):
        sj_ok = trans[f"next_sj_{i}"] == trans["Schooljaar"] + i
        lf_ok = trans[f"next_lf_{i}"].notna() & (trans[f"next_lf_{i}"] != "Doorstroom")
        can_extend = sj_ok & lf_ok

        # Mag alleen uitbreiden als vorige stap ook aanwezig was (aaneengesloten reeks)
        if i > 1:
            prev_ok = trans[f"next_sj_{i - 1}"] == trans["Schooljaar"] + (i - 1)
            can_extend = can_extend & prev_ok

        trans["Transitie"] = np.where(
            can_extend,
            trans["Transitie"] + " -> " + trans[f"next_lf_{i}"],
            trans["Transitie"],
        )

    # --- 5. Aggregatie ---
    total = len(trans)
    counts = trans["Transitie"].value_counts().rename("Aantal").to_frame()
    counts["Percentage"] = (counts["Aantal"] / total * 100).round(1).astype(str) + "%"

    # # --- 6. Basisschooladvies uitsplitsing per transitie ---
    # bsa_col = "Basisschooladvies"
    # if bsa_col in trans.columns:
    #     bsa_pivot = (
    #         trans.groupby("Transitie")[bsa_col]
    #         .value_counts()
    #         .unstack(fill_value=0)
    #     )
    #     # Sorteer BSA-kolommen alfabetisch
    #     bsa_pivot = bsa_pivot.reindex(sorted(bsa_pivot.columns), axis=1)
    #     result = counts.join(bsa_pivot, how="left")
    # else:
    result = counts

    return result