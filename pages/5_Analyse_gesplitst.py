import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from components.helper import *


# --- Helper Functions ---

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
        return pd.Series([], dtype=float), pd.Series([], dtype=int), {}

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
        return pd.Series([], dtype=float), pd.Series([], dtype=int), {}

    transitions_df['Progression'] = transitions_df.apply(categorize_progression, axis=1)

    # Calculate percentages and counts
    total_students = len(transitions_df)
    if total_students == 0:
        return pd.Series([], dtype=float), pd.Series([], dtype=int), {}

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

    return progression_percentages.sort_index(), progression_counts.sort_index(), progression_students_by_category

def analyze_three_year_leerfase_transitions(df, schooljaar_start, schooljaar_eind, leerfase_start, leerlingnummer_filter=None):
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

    Returns:
        pd.Series: A Series with three-year transition strings as index and counts as values.
                   (e.g., "v5 -> v6", "v5 -> v6 -> h1", or "v5 -> v6 -> h1 -> h2").
    """
    # Filter students who were in the leerfase_start within the specified year range.
    initial_phase_students_df = df[
        (df['Schooljaar'] >= schooljaar_start) &
        (df['Schooljaar'] <= schooljaar_eind) &
        (df['Leerfase (afk)'] == leerfase_start)
    ].copy() # Use .copy() to avoid SettingWithCopyWarning

    if leerlingnummer_filter is not None:
        if isinstance(leerlingnummer_filter, int):
            leerlingnummer_filter = [leerlingnummer_filter]
        initial_phase_students_df = initial_phase_students_df[
            initial_phase_students_df['Leerlingnummer'].isin(leerlingnummer_filter)
        ]

    # Get unique Leerlingnummer's from the filtered initial phase students
    relevant_leerlingnummers = initial_phase_students_df['Leerlingnummer'].unique()

    if len(relevant_leerlingnummers) == 0:
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

    if transitions_df.empty:
        return pd.Series([], dtype=int)

    # Initialize the transition string with the starting phase
    transitions_df['Transition'] = transitions_df['Leerfase (afk)']

    # Conditionally add the first transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) & (transitions_df['next_leerfase_1'].notna()),
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_1'],
        transitions_df['Transition']
    )

    # Conditionally add the second transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) &
        (transitions_df['next_schooljaar_2'] == transitions_df['Schooljaar'] + 2) &
        (transitions_df['next_leerfase_2'].notna()),
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_2'],
        transitions_df['Transition']
    )

    # Conditionally add the third transition
    transitions_df['Transition'] = np.where(
        (transitions_df['next_schooljaar_1'] == transitions_df['Schooljaar'] + 1) &
        (transitions_df['next_schooljaar_2'] == transitions_df['Schooljaar'] + 2) &
        (transitions_df['next_schooljaar_3'] == transitions_df['Schooljaar'] + 3) &
        (transitions_df['next_leerfase_3'].notna()),
        transitions_df['Transition'] + ' -> ' + transitions_df['next_leerfase_3'],
        transitions_df['Transition']
    )

    # Count the occurrences of each unique transition
    transition_counts = transitions_df['Transition'].value_counts()

    return transition_counts

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

    for transition_string, count in transition_counts.items():
        steps = transition_string.split(' -> ')
        for i in range(len(steps) - 1):
            step_current = steps[i]
            step_next = steps[i+1]

            # Get indices for source and target
            source_index = label_to_index[step_current]
            target_index = label_to_index[step_next]

            source.append(source_index)
            target.append(target_index)
            value.append(count)

    # Aggregate values for identical source-target links
    sankey_links_df = pd.DataFrame({
        'source': source,
        'target': target,
        'value': value
    })

    # Group by source and target and sum the values
    aggregated_links = sankey_links_df.groupby(['source', 'target'])['value'].sum().reset_index()

    return labels, aggregated_links['source'].tolist(), aggregated_links['target'].tolist(), aggregated_links['value'].tolist()

def plot_sankey_diagram(labels, source, target, value, title="Doorstroom van leerlingen (3-Year Transitions)"):
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
                source=source, # indices correspond to labels, e.g. 0 = 'A', 1 = 'B', 2 = 'C'
                target=target,
                value=value,
                # color=["rgba(0,0,255,0.2)", ...] # Example: assign colors to links
            )
        )
    ])

    fig.update_layout(title_text=title, font_size=10)
    # fig.show() # In Streamlit, use st.plotly_chart(fig)
    return fig

# --- Streamlit App Layout ---
st.set_page_config(layout="wide")
from components.data import load_data
from components.styling import apply_styling
from components.doorstroom_functions import examenklas_noot
apply_styling()

st.title("Selecteer een groep leerlingen om doorstroom te bekijken")

check_password()

# --- Data Loading ---

updated_df = load_data()

# --- Sidebar for Filters ---
#st.sidebar.header("Analysis Filters")

# Schooljaar_start and Schooljaar_eind
all_schoolyears = sorted(updated_df['Schooljaar'].unique().tolist())
if len(all_schoolyears) > 1:
    default_schooljaar_start_idx = 0 # First year
    default_schooljaar_end_idx = min(2, len(all_schoolyears) - 1) # Third year, or last if fewer than 3
else:
    default_schooljaar_start_idx = 0
    default_schooljaar_end_idx = 0

schooljaar_start = st.selectbox(
    "Select Start Schooljaar:",
    options=all_schoolyears,
    index=5
)
schooljaar_eind = st.selectbox(
    "Select End Schooljaar:",
    options=all_schoolyears,
    index=5
)

if schooljaar_start > schooljaar_eind:
    st.sidebar.error("Start Schooljaar cannot be after End Schooljaar.")
    st.stop()

# Leerfase_start
all_leerfases = sorted(updated_df['Leerfase (afk)'].dropna().unique().tolist())
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
all_leerfases.pop(0)
leerfase_start = st.selectbox(
    "Select Start Leerfase (afk):",
    options=all_leerfases
)

# Leerfase_vergelijk (new filter)
leerfase_vergelijk_options = ['None'] #+ all_leerfases # Add 'None' option
leerfase_vergelijk_selection = st.selectbox(
    "Vergelijk (nog niet mogelijk):",
    options=leerfase_vergelijk_options,
    index=0 # Default to 'None'
)
leerfase_vergelijk = None if leerfase_vergelijk_selection == 'None' else leerfase_vergelijk_selection

# Tekortpunten_Bucket filter
all_tekortpunten_buckets = sorted(updated_df['Tekortpunten_Bucket'].dropna().unique().tolist())
selected_tekortpunten_buckets = st.multiselect(
    "Select Tekortpunten Bucket(s) (Start Year):",
    options=all_tekortpunten_buckets,
    default=all_tekortpunten_buckets # Default to all selected
)

# --- Main Content ---
st.subheader(f"Doorstroom van '{leerfase_start}' ({schooljaar_start}-{schooljaar_eind}' met tekortpunten '{selected_tekortpunten_buckets})")

if st.button("Run Analysis"):
    if updated_df is not None:
        with st.spinner("Running analysis and generating results..."):
            # --- One-Year Progression Analysis ---
            progression_percentages, progression_counts, progression_students_by_category = analyze_next_leerfase(
                updated_df,
                schooljaar_start=schooljaar_start,
                schooljaar_eind=schooljaar_eind,
                leerfase_start=leerfase_start,
                tekortpunten_bucket_filter=selected_tekortpunten_buckets,
                leerfase_vergelijk=leerfase_vergelijk
            )

            if not progression_percentages.empty:
                st.write("### One-Year Progression Percentages")
                st.dataframe(progression_percentages.reset_index().rename(columns={'index': 'Progression Category', 0: 'Percentage (%)'}))

                st.write("### One-Year Progression Counts")
                st.dataframe(progression_counts.reset_index().rename(columns={'index': 'Progression Category', 0: 'Count'}))
                examenklas_noot(leerfase_start)
            else:
                st.info("No one-year transitions found for the selected criteria.")

            # --- Three-Year Sankey Diagram for each category ---
            if progression_students_by_category:
                st.write("### Three-Year Progression Sankey Diagrams by Category")
                for category, leerlingnummers in progression_students_by_category.items():
                    if leerlingnummers:
                        st.markdown(f"#### {category} (Count: {len(leerlingnummers)})")
                        three_year_transition_counts = analyze_three_year_leerfase_transitions(
                            updated_df,
                            schooljaar_start=schooljaar_start,
                            schooljaar_eind=schooljaar_eind, # Sankey should cover the whole range
                            leerfase_start=leerfase_start,
                            leerlingnummer_filter=leerlingnummers
                        )

                        if not three_year_transition_counts.empty:
                            st.write(f"##### Transitions for {category}")
                            st.dataframe(three_year_transition_counts)

                            labels, source, target, value = prepare_sankey_data(three_year_transition_counts)
                            if labels and source and target and value:
                                sankey_title = f"3-Year Progression: {leerfase_start} ({schooljaar_start}-{schooljaar_eind}) - Category: {category}"
                                fig = plot_sankey_diagram(labels, source, target, value, title=sankey_title)
                                st.plotly_chart(fig, width="stretch")
                            else:
                                st.warning(f"Not enough data to generate a Sankey diagram for '{category}' with the selected filters.")
                        else:
                            st.info(f"No three-year transitions found for '{category}' with the selected filters.")
            else:
                st.info("No students found to generate three-year progression diagrams.")
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