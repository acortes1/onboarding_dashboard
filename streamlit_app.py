import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # For Sankey if added later, and more control
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta # For MoM calculation
import gspread
from google.oauth2.service_account import Credentials
import time
import numpy as np

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.0",
    page_icon="🚀",
    layout="wide"
)

# --- Custom Styling (Gold Accents) ---
GOLD_ACCENT_COLOR = "#FFD700" # Gold
PRIMARY_TEXT_COLOR = "#FFFFFF" # White
SECONDARY_TEXT_COLOR = "#B0B0B0" # Light Gray
BACKGROUND_COLOR = "#0E1117" # Streamlit Dark Default
PLOT_BG_COLOR = "rgba(0,0,0,0)" # Transparent for plots

st.markdown(f"""
<style>
    .stApp > header {{
        background-color: transparent;
    }}
    h1 {{
        color: {GOLD_ACCENT_COLOR};
        text-align: center;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
    }}
    h2, h3 {{
        color: {GOLD_ACCENT_COLOR};
        border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important;
        padding-bottom: 0.3em;
    }}
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{
        color: {PRIMARY_TEXT_COLOR} !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        font-size: 1.85rem;
    }}
    .streamlit-expanderHeader {{
        color: {GOLD_ACCENT_COLOR} !important;
        font-weight: bold;
    }}
    .stDataFrame {{
        border: 1px solid #333;
    }}
    /* Sidebar text color */
    .css-1d391kg p, .css- F_1U7P p {{
        color: {PRIMARY_TEXT_COLOR} !important;
    }}
    /* Tab styling */
    button[data-baseweb="tab"] {{
        background-color: transparent !important;
        color: {SECONDARY_TEXT_COLOR} !important;
        border-bottom: 2px solid transparent !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {GOLD_ACCENT_COLOR} !important;
        border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important;
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)


# --- Google Sheets Authentication and Data Loading ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread(secrets_dict=None):
    try:
        if secrets_dict:
            creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except FileNotFoundError:
        st.error("Auth Error: 'google_credentials.json' not found. Place it in root or set Streamlit Secrets.")
        return None
    except Exception as e:
        st.error(f"Google Sheets Auth Error: {e}")
        return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    common_formats = [
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
        '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d',
        '%m/%d/%Y', '%d/%m/%Y',
    ]
    if dates.isnull().sum() > len(series) * 0.7: # If >70% are NaT, try others
        for fmt in common_formats:
            temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
            if temp_dates.notnull().sum() > dates.notnull().sum():
                dates = temp_dates
            if dates.notnull().all(): break
    return dates

@st.cache_data(ttl=600)
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    gc = authenticate_gspread(st.secrets.get("gcp_service_account"))
    if gc is None: return pd.DataFrame()

    try:
        spreadsheet = gc.open_by_url(sheet_url_or_name) if "docs.google.com" in sheet_url_or_name else gc.open(sheet_url_or_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1)
        df = pd.DataFrame(data)
        st.sidebar.success(f"Loaded {len(df)} records.") # Feedback in sidebar
        if df.empty:
            st.warning("No data records found in the Google Sheet.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading from Google Sheet: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_columns = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
    for col, new_col in date_columns.items():
        if col in df.columns:
            df[f'{col}_str'] = df[col].astype(str).str.replace('Z', '', regex=False).str.replace('\n', '', regex=False).str.strip()
            df[new_col] = robust_to_datetime(df[f'{col}_str'])
            if df[new_col].isnull().all() and not df[f'{col}_str'].isin(['', 'None', 'nan', 'NaT']).all():
                st.warning(f"Could not parse any dates in '{col}'. Check formats.")
            if col == 'onboardingDate':
                df['onboarding_date_only'] = df[new_col].dt.date
        else:
            st.warning(f"Date column '{col}' not found.")
            df[new_col] = pd.NaT
            if col == 'onboardingDate': df['onboarding_date_only'] = pd.NaT

    if 'deliveryDate_dt' in df and 'confirmationTimestamp_dt' in df:
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')
        valid_mask = df['deliveryDate_dt'].notna() & df['confirmationTimestamp_dt'].notna()
        df['days_to_confirmation'] = pd.NA
        df.loc[valid_mask, 'days_to_confirmation'] = (df.loc[valid_mask, 'confirmationTimestamp_dt'] - df.loc[valid_mask, 'deliveryDate_dt']).dt.days
    else:
        df['days_to_confirmation'] = pd.NA

    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else: df['score'] = pd.NA
    return df

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input, period_name=""):
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA

    total = len(df_input)
    success_rate = (df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0] / total * 100) if total > 0 and 'status' in df_input else 0.0
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean() if 'score' in df_input else pd.NA
    avg_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean() if 'days_to_confirmation' in df_input else pd.NA
    return total, success_rate, avg_score, avg_days

def get_default_date_range(df_col):
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today
    min_data_date, max_data_date = None, None

    if df_col is not None and not df_col.empty:
        # Convert to date objects safely
        date_objects = pd.to_datetime(df_col, errors='coerce').dt.date
        valid_dates = date_objects.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min()
            max_data_date = valid_dates.max()

            default_start = max(default_start, min_data_date)
            default_end = min(default_end, max_data_date)
            if default_start > default_end : # If current month is outside data range
                default_start = min_data_date
                default_end = max_data_date

    return default_start, default_end, min_data_date, max_data_date


# --- Initialize Session State ---
default_sheet_url = st.secrets.get("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing")
default_worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME", "Sheet1")

if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()

# Filter defaults - will be set after data load for date range
if 'date_range_filter' not in st.session_state: st.session_state.date_range_filter = (date.today().replace(day=1), date.today())
if 'repName_filter' not in st.session_state: st.session_state.repName_filter = []
if 'status_filter' not in st.session_state: st.session_state.status_filter = []
if 'clientSentiment_filter' not in st.session_state: st.session_state.clientSentiment_filter = []
if 'license_search' not in st.session_state: st.session_state.license_search = ""
if 'storeName_search' not in st.session_state: st.session_state.storeName_search = ""


# --- Data Loading Trigger ---
if not st.session_state.data_loaded_successfully:
    with st.spinner("Connecting to Google Sheet..."):
        df = load_data_from_google_sheet(default_sheet_url, default_worksheet_name)
        if not df.empty:
            st.session_state.df_original = df
            st.session_state.data_loaded_successfully = True
            # Initialize date filter state AFTER data load
            ds, de, _, _ = get_default_date_range(df['onboarding_date_only'] if 'onboarding_date_only' in df else None)
            st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
        else:
            st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF

df_original = st.session_state.df_original

# --- UI ---
st.title("🚀 Onboarding Performance Dashboard v2.0 🚀")

if not st.session_state.data_loaded_successfully or df_original.empty:
    st.error("Failed to load data or data source is empty. Please check Google Sheet permissions/availability and try refreshing.")
    if st.sidebar.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.session_state.data_loaded_successfully = False
        st.rerun()
    st.stop()


# --- Sidebar ---
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False
    st.rerun()

st.sidebar.header("🔍 Filters")

# Date Range Filter
onboarding_dates_col = df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original.columns else None
def_start, def_end, min_dt, max_dt = get_default_date_range(onboarding_dates_col)

# Update session state if it hasn't been properly initialized or if defaults changed
if 'date_range_filter' not in st.session_state or \
   (st.session_state.date_range_filter[0] is None and def_start is not None) :
    st.session_state.date_range_filter = (def_start, def_end)


if min_dt and max_dt:
    st.session_state.date_range_filter = st.sidebar.date_input(
        "Onboarding Date Range:",
        value=st.session_state.date_range_filter,
        min_value=min_dt,
        max_value=max_dt,
        key="date_range_widget" # Use a different key for the widget
    )
else:
    st.sidebar.warning("Onboarding date data not available for range filter.")
start_date_filter, end_date_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)


# Search Filters
search_cols_map = {"licenseNumber": "License Number", "storeName": "Store Name"} # Column_in_df: Display_Name
actual_search_cols = {k:v for k,v in search_cols_map.items() if k in df_original.columns}

for col_key, display_name in actual_search_cols.items():
    st.session_state[f"{col_key}_search"] = st.sidebar.text_input(
        f"Search by {display_name}:",
        value=st.session_state.get(f"{col_key}_search", ""), # Use .get for safety
        key=f"{col_key}_search_widget"
    )

# Multi-Select Filters
categorical_cols = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for col_name, display_label in categorical_cols.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = sorted(df_original[col_name].astype(str).dropna().unique())
        # Initialize session state for multiselect if not present
        if f"{col_name}_filter" not in st.session_state:
            st.session_state[f"{col_name}_filter"] = [] # Default to empty or unique_values for all selected

        st.session_state[f"{col_name}_filter"] = st.sidebar.multiselect(
            f"Select {display_label}:",
            options=unique_values,
            default=st.session_state[f"{col_name}_filter"], # Use session state for default
            key=f"{col_name}_filter_widget"
        )
    else:
        st.sidebar.text(f"{display_label} data not available.")

# Clear All Filters Button
def clear_all_filters_callback():
    # Reset date range
    ds, de, _, _ = get_default_date_range(df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original else None)
    st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
    if "date_range_widget" in st.session_state: # Reset widget if it exists
        st.session_state.date_range_widget = st.session_state.date_range_filter

    # Reset search terms
    for col_key in actual_search_cols:
        st.session_state[f"{col_key}_search"] = ""
        if f"{col_key}_search_widget" in st.session_state:
             st.session_state[f"{col_key}_search_widget"] = ""


    # Reset multi-selects
    for col_name in categorical_cols:
        st.session_state[f"{col_name}_filter"] = [] # Empty list for "select all" or no selection
        if f"{col_name}_filter_widget" in st.session_state:
            st.session_state[f"{col_name}_filter_widget"] = []


if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback, use_container_width=True):
    st.experimental_rerun() # Rerun to apply cleared filters, use st.rerun for newer versions


# --- Filtering Logic ---
df_filtered = df_original.copy()

# Apply date filter
if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
    date_objects_filter = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
    df_filtered = df_filtered[date_objects_filter.notna() & (date_objects_filter >= start_date_filter) & (date_objects_filter <= end_date_filter)]

# Apply search filters
for col_key in actual_search_cols:
    search_term = st.session_state.get(f"{col_key}_search", "")
    if search_term:
        df_filtered = df_filtered[df_filtered[col_key].astype(str).str.contains(search_term, case=False, na=False)]

# Apply multi-select filters
for col_name in categorical_cols:
    selected_values = st.session_state.get(f"{col_name}_filter", [])
    if selected_values: # If list is not empty
        df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(selected_values)]


# --- Plotly Layout ---
plotly_layout_updates = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "font_color": PRIMARY_TEXT_COLOR, "title_font_color": GOLD_ACCENT_COLOR,
    "legend_font_color": PRIMARY_TEXT_COLOR,
    "title_x": 0.5 # Center Plotly chart title
}

# --- MTD Metrics ---
today = date.today()
current_month_start = today.replace(day=1)
prev_month_end = current_month_start - timedelta(days=1)
prev_month_start = prev_month_end.replace(day=1)

df_mtd = pd.DataFrame()
df_prev_mtd = pd.DataFrame()

if 'onboarding_date_only' in df_original.columns:
    date_objects_mtd = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_mtd_mask = date_objects_mtd.notna()
    if valid_mtd_mask.any():
        df_mtd = df_original[valid_mtd_mask & (date_objects_mtd >= current_month_start) & (date_objects_mtd <= today)]
        df_prev_mtd = df_original[valid_mtd_mask & (date_objects_mtd >= prev_month_start) & (date_objects_mtd <= prev_month_end)]

total_mtd, success_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd, "MTD")
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd, "Prev MTD")
mtd_onboarding_delta = total_mtd - total_prev_mtd if total_prev_mtd else None


# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1: # Overview
    st.header("📈 Month-to-Date (MTD) Overview")
    mtd_cols = st.columns(4)
    mtd_cols[0].metric(label="Total Onboardings MTD", value=total_mtd, delta=f"{mtd_onboarding_delta}" if mtd_onboarding_delta is not None else "N/A vs LY")
    mtd_cols[1].metric(label="Success Rate MTD", value=f"{success_mtd:.1f}%")
    mtd_cols[2].metric(label="Avg Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    mtd_cols[3].metric(label="Avg Days to Confirm MTD", value=f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")

    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_f, success_f, score_f, days_f = calculate_metrics(df_filtered, "Filtered")
        f_cols = st.columns(4)
        f_cols[0].metric(label="Total Filtered Onboardings", value=total_f)
        f_cols[1].metric(label="Filtered Success Rate", value=f"{success_f:.1f}%")
        f_cols[2].metric(label="Filtered Avg Score", value=f"{score_f:.2f}" if pd.notna(score_f) else "N/A")
        f_cols[3].metric(label="Filtered Avg Days to Confirm", value=f"{days_f:.1f}" if pd.notna(days_f) else "N/A")
    else:
        st.info("No data matches current filters for Overview.")

with tab2: # Detailed Analysis & Data
    st.header("📋 Filtered Onboarding Data")
    if not df_filtered.empty:
        # Conditional Formatting for Table
        def style_dataframe(df_to_style):
            styled = df_to_style.style
            if 'score' in df_to_style.columns:
                styled = styled.background_gradient(subset=['score'], cmap='RdYlGn', vmin=0, vmax=df_to_style['score'].astype(float).max())
            if 'days_to_confirmation' in df_to_style.columns:
                # Ensure numeric for styling, handle NaNs by not styling them or styling with a neutral color
                numeric_days = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if numeric_days.notna().any(): # Only apply if there's some valid data
                     styled = styled.background_gradient(subset=['days_to_confirmation'], cmap='RdYlGn_r', gmap=numeric_days)
            return styled

        df_display = df_filtered.copy()
        if 'deliveryDate_dt' in df_display.columns:
            df_display_sorted = df_display.sort_values(by='deliveryDate_dt', ascending=True, na_position='last')
        else:
            df_display_sorted = df_display

        # Select and reorder columns for display if needed
        # cols_to_show = [col for col in df_display_sorted.columns if not ('_str' in col or '_cleaned' in col or '_dt_sortable' in col)]
        # st.dataframe(style_dataframe(df_display_sorted[cols_to_show].reset_index(drop=True)))
        st.dataframe(style_dataframe(df_display_sorted.reset_index(drop=True)))


        csv_data = convert_df_to_csv(df_filtered)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_data,
            file_name='filtered_onboarding_data.csv',
            mime='text/csv',
            use_container_width=True
        )
    elif not df_original.empty:
        st.info("No data matches the current filter criteria.")
    else:
        st.warning("Original data is empty.")

    st.header("📊 Key Visuals (Filtered Data)")
    if not df_filtered.empty:
        viz_cols_detail = st.columns(2)
        with viz_cols_detail[0]:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                st.subheader("Onboarding Status")
                status_counts = df_filtered['status'].value_counts().reset_index()
                fig_status = px.bar(status_counts, x='status', y='count', color='status', template="plotly_dark")
                fig_status.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_status, use_container_width=True)

            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                st.subheader("Onboardings by Rep")
                rep_counts = df_filtered['repName'].value_counts().reset_index()
                fig_rep = px.bar(rep_counts, x='repName', y='count', color='repName', template="plotly_dark")
                fig_rep.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_rep, use_container_width=True)

        with viz_cols_detail[1]:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                st.subheader("Client Sentiment")
                sentiment_counts = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map = {str(s).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s).lower() else ('#2ca02c' if 'positive' in str(s).lower() else ('#d62728' if 'negative' in str(s).lower() else None))) for s in sentiment_counts['clientSentiment'].unique()}
                fig_sentiment = px.pie(sentiment_counts, names='clientSentiment', values='count', hole=0.4, template="plotly_dark", color='clientSentiment', color_discrete_map=sentiment_color_map)
                fig_sentiment.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_sentiment, use_container_width=True)

            # Checklist Item Completion (Simplified from previous)
            boolean_cols = [col for col in ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink'] if col in df_filtered.columns]
            final_bool_cols = []
            for b_col in boolean_cols: # Attempt to convert to boolean
                if df_filtered[b_col].dtype == 'object':
                    map_to_bool = {'true': True, 'false': False, 'yes': True, 'no': False, '1':True, '0':False, 1:True, 0:False, '':pd.NA, 'nan':pd.NA, None: pd.NA}
                    converted = df_filtered[b_col].astype(str).str.lower().map(map_to_bool)
                    if converted.notna().sum() > 0: df_filtered[b_col] = converted
                if df_filtered[b_col].dtype == 'bool' or (pd.api.types.is_numeric_dtype(df_filtered[b_col]) and df_filtered[b_col].isin([0,1,pd.NA]).all()):
                     final_bool_cols.append(b_col)
            
            if final_bool_cols:
                st.subheader("Checklist Item Completion")
                completion_data = []
                for col in final_bool_cols:
                    # Ensure boolean for sum, count only non-NA
                    bool_series = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0).astype(bool) if not df_filtered[col].dtype == 'bool' else df_filtered[col]
                    if bool_series.notna().any():
                        true_count = bool_series.sum()
                        total_valid = bool_series.notna().sum()
                        if total_valid > 0:
                            completion_data.append({"Item": col.replace("onboarding", ""), "Completion (%)": (true_count / total_valid) * 100})
                if completion_data:
                    fig_checklist = px.bar(pd.DataFrame(completion_data), x="Completion (%)", y="Item", orientation='h', template="plotly_dark", color_discrete_sequence=[GOLD_ACCENT_COLOR])
                    fig_checklist.update_layout(plotly_layout_updates, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_checklist, use_container_width=True)
    else:
        st.info("No data matches current filters for detailed visuals.")


with tab3: # Trends & Distributions
    st.header("💡 Trends & Distributions (Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            st.subheader("Total Onboardings Over Time")
            # Ensure 'onboarding_date_only' is datetime for resampling
            df_trend = df_filtered.copy()
            df_trend['onboarding_date_only'] = pd.to_datetime(df_trend['onboarding_date_only'], errors='coerce')
            df_trend = df_trend.dropna(subset=['onboarding_date_only'])

            if not df_trend.empty:
                # Determine resampling frequency based on date range span
                date_span_days = (df_trend['onboarding_date_only'].max() - df_trend['onboarding_date_only'].min()).days
                if date_span_days <= 31*2 : freq = 'D' # Daily for up to 2 months
                elif date_span_days <= 365 * 1.5: freq = 'W-MON' # Weekly for up to 1.5 years
                else: freq = 'ME' # Monthly for longer

                onboardings_over_time = df_trend.set_index('onboarding_date_only').resample(freq).size().reset_index(name='count')
                if not onboardings_over_time.empty:
                    fig_trend = px.line(onboardings_over_time, x='onboarding_date_only', y='count', markers=True, template="plotly_dark")
                    fig_trend.update_layout(plotly_layout_updates, title_text="Onboardings Over Filtered Period")
                    st.plotly_chart(fig_trend, use_container_width=True)
                else: st.info("Not enough data to plot onboarding trend for the selected period/frequency.")
            else: st.info("No valid date data for onboarding trend.")


        # Distribution of Days to Confirmation
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            st.subheader("Distribution of Days to Confirmation")
            days_data_dist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_dist.empty:
                fig_days_hist = px.histogram(days_data_dist, nbins=max(10, int(len(days_data_dist)/5)), title="Days to Confirmation Distribution", template="plotly_dark")
                fig_days_hist.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_days_hist, use_container_width=True)
            else: st.info("No valid 'Days to Confirmation' data to plot distribution.")
    else:
        st.info("No data matches current filters for Trends & Distributions.")


st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.0 | Enhanced Edition")