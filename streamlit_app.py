import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
import time
import numpy as np
import matplotlib # Required for pandas styler background_gradient

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.1", # Incremented version
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
    .css-1d391kg p, .css- F_1U7P p {{ /* Adjust selectors if Streamlit updates them */
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
    """
    Attempts to convert a pandas Series to datetime objects, trying multiple formats.
    `infer_datetime_format=True` is good for ISO 8601 (like those with 'Z').
    """
    # Attempt default conversion first (often handles ISO 8601 and common formats)
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    
    # If many values are still NaT, try specific formats
    # Common date formats (add more as needed based on your data)
    common_formats = [
        '%Y-%m-%d %H:%M:%S.%f', # With microseconds
        '%Y-%m-%d %H:%M:%S',   # Standard datetime
        '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %I:%M:%S %p', # With AM/PM
        '%m/%d/%Y %I:%M:%S %p',
        # '%Y-%m-%dT%H:%M:%S.%fZ', # infer_datetime_format usually handles this
        # '%Y-%m-%dT%H:%M:%S%z',  # infer_datetime_format usually handles this
        '%Y-%m-%d',            # Date only
        '%m/%d/%Y',
        '%d/%m/%Y',
    ]
    # Only try other formats if the first attempt resulted in mostly NaT
    # and the series is not empty or all obviously non-date strings
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and \
       not series.isin(['', 'None', 'nan', 'NaT', None]).all():
        for fmt in common_formats:
            # Create a temporary series to try the format
            temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
            # If this format successfully parsed more dates than the previous best, update
            if temp_dates.notnull().sum() > dates.notnull().sum():
                dates = temp_dates
            # If all dates are parsed, no need to try further formats
            if dates.notnull().all():
                break
    return dates


@st.cache_data(ttl=600)
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    gc = authenticate_gspread(st.secrets.get("gcp_service_account"))
    if gc is None: return pd.DataFrame()

    try:
        spreadsheet = gc.open_by_url(sheet_url_or_name) if "docs.google.com" in sheet_url_or_name else gc.open(sheet_url_or_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1) # Get data as list of dicts
        df = pd.DataFrame(data) # Convert to DataFrame
        st.sidebar.success(f"Loaded {len(df)} records.")
        if df.empty:
            st.warning("No data records found in the Google Sheet.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading from Google Sheet: {e}")
        return pd.DataFrame()

    # --- Data Preprocessing ---
    df.columns = df.columns.str.strip() # Clean column names

    date_columns_to_parse = {
        'onboardingDate': 'onboardingDate_dt',
        'deliveryDate': 'deliveryDate_dt',
        'confirmationTimestamp': 'confirmationTimestamp_dt'
    }

    for original_col, new_dt_col in date_columns_to_parse.items():
        if original_col in df.columns:
            # Minimal cleaning: just strip spaces and newlines. Let robust_to_datetime handle 'Z' and other formats.
            cleaned_series = df[original_col].astype(str).str.replace('\n', '', regex=False).str.strip()
            
            parsed_dates = robust_to_datetime(cleaned_series)
            df[new_dt_col] = parsed_dates

            if parsed_dates.isnull().all() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                 st.warning(f"Could not parse any dates in '{original_col}'. All values are NaT. Please check date formats in the sheet.")
            elif parsed_dates.isnull().any() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                 st.warning(f"Some dates in '{original_col}' could not be parsed and are NaT. Date-dependent features might be affected for these rows.")

            if original_col == 'onboardingDate': # Specific logic for onboarding_date_only
                 df['onboarding_date_only'] = df[new_dt_col].dt.date # Extract only the date part
                 if df['onboarding_date_only'].isnull().all() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                    st.warning(f"Could not parse '{original_col}' for any rows to extract date part. Date-dependent features might not work.")
        else:
            st.warning(f"Date column '{original_col}' not found. Dependent calculations might fail.")
            df[new_dt_col] = pd.NaT # Create NaT column if original is missing
            if original_col == 'onboardingDate':
                df['onboarding_date_only'] = pd.NaT
    
    # Calculate Days to Confirmation with UTC standardization
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
        # Ensure they are datetime objects (robust_to_datetime should have done this)
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')

        # Helper function to convert a datetime series to UTC
        def convert_series_to_utc(dt_series):
            if pd.api.types.is_datetime64_any_dtype(dt_series): # Check if it's a datetime type
                # Check if any non-NaT values exist before trying to access .dt accessor
                if dt_series.notna().any():
                    if dt_series.dt.tz is None: # If naive
                        # Localize to UTC, handling ambiguous/nonexistent times by setting to NaT
                        return dt_series.dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
                    else: # If already aware
                        return dt_series.dt.tz_convert('UTC')
            return dt_series # Return as is if not datetime or all NaT

        # Create new columns for UTC versions to preserve original parsed datetimes if needed
        df['deliveryDate_dt_utc'] = convert_series_to_utc(df['deliveryDate_dt'])
        df['confirmationTimestamp_dt_utc'] = convert_series_to_utc(df['confirmationTimestamp_dt'])
        
        # Calculate difference using UTC columns
        valid_dates_mask = df['deliveryDate_dt_utc'].notna() & df['confirmationTimestamp_dt_utc'].notna()
        df['days_to_confirmation'] = pd.NA # Initialize with Pandas NA
        
        if valid_dates_mask.any():
            # Subtracting two UTC timezone-aware datetimes gives a timedelta
            time_difference = (df.loc[valid_dates_mask, 'confirmationTimestamp_dt_utc'] - 
                               df.loc[valid_dates_mask, 'deliveryDate_dt_utc'])
            df.loc[valid_dates_mask, 'days_to_confirmation'] = time_difference.dt.days
        
        # One final check: if days_to_confirmation is still all NA but inputs were not, it indicates a problem
        if df['days_to_confirmation'].isnull().all() and valid_dates_mask.any():
            st.warning("Failed to calculate 'Days to Confirmation' despite having some valid date inputs. Check timezone logic or specific date values.")

    else:
        st.warning(" 'deliveryDate' or 'confirmationTimestamp' column missing/empty for 'Days to Confirmation' calculation.")
        df['days_to_confirmation'] = pd.NA


    if 'status' not in df.columns: st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found.")
        df['score'] = pd.NA # Assign pd.NA if 'score' column is missing
            
    return df

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for download."""
    return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input, period_name=""): # period_name is for debugging/logging if needed
    """Calculates key metrics from a DataFrame."""
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA # total, success_rate, avg_score, avg_days_to_confirm

    total_onboardings = len(df_input)
    success_rate = 0.0
    avg_score = pd.NA
    avg_days_to_confirm = pd.NA

    if 'status' in df_input.columns:
        successful_onboardings = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
        if total_onboardings > 0:
            success_rate = (successful_onboardings / total_onboardings) * 100
    
    if 'score' in df_input.columns and df_input['score'].notna().any():
        avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    
    if 'days_to_confirmation' in df_input.columns and df_input['days_to_confirmation'].notna().any():
        numeric_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce')
        if numeric_days.notna().any():
             avg_days_to_confirm = numeric_days.mean()

    return total_onboardings, success_rate, avg_score, avg_days_to_confirm

def get_default_date_range(df_date_column_series):
    """Calculates default and min/max date range for filters from a date series."""
    today = date.today()
    default_start_date = today.replace(day=1)
    default_end_date = today
    min_data_date, max_data_date = None, None

    if df_date_column_series is not None and not df_date_column_series.empty:
        # Ensure the series contains actual date objects for min/max
        date_objects = pd.to_datetime(df_date_column_series, errors='coerce').dt.date
        valid_dates = date_objects.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min()
            max_data_date = valid_dates.max()

            # Adjust defaults to be within the actual data range
            default_start_date = max(default_start_date, min_data_date)
            default_end_date = min(default_end_date, max_data_date)
            
            # Ensure start is not after end, if so, use full data range
            if default_start_date > default_end_date : 
                default_start_date = min_data_date 
                default_end_date = max_data_date
    
    return default_start_date, default_end_date, min_data_date, max_data_date


# --- Initialize Session State ---
# Attempt to get Google Sheet URL and Name from secrets, otherwise use hardcoded defaults
default_sheet_url = st.secrets.get("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing")
default_worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME", "Sheet1")

# Initialize session state variables if they don't exist
if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()

# Filter defaults - these will be properly set after data is loaded for date range
if 'date_range_filter' not in st.session_state: st.session_state.date_range_filter = (date.today().replace(day=1), date.today())
if 'repName_filter' not in st.session_state: st.session_state.repName_filter = []
if 'status_filter' not in st.session_state: st.session_state.status_filter = []
if 'clientSentiment_filter' not in st.session_state: st.session_state.clientSentiment_filter = []
# Search term states
if 'licenseNumber_search' not in st.session_state: st.session_state.licenseNumber_search = "" # Example, adjust if actual col name is different
if 'storeName_search' not in st.session_state: st.session_state.storeName_search = ""


# --- Data Loading Trigger ---
if not st.session_state.data_loaded_successfully:
    with st.spinner("Connecting to Google Sheet and processing data..."): # Updated spinner message
        df = load_data_from_google_sheet(default_sheet_url, default_worksheet_name)
        if not df.empty:
            st.session_state.df_original = df
            st.session_state.data_loaded_successfully = True
            # Initialize date filter state AFTER data load, using the actual data's range
            ds, de, _, _ = get_default_date_range(df['onboarding_date_only'] if 'onboarding_date_only' in df else None)
            st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
        else:
            st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF if load fails or sheet is empty
            st.session_state.data_loaded_successfully = False # Explicitly set if data is empty

df_original = st.session_state.df_original # Get the original dataframe from session state

# --- Main Application UI Starts Here ---
st.title("🚀 Onboarding Performance Dashboard v2.1 🚀")

# Stop execution if data loading failed or the original dataframe is empty
if not st.session_state.data_loaded_successfully or df_original.empty:
    st.error("Failed to load data or the data source is empty. Please check Google Sheet permissions/availability and sheet content. Try refreshing.")
    if st.sidebar.button("🔄 Force Refresh Data & Reload App"): # More descriptive button
        st.cache_data.clear() # Clear cached data
        st.session_state.clear() # Clear all session state to force full re-initialization
        st.rerun() # Rerun the app from scratch
    st.stop()


# --- Sidebar ---
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False # Reset flag to trigger reload
    st.rerun()

st.sidebar.header("🔍 Filters")

# Date Range Filter
# Use 'onboarding_date_only' from the loaded df_original for min/max values
onboarding_dates_for_filter = df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original.columns else None
def_start, def_end, min_dt_data, max_dt_data = get_default_date_range(onboarding_dates_for_filter)

# Ensure session state for date_range_filter is initialized or updated if necessary
if 'date_range_filter' not in st.session_state or \
   (st.session_state.date_range_filter[0] is None and def_start is not None) or \
   (st.session_state.date_range_filter[0] != def_start or st.session_state.date_range_filter[1] != def_end): # If defaults changed
    st.session_state.date_range_filter = (def_start, def_end)


if min_dt_data and max_dt_data: # Only show date input if min/max dates are valid
    # Use a different key for the widget to avoid conflict if we directly set session_state.date_range_filter
    selected_date_range_widget = st.sidebar.date_input(
        "Onboarding Date Range:",
        value=st.session_state.date_range_filter, # Use session state value
        min_value=min_dt_data,
        max_value=max_dt_data,
        key="date_range_selector_widget" 
    )
    # Update session state if widget value changes
    if selected_date_range_widget != st.session_state.date_range_filter:
        st.session_state.date_range_filter = selected_date_range_widget
        # st.rerun() # Optionally rerun if immediate update is needed, but usually Streamlit handles it
else:
    st.sidebar.warning("Onboarding date data not available for setting a date range filter.")
# Retrieve the possibly updated start and end dates from session state
start_date_filter, end_date_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)


# Search Filters - Define your actual column names from the sheet here
# Format: {"column_name_in_dataframe": "Display Name for UI"}
expected_search_cols = {
    "licenseNumber": "License Number", # ADJUST THIS if your column name is different
    "storeName": "Store Name"      # ADJUST THIS if your column name is different
}
actual_search_cols_present = {k: v for k, v in expected_search_cols.items() if k in df_original.columns}

for col_key, display_name in actual_search_cols_present.items():
    # Ensure session state key for search term exists
    if f"{col_key}_search" not in st.session_state:
        st.session_state[f"{col_key}_search"] = ""
    
    st.session_state[f"{col_key}_search"] = st.sidebar.text_input(
        f"Search by {display_name}:",
        value=st.session_state[f"{col_key}_search"], # Use session state value
        key=f"{col_key}_search_widget" # Unique key for the widget
    )

# Multi-Select Filters
categorical_filter_cols = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for col_name, display_label in categorical_filter_cols.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = sorted(df_original[col_name].astype(str).dropna().unique())
        # Ensure session state key for this filter exists
        if f"{col_name}_filter" not in st.session_state:
            st.session_state[f"{col_name}_filter"] = [] # Default to empty list (no items selected)
        
        st.session_state[f"{col_name}_filter"] = st.sidebar.multiselect(
            f"Select {display_label}:",
            options=unique_values,
            default=st.session_state[f"{col_name}_filter"], # Use session state for default
            key=f"{col_name}_filter_widget" # Unique key for the widget
        )
    else:
        st.sidebar.text(f"{display_label} data not available for filtering.")

# Clear All Filters Button
def clear_all_filters_callback():
    # Reset date range to its default based on current data
    ds, de, _, _ = get_default_date_range(df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original else None)
    st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
    # Also reset the widget's state if it exists
    if "date_range_selector_widget" in st.session_state:
        st.session_state.date_range_selector_widget = st.session_state.date_range_filter

    # Reset search terms
    for col_key_search in actual_search_cols_present:
        st.session_state[f"{col_key_search}_search"] = ""
        if f"{col_key_search}_search_widget" in st.session_state: # Reset widget state
             st.session_state[f"{col_key_search}_search_widget"] = ""

    # Reset multi-selects to empty lists
    for col_name_cat in categorical_filter_cols:
        st.session_state[f"{col_name_cat}_filter"] = []
        if f"{col_name_cat}_filter_widget" in st.session_state: # Reset widget state
            st.session_state[f"{col_name_cat}_filter_widget"] = []
    # No explicit rerun here, Streamlit should pick up changes. If not, add st.rerun()

if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback, use_container_width=True):
    st.rerun() # Explicitly rerun to ensure UI updates correctly after clearing filters


# --- Filtering Logic ---
df_filtered = df_original.copy() # Start with a copy of the original data

# Apply date filter first
if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
    # Ensure 'onboarding_date_only' is in date format for comparison
    date_objects_for_filtering = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
    df_filtered = df_filtered[
        date_objects_for_filtering.notna() &
        (date_objects_for_filtering >= start_date_filter) &
        (date_objects_for_filtering <= end_date_filter)
    ]

# Apply search filters
for col_key, display_name in actual_search_cols_present.items():
    search_term = st.session_state.get(f"{col_key}_search", "") # Get from session state
    if search_term: # If user entered something
        df_filtered = df_filtered[df_filtered[col_key].astype(str).str.contains(search_term, case=False, na=False)]

# Apply multi-select filters
for col_name, display_label in categorical_filter_cols.items():
    selected_values = st.session_state.get(f"{col_name}_filter", []) # Get from session state
    if selected_values: # If list is not empty (i.e., some selections were made)
        df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(selected_values)]


# --- Plotly Layout Configuration ---
plotly_layout_updates = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "font_color": PRIMARY_TEXT_COLOR, "title_font_color": GOLD_ACCENT_COLOR,
    "legend_font_color": PRIMARY_TEXT_COLOR,
    "title_x": 0.5 # Center Plotly chart title (if Plotly adds one by default)
}

# --- MTD Metrics Calculation (using df_original for a true MTD) ---
today_date = date.today()
current_month_start_date = today_date.replace(day=1)
# Previous month for MoM comparison
prev_month_end_date = current_month_start_date - timedelta(days=1)
prev_month_start_date = prev_month_end_date.replace(day=1)

df_mtd_calc = pd.DataFrame() # For current MTD
df_prev_mtd_calc = pd.DataFrame() # For previous MTD

if 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    # Convert 'onboarding_date_only' to actual date objects for comparison
    original_date_objects = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_original_dates_mask = original_date_objects.notna()

    if valid_original_dates_mask.any():
        df_mtd_calc = df_original[
            valid_original_dates_mask &
            (original_date_objects >= current_month_start_date) &
            (original_date_objects <= today_date)
        ]
        df_prev_mtd_calc = df_original[
            valid_original_dates_mask &
            (original_date_objects >= prev_month_start_date) &
            (original_date_objects <= prev_month_end_date)
        ]

total_mtd, success_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd_calc)
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_calc) # Only need total for delta
mtd_onboarding_delta_val = total_mtd - total_prev_mtd if pd.notna(total_mtd) and pd.notna(total_prev_mtd) else None


# --- Main Content Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1: # Overview Tab
    st.header("📈 Month-to-Date (MTD) Overview")
    mtd_cols_display = st.columns(4)
    mtd_cols_display[0].metric(
        label="Total Onboardings MTD", 
        value=total_mtd, 
        delta=f"{mtd_onboarding_delta_val:+}" if mtd_onboarding_delta_val is not None else "N/A vs Prev Month",
        delta_color="normal" if mtd_onboarding_delta_val is None or mtd_onboarding_delta_val == 0 else ("inverse" if mtd_onboarding_delta_val < 0 else "normal")
    )
    mtd_cols_display[1].metric(label="Success Rate MTD", value=f"{success_mtd:.1f}%" if pd.notna(success_mtd) else "N/A")
    mtd_cols_display[2].metric(label="Avg Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    mtd_cols_display[3].metric(label="Avg Days to Confirm MTD", value=f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")

    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_filtered_val, success_filtered_val, score_filtered_val, days_filtered_val = calculate_metrics(df_filtered)
        filtered_cols_display = st.columns(4)
        filtered_cols_display[0].metric(label="Total Filtered Onboardings", value=total_filtered_val)
        filtered_cols_display[1].metric(label="Filtered Success Rate", value=f"{success_filtered_val:.1f}%" if pd.notna(success_filtered_val) else "N/A")
        filtered_cols_display[2].metric(label="Filtered Average Score", value=f"{score_filtered_val:.2f}" if pd.notna(score_filtered_val) else "N/A")
        filtered_cols_display[3].metric(label="Filtered Avg Days to Confirm", value=f"{days_filtered_val:.1f}" if pd.notna(days_filtered_val) else "N/A")
    else:
        st.info("No data matches the current filter criteria to display in Overview.")

with tab2: # Detailed Analysis & Data Tab
    st.header("📋 Filtered Onboarding Data Table")
    if not df_filtered.empty:
        # Conditional Formatting for the DataFrame
        def style_dataframe_conditionally(df_to_style):
            styled_df = df_to_style.style # Create a Styler object
            if 'score' in df_to_style.columns and df_to_style['score'].notna().any():
                # Ensure score is numeric for gradient
                scores_numeric = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_numeric.notna().any():
                    styled_df = styled_df.background_gradient(subset=['score'], cmap='RdYlGn', 
                                                              low=0.3, high=0.7, # Adjust low/high for color intensity if needed
                                                              gmap=scores_numeric.fillna(scores_numeric.min() -1 )) # fillna for gmap
            
            if 'days_to_confirmation' in df_to_style.columns and df_to_style['days_to_confirmation'].notna().any():
                days_numeric = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_numeric.notna().any(): # Only apply if there's some valid data
                     styled_df = styled_df.background_gradient(subset=['days_to_confirmation'], cmap='RdYlGn_r', # _r reverses color map
                                                               gmap=days_numeric.fillna(days_numeric.min() -1)) # fillna for gmap
            return styled_df

        df_display_table = df_filtered.copy()
        # Sort by deliveryDate_dt if it exists and has valid dates
        if 'deliveryDate_dt' in df_display_table.columns and df_display_table['deliveryDate_dt'].notna().any():
            df_display_table_sorted = df_display_table.sort_values(by='deliveryDate_dt', ascending=True, na_position='last')
        else:
            df_display_table_sorted = df_display_table # Keep as is if no valid deliveryDate_dt

        # Define columns to display (excluding intermediate _utc or _str columns if any)
        cols_for_display = [col for col in df_display_table_sorted.columns if not col.endswith('_utc') and not col.endswith('_str_original')]
        
        st.dataframe(style_dataframe_conditionally(df_display_table_sorted[cols_for_display].reset_index(drop=True)), use_container_width=True)

        # Download Button for Filtered Data
        csv_download_data = convert_df_to_csv(df_filtered) # Use the filtered data
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_download_data,
            file_name='filtered_onboarding_data.csv',
            mime='text/csv',
            use_container_width=True # Make button wider
        )
    elif not df_original.empty: # Original data was loaded, but current filters yield no results
        st.info("No data matches the current filter criteria for the table display.")
    # If df_original was also empty, the main check at the beginning handles the message.

    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        viz_cols_in_detail_tab = st.columns(2) # Create two columns for charts
        with viz_cols_in_detail_tab[0]:
            # Onboarding Status Chart
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                st.subheader("Onboarding Status")
                status_counts_chart = df_filtered['status'].value_counts().reset_index()
                # status_counts_chart.columns = ['status', 'count'] # Already named by value_counts
                fig_status_chart = px.bar(status_counts_chart, x='status', y='count', color='status', template="plotly_dark")
                fig_status_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_status_chart, use_container_width=True)

            # Onboardings by Rep Chart
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                st.subheader("Onboardings by Rep")
                rep_counts_chart = df_filtered['repName'].value_counts().reset_index()
                # rep_counts_chart.columns = ['Representative', 'Count']
                fig_rep_chart = px.bar(rep_counts_chart, x='repName', y='count', color='repName', template="plotly_dark")
                fig_rep_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_rep_chart, use_container_width=True)

        with viz_cols_in_detail_tab[1]:
            # Client Sentiment Chart
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                st.subheader("Client Sentiment")
                sentiment_counts_chart = df_filtered['clientSentiment'].value_counts().reset_index()
                # sentiment_counts_chart.columns = ['sentiment', 'count']
                # Define a color map for sentiments
                sentiment_color_map_def = {
                    str(s).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s).lower() else 
                                     ('#2ca02c' if 'positive' in str(s).lower() else 
                                      ('#d62728' if 'negative' in str(s).lower() else None)))
                    for s in sentiment_counts_chart['clientSentiment'].unique()
                }
                fig_sentiment_chart = px.pie(sentiment_counts_chart, names='clientSentiment', values='count', 
                                             hole=0.4, template="plotly_dark", 
                                             color='clientSentiment', color_discrete_map=sentiment_color_map_def)
                fig_sentiment_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_sentiment_chart, use_container_width=True)

            # Checklist Item Completion Chart
            checklist_item_cols = ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 
                                   'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 
                                   'providePromoCreditLink']
            actual_checklist_cols = [col for col in checklist_item_cols if col in df_filtered.columns]
            
            processed_checklist_cols_data = []
            for b_col in actual_checklist_cols: # Attempt to convert to boolean and calculate
                # Standardize to boolean: True for 'true'/'yes'/'1', False for 'false'/'no'/'0', else NaP (Pandas NA for boolean)
                # This mapping is crucial for accurate sum and count
                map_to_bool_strict = {'true': True, 'false': False, 'yes': True, 'no': False, 
                                      '1':True, '0':False, 1:True, 0:False, 
                                      '':pd.NA, 'nan':pd.NA, None:pd.NA}
                
                # Apply mapping carefully, ensuring it results in a boolean or NA series
                bool_series_strict = df_filtered[b_col].astype(str).str.lower().map(map_to_bool_strict).astype('boolean')

                if bool_series_strict.notna().any(): # If there are any non-NA values after conversion
                    true_count = bool_series_strict.sum() # Sum of True values
                    total_valid_responses = bool_series_strict.notna().sum() # Count of non-NA (True or False)
                    if total_valid_responses > 0:
                        item_display_name = b_col.replace("onboarding", "").replace("provide", "Provided ").replace("confirm", "Confirmed ")
                        # Add spaces before capital letters for better readability
                        item_display_name = ''.join([' ' + char if char.isupper() else char for char in item_display_name]).strip().title()
                        processed_checklist_cols_data.append({
                            "Checklist Item": item_display_name, 
                            "Completion (%)": (true_count / total_valid_responses) * 100
                        })
            
            if processed_checklist_cols_data:
                st.subheader("Checklist Item Completion")
                completion_df_chart = pd.DataFrame(processed_checklist_cols_data)
                fig_checklist_chart = px.bar(completion_df_chart, x="Completion (%)", y="Checklist Item", 
                                             orientation='h', template="plotly_dark", color_discrete_sequence=[GOLD_ACCENT_COLOR])
                fig_checklist_chart.update_layout(plotly_layout_updates, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_checklist_chart, use_container_width=True)
    else:
        st.info("No data matches current filters to display detailed visuals.")


with tab3: # Trends & Distributions Tab
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time Trend Line Chart
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            st.subheader("Total Onboardings Over Time")
            df_trend_chart = df_filtered.copy()
            # Ensure 'onboarding_date_only' is datetime for resampling
            df_trend_chart['onboarding_date_only'] = pd.to_datetime(df_trend_chart['onboarding_date_only'], errors='coerce')
            df_trend_chart = df_trend_chart.dropna(subset=['onboarding_date_only']) # Drop rows where date conversion failed

            if not df_trend_chart.empty:
                # Determine resampling frequency based on the span of dates in the filtered data
                date_span_days_trend = (df_trend_chart['onboarding_date_only'].max() - df_trend_chart['onboarding_date_only'].min()).days
                if date_span_days_trend <= 62 : freq_resample = 'D' # Daily for up to ~2 months
                elif date_span_days_trend <= 365 * 1.5 : freq_resample = 'W-MON' # Weekly (start on Monday) for up to ~1.5 years
                else: freq_resample = 'ME' # Month End frequency for longer periods

                onboardings_over_time_data = df_trend_chart.set_index('onboarding_date_only').resample(freq_resample).size().reset_index(name='count')
                
                if not onboardings_over_time_data.empty:
                    fig_trend_line = px.line(onboardings_over_time_data, x='onboarding_date_only', y='count', 
                                             markers=True, template="plotly_dark",
                                             labels={'onboarding_date_only': 'Date', 'count': 'Number of Onboardings'})
                    fig_trend_line.update_layout(plotly_layout_updates, title_text="Onboardings Over Filtered Period")
                    st.plotly_chart(fig_trend_line, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend for the selected period/frequency.")
            else: 
                st.info("No valid date data available in the filtered set for the onboarding trend chart.")

        # Distribution of "Days to Confirmation" Histogram
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            st.subheader("Distribution of Days to Confirmation")
            # Ensure data is numeric and drop NAs for histogram
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist.empty:
                # Adjust nbins dynamically or set a reasonable default
                nbins_hist = max(10, min(50, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else 10
                fig_days_dist_hist = px.histogram(days_data_for_hist, nbins=nbins_hist, 
                                                  title="Days to Confirmation Distribution", template="plotly_dark",
                                                  labels={'value': 'Days to Confirmation'}) # 'value' is default for px.histogram input
                fig_days_dist_hist.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_days_dist_hist, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data available in the filtered set to plot distribution.")
    else:
        st.info("No data matches the current filter criteria to display Trends & Distributions.")


st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.1 | Enhanced DateTime")