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
    page_title="Onboarding Performance Dashboard v2.2", # Incremented version
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
    .css-1d391kg p, .css- F_1U7P p {{ /* Note: These CSS selectors might be unstable across Streamlit versions */
        color: {PRIMARY_TEXT_COLOR} !important;
    }}
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

# --- BEGIN SECRETS DEBUGGING CODE ---
st.subheader("Secrets Debugging Information:")
try:
    # Attempt to list all keys available in st.secrets
    # This is safe as it only lists keys, not values.
    secret_keys = list(st.secrets.keys())
    st.write(f"Available secret keys: {secret_keys}")

    if not secret_keys:
        st.warning("No secrets appear to be loaded directly via st.secrets.keys(). This might indicate a broader issue with secrets configuration or access.")

    # Check for specific keys you expect, using .get() to avoid errors if a key is missing
    expected_top_level_keys = ["APP_ACCESS_KEY", "APP_ACCESS_HINT", "GOOGLE_SHEET_URL_OR_NAME", "GOOGLE_WORKSHEET_NAME", "gcp_service_account"]
    
    st.write("Checking individual expected secrets:")
    for key in expected_top_level_keys:
        secret_value = st.secrets.get(key)
        if secret_value is not None:
            st.success(f"Secret '{key}' IS available.")
            if key == "gcp_service_account":
                if isinstance(secret_value, dict) and "type" in secret_value and "private_key" in secret_value:
                    st.success(f"   '{key}' seems to be a correctly structured dictionary (contains 'type' and 'private_key').")
                else:
                    st.error(f"   '{key}' is available BUT might NOT be a correctly structured dictionary or is missing essential fields like 'type' or 'private_key'. Type found: {type(secret_value)}")
        else:
            st.error(f"Secret '{key}' is NOT available (st.secrets.get('{key}') returned None).")

except Exception as e:
    st.error(f"An error occurred while trying to access or list st.secrets: {e}")
    st.error("This could mean st.secrets itself is not available or there's a problem with its internal structure.")
st.markdown("---") # Separator
# --- END OF SECRETS DEBUGGING CODE ---

# --- Application Access Control ---
def check_password():
    """Returns true if password is correct or if secrets are not set (allowing local dev without password)"""
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")

    if app_password is None:
        # This warning will now appear below the debug section if APP_ACCESS_KEY is indeed missing
        st.sidebar.warning("APP_ACCESS_KEY not found by `st.secrets.get()`. Bypassing password for local development or if not set in deployment.")
        return True

    if "password_entered" not in st.session_state:
        st.session_state.password_entered = False

    if st.session_state.password_entered:
        return True

    with st.form("password_form"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Enter Access Key:", type="password", help=app_hint)
        submitted = st.form_submit_button("Submit")

        if submitted:
            if password_attempt == app_password:
                st.session_state.password_entered = True
                st.rerun() 
            else:
                st.error("Incorrect Access Key. Please try again.")
                return False
    return False

if not check_password():
    st.stop() 

# --- Google Sheets Authentication and Data Loading ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread(): # Removed secrets_dict argument
    try:
        gcp_secrets = st.secrets.get("gcp_service_account")
        if gcp_secrets is None: # Explicitly check for None
            st.error("GCP service account secrets (gcp_service_account) not found or is None. Please configure them in Streamlit secrets.")
            return None
        if not isinstance(gcp_secrets, dict):
            st.error(f"GCP service account secrets ('gcp_service_account') is not a dictionary. Type found: {type(gcp_secrets)}. Check Streamlit secrets configuration.")
            return None
        
        creds = Credentials.from_service_account_info(gcp_secrets, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Google Sheets Auth Error: {e}")
        st.error("This could be due to malformed 'gcp_service_account' secrets or issues with Google API permissions.")
        return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    # Fallback formats, simplified - add more if specific non-standard formats are common
    common_formats = [
        # Standard ISO-like formats
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', 
        # Common US formats
        '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %I:%M:%S %p',
        # Common European formats
        '%d/%m/%Y %H:%M:%S', 
        # Date only formats
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
    ]
    # Only attempt intensive parsing if initial pass fails significantly and series is not mostly empty/placeholder
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and \
       not series.astype(str).str.lower().isin(['', 'none', 'nan', 'nat', 'null']).all(): # Check for actual content
        original_success_rate = dates.notnull().sum()
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                if temp_dates.notnull().sum() > dates.notnull().sum():
                    dates = temp_dates
                if dates.notnull().all(): # All parsed, exit early
                    break
            except ValueError: # Catch specific errors if a format is wildly inappropriate for all values
                continue 
        if dates.notnull().sum() <= original_success_rate and original_success_rate < len(series):
             pass # Could add a warning here if intensive parsing didn't improve things
    return dates


@st.cache_data(ttl=600)
def load_data_from_google_sheet(_sheet_url_or_name, _worksheet_name): # Renamed args to avoid conflict with global
    # Fetch secrets inside the cached function if they might change, or ensure they are passed if stable
    # For this use case, fetching them here is fine as they are part of app config
    # However, note that st.secrets cannot be directly used in @st.cache_data args for hashing.
    # The parameters _sheet_url_or_name and _worksheet_name are passed to ensure cache invalidation if they change.

    current_sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    current_worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")

    if not current_sheet_url_or_name or not current_worksheet_name:
        # This error should ideally be caught before calling this function if possible
        st.error("Data source (Google Sheet URL/Name or Worksheet Name) is not configured/found in Streamlit Secrets within load_data function.")
        return pd.DataFrame()

    gc = authenticate_gspread() 
    if gc is None: return pd.DataFrame()

    try:
        if "docs.google.com" in current_sheet_url_or_name or "spreadsheets.google.com" in current_sheet_url_or_name:
            spreadsheet = gc.open_by_url(current_sheet_url_or_name)
        else:
            spreadsheet = gc.open(current_sheet_url_or_name) 
        worksheet = spreadsheet.worksheet(current_worksheet_name)
        data = worksheet.get_all_records(head=1, expected_headers=None) # Allow flexible headers
        
        if not data: # Check if data is empty list
            st.warning("No data records found in the Google Sheet or worksheet is empty.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        st.sidebar.success(f"Successfully loaded {len(df)} records from '{current_worksheet_name}'.")
        if df.empty: # Should be caught by `if not data` but as a safeguard
            st.warning("DataFrame is empty after loading records.")
            return pd.DataFrame()

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet not found. Ensure '{current_sheet_url_or_name}' is correct and the service account has access.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{current_worksheet_name}' not found. Check the name.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_columns_to_parse = {
        'onboardingDate': 'onboardingDate_dt',
        'deliveryDate': 'deliveryDate_dt',
        'confirmationTimestamp': 'confirmationTimestamp_dt'
    }

    for original_col, new_dt_col in date_columns_to_parse.items():
        if original_col in df.columns:
            # Clean series by removing newlines and stripping whitespace before parsing
            cleaned_series = df[original_col].astype(str).str.replace('\n', '', regex=False).str.strip()
            parsed_dates = robust_to_datetime(cleaned_series)
            df[new_dt_col] = parsed_dates
            
            # Enhanced warnings for parsing issues
            is_mostly_empty_placeholders = cleaned_series.str.lower().isin(['', 'none', 'nan', 'nat', 'null']).all()
            if parsed_dates.isnull().all() and not is_mostly_empty_placeholders:
                 st.warning(f"Could not parse any dates in column '{original_col}'. All values resulted in NaT (Not a Time). Original values might be non-date strings or in an unrecognized format.")
            elif parsed_dates.isnull().any() and not is_mostly_empty_placeholders:
                 num_failed = parsed_dates.isnull().sum()
                 st.warning(f"{num_failed} out of {len(cleaned_series)} date(s) in '{original_col}' could not be parsed and are NaT.")
            
            if original_col == 'onboardingDate': # Specific handling for onboardingDate
                 df['onboarding_date_only'] = df[new_dt_col].dt.date
                 if df['onboarding_date_only'].isnull().all() and not is_mostly_empty_placeholders: # if all are NaT
                    st.warning(f"Could not extract date part for any rows from '{original_col}' (all resulted in NaT).")
        else:
            st.warning(f"Expected date column '{original_col}' not found in the sheet. Corresponding datetime column '{new_dt_col}' will be empty.")
            df[new_dt_col] = pd.NaT # Create empty datetime column
            if original_col == 'onboardingDate': # Ensure 'onboarding_date_only' exists if 'onboardingDate' was expected
                df['onboarding_date_only'] = pd.NaT
    
    # Calculate 'days_to_confirmation'
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
        # Ensure they are datetime objects before proceeding
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')

        def convert_series_to_utc(dt_series):
            if pd.api.types.is_datetime64_any_dtype(dt_series) and dt_series.notna().any():
                try:
                    if dt_series.dt.tz is None:
                        return dt_series.dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
                    else:
                        return dt_series.dt.tz_convert('UTC')
                except Exception as e:
                    # st.warning(f"Could not convert series to UTC: {e}") # Optional: warning for TZ conversion issues
                    return dt_series # Return original series if conversion fails
            return dt_series

        df['deliveryDate_dt_utc'] = convert_series_to_utc(df['deliveryDate_dt'])
        df['confirmationTimestamp_dt_utc'] = convert_series_to_utc(df['confirmationTimestamp_dt'])
        
        valid_dates_mask = df['deliveryDate_dt_utc'].notna() & df['confirmationTimestamp_dt_utc'].notna()
        df['days_to_confirmation'] = pd.NA # Initialize with pandas NA
        
        if valid_dates_mask.any():
            time_difference = (df.loc[valid_dates_mask, 'confirmationTimestamp_dt_utc'] - 
                               df.loc[valid_dates_mask, 'deliveryDate_dt_utc'])
            # Ensure the result of subtraction is timedelta before accessing .dt.days
            if pd.api.types.is_timedelta64_dtype(time_difference):
                df.loc[valid_dates_mask, 'days_to_confirmation'] = time_difference.dt.days
            else:
                st.warning("Time difference calculation for 'days_to_confirmation' did not result in timedelta. Check date types.")
        
        if df['days_to_confirmation'].isnull().all() and valid_dates_mask.any(): # If all were valid but calculation failed
            st.warning("Failed to calculate 'Days to Confirmation' for all valid rows. Check for extreme date values or calculation logic.")
    else:
        st.warning("Either 'deliveryDate_dt' or 'confirmationTimestamp_dt' (derived from 'deliveryDate'/'confirmationTimestamp') column is missing. Cannot calculate 'Days to Confirmation'.")
        df['days_to_confirmation'] = pd.NA


    if 'status' not in df.columns: st.warning("Column 'status' for success rate not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce') # Coerce errors to NaT
    else:
        st.warning("Column 'score' for average score not found.")
        df['score'] = pd.NA # Ensure column exists as NA if missing
            
    return df

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input, period_name=""): # period_name is unused, can remove
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA # Return neutral defaults for empty df

    total_onboardings = len(df_input)
    successful_onboardings = 0
    success_rate = 0.0
    avg_score = pd.NA # Use pandas NA for consistency
    avg_days_to_confirm = pd.NA

    if 'status' in df_input.columns:
        # Ensure case-insensitivity and handle potential mixed types
        successful_onboardings = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
        if total_onboardings > 0:
            success_rate = (successful_onboardings / total_onboardings) * 100
    
    if 'score' in df_input.columns and df_input['score'].notna().any(): # Check if any non-NA scores exist
        avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean() # .mean() handles NaNs
    
    if 'days_to_confirmation' in df_input.columns and df_input['days_to_confirmation'].notna().any():
        numeric_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce')
        if numeric_days.notna().any(): # Check again after coercion
             avg_days_to_confirm = numeric_days.mean()
    return total_onboardings, success_rate, avg_score, avg_days_to_confirm

def get_default_date_range(df_date_column_series):
    today = date.today()
    # Default to current month if no data, or data doesn't span a month
    default_start_date = today.replace(day=1) 
    default_end_date = today
    min_data_date, max_data_date = None, None

    if df_date_column_series is not None and not df_date_column_series.empty:
        # Ensure the series is actual date objects for min/max
        date_objects = pd.to_datetime(df_date_column_series, errors='coerce').dt.date
        valid_dates = date_objects.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min()
            max_data_date = valid_dates.max()
            
            # Try to set a sensible default range, e.g., last 30 days or full range if small
            # For MTD as default:
            default_start_date = max(today.replace(day=1), min_data_date) # Start of current month or min_data_date
            default_end_date = min(today, max_data_date) # Today or max_data_date

            # If the above results in start > end (e.g. all data is future), fallback to full data range
            if default_start_date > default_end_date : 
                default_start_date = min_data_date 
                default_end_date = max_data_date
            # Ensure default_start_date is not after default_end_date after all adjustments
            if default_start_date > default_end_date:
                default_start_date = min_data_date # Fallback

    return default_start_date, default_end_date, min_data_date, max_data_date

# --- Initialize Session State & Load Secrets (Done once at top by debug block) ---
# These are now primarily for app logic, secrets checked by debug block & within functions
# GOOGLE_SHEET_URL_OR_NAME and GOOGLE_WORKSHEET_NAME are fetched from secrets inside load_data_from_google_sheet

# Initialize session state variables if they don't exist
default_date_val_start, default_date_val_end, _, _ = get_default_date_range(None) # Initial default before data
if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'date_range_filter' not in st.session_state: st.session_state.date_range_filter = (default_date_val_start, default_date_val_end)
if 'repName_filter' not in st.session_state: st.session_state.repName_filter = []
if 'status_filter' not in st.session_state: st.session_state.status_filter = []
if 'clientSentiment_filter' not in st.session_state: st.session_state.clientSentiment_filter = []
if 'licenseNumber_search' not in st.session_state: st.session_state.licenseNumber_search = ""
if 'storeName_search' not in st.session_state: st.session_state.storeName_search = ""


# --- Data Loading Trigger ---
# Check if secrets for sheet are available before attempting to load
# The debug block at the top will have already printed status of these secrets
# This check is more for graceful failure if secrets are missing.
gs_url_secret = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
gs_worksheet_secret = st.secrets.get("GOOGLE_WORKSHEET_NAME")

if not st.session_state.data_loaded_successfully:
    if not gs_url_secret or not gs_worksheet_secret:
        # This error will appear if the secrets are missing, in addition to the debug output
        st.error("Application cannot load data: GOOGLE_SHEET_URL_OR_NAME or GOOGLE_WORKSHEET_NAME not found in Streamlit secrets.")
        # The st.stop() might be too aggressive here if we want the debug output to always show.
        # Consider allowing the app to proceed to show debug info, then it will fail gracefully later.
        # For now, keeping st.stop() as per original logic if critical secrets for data are missing.
        # However, the debug output is placed *before* this.
    else:
        with st.spinner("Connecting to Google Sheet and processing data... This may take a moment."):
            # Pass the secret values to the loading function, for cache invalidation purposes
            # even though the function also internally fetches them.
            df = load_data_from_google_sheet(gs_url_secret, gs_worksheet_secret) 
            if not df.empty:
                st.session_state.df_original = df
                st.session_state.data_loaded_successfully = True
                # Recalculate default date range based on actual loaded data
                ds, de, _, _ = get_default_date_range(df['onboarding_date_only'] if 'onboarding_date_only' in df else None)
                st.session_state.date_range_filter = (ds, de) if ds and de else (default_date_val_start, default_date_val_end)
            else:
                st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF
                st.session_state.data_loaded_successfully = False
                # Do not stop here, allow app to render with error messages if data loading fails

df_original = st.session_state.df_original # Get the loaded data (or empty DF) from session state

# --- Main Application UI Starts Here ---
st.title("🚀 Onboarding Performance Dashboard v2.2 🚀")

if not st.session_state.data_loaded_successfully or df_original.empty:
    # This message will show if data loading failed, even if secrets were present but data was empty or unreadable
    if not gs_url_secret or not gs_worksheet_secret:
         # This specific error about missing secrets might be redundant if the debug output already showed it
         pass # Error handled by debug block and initial check
    else:
        st.warning("Failed to load data, or the data source is empty or unreadable. Please check the Google Sheet content and permissions. Ensure the sheet and worksheet names in secrets are correct. You can try refreshing.")
    
    if st.sidebar.button("🔄 Force Refresh Data & Reload App", key="force_refresh_sidebar_initial_fail"):
        st.cache_data.clear() # Clear all @st.cache_data
        # Clear specific session state items related to data and filters
        keys_to_clear = ['data_loaded_successfully', 'df_original', 'date_range_filter', 
                         'repName_filter', 'status_filter', 'clientSentiment_filter',
                         'licenseNumber_search', 'storeName_search']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    # Do not st.stop() here, allow the rest of the UI (like sidebar) to render
    # This allows user to potentially retry or see debug info.

# --- Sidebar ---
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_button_sidebar"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False # Force reload
    # Clear filters as data context might change
    keys_to_clear_on_refresh = ['df_original', 'date_range_filter', 
                                'repName_filter', 'status_filter', 'clientSentiment_filter',
                                'licenseNumber_search', 'storeName_search']
    for key in keys_to_clear_on_refresh:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.sidebar.header("🔍 Filters")

# Initialize onboarding_dates_for_filter safely
onboarding_dates_for_filter = None
if 'onboarding_date_only' in df_original.columns and not df_original['onboarding_date_only'].empty:
    onboarding_dates_for_filter = df_original['onboarding_date_only']

def_start, def_end, min_dt_data, max_dt_data = get_default_date_range(onboarding_dates_for_filter)

# Ensure date_range_filter in session state is valid before use
if 'date_range_filter' not in st.session_state or \
   not (isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 and \
        isinstance(st.session_state.date_range_filter[0], date) and isinstance(st.session_state.date_range_filter[1], date)):
    st.session_state.date_range_filter = (def_start, def_end) if def_start and def_end else (date.today().replace(day=1), date.today())


if min_dt_data and max_dt_data and def_start and def_end: # Check if valid range could be determined
    # Ensure the default value for date_input is within min/max bounds
    current_filter_start, current_filter_end = st.session_state.date_range_filter
    # Clamp current filter values to be within the actual data range if they somehow went outside
    # This can happen if data changes upon refresh.
    clamped_start = max(min_dt_data, current_filter_start) if current_filter_start else min_dt_data
    clamped_end = min(max_dt_data, current_filter_end) if current_filter_end else max_dt_data
    
    # Ensure start is not after end after clamping
    if clamped_start and clamped_end and clamped_start > clamped_end:
        clamped_start = min_dt_data # Fallback to min_data_date
        clamped_end = max_dt_data # Fallback to max_data_date

    # If after clamping, any is None, it means data range is problematic, use overall min/max
    value_for_widget = (clamped_start if clamped_start else min_dt_data, 
                        clamped_end if clamped_end else max_dt_data)


    selected_date_range_widget = st.sidebar.date_input(
        "Onboarding Date Range:",
        value=value_for_widget, # Use clamped value
        min_value=min_dt_data,
        max_value=max_dt_data,
        key="date_range_selector_widget" 
    )
    # Update session state if the widget's value changes
    if selected_date_range_widget != st.session_state.date_range_filter:
        st.session_state.date_range_filter = selected_date_range_widget
else:
    st.sidebar.warning("Onboarding date data not available or insufficient for date range filter.")
# Ensure start_date_filter and end_date_filter are properly unpacked
start_date_filter, end_date_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)


expected_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
actual_search_cols_present = {k: v for k, v in expected_search_cols.items() if k in df_original.columns}

for col_key, display_name in actual_search_cols_present.items():
    # Ensure session state key exists
    if f"{col_key}_search" not in st.session_state:
        st.session_state[f"{col_key}_search"] = ""
    
    # Create widget and update session state based on widget's current value
    current_search_val = st.sidebar.text_input(
        f"Search by {display_name}:", 
        value=st.session_state[f"{col_key}_search"], 
        key=f"{col_key}_search_widget_{col_key}" # Ensure unique key
    )
    if current_search_val != st.session_state[f"{col_key}_search"]:
         st.session_state[f"{col_key}_search"] = current_search_val


categorical_filter_cols = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for col_name, display_label in categorical_filter_cols.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        # Convert to string, handle NaN, get unique, sort. Filter out empty strings after converting to unique.
        unique_values_series = df_original[col_name].astype(str).dropna()
        unique_values = sorted([val for val in unique_values_series.unique() if val.strip() != ""])


        if f"{col_name}_filter" not in st.session_state:
            st.session_state[f"{col_name}_filter"] = [] # Default to empty list
        
        # Ensure default selection is valid (subset of available options)
        current_selection = [val for val in st.session_state[f"{col_name}_filter"] if val in unique_values]

        selected_values_widget = st.sidebar.multiselect(
            f"Select {display_label}:", 
            options=unique_values, 
            default=current_selection, 
            key=f"{col_name}_filter_widget_{col_name}" # Unique key
        )
        # Update session state if the widget's selection changes
        if selected_values_widget != st.session_state[f"{col_name}_filter"]:
            st.session_state[f"{col_name}_filter"] = selected_values_widget
    # else: # Avoid printing "data not available" if column simply has no filterable data
    #     st.sidebar.text(f"{display_label} data not available or empty for filtering.")


def clear_all_filters_callback():
    # Reset date range filter to default based on current data (or overall default)
    ds_cb, de_cb, _, _ = get_default_date_range(st.session_state.df_original['onboarding_date_only'] if 'onboarding_date_only' in st.session_state.df_original else None)
    st.session_state.date_range_filter = (ds_cb, de_cb) if ds_cb and de_cb else (date.today().replace(day=1), date.today())
    
    # Reset text search filters
    for col_key_search in actual_search_cols_present: # Use actual_search_cols_present defined earlier
        st.session_state[f"{col_key_search}_search"] = ""
    
    # Reset multiselect filters
    for col_name_cat in categorical_filter_cols: # Use categorical_filter_cols defined earlier
        st.session_state[f"{col_name_cat}_filter"] = []
    
    # No need to manually update widget states if we do a rerun, but good practice for direct interaction.
    # For widgets, their values are tied to session_state keys if `key` param is used correctly.
    # A st.rerun() will cause them to pick up the new session_state values.

if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback, use_container_width=True, key="clear_filters_button"):
    st.rerun() # Rerun to apply cleared filters and refresh widgets

# --- Filtering Logic ---
# Start with a fresh copy of the original dataframe if it exists and is not empty
if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    df_filtered = st.session_state.df_original.copy()

    # Apply date range filter
    if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
        # Ensure the column is in datetime.date format for comparison, handling potential NaT
        date_objects_for_filtering = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
        df_filtered = df_filtered[
            date_objects_for_filtering.notna() &
            (date_objects_for_filtering >= start_date_filter) &
            (date_objects_for_filtering <= end_date_filter)
        ]
    
    # Apply text search filters
    for col_key, display_name in actual_search_cols_present.items():
        search_term = st.session_state.get(f"{col_key}_search", "")
        if search_term and col_key in df_filtered.columns: # Ensure column exists in current df_filtered
            df_filtered = df_filtered[df_filtered[col_key].astype(str).str.contains(search_term, case=False, na=False)]

    # Apply categorical multiselect filters
    for col_name, display_label in categorical_filter_cols.items():
        selected_values = st.session_state.get(f"{col_name}_filter", [])
        if selected_values and col_name in df_filtered.columns: # Ensure column exists
            df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(selected_values)]
else:
    df_filtered = pd.DataFrame() # Ensure df_filtered is an empty DataFrame if no original data


# --- Plotly Layout Configuration ---
plotly_layout_updates = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "font_color": PRIMARY_TEXT_COLOR, "title_font_color": GOLD_ACCENT_COLOR,
    "legend_font_color": PRIMARY_TEXT_COLOR, "title_x": 0.5,
    "xaxis_showgrid": False, "yaxis_showgrid": False # Cleaner look
}

# --- MTD Metrics Calculation ---
today_date = date.today()
current_month_start_date = today_date.replace(day=1)
prev_month_end_date = current_month_start_date - timedelta(days=1)
prev_month_start_date = prev_month_end_date.replace(day=1)
df_mtd_calc = pd.DataFrame()
df_prev_mtd_calc = pd.DataFrame()

# Ensure df_original is not empty and has the required date column
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    original_date_objects = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_original_dates_mask = original_date_objects.notna()
    
    if valid_original_dates_mask.any(): # Check if there's any valid date data at all
        df_original_valid_dates = df_original[valid_original_dates_mask]
        original_date_objects_valid = original_date_objects[valid_original_dates_mask]

        df_mtd_calc = df_original_valid_dates[
            (original_date_objects_valid >= current_month_start_date) &
            (original_date_objects_valid <= today_date)
        ]
        df_prev_mtd_calc = df_original_valid_dates[
            (original_date_objects_valid >= prev_month_start_date) &
            (original_date_objects_valid <= prev_month_end_date)
        ]

total_mtd, success_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd_calc)
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_calc) # Only need total for delta
mtd_onboarding_delta_val = None
if pd.notna(total_mtd) and pd.notna(total_prev_mtd):
    mtd_onboarding_delta_val = total_mtd - total_prev_mtd


# --- Main Content Tabs ---
# Ensure tabs are created even if df_filtered is empty, but content within them handles emptiness.
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1:
    st.header("📈 Month-to-Date (MTD) Overview")
    mtd_cols_display = st.columns(4)
    mtd_cols_display[0].metric(
        label="Total Onboardings MTD", value=total_mtd if pd.notna(total_mtd) else "0", 
        delta=(f"{mtd_onboarding_delta_val:+}" if pd.notna(mtd_onboarding_delta_val) else "N/A vs Prev Mth"),
        delta_color="normal" # Simplified delta color logic
    )
    mtd_cols_display[1].metric(label="Success Rate MTD", value=f"{success_mtd:.1f}%" if pd.notna(success_mtd) else "N/A")
    mtd_cols_display[2].metric(label="Avg Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    mtd_cols_display[3].metric(label="Avg Days to Confirm MTD", value=f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")

    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_filtered_val, success_filtered_val, score_filtered_val, days_filtered_val = calculate_metrics(df_filtered)
        filtered_cols_display = st.columns(4)
        filtered_cols_display[0].metric(label="Total Filtered Onboardings", value=total_filtered_val if pd.notna(total_filtered_val) else "0")
        filtered_cols_display[1].metric(label="Filtered Success Rate", value=f"{success_filtered_val:.1f}%" if pd.notna(success_filtered_val) else "N/A")
        filtered_cols_display[2].metric(label="Filtered Average Score", value=f"{score_filtered_val:.2f}" if pd.notna(score_filtered_val) else "N/A")
        filtered_cols_display[3].metric(label="Filtered Avg Days to Confirm", value=f"{days_filtered_val:.1f}" if pd.notna(days_filtered_val) else "N/A")
    else:
        st.info("No data matches the current filter criteria to display in Overview. Adjust filters or check data source.")

with tab2:
    st.header("📋 Filtered Onboarding Data Table")
    if not df_filtered.empty:
        def style_dataframe_conditionally(df_to_style):
            styled_df = df_to_style.style
            # Apply score gradient if column exists and has numeric data
            if 'score' in df_to_style.columns:
                scores_numeric = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_numeric.notna().any(): # Check if there's any numeric score data
                    styled_df = styled_df.background_gradient(subset=['score'], cmap='RdYlGn', low=0.3, high=0.7, gmap=scores_numeric) # Removed fillna for gmap
            # Apply days_to_confirmation gradient
            if 'days_to_confirmation' in df_to_style.columns:
                days_numeric = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_numeric.notna().any():
                     styled_df = styled_df.background_gradient(subset=['days_to_confirmation'], cmap='RdYlGn_r', gmap=days_numeric)
            return styled_df

        df_display_table = df_filtered.copy()
        # Sort by deliveryDate_dt if available and not all NaT
        if 'deliveryDate_dt' in df_display_table.columns and df_display_table['deliveryDate_dt'].notna().any():
            df_display_table_sorted = df_display_table.sort_values(by='deliveryDate_dt', ascending=True, na_position='last')
        else:
            df_display_table_sorted = df_display_table # Keep original order if sort key is problematic
        
        # Define columns to show, excluding intermediate UTC or original string columns
        cols_for_display = [
            col for col in df_display_table_sorted.columns 
            if not col.endswith('_utc') and \
               not col.endswith('_str_original') and \
               col not in ['onboardingDate_dt', 'deliveryDate_dt', 'confirmationTimestamp_dt'] # Show 'onboarding_date_only' instead
        ]
        # Ensure key date columns are present if original raw dates were dropped
        if 'onboardingDate' in df_display_table_sorted.columns and 'onboarding_date_only' not in cols_for_display:
            cols_for_display.insert(0, 'onboardingDate') # Or 'onboarding_date_only' if preferred

        st.dataframe(style_dataframe_conditionally(df_display_table_sorted[cols_for_display].reset_index(drop=True)), use_container_width=True, height=500) # Added height
        
        csv_download_data = convert_df_to_csv(df_filtered) # Use df_filtered for download
        st.download_button(label="📥 Download Filtered Data as CSV", data=csv_download_data, file_name='filtered_onboarding_data.csv', mime='text/csv', use_container_width=True, key="download_csv_button")
    elif not df_original.empty: # If original data was loaded but current filters yield nothing
        st.info("No data matches current filter criteria for table display. Try adjusting filters.")
    # If df_original is also empty, the message in Tab1 or initial load message covers it.

    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        viz_cols_in_detail_tab = st.columns(2)
        with viz_cols_in_detail_tab[0]:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                st.subheader("Onboarding Status")
                status_counts_chart = df_filtered['status'].value_counts().reset_index()
                # status_counts_chart.columns = ['status', 'count'] # Ensure column names
                fig_status_chart = px.bar(status_counts_chart, x='status', y='count', color='status', template="plotly_dark")
                fig_status_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_status_chart, use_container_width=True)
            
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                st.subheader("Onboardings by Rep")
                rep_counts_chart = df_filtered['repName'].value_counts().reset_index()
                # rep_counts_chart.columns = ['repName', 'count']
                fig_rep_chart = px.bar(rep_counts_chart, x='repName', y='count', color='repName', template="plotly_dark")
                fig_rep_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_rep_chart, use_container_width=True)

        with viz_cols_in_detail_tab[1]:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                st.subheader("Client Sentiment")
                sentiment_counts_chart = df_filtered['clientSentiment'].value_counts().reset_index()
                # sentiment_counts_chart.columns = ['clientSentiment', 'count']
                # Define a more robust color map
                sentiment_color_map = {}
                if 'clientSentiment' in sentiment_counts_chart.columns: # Check column exists
                    for sentiment_val in sentiment_counts_chart['clientSentiment'].unique():
                        s_lower = str(sentiment_val).lower()
                        if 'positive' in s_lower: sentiment_color_map[sentiment_val] = '#2ca02c' # Green
                        elif 'negative' in s_lower: sentiment_color_map[sentiment_val] = '#d62728' # Red
                        elif 'neutral' in s_lower: sentiment_color_map[sentiment_val] = GOLD_ACCENT_COLOR # Gold/Yellow
                        # else: sentiment_color_map[sentiment_val] = '#888888' # Default grey for others
                
                fig_sentiment_chart = px.pie(sentiment_counts_chart, names='clientSentiment', values='count', 
                                             hole=0.4, template="plotly_dark", 
                                             color='clientSentiment', color_discrete_map=sentiment_color_map)
                fig_sentiment_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_sentiment_chart, use_container_width=True)

            # Checklist Item Completion - more robust processing
            checklist_item_cols = ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 
                                   'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 
                                   'providePromoCreditLink']
            actual_checklist_cols = [col for col in checklist_item_cols if col in df_filtered.columns]
            processed_checklist_data = []

            if actual_checklist_cols:
                for b_col in actual_checklist_cols:
                    # Map various string/int representations of True/False to boolean, then to 0/1 for sum
                    # Ensure the mapping handles various cases robustly
                    map_to_bool_val = {'true': True, 'yes': True, '1': True, 1: True,
                                    'false': False, 'no': False, '0': False, 0: False}
                    
                    bool_series = df_filtered[b_col].astype(str).str.lower().map(map_to_bool_val)
                    bool_series = pd.to_numeric(bool_series, errors='coerce') # Converts True to 1, False to 0, others to NaN
                    
                    if bool_series.notna().any(): # If there are any valid (0 or 1) responses
                        true_count = bool_series.sum() # Sum of 1s (True)
                        total_valid_responses = bool_series.notna().sum() # Count of 0s and 1s

                        if total_valid_responses > 0:
                            # Create display name (simplified)
                            item_display_name = ' '.join(b_col.replace("onboarding", "")
                                                         .replace("provide", "Provided ")
                                                         .replace("confirm", "Confirmed ")
                                                         .split_camel_case_if_needed_or_just_title(b_col)).title() # (Pseudo-code for camel case splitting)
                            # Simpler way to generate display name from camelCase:
                            item_display_name = ''.join([' ' + char if char.isupper() else char for char in b_col]).replace("onboarding ", "").strip().title()


                            processed_checklist_data.append({
                                "Checklist Item": item_display_name, 
                                "Completion (%)": (true_count / total_valid_responses) * 100
                            })
                
                if processed_checklist_data:
                    st.subheader("Checklist Item Completion")
                    completion_df_chart = pd.DataFrame(processed_checklist_data)
                    if not completion_df_chart.empty:
                        fig_checklist_chart = px.bar(completion_df_chart.sort_values("Completion (%)", ascending=True), 
                                                     x="Completion (%)", y="Checklist Item", orientation='h', 
                                                     template="plotly_dark", color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        fig_checklist_chart.update_layout(plotly_layout_updates, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_checklist_chart, use_container_width=True)
    else: # If df_filtered is empty
        st.info("No data matches current filters to display detailed visuals. Adjust filters or check data source.")


with tab3:
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            st.subheader("Total Onboardings Over Time")
            df_trend_chart = df_filtered.copy()
            # Ensure 'onboarding_date_only' is datetime for resampling
            df_trend_chart['onboarding_date_only'] = pd.to_datetime(df_trend_chart['onboarding_date_only'], errors='coerce')
            df_trend_chart = df_trend_chart.dropna(subset=['onboarding_date_only']) # Drop rows where date conversion failed

            if not df_trend_chart.empty:
                # Determine resampling frequency based on data span
                date_span_days_trend = (df_trend_chart['onboarding_date_only'].max() - df_trend_chart['onboarding_date_only'].min()).days
                if date_span_days_trend <= 62 : freq_resample = 'D' # Daily for up to ~2 months
                elif date_span_days_trend <= 365 * 1.5 : freq_resample = 'W-MON' # Weekly for up to ~1.5 years
                else: freq_resample = 'ME' # Monthly ('M' is deprecated, use 'ME' for month-end or 'MS' for month-start)
                
                onboardings_over_time_data = df_trend_chart.set_index('onboarding_date_only').resample(freq_resample).size().reset_index(name='count')
                
                if not onboardings_over_time_data.empty:
                    fig_trend_line = px.line(onboardings_over_time_data, x='onboarding_date_only', y='count', 
                                             markers=True, template="plotly_dark", 
                                             labels={'onboarding_date_only': 'Date', 'count': 'Number of Onboardings'})
                    fig_trend_line.update_layout(plotly_layout_updates, title_text="Onboardings Over Filtered Period")
                    st.plotly_chart(fig_trend_line, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend after resampling.")
            else: 
                st.info("No valid date data available in filtered set for onboarding trend chart.")
        
        # Distribution of Days to Confirmation
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            st.subheader("Distribution of Days to Confirmation")
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist.empty:
                # Determine number of bins, ensure it's reasonable
                nbins_hist = max(10, min(50, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else 10
                if len(days_data_for_hist.unique()) < nbins_hist: # If fewer unique values than proposed bins
                    nbins_hist = len(days_data_for_hist.unique())

                fig_days_dist_hist = px.histogram(days_data_for_hist, nbins=nbins_hist, 
                                                  title="Days to Confirmation Distribution", 
                                                  template="plotly_dark", labels={'value': 'Days to Confirmation'})
                fig_days_dist_hist.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_days_dist_hist, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data in filtered set to plot distribution.")
    else: # If df_filtered is empty
        st.info("No data matches current filter criteria to display Trends & Distributions. Adjust filters or check data source.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.2 | Secured Access")