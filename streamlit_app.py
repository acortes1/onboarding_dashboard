import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
from collections.abc import Mapping # Keep this import for good practice
import time
import numpy as np
import matplotlib # Required for pandas styler background_gradient

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.2",
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
# This section can be removed once everything is working.
st.sidebar.subheader("Secrets Debug Output:") 
try:
    secret_keys = list(st.secrets.keys())
    st.sidebar.write(f"Available secret keys: {secret_keys}")

    if not secret_keys:
        st.sidebar.warning("No secrets loaded via st.secrets.keys().")

    expected_top_level_keys = ["APP_ACCESS_KEY", "APP_ACCESS_HINT", "GOOGLE_SHEET_URL_OR_NAME", "GOOGLE_WORKSHEET_NAME", "gcp_service_account"]
    
    st.sidebar.write("Checking individual expected secrets:")
    for key in expected_top_level_keys:
        secret_value = st.secrets.get(key)
        if secret_value is not None:
            st.sidebar.success(f"Secret '{key}' IS available.")
            if key == "gcp_service_account":
                is_mapping = isinstance(secret_value, Mapping) 
                has_type = hasattr(secret_value, 'get') and secret_value.get("type")
                has_pkey = hasattr(secret_value, 'get') and secret_value.get("private_key")
                has_cemail = hasattr(secret_value, 'get') and secret_value.get("client_email")

                if is_mapping and has_type and has_pkey and has_cemail:
                    st.sidebar.info(f"   '{key}' seems structured (has type, private_key, client_email).")
                else:
                    gcp_keys_present = list(secret_value.keys()) if hasattr(secret_value, 'keys') else "N/A (not dict-like)"
                    st.sidebar.warning(f"   '{key}' (type: {type(secret_value)}) may lack essential fields or not be fully dict-like for checks. Keys found: {gcp_keys_present}.")
        else:
            st.sidebar.error(f"Secret '{key}' is NOT available.")
except Exception as e:
    st.sidebar.error(f"Error accessing st.secrets: {e}")
st.sidebar.markdown("---") 
# --- END OF SECRETS DEBUGGING CODE ---

# --- Application Access Control ---
def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")

    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not found. Bypassing password.")
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

# --- Enhanced Debugging for Google Sheets ---
st.subheader("Google Sheets Loading Debug:") # This will appear on the main page

# --- Google Sheets Authentication and Data Loading ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread():
    st.write("Attempting to authenticate with Google (authenticate_gspread function)...")
    gcp_secrets = st.secrets.get("gcp_service_account")
    
    if gcp_secrets is None:
        st.error("❌ GCP service account secrets ('gcp_service_account') NOT FOUND in st.secrets.")
        return None
    st.write(f"✅ 'gcp_service_account' secret retrieved. Type: {type(gcp_secrets)}")

    # NEW DEBUG LINE: Print all available attributes and methods of gcp_secrets
    try:
        st.write(f"🕵️ Attributes/methods of gcp_secrets object: {dir(gcp_secrets)}")
    except Exception as dir_e:
        st.write(f"⚠️ Could not get dir() of gcp_secrets: {dir_e}")

    # TYPE CHECK (using hasattr, dir() output will help us understand if this is wrong)
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"❌ 'gcp_service_account' does not appear to have '.get()' or '.keys()' methods. Type: {type(gcp_secrets)}. Critical error.")
        return None
    st.write(f"✅ 'gcp_service_account' appears to have '.get()' and '.keys()' methods (type: {type(gcp_secrets)}).")

    required_gcp_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri"]
    missing_keys = [key for key in required_gcp_keys if gcp_secrets.get(key) is None] 
    
    if missing_keys:
        st.error(f"❌ 'gcp_service_account' is MISSING values for essential sub-keys: {', '.join(missing_keys)}. Check TOML values.")
        present_keys = list(gcp_secrets.keys()) if hasattr(gcp_secrets, 'keys') else "N/A"
        st.info(f"   Keys actually found in 'gcp_service_account' with values: {[k for k, v in gcp_secrets.items() if v is not None]}")
        st.info(f"   All keys found by .keys(): {present_keys}")
        return None
    st.write(f"✅ All required sub-keys appear to have values in 'gcp_service_account'. Client email: {gcp_secrets.get('client_email')}")

    try:
        st.write("Attempting Credentials.from_service_account_info(dict(gcp_secrets), ...)...")
        # Explicitly cast to dict for safety for the google-auth library.
        creds_dict = dict(gcp_secrets)
        st.write(f"   Service account email being used for credentials: {creds_dict.get('client_email')}") 
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES) 
        st.write("✅ Credentials.from_service_account_info() SUCCEEDED.")
        st.write("Attempting gspread.authorize(creds)...")
        gc = gspread.authorize(creds)
        st.write("✅ gspread.authorize(creds) SUCCEEDED.")
        return gc
    except Exception as e:
        st.error(f"❌ Google Sheets Auth Error during credential creation or authorization: {e}")
        st.error(f"   Type of gcp_secrets passed to Credentials (after casting): {type(creds_dict if 'creds_dict' in locals() else None)}")
        st.error("   Ensure the private_key is correctly formatted (including newlines \\n) and all gcp_service_account fields are accurate and have correct values.")
        return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    common_formats = [
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
    ]
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and \
       not series.astype(str).str.lower().isin(['', 'none', 'nan', 'nat', 'null']).all():
        original_success_rate = dates.notnull().sum()
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                if temp_dates.notnull().sum() > dates.notnull().sum():
                    dates = temp_dates
                if dates.notnull().all(): 
                    break
            except ValueError: 
                continue 
        if dates.notnull().sum() <= original_success_rate and original_success_rate < len(series):
             pass
    return dates

@st.cache_data(ttl=600)
def load_data_from_google_sheet(_sheet_url_or_name_param, _worksheet_name_param):
    st.write(f"--- load_data_from_google_sheet called with URL/Name: '{_sheet_url_or_name_param}', Worksheet: '{_worksheet_name_param}' ---")
    
    current_sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    current_worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")

    if not current_sheet_url_or_name:
        st.error("❌ GOOGLE_SHEET_URL_OR_NAME not found in secrets INSIDE load_data function.")
        return pd.DataFrame()
    st.write(f"✅ Using Sheet URL/Name from secrets: {current_sheet_url_or_name}")
    
    if not current_worksheet_name:
        st.error("❌ GOOGLE_WORKSHEET_NAME not found in secrets INSIDE load_data function.")
        return pd.DataFrame()
    st.write(f"✅ Using Worksheet Name from secrets: {current_worksheet_name}")

    gc = authenticate_gspread() 
    if gc is None:
        st.error("❌ Authentication failed (gc is None) in load_data_from_google_sheet.")
        return pd.DataFrame()
    st.write("✅ Authentication successful (gc object created) in load_data_from_google_sheet.")

    try:
        st.write(f"Attempting to open spreadsheet: '{current_sheet_url_or_name}'...")
        if "docs.google.com" in current_sheet_url_or_name or "spreadsheets.google.com" in current_sheet_url_or_name:
            spreadsheet = gc.open_by_url(current_sheet_url_or_name)
        else:
            spreadsheet = gc.open(current_sheet_url_or_name) 
        st.write(f"✅ Spreadsheet '{spreadsheet.title}' opened successfully.")
        
        st.write(f"Attempting to open worksheet: '{current_worksheet_name}'...")
        worksheet = spreadsheet.worksheet(current_worksheet_name)
        st.write(f"✅ Worksheet '{worksheet.title}' opened successfully.")
        
        st.write("Attempting to get all records from worksheet...")
        data = worksheet.get_all_records(head=1, expected_headers=None)
        
        if not data:
            st.warning("⚠️ No data records returned from worksheet.get_all_records(). The sheet might be empty or have only a header.")
            return pd.DataFrame()
        st.write(f"✅ Retrieved {len(data)} records (rows) from worksheet.")

        df = pd.DataFrame(data)
        st.sidebar.success(f"Loaded {len(df)} records from '{current_worksheet_name}'.") 
        if df.empty:
            st.warning("⚠️ DataFrame is empty after pd.DataFrame(data). This is unexpected if records were retrieved.")
            return pd.DataFrame()
        st.write("✅ DataFrame created successfully.")

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ SpreadsheetNotFound: Ensure '{current_sheet_url_or_name}' is correct, and the service account has explicit 'Viewer' (or 'Editor') access shared with it for this specific sheet.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ WorksheetNotFound: Worksheet '{current_worksheet_name}' not found in spreadsheet '{spreadsheet.title if 'spreadsheet' in locals() else 'unknown'}'. Check spelling and case sensitivity.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheet: {e}")
        st.error("   This could be due to various issues like API permissions in GCP, network problems, or unexpected sheet structure.")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_columns_to_parse = {
        'onboardingDate': 'onboardingDate_dt',
        'deliveryDate': 'deliveryDate_dt',
        'confirmationTimestamp': 'confirmationTimestamp_dt'
    }

    for original_col, new_dt_col in date_columns_to_parse.items():
        if original_col in df.columns:
            cleaned_series = df[original_col].astype(str).str.replace('\n', '', regex=False).str.strip()
            parsed_dates = robust_to_datetime(cleaned_series)
            df[new_dt_col] = parsed_dates
            is_mostly_empty_placeholders = cleaned_series.str.lower().isin(['', 'none', 'nan', 'nat', 'null']).all()
            if parsed_dates.isnull().all() and not is_mostly_empty_placeholders:
                 st.warning(f"Could not parse any dates in column '{original_col}'.")
            elif parsed_dates.isnull().any() and not is_mostly_empty_placeholders:
                 num_failed = parsed_dates.isnull().sum()
                 st.warning(f"{num_failed} out of {len(cleaned_series)} date(s) in '{original_col}' could not be parsed.")
            if original_col == 'onboardingDate':
                 df['onboarding_date_only'] = df[new_dt_col].dt.date
                 if df['onboarding_date_only'].isnull().all() and not is_mostly_empty_placeholders:
                    st.warning(f"Could not extract date part for any rows from '{original_col}'.")
        else:
            df[new_dt_col] = pd.NaT 
            if original_col == 'onboardingDate':
                df['onboarding_date_only'] = pd.NaT
    
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
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
                    return dt_series 
            return dt_series

        df['deliveryDate_dt_utc'] = convert_series_to_utc(df['deliveryDate_dt'])
        df['confirmationTimestamp_dt_utc'] = convert_series_to_utc(df['confirmationTimestamp_dt'])
        
        valid_dates_mask = df['deliveryDate_dt_utc'].notna() & df['confirmationTimestamp_dt_utc'].notna()
        df['days_to_confirmation'] = pd.NA 
        
        if valid_dates_mask.any():
            time_difference = (df.loc[valid_dates_mask, 'confirmationTimestamp_dt_utc'] - 
                               df.loc[valid_dates_mask, 'deliveryDate_dt_utc'])
            if pd.api.types.is_timedelta64_dtype(time_difference):
                df.loc[valid_dates_mask, 'days_to_confirmation'] = time_difference.dt.days
            else:
                st.warning("Time difference for 'days_to_confirmation' not timedelta.")
        
        if df['days_to_confirmation'].isnull().all() and valid_dates_mask.any():
            st.warning("Failed to calculate 'Days to Confirmation' for valid rows.")
    else:
        df['days_to_confirmation'] = pd.NA

    if 'status' not in df.columns: st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        df['score'] = pd.NA 
            
    return df

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input, period_name=""):
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA 
    total_onboardings = len(df_input)
    successful_onboardings = 0
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
    today = date.today()
    default_start_date = today.replace(day=1) 
    default_end_date = today
    min_data_date, max_data_date = None, None
    if df_date_column_series is not None and not df_date_column_series.empty:
        date_objects = pd.to_datetime(df_date_column_series, errors='coerce').dt.date
        valid_dates = date_objects.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min()
            max_data_date = valid_dates.max()
            default_start_date = max(today.replace(day=1), min_data_date)
            default_end_date = min(today, max_data_date) 
            if default_start_date > default_end_date : 
                default_start_date = min_data_date 
                default_end_date = max_data_date
            if default_start_date > default_end_date:
                default_start_date = min_data_date
    return default_start_date, default_end_date, min_data_date, max_data_date

default_date_val_start, default_date_val_end, _, _ = get_default_date_range(None)
if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'date_range_filter' not in st.session_state: st.session_state.date_range_filter = (default_date_val_start, default_date_val_end)
if 'repName_filter' not in st.session_state: st.session_state.repName_filter = []
if 'status_filter' not in st.session_state: st.session_state.status_filter = []
if 'clientSentiment_filter' not in st.session_state: st.session_state.clientSentiment_filter = []
if 'licenseNumber_search' not in st.session_state: st.session_state.licenseNumber_search = ""
if 'storeName_search' not in st.session_state: st.session_state.storeName_search = ""

gs_url_secret = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
gs_worksheet_secret = st.secrets.get("GOOGLE_WORKSHEET_NAME")

if not st.session_state.data_loaded_successfully:
    if not gs_url_secret or not gs_worksheet_secret:
        st.error("Config Error: GOOGLE_SHEET_URL_OR_NAME or GOOGLE_WORKSHEET_NAME not in secrets. Cannot load data.")
    else:
        st.write(f"--- Attempting initial data load (gs_url_secret: {bool(gs_url_secret)}, gs_worksheet_secret: {bool(gs_worksheet_secret)}) ---")
        with st.spinner("Connecting to Google Sheet and processing data... This may take a moment."):
            df = load_data_from_google_sheet(gs_url_secret, gs_worksheet_secret) 
            if not df.empty:
                st.session_state.df_original = df
                st.session_state.data_loaded_successfully = True
                st.write("✅ Initial data load successful, df_original populated.")
                ds, de, _, _ = get_default_date_range(df['onboarding_date_only'] if 'onboarding_date_only' in df else None)
                st.session_state.date_range_filter = (ds, de) if ds and de else (default_date_val_start, default_date_val_end)
            else:
                st.session_state.df_original = pd.DataFrame() 
                st.session_state.data_loaded_successfully = False
                st.warning("⚠️ Initial data load returned an empty DataFrame.")

df_original = st.session_state.df_original 

st.title("🚀 Onboarding Performance Dashboard v2.2 🚀")
st.markdown("---")

if not st.session_state.data_loaded_successfully or df_original.empty:
    if not gs_url_secret or not gs_worksheet_secret:
         pass 
    else:
        st.error("Failed to load data, or the data source is empty or unreadable. Please check the Google Sheet content and permissions. Ensure the sheet and worksheet names in secrets are correct. You can try refreshing. Review messages under 'Google Sheets Loading Debug' above for details.")
    
    if st.sidebar.button("🔄 Force Refresh Data & Reload App", key="force_refresh_sidebar_initial_fail"):
        st.cache_data.clear() 
        keys_to_clear = ['data_loaded_successfully', 'df_original', 'date_range_filter', 
                         'repName_filter', 'status_filter', 'clientSentiment_filter',
                         'licenseNumber_search', 'storeName_search']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_button_sidebar"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False 
    keys_to_clear_on_refresh = ['df_original', 'date_range_filter', 
                                'repName_filter', 'status_filter', 'clientSentiment_filter',
                                'licenseNumber_search', 'storeName_search']
    for key in keys_to_clear_on_refresh:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.sidebar.header("🔍 Filters")
onboarding_dates_for_filter = None
if 'onboarding_date_only' in df_original.columns and not df_original['onboarding_date_only'].empty:
    onboarding_dates_for_filter = df_original['onboarding_date_only']
def_start, def_end, min_dt_data, max_dt_data = get_default_date_range(onboarding_dates_for_filter)
if 'date_range_filter' not in st.session_state or \
   not (isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 and \
        isinstance(st.session_state.date_range_filter[0], date) and isinstance(st.session_state.date_range_filter[1], date)):
    st.session_state.date_range_filter = (def_start, def_end) if def_start and def_end else (date.today().replace(day=1), date.today())

if min_dt_data and max_dt_data and def_start and def_end: 
    current_filter_start, current_filter_end = st.session_state.date_range_filter
    clamped_start = max(min_dt_data, current_filter_start) if current_filter_start else min_dt_data
    clamped_end = min(max_dt_data, current_filter_end) if current_filter_end else max_dt_data
    if clamped_start and clamped_end and clamped_start > clamped_end:
        clamped_start = min_dt_data 
        clamped_end = max_dt_data 
    value_for_widget = (clamped_start if clamped_start else min_dt_data, 
                        clamped_end if clamped_end else max_dt_data)
    selected_date_range_widget = st.sidebar.date_input(
        "Onboarding Date Range:", value=value_for_widget, 
        min_value=min_dt_data, max_value=max_dt_data, key="date_range_selector_widget" 
    )
    if selected_date_range_widget != st.session_state.date_range_filter:
        st.session_state.date_range_filter = selected_date_range_widget
else:
    st.sidebar.warning("Onboarding date data not available for date range filter.")
start_date_filter, end_date_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)

expected_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
actual_search_cols_present = {k: v for k, v in expected_search_cols.items() if k in df_original.columns}
for col_key, display_name in actual_search_cols_present.items():
    if f"{col_key}_search" not in st.session_state: st.session_state[f"{col_key}_search"] = ""
    current_search_val = st.sidebar.text_input(
        f"Search by {display_name}:", value=st.session_state[f"{col_key}_search"], 
        key=f"{col_key}_search_widget_{col_key}" 
    )
    if current_search_val != st.session_state[f"{col_key}_search"]:
         st.session_state[f"{col_key}_search"] = current_search_val

categorical_filter_cols = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for col_name, display_label in categorical_filter_cols.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values_series = df_original[col_name].astype(str).dropna()
        unique_values = sorted([val for val in unique_values_series.unique() if val.strip() != ""])
        if f"{col_name}_filter" not in st.session_state: st.session_state[f"{col_name}_filter"] = []
        current_selection = [val for val in st.session_state[f"{col_name}_filter"] if val in unique_values]
        selected_values_widget = st.sidebar.multiselect(
            f"Select {display_label}:", options=unique_values, default=current_selection, 
            key=f"{col_name}_filter_widget_{col_name}"
        )
        if selected_values_widget != st.session_state[f"{col_name}_filter"]:
            st.session_state[f"{col_name}_filter"] = selected_values_widget

def clear_all_filters_callback():
    ds_cb, de_cb, _, _ = get_default_date_range(st.session_state.df_original['onboarding_date_only'] if 'onboarding_date_only' in st.session_state.df_original else None)
    st.session_state.date_range_filter = (ds_cb, de_cb) if ds_cb and de_cb else (date.today().replace(day=1), date.today())
    for col_key_search in actual_search_cols_present: 
        st.session_state[f"{col_key_search}_search"] = ""
    for col_name_cat in categorical_filter_cols: 
        st.session_state[f"{col_name_cat}_filter"] = []
if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback, use_container_width=True, key="clear_filters_button"):
    st.rerun() 

if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    df_filtered = st.session_state.df_original.copy()
    if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
        date_objects_for_filtering = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
        df_filtered = df_filtered[
            date_objects_for_filtering.notna() &
            (date_objects_for_filtering >= start_date_filter) &
            (date_objects_for_filtering <= end_date_filter)
        ]
    for col_key, display_name in actual_search_cols_present.items():
        search_term = st.session_state.get(f"{col_key}_search", "")
        if search_term and col_key in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered[col_key].astype(str).str.contains(search_term, case=False, na=False)]
    for col_name, display_label in categorical_filter_cols.items():
        selected_values = st.session_state.get(f"{col_name}_filter", [])
        if selected_values and col_name in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(selected_values)]
else:
    df_filtered = pd.DataFrame() 

plotly_layout_updates = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "font_color": PRIMARY_TEXT_COLOR, "title_font_color": GOLD_ACCENT_COLOR,
    "legend_font_color": PRIMARY_TEXT_COLOR, "title_x": 0.5,
    "xaxis_showgrid": False, "yaxis_showgrid": False 
}
today_date = date.today()
current_month_start_date = today_date.replace(day=1)
prev_month_end_date = current_month_start_date - timedelta(days=1)
prev_month_start_date = prev_month_end_date.replace(day=1)
df_mtd_calc = pd.DataFrame()
df_prev_mtd_calc = pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    original_date_objects = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_original_dates_mask = original_date_objects.notna()
    if valid_original_dates_mask.any(): 
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
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_calc) 
mtd_onboarding_delta_val = None
if pd.notna(total_mtd) and pd.notna(total_prev_mtd):
    mtd_onboarding_delta_val = total_mtd - total_prev_mtd

tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])
with tab1:
    st.header("📈 Month-to-Date (MTD) Overview")
    mtd_cols_display = st.columns(4)
    mtd_cols_display[0].metric(
        label="Total Onboardings MTD", value=total_mtd if pd.notna(total_mtd) else "0", 
        delta=(f"{mtd_onboarding_delta_val:+}" if pd.notna(mtd_onboarding_delta_val) else "N/A vs Prev Mth"),
        delta_color="normal" 
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
            if 'score' in df_to_style.columns:
                scores_numeric = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_numeric.notna().any(): 
                    styled_df = styled_df.background_gradient(subset=['score'], cmap='RdYlGn', low=0.3, high=0.7, gmap=scores_numeric)
            if 'days_to_confirmation' in df_to_style.columns:
                days_numeric = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_numeric.notna().any():
                     styled_df = styled_df.background_gradient(subset=['days_to_confirmation'], cmap='RdYlGn_r', gmap=days_numeric)
            return styled_df
        df_display_table = df_filtered.copy()
        if 'deliveryDate_dt' in df_display_table.columns and df_display_table['deliveryDate_dt'].notna().any():
            df_display_table_sorted = df_display_table.sort_values(by='deliveryDate_dt', ascending=True, na_position='last')
        else:
            df_display_table_sorted = df_display_table 
        cols_for_display = [
            col for col in df_display_table_sorted.columns 
            if not col.endswith('_utc') and \
               not col.endswith('_str_original') and \
               col not in ['onboardingDate_dt', 'deliveryDate_dt', 'confirmationTimestamp_dt'] 
        ]
        if 'onboardingDate' in df_display_table_sorted.columns and 'onboarding_date_only' not in cols_for_display:
            cols_for_display.insert(0, 'onboardingDate')
        st.dataframe(style_dataframe_conditionally(df_display_table_sorted[cols_for_display].reset_index(drop=True)), use_container_width=True, height=500) 
        csv_download_data = convert_df_to_csv(df_filtered) 
        st.download_button(label="📥 Download Filtered Data as CSV", data=csv_download_data, file_name='filtered_onboarding_data.csv', mime='text/csv', use_container_width=True, key="download_csv_button")
    elif not df_original.empty: 
        st.info("No data matches current filter criteria for table display. Try adjusting filters.")
    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        viz_cols_in_detail_tab = st.columns(2)
        with viz_cols_in_detail_tab[0]:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                st.subheader("Onboarding Status")
                status_counts_chart = df_filtered['status'].value_counts().reset_index()
                fig_status_chart = px.bar(status_counts_chart, x='status', y='count', color='status', template="plotly_dark")
                fig_status_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_status_chart, use_container_width=True)
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                st.subheader("Onboardings by Rep")
                rep_counts_chart = df_filtered['repName'].value_counts().reset_index()
                fig_rep_chart = px.bar(rep_counts_chart, x='repName', y='count', color='repName', template="plotly_dark")
                fig_rep_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_rep_chart, use_container_width=True)
        with viz_cols_in_detail_tab[1]:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                st.subheader("Client Sentiment")
                sentiment_counts_chart = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map = {}
                if 'clientSentiment' in sentiment_counts_chart.columns: 
                    for sentiment_val in sentiment_counts_chart['clientSentiment'].unique():
                        s_lower = str(sentiment_val).lower()
                        if 'positive' in s_lower: sentiment_color_map[sentiment_val] = '#2ca02c' 
                        elif 'negative' in s_lower: sentiment_color_map[sentiment_val] = '#d62728' 
                        elif 'neutral' in s_lower: sentiment_color_map[sentiment_val] = GOLD_ACCENT_COLOR
                fig_sentiment_chart = px.pie(sentiment_counts_chart, names='clientSentiment', values='count', 
                                             hole=0.4, template="plotly_dark", 
                                             color='clientSentiment', color_discrete_map=sentiment_color_map)
                fig_sentiment_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_sentiment_chart, use_container_width=True)
            checklist_item_cols = ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 
                                   'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 
                                   'providePromoCreditLink']
            actual_checklist_cols = [col for col in checklist_item_cols if col in df_filtered.columns]
            processed_checklist_data = []
            if actual_checklist_cols:
                for b_col in actual_checklist_cols:
                    map_to_bool_val = {'true': True, 'yes': True, '1': True, 1: True,
                                    'false': False, 'no': False, '0': False, 0: False}
                    bool_series = df_filtered[b_col].astype(str).str.lower().map(map_to_bool_val)
                    bool_series = pd.to_numeric(bool_series, errors='coerce') 
                    if bool_series.notna().any(): 
                        true_count = bool_series.sum() 
                        total_valid_responses = bool_series.notna().sum() 
                        if total_valid_responses > 0:
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
    else: 
        st.info("No data matches current filters to display detailed visuals.")
with tab3:
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            st.subheader("Total Onboardings Over Time")
            df_trend_chart = df_filtered.copy()
            df_trend_chart['onboarding_date_only'] = pd.to_datetime(df_trend_chart['onboarding_date_only'], errors='coerce')
            df_trend_chart = df_trend_chart.dropna(subset=['onboarding_date_only']) 
            if not df_trend_chart.empty:
                date_span_days_trend = (df_trend_chart['onboarding_date_only'].max() - df_trend_chart['onboarding_date_only'].min()).days
                if date_span_days_trend <= 62 : freq_resample = 'D' 
                elif date_span_days_trend <= 365 * 1.5 : freq_resample = 'W-MON' 
                else: freq_resample = 'ME' 
                onboardings_over_time_data = df_trend_chart.set_index('onboarding_date_only').resample(freq_resample).size().reset_index(name='count')
                if not onboardings_over_time_data.empty:
                    fig_trend_line = px.line(onboardings_over_time_data, x='onboarding_date_only', y='count', 
                                             markers=True, template="plotly_dark", 
                                             labels={'onboarding_date_only': 'Date', 'count': 'Number of Onboardings'})
                    fig_trend_line.update_layout(plotly_layout_updates, title_text="Onboardings Over Filtered Period")
                    st.plotly_chart(fig_trend_line, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend.")
            else: 
                st.info("No valid date data for onboarding trend chart.")
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            st.subheader("Distribution of Days to Confirmation")
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist.empty:
                nbins_hist = max(10, min(50, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else 10
                if len(days_data_for_hist.unique()) < nbins_hist: 
                    nbins_hist = len(days_data_for_hist.unique())
                fig_days_dist_hist = px.histogram(days_data_for_hist, nbins=nbins_hist, 
                                                  title="Days to Confirmation Distribution", 
                                                  template="plotly_dark", labels={'value': 'Days to Confirmation'})
                fig_days_dist_hist.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_days_dist_hist, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data to plot distribution.")
    else: 
        st.info("No data matches current filter criteria to display Trends & Distributions.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.2 | Secured Access")