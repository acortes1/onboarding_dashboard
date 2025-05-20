# Import necessary libraries
import streamlit as st  # For creating the web application interface
import pandas as pd  # For data manipulation and analysis (DataFrames)
import plotly.express as px  # For creating interactive charts easily
import plotly.graph_objects as go  # For more control over Plotly charts
from datetime import datetime, date, timedelta  # For working with dates and times
from dateutil.relativedelta import relativedelta  # For more complex date calculations
import gspread  # For interacting with Google Sheets API
from google.oauth2.service_account import Credentials  # For authenticating with Google services
from collections.abc import Mapping  # For robustly checking if an object is dictionary-like
import time  # For time-related functions (not actively used but often useful)
import numpy as np  # For numerical operations, often a dependency for Pandas
import re  # For regular expressions, used here for parsing transcripts
import matplotlib # Imported because pandas styling (e.g., background_gradient) might use it under the hood

# --- Page Configuration ---
# This function must be the first Streamlit command in your script, except for comments.
# It sets up the basic properties of the web page, like its title in the browser tab,
# the icon (favicon), and the layout (wide means it uses the full width of the screen).
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.11", # Updated version for this fix
    page_icon="🛠️", # A tool emoji for fixing
    layout="wide"
)

# --- Custom Styling (CSS) ---
# These are global CSS styles to customize the appearance of the Streamlit app.
# Streamlit allows embedding HTML and CSS using st.markdown with unsafe_allow_html=True.
GOLD_ACCENT_COLOR = "#FFD700"  # Define a gold color for accents
PRIMARY_TEXT_COLOR = "#FFFFFF"  # White text for good contrast on dark backgrounds
SECONDARY_TEXT_COLOR = "#B0B0B0"  # Light gray for less prominent text
BACKGROUND_COLOR = "#0E1117"  # Default dark background color of Streamlit (for reference)
PLOT_BG_COLOR = "rgba(0,0,0,0)"  # Transparent background for plots for a seamless look

# The st.markdown function is used to render Markdown text.
# By setting unsafe_allow_html=True, we can embed HTML and CSS.
st.markdown(f"""
<style>
    /* General App Styles */
    .stApp > header {{ background-color: transparent; }} /* Remove Streamlit's default header background */
    h1 {{ color: {GOLD_ACCENT_COLOR}; text-align: center; padding-top: 0.5em; padding-bottom: 0.5em; }} /* Main title style */
    h2, h3 {{ color: {GOLD_ACCENT_COLOR}; border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important; padding-bottom: 0.3em; }} /* Sub-header styles with gold underline */
    
    /* Metric Widget Styles */
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{ color: {PRIMARY_TEXT_COLOR} !important; }} /* Text color for metric parts */
    div[data-testid="stMetricValue"] > div {{ font-size: 1.85rem; }} /* Larger font for the main metric value */
    
    /* Expander Styles */
    .streamlit-expanderHeader {{ color: {GOLD_ACCENT_COLOR} !important; font-weight: bold; }} /* Style for expander titles */
    
    /* DataFrame Styles */
    .stDataFrame {{ border: 1px solid #333; }} /* Add a subtle border to DataFrames */
    
    /* Paragraph Text (CSS selectors might change with future Streamlit versions) */
    .css-1d391kg p, .css- F_1U7P p {{ color: {PRIMARY_TEXT_COLOR} !important; }}
    
    /* Tab Styles */
    button[data-baseweb="tab"] {{ background-color: transparent !important; color: {SECONDARY_TEXT_COLOR} !important; border-bottom: 2px solid transparent !important; }} /* Default tab style */
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {GOLD_ACCENT_COLOR} !important; border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important; font-weight: bold; }} /* Active tab style */
    
    /* Transcript Viewer Specific Styles */
    .transcript-summary-grid {{ 
        display: grid; /* Use CSS Grid for a responsive layout of summary items */
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* Columns adjust to fit content */
        gap: 12px; 
        margin-bottom: 18px; 
    }}
    .transcript-summary-item strong {{ color: {GOLD_ACCENT_COLOR}; }} /* Highlight labels in the summary */
    .transcript-summary-item-fullwidth {{ /* Class for summary items that should span the full width */
        grid-column: 1 / -1; /* Make this item span all available columns in the grid */
        margin-top: 5px;
    }}
    .requirement-item {{ 
        margin-bottom: 10px; /* Spacing for checklist items in transcript view */
        padding-left: 5px;
        border-left: 3px solid #444; /* Subtle left border for visual grouping */
    }}
    .requirement-item .type {{ /* Style for [Primary] / [Secondary] tag within requirement items */
        font-weight: bold;
        color: {SECONDARY_TEXT_COLOR};
        font-size: 0.9em;
        margin-left: 5px;
    }}
    .transcript-container {{ 
        background-color: #262730; /* Dark background for the transcript box */
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #333; 
        max-height: 400px; /* Limit height and make it scrollable if content exceeds */
        overflow-y: auto; 
        font-family: monospace; /* Monospace font for better readability of transcripts */
    }}
    .transcript-line {{ 
        margin-bottom: 8px; /* Space between lines in the transcript */
        line-height: 1.4; /* Improve line spacing */
        word-wrap: break-word; /* Ensure long lines without spaces wrap */
        white-space: pre-wrap; /* Preserve newlines and spaces from the original transcript */
    }}
    .transcript-line strong {{ 
        color: {GOLD_ACCENT_COLOR}; /* Highlight speaker names in the transcript */
    }}
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
# This function checks if the user has provided the correct access key (password).
def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY") # Get password from secrets
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.") # Get hint, with a default
    
    # Bypass password if not set in secrets (for local development)
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set in secrets. Bypassing password for local development.")
        return True # Allow access

    # Initialize 'password_entered' in session_state if it doesn't exist
    if "password_entered" not in st.session_state: 
        st.session_state.password_entered = False

    # If password already entered correctly, allow access
    if st.session_state.password_entered: 
        return True

    # Display password input form
    with st.form("password_form_main_app"): # Unique key for the form
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint)
        submitted = st.form_submit_button("Submit")
        if submitted: # If form submitted
            if password_attempt == app_password: # Check password
                st.session_state.password_entered = True # Mark as entered
                st.rerun() # Rerun app to show main content
            else: 
                st.error("Incorrect Access Key. Please try again.")
                return False # Deny access
    return False # Deny access if form not submitted or password wrong

# Stop script execution if password check fails
if not check_password(): 
    st.stop() 

# --- Constants ---
# SCOPES define the level of access the script requests from Google APIs.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',  # Access to read/write Google Sheets
          'https://www.googleapis.com/auth/drive']         # Access to Google Drive (often needed for Sheets)

# Dictionary storing detailed information about each key requirement for display purposes.
KEY_REQUIREMENT_DETAILS = {
    'expectationsSet': {
        "description": "Client expectations were clearly set.",
        "type": "Bonus Criterion", # Classification for display (e.g., in transcript view)
        "chart_label": "Expectations Set" # Shorter label used in charts
    },
    'introSelfAndDIME': {
        "description": "Warmly introduce yourself and DIME Industries.",
        "type": "Secondary",
        "chart_label": "Intro Self & DIME"
    },
    'confirmKitReceived': {
        "description": "Confirm the reseller has received their onboarding kit and initial order.",
        "type": "Primary",
        "chart_label": "Kit & Order Received"
    },
    'offerDisplayHelp': {
        "description": "Ask whether they need help setting up the in-store display kit.",
        "type": "Secondary",
        "chart_label": "Offer Display Help"
    },
    'scheduleTrainingAndPromo': {
        "description": "Schedule a budtender-training session and the first promotional event.",
        "type": "Primary",
        "chart_label": "Schedule Training & Promo"
    },
    'providePromoCreditLink': {
        "description": "Provide the link for submitting future promo-credit reimbursement requests.",
        "type": "Secondary",
        "chart_label": "Provide Promo Link"
    }
}
# A list to maintain a specific order when displaying or iterating through these checklist items.
ORDERED_KEY_CHECKLIST_ITEMS = [
    'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
    'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink'
]

# --- Google Sheets Authentication and Data Loading Functions ---

# Authenticates with Google using service account credentials.
def authenticate_gspread():
    gcp_secrets = st.secrets.get("gcp_service_account") # Get service account JSON from secrets
    if gcp_secrets is None: 
        st.error("GCP service account secrets ('gcp_service_account') NOT FOUND. App cannot authenticate."); return None
    
    # Check if the secret is dictionary-like (has .get and .keys methods)
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"GCP service account secrets ('gcp_service_account') is not structured correctly (type: {type(gcp_secrets)}). App cannot authenticate."); return None
    
    # Ensure all required keys for service account are present in the secret.
    required_keys_for_gcp = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_gcp_keys = [key for key in required_keys_for_gcp if gcp_secrets.get(key) is None]
    if missing_gcp_keys: 
        st.error(f"GCP service account secrets is MISSING values for essential sub-keys: {', '.join(missing_gcp_keys)}. App cannot authenticate."); return None
    
    try:
        # Create credentials object from the service account info.
        # Explicitly cast gcp_secrets to dict() for compatibility with the google-auth library.
        credentials_obj = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES) 
        # Authorize gspread (Google Sheets Python client) with these credentials.
        return gspread.authorize(credentials_obj)
    except Exception as e: 
        st.error(f"Google Sheets Authentication Error: {e}"); return None

# Converts a Pandas Series of date-like strings to datetime objects, trying multiple common formats.
def robust_to_datetime(date_series_to_parse):
    # Attempt initial conversion using Pandas' smart parsing.
    parsed_dates_series = pd.to_datetime(date_series_to_parse, errors='coerce', infer_datetime_format=True)
    
    # List of common date formats to try if initial parsing fails for a significant portion.
    common_date_formats_list = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', 
                                '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    # If many values are still NaT (Not a Time) and the series isn't just empty strings/placeholders:
    if not date_series_to_parse.empty and \
       parsed_dates_series.isnull().sum() > len(date_series_to_parse) * 0.7 and \
       not date_series_to_parse.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        for date_format_str in common_date_formats_list:
            try:
                temp_parsed_dates = pd.to_datetime(date_series_to_parse, format=date_format_str, errors='coerce')
                # If this format successfully parses more dates, update our result.
                if temp_parsed_dates.notnull().sum() > parsed_dates_series.notnull().sum(): 
                    parsed_dates_series = temp_parsed_dates
                if parsed_dates_series.notnull().all(): break # Exit if all dates are now parsed
            except ValueError: continue # Ignore formats that are completely incompatible
    return parsed_dates_series

# Loads data from the specified Google Sheet. Cached for performance.
@st.cache_data(ttl=600) # Cache results for 10 minutes
def load_data_from_google_sheet(_sheet_url_or_name_for_cache, _worksheet_name_for_cache): # Args are for cache key
    # Retrieve actual sheet URL and name from secrets inside the function.
    google_sheet_url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    google_worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    
    if not google_sheet_url: st.error("Configuration Error: GOOGLE_SHEET_URL_OR_NAME missing in secrets."); return pd.DataFrame()
    if not google_worksheet_name: st.error("Configuration Error: GOOGLE_WORKSHEET_NAME missing in secrets."); return pd.DataFrame()
    
    gspread_client = authenticate_gspread() # Authenticate with Google
    if gspread_client is None: return pd.DataFrame() # Return empty DataFrame if auth fails
    
    try:
        # Open spreadsheet by URL or by name.
        spreadsheet_obj = gspread_client.open_by_url(google_sheet_url) if "docs.google.com" in google_sheet_url else gspread_client.open(google_sheet_url) 
        worksheet_obj = spreadsheet_obj.worksheet(google_worksheet_name) # Open the specific worksheet
        raw_data_from_sheet = worksheet_obj.get_all_records(head=1, expected_headers=None) # Get all data
        
        if not raw_data_from_sheet: st.warning("No data records found in the Google Sheet."); return pd.DataFrame()
        df_loaded = pd.DataFrame(raw_data_from_sheet) # Convert to Pandas DataFrame
        st.sidebar.success(f"Successfully loaded {len(df_loaded)} records from '{google_worksheet_name}'.") 
        if df_loaded.empty: st.warning("DataFrame is empty after loading from Google Sheet."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound: 
        st.error(f"Spreadsheet Not Found: '{google_sheet_url}'. Check URL/Name & service account permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: 
        st.error(f"Worksheet Not Found: '{google_worksheet_name}'. Check name (case-sensitive)."); return pd.DataFrame()
    except Exception as e: 
        st.error(f"An error occurred while loading data from Google Sheet: {e}"); return pd.DataFrame()

    # --- Data Cleaning and Preprocessing ---
    df_loaded.columns = df_loaded.columns.str.strip() # Clean column names
    
    date_columns_to_process = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for original_col_name, new_datetime_col_name in date_columns_to_process.items():
        if original_col_name in df_loaded.columns:
            cleaned_date_series = df_loaded[original_col_name].astype(str).str.replace('\n','',regex=False).str.strip()
            df_loaded[new_datetime_col_name] = robust_to_datetime(cleaned_date_series)
            if original_col_name == 'onboardingDate': 
                df_loaded['onboarding_date_only'] = df_loaded[new_datetime_col_name].dt.date
        else: 
            df_loaded[new_datetime_col_name] = pd.NaT 
            if original_col_name == 'onboardingDate': df_loaded['onboarding_date_only'] = pd.NaT
    
    if 'deliveryDate_dt' in df_loaded.columns and 'confirmationTimestamp_dt' in df_loaded.columns:
        df_loaded['deliveryDate_dt'] = pd.to_datetime(df_loaded['deliveryDate_dt'], errors='coerce')
        df_loaded['confirmationTimestamp_dt'] = pd.to_datetime(df_loaded['confirmationTimestamp_dt'], errors='coerce')
        def convert_datetime_to_utc(dt_series_to_convert): 
            if pd.api.types.is_datetime64_any_dtype(dt_series_to_convert) and dt_series_to_convert.notna().any():
                try: 
                    return dt_series_to_convert.dt.tz_localize('UTC') if dt_series_to_convert.dt.tz is None else dt_series_to_convert.dt.tz_convert('UTC')
                except Exception: return dt_series_to_convert
            return dt_series_to_convert
        df_loaded['days_to_confirmation'] = (convert_datetime_to_utc(df_loaded['confirmationTimestamp_dt']) - convert_datetime_to_utc(df_loaded['deliveryDate_dt'])).dt.days
    else: 
        df_loaded['days_to_confirmation'] = pd.NA

    string_cols_to_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary']
    for str_col_name in string_cols_to_ensure:
        if str_col_name not in df_loaded.columns: df_loaded[str_col_name] = ""
        else: df_loaded[str_col_name] = df_loaded[str_col_name].astype(str).fillna("")
    
    if 'score' not in df_loaded.columns: df_loaded['score'] = pd.NA
    df_loaded['score'] = pd.to_numeric(df_loaded['score'], errors='coerce')
    
    checklist_cols_to_ensure_exist = ORDERED_KEY_CHECKLIST_ITEMS + ['onboardingWelcome'] 
    for checklist_col_name in checklist_cols_to_ensure_exist:
        if checklist_col_name not in df_loaded.columns: df_loaded[checklist_col_name] = pd.NA 
            
    return df_loaded

# --- Helper Functions ---
@st.cache_data # Cache this function's result
def convert_df_to_csv(df_for_csv): 
    return df_for_csv.to_csv(index=False).encode('utf-8') # Convert DataFrame to CSV bytes

# Calculates key performance metrics from a DataFrame.
def calculate_metrics(df_input_for_metrics):
    if df_input_for_metrics.empty: return 0, 0.0, pd.NA, pd.NA 
    total_records_metrics = len(df_input_for_metrics)
    success_rate_metrics = (df_input_for_metrics[df_input_for_metrics['status'].astype(str).str.lower()=='confirmed'].shape[0]/total_records_metrics*100) if total_records_metrics>0 else 0.0
    avg_score_metrics = pd.to_numeric(df_input_for_metrics['score'], errors='coerce').mean()
    avg_days_metrics = pd.to_numeric(df_input_for_metrics['days_to_confirmation'], errors='coerce').mean()
    return total_records_metrics, success_rate_metrics, avg_score_metrics, avg_days_metrics

# Determines a default date range for filters.
def get_default_date_range(date_series_for_default_range):
    today_for_range = date.today()
    start_date_default_range = today_for_range.replace(day=1) # Default: start of current month
    end_date_default_range = today_for_range # Default: today
    min_date_in_data, max_date_in_data = None, None
    
    if date_series_for_default_range is not None and not date_series_for_default_range.empty:
        parsed_dates_for_range_calc = pd.to_datetime(date_series_for_default_range, errors='coerce').dt.date.dropna()
        if not parsed_dates_for_range_calc.empty:
            min_date_in_data = parsed_dates_for_range_calc.min()
            max_date_in_data = parsed_dates_for_range_calc.max()
            start_date_default_range = max(start_date_default_range, min_date_in_data)
            end_date_default_range = min(end_date_default_range, max_date_in_data)
            if start_date_default_range > end_date_default_range: # If default range is invalid
                start_date_default_range, end_date_default_range = min_date_in_data, max_date_in_data
    return start_date_default_range, end_date_default_range, min_date_in_data, max_date_in_data

# --- Initialize Session State ---
# Set up default values for variables that need to persist across user interactions.
default_start_date_for_ss, default_end_date_for_ss, _, _ = get_default_date_range(None)
session_state_key_value_pairs = {
    'data_loaded_successfully': False, 'df_original': pd.DataFrame(),
    'date_range_filter': (default_start_date_for_ss, default_end_date_for_ss),
    'repName_filter': [], 'status_filter': [], 'clientSentiment_filter': [],
    'licenseNumber_search': "", 'storeName_search': "",
    'selected_transcript_key': None 
}
for session_key, session_default_value in session_state_key_value_pairs.items():
    if session_key not in st.session_state: 
        st.session_state[session_key] = session_default_value

# --- Data Loading Trigger ---
# Load data if it hasn't been loaded successfully yet in this session.
if not st.session_state.data_loaded_successfully:
    gs_url_secret_for_load = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    gs_worksheet_secret_for_load = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not gs_url_secret_for_load or not gs_worksheet_secret_for_load: 
        st.error("Configuration Error: Google Sheet URL/Name or Worksheet Name missing in Streamlit secrets.")
    else:
        with st.spinner("Loading onboarding data... This may take a moment."): 
            main_loaded_df = load_data_from_google_sheet(gs_url_secret_for_load, gs_worksheet_secret_for_load) 
            if not main_loaded_df.empty:
                st.session_state.df_original = main_loaded_df 
                st.session_state.data_loaded_successfully = True
                ds_main_load, de_main_load, _, _ = get_default_date_range(main_loaded_df.get('onboarding_date_only'))
                st.session_state.date_range_filter = (ds_main_load, de_main_load) if ds_main_load and de_main_load else (default_start_date_for_ss, default_end_date_for_ss)
            else: 
                st.session_state.df_original = pd.DataFrame() 
                st.session_state.data_loaded_successfully = False
df_original = st.session_state.df_original 

# --- Main Application UI ---
st.title("🚀 Onboarding Performance Dashboard v2.10 🚀") 

if not st.session_state.data_loaded_successfully or df_original.empty:
    st.error("Failed to load data. Please check Google Sheet content, permissions, and secret configurations. You can try refreshing the data.")
    if st.sidebar.button("🔄 Force Refresh Data", key="refresh_button_on_fail_sidebar"):
        st.cache_data.clear(); st.session_state.clear(); st.rerun()

# Sidebar: Scoring System Explanation
with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)

# Sidebar: Data Controls
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_data_button_sidebar_main"):
    st.cache_data.clear(); st.session_state.clear(); st.rerun()

# Sidebar: Filters
st.sidebar.header("🔍 Filters")
onboarding_dates_for_sidebar_date_filter = df_original.get('onboarding_date_only')
def_start_date_sidebar, def_end_date_sidebar, min_date_sidebar, max_date_sidebar = get_default_date_range(onboarding_dates_for_sidebar_date_filter)
if 'date_range_filter' not in st.session_state or \
   not (isinstance(st.session_state.date_range_filter,tuple) and len(st.session_state.date_range_filter)==2 and \
        all(isinstance(d_val, date) for d_val in st.session_state.date_range_filter)): 
    st.session_state.date_range_filter = (def_start_date_sidebar,def_end_date_sidebar) if def_start_date_sidebar and def_end_date_sidebar else (date.today().replace(day=1),date.today())

if min_date_sidebar and max_date_sidebar and def_start_date_sidebar and def_end_date_sidebar:
    current_val_start_sidebar, current_val_end_sidebar = st.session_state.date_range_filter
    widget_val_start_sidebar = max(min_date_sidebar,current_val_start_sidebar) if current_val_start_sidebar else min_date_sidebar
    widget_val_end_sidebar = min(max_date_sidebar,current_val_end_sidebar) if current_val_end_sidebar else max_date_sidebar
    if widget_val_start_sidebar and widget_val_end_sidebar and widget_val_start_sidebar > widget_val_end_sidebar:
        widget_val_start_sidebar, widget_val_end_sidebar = min_date_sidebar, max_date_sidebar 
    
    selected_date_range_sidebar_widget = st.sidebar.date_input("Date Range:",
                                         value=(widget_val_start_sidebar, widget_val_end_sidebar), 
                                         min_value=min_date_sidebar,max_value=max_date_sidebar,key="date_selector_sidebar_ui_widget")
    if selected_date_range_sidebar_widget != st.session_state.date_range_filter: 
        st.session_state.date_range_filter = selected_date_range_sidebar_widget
else: 
    st.sidebar.warning("Onboarding date data not available for range filter.")
start_date_filter_active_main, end_date_filter_active_main = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter,tuple) and len(st.session_state.date_range_filter)==2 else (None,None)

search_cols_definitions_sidebar_main = {"licenseNumber":"License Number", "storeName":"Store Name"}
for col_key_search_main, display_label_search_main in search_cols_definitions_sidebar_main.items():
    if f"{col_key_search_main}_search" not in st.session_state: st.session_state[f"{col_key_search_main}_search"]=""
    input_val_search_main = st.sidebar.text_input(f"Search {display_label_search_main} (on all data):",
                                           value=st.session_state[f"{col_key_search_main}_search"],
                                           key=f"{col_key_search_main}_search_input_widget_main")
    if input_val_search_main != st.session_state[f"{col_key_search_main}_search"]: 
        st.session_state[f"{col_key_search_main}_search"]=input_val_search_main

cat_filters_definitions_sidebar_main = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_name_cat_main, display_label_cat_main in cat_filters_definitions_sidebar_main.items():
    if col_name_cat_main in df_original.columns and df_original[col_name_cat_main].notna().any():
        options_cat_main = sorted([val_cat for val_cat in df_original[col_name_cat_main].astype(str).dropna().unique() if val_cat.strip()])
        if f"{col_name_cat_main}_filter" not in st.session_state: st.session_state[f"{col_name_cat_main}_filter"]=[]
        current_selection_cat_main = [val_cat_sel for val_cat_sel in st.session_state[f"{col_name_cat_main}_filter"] if val_cat_sel in options_cat_main]
        new_selection_cat_main = st.sidebar.multiselect(f"Filter by {display_label_cat_main}:",
                                                 options_cat_main,default=current_selection_cat_main,
                                                 key=f"{col_name_cat_main}_multiselect_widget_main")
        if new_selection_cat_main != st.session_state[f"{col_name_cat_main}_filter"]: 
            st.session_state[f"{col_name_cat_main}_filter"]=new_selection_cat_main

def clear_all_filters_callback_main():
    ds_cb_main, de_cb_main, _, _ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range_filter = (ds_cb_main,de_cb_main) if ds_cb_main and de_cb_main else (date.today().replace(day=1),date.today())
    for key_search_main_cb in search_cols_definitions_sidebar_main: st.session_state[f"{key_search_main_cb}_search"]=""
    for key_cat_main_cb in cat_filters_definitions_sidebar_main: st.session_state[f"{key_cat_main_cb}_filter"]=[]
    st.session_state.selected_transcript_key = None 
if st.sidebar.button("🧹 Clear All Filters",on_click=clear_all_filters_callback_main,use_container_width=True): 
    st.rerun() 

# --- Filtering Logic (Revised for search order) ---
df_filtered = pd.DataFrame() 
if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    df_working_copy_for_filtering = st.session_state.df_original.copy()
    license_search_term_for_filter = st.session_state.get("licenseNumber_search", "")
    if license_search_term_for_filter and "licenseNumber" in df_working_copy_for_filtering.columns:
        df_working_copy_for_filtering = df_working_copy_for_filtering[df_working_copy_for_filtering['licenseNumber'].astype(str).str.contains(license_search_term_for_filter, case=False, na=False)]
    store_search_term_for_filter = st.session_state.get("storeName_search", "")
    if store_search_term_for_filter and "storeName" in df_working_copy_for_filtering.columns:
        df_working_copy_for_filtering = df_working_copy_for_filtering[df_working_copy_for_filtering['storeName'].astype(str).str.contains(store_search_term_for_filter, case=False, na=False)]
    if start_date_filter_active_main and end_date_filter_active_main and 'onboarding_date_only' in df_working_copy_for_filtering.columns:
        parsed_dates_for_date_filter = pd.to_datetime(df_working_copy_for_filtering['onboarding_date_only'], errors='coerce').dt.date
        date_filter_mask_apply = parsed_dates_for_date_filter.notna() & (parsed_dates_for_date_filter >= start_date_filter_active_main) & (parsed_dates_for_date_filter <= end_date_filter_active_main)
        df_working_copy_for_filtering = df_working_copy_for_filtering[date_filter_mask_apply]
    for col_name_cat_filter_apply, _ in cat_filters_definitions_sidebar_main.items(): 
        selected_values_cat_filter_apply = st.session_state.get(f"{col_name_cat_filter_apply}_filter", [])
        if selected_values_cat_filter_apply and col_name_cat_filter_apply in df_working_copy_for_filtering.columns: 
            df_working_copy_for_filtering = df_working_copy_for_filtering[df_working_copy_for_filtering[col_name_cat_filter_apply].astype(str).isin(selected_values_cat_filter_apply)]
    df_filtered = df_working_copy_for_filtering.copy() 
else: df_filtered = pd.DataFrame() 

# --- Plotly Layout Configuration ---
# CORRECTED Variable name used here
plotly_base_layout_settings = {"plot_bgcolor":PLOT_BG_COLOR, "paper_bgcolor":PLOT_BG_COLOR, "font_color":PRIMARY_TEXT_COLOR, 
                               "title_font_color":GOLD_ACCENT_COLOR, "legend_font_color":PRIMARY_TEXT_COLOR, 
                               "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":False}

# --- MTD Metrics Calculation ---
today_date_for_mtd_metrics = date.today(); mtd_start_calc = today_date_for_mtd_metrics.replace(day=1)
prev_month_end_mtd_calc = mtd_start_calc - timedelta(days=1); prev_month_start_mtd_calc = prev_month_end_mtd_calc.replace(day=1)
df_current_mtd_calc, df_prev_mtd_calc = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_series_mtd_calc = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date
    valid_mask_mtd_calc = dates_series_mtd_calc.notna()
    if valid_mask_mtd_calc.any():
        df_valid_mtd_calc = df_original[valid_mask_mtd_calc].copy(); valid_dates_mtd_calc = dates_series_mtd_calc[valid_mask_mtd_calc]
        mtd_mask_calc = (valid_dates_mtd_calc >= mtd_start_calc) & (valid_dates_mtd_calc <= today_date_for_mtd_metrics)
        prev_mask_calc = (valid_dates_mtd_calc >= prev_month_start_mtd_calc) & (valid_dates_mtd_calc <= prev_month_end_mtd_calc)
        df_current_mtd_calc = df_valid_mtd_calc[mtd_mask_calc.values]; df_prev_mtd_calc = df_valid_mtd_calc[prev_mask_calc.values]
total_mtd_val, sr_mtd_val, score_mtd_val, days_mtd_val = calculate_metrics(df_current_mtd_calc)
total_prev_val,_,_,_ = calculate_metrics(df_prev_mtd_calc) 
delta_mtd_val = total_mtd_val - total_prev_val if pd.notna(total_mtd_val) and pd.notna(total_prev_val) else None

# --- Main Content Tabs ---
tab1_main_content, tab2_main_content, tab3_main_content = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1_main_content: 
    st.header("📈 Month-to-Date (MTD) Overview")
    col1_tab1, col2_tab1, col3_tab1, col4_tab1 = st.columns(4)
    col1_tab1.metric("Onboardings MTD", total_mtd_val or "0", f"{delta_mtd_val:+}" if delta_mtd_val is not None else "N/A")
    col2_tab1.metric("Success Rate MTD", f"{sr_mtd_val:.1f}%" if pd.notna(sr_mtd_val) else "N/A")
    col3_tab1.metric("Avg Score MTD", f"{score_mtd_val:.2f}" if pd.notna(score_mtd_val) else "N/A")
    col4_tab1.metric("Avg Days to Confirm MTD", f"{days_mtd_val:.1f}" if pd.notna(days_mtd_val) else "N/A")
    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        tot_filt_tab1, sr_filt_tab1, score_filt_tab1, days_filt_tab1 = calculate_metrics(df_filtered)
        fc1_tab1,fc2_tab1,fc3_tab1,fc4_tab1 = st.columns(4)
        fc1_tab1.metric("Filtered Onboardings", tot_filt_tab1 or "0")
        fc2_tab1.metric("Filtered Success Rate", f"{sr_filt_tab1:.1f}%" if pd.notna(sr_filt_tab1) else "N/A")
        fc3_tab1.metric("Filtered Avg Score", f"{score_filt_tab1:.2f}" if pd.notna(score_filt_tab1) else "N/A")
        fc4_tab1.metric("Filtered Avg Days Confirm", f"{days_filt_tab1:.1f}" if pd.notna(days_filt_tab1) else "N/A")
    else: st.info("No data matches current filters for Overview.")

with tab2_main_content: 
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table_for_tab2_content = df_filtered.copy().reset_index(drop=True) 
    
    cols_to_try_for_main_table = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                                  'clientSentiment', 'days_to_confirmation'] + ORDERED_KEY_CHECKLIST_ITEMS
    cols_for_main_table_display_final = [col for col in cols_to_try_for_main_table if col in df_display_table_for_tab2_content.columns]
    other_cols_for_main_table = [col for col in df_display_table_for_tab2_content.columns 
                                 if col not in cols_for_main_table_display_final and 
                                    not col.endswith(('_utc', '_str_original', '_dt')) and 
                                    col not in ['fullTranscript', 'summary']] 
    cols_for_main_table_display_final.extend(other_cols_for_main_table)

    if not df_display_table_for_tab2_content.empty:
        def style_dataframe_for_tab2_display(df_to_style_in_tab2): 
            styled_df_in_tab2 = df_to_style_in_tab2.style
            if 'score' in df_to_style_in_tab2.columns: 
                scores_numeric_for_style_tab2 = pd.to_numeric(df_to_style_in_tab2['score'], errors='coerce')
                if scores_numeric_for_style_tab2.notna().any():
                    styled_df_in_tab2 = styled_df_in_tab2.background_gradient(subset=['score'],cmap='RdYlGn',low=0.3,high=0.7, gmap=scores_numeric_for_style_tab2)
            if 'days_to_confirmation' in df_to_style_in_tab2.columns:
                days_numeric_for_style_tab2 = pd.to_numeric(df_to_style_in_tab2['days_to_confirmation'], errors='coerce')
                if days_numeric_for_style_tab2.notna().any():
                    styled_df_in_tab2 = styled_df_in_tab2.background_gradient(subset=['days_to_confirmation'],cmap='RdYlGn_r', gmap=days_numeric_for_style_tab2)
            return styled_df_in_tab2
        st.dataframe(style_dataframe_for_tab2_display(df_display_table_for_tab2_content[cols_for_main_table_display_final]), 
                     use_container_width=True, height=300) 
        
        st.markdown("---") 
        st.subheader("🔍 View Full Onboarding Details & Transcript")
        
        if not df_display_table_for_tab2_content.empty and 'fullTranscript' in df_display_table_for_tab2_content.columns:
            transcript_options_map_for_selectbox = {
                f"Idx {idx_for_selectbox}: {row_for_selectbox.get('storeName', 'N/A')} ({row_for_selectbox.get('onboardingDate', 'N/A')})": idx_for_selectbox 
                for idx_for_selectbox, row_for_selectbox in df_display_table_for_tab2_content.iterrows()
            }
            if transcript_options_map_for_selectbox: 
                if 'selected_transcript_key' not in st.session_state: st.session_state.selected_transcript_key = None
                selected_key_from_transcript_selectbox = st.selectbox("Select onboarding to view details:",
                    options=[None] + list(transcript_options_map_for_selectbox.keys()), index=0, 
                    format_func=lambda x_select: "Choose an entry..." if x_select is None else x_select, 
                    key="transcript_selector_widget_main_tab2")
                if selected_key_from_transcript_selectbox != st.session_state.selected_transcript_key:
                    st.session_state.selected_transcript_key = selected_key_from_transcript_selectbox
                
                if st.session_state.selected_transcript_key :
                    selected_row_index_for_transcript = transcript_options_map_for_selectbox[st.session_state.selected_transcript_key]
                    selected_onboarding_row_details = df_display_table_for_tab2_content.loc[selected_row_index_for_transcript]
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html_output_details = "<div class='transcript-summary-grid'>"
                    summary_data_items_details = { 
                        "Store": selected_onboarding_row_details.get('storeName', 'N/A'), 
                        "Rep": selected_onboarding_row_details.get('repName', 'N/A'),
                        "Score": selected_onboarding_row_details.get('score', 'N/A'),
                        "Status": selected_onboarding_row_details.get('status', 'N/A'),
                        "Sentiment": selected_onboarding_row_details.get('clientSentiment', 'N/A')
                    }
                    for item_label_details, item_value_details in summary_data_items_details.items():
                        summary_html_output_details += f"<div class='transcript-summary-item'><strong>{item_label_details}:</strong> {item_value_details}</div>"
                    
                    data_summary_text_from_sheet = selected_onboarding_row_details.get('summary', 'N/A') 
                    summary_html_output_details += f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary (from data):</strong> {data_summary_text_from_sheet}</div>"
                    
                    summary_html_output_details += "</div>" 
                    st.markdown(summary_html_output_details, unsafe_allow_html=True)

                    st.markdown("##### Key Requirement Checks:")
                    for item_column_name_details in ORDERED_KEY_CHECKLIST_ITEMS:
                        requirement_details_obj = KEY_REQUIREMENT_DETAILS.get(item_column_name_details)
                        if requirement_details_obj: 
                            item_description_details = requirement_details_obj.get("description", item_column_name_details.replace('_',' ').title())
                            item_type_details = requirement_details_obj.get("type", "") 
                            
                            item_value_str_details = str(selected_onboarding_row_details.get(item_column_name_details, "")).lower()
                            is_requirement_met_details = item_value_str_details in ['true', '1', 'yes']
                            status_emoji_details = "✅" if is_requirement_met_details else "❌"
                            
                            type_tag_html = f"<span class='type'>[{item_type_details}]</span>" if item_type_details else ""
                            st.markdown(f"<div class='requirement-item'>{status_emoji_details} {item_description_details} {type_tag_html}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---") 
                    st.markdown("##### Full Transcript:")
                    transcript_content_details = selected_onboarding_row_details.get('fullTranscript', "")
                    if transcript_content_details:
                        html_transcript_output_details = "<div class='transcript-container'>"
                        processed_transcript_content_details = transcript_content_details.replace('\\n', '\n') 
                        
                        for line_segment_from_transcript_details in processed_transcript_content_details.split('\n'):
                            current_line_details = line_segment_from_transcript_details.strip()
                            if not current_line_details: continue 
                            
                            parts_of_line_details = current_line_details.split(":", 1)
                            speaker_html_part_details = f"<strong>{parts_of_line_details[0].strip()}:</strong>" if len(parts_of_line_details) == 2 else ""
                            message_html_part_details = parts_of_line_details[1].strip().replace('\n', '<br>') if len(parts_of_line_details) == 2 else current_line_details.replace('\n', '<br>')
                            
                            html_transcript_output_details += f"<p class='transcript-line'>{speaker_html_part_details} {message_html_part_details}</p>"
                        html_transcript_output_details += "</div>"
                        st.markdown(html_transcript_output_details, unsafe_allow_html=True)
                    else: 
                        st.info("No transcript available for this selection or the transcript is empty.")
        else: 
            st.info("No data in the filtered table to select a transcript from, or 'fullTranscript' column is missing.")
        st.markdown("---") 

        csv_data_to_download_tab2_final = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data as CSV", csv_data_to_download_tab2_final, 'filtered_onboarding_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: 
        st.info("No data matches current filter criteria for table display.")
    
    st.header("📊 Key Visuals (Based on Filtered Data)") 
    if not df_filtered.empty:
        col_viz1_tab2_charts, col_viz2_tab2_charts = st.columns(2) 
        with col_viz1_tab2_charts: 
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_fig_tab2_chart = px.bar(df_filtered['status'].value_counts().reset_index(), x='status', y='count', 
                                     color='status', title="Onboarding Status Distribution")
                status_fig_tab2_chart.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig_tab2_chart, use_container_width=True) # CORRECTED variable name
            
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_fig_tab2_chart = px.bar(df_filtered['repName'].value_counts().reset_index(), x='repName', y='count', 
                                     color='repName', title="Onboardings by Representative")
                rep_fig_tab2_chart.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig_tab2_chart, use_container_width=True) # CORRECTED variable name
        
        with col_viz2_tab2_charts: 
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sentiment_counts_tab2_chart = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map_config_tab2 = {
                    str(s_tab2_chart).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s_tab2_chart).lower() else 
                                     ('#2ca02c' if 'positive' in str(s_tab2_chart).lower() else 
                                      ('#d62728' if 'negative' in str(s_tab2_chart).lower() else None)))
                    for s_tab2_chart in sentiment_counts_tab2_chart['clientSentiment'].unique()
                }
                sentiment_fig_tab2_chart = px.pie(sentiment_counts_tab2_chart, names='clientSentiment', values='count', hole=0.4, 
                                     title="Client Sentiment Breakdown", color='clientSentiment', 
                                     color_discrete_map=sentiment_color_map_config_tab2)
                sentiment_fig_tab2_chart.update_layout(plotly_base_layout_settings); st.plotly_chart(sentiment_fig_tab2_chart, use_container_width=True) # CORRECTED variable name

            df_confirmed_tab2_chart = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            actual_key_cols_tab2_chart = [col_tab2_chart for col_tab2_chart in ORDERED_KEY_CHECKLIST_ITEMS if col_tab2_chart in df_confirmed_tab2_chart.columns]
            checklist_data_tab2_chart = []
            if not df_confirmed_tab2_chart.empty and actual_key_cols_tab2_chart:
                for item_col_name_tab2_chart_viz in actual_key_cols_tab2_chart:
                    item_details_for_chart_viz = KEY_REQUIREMENT_DETAILS.get(item_col_name_tab2_chart_viz)
                    chart_label_for_item_chart_viz = item_details_for_chart_viz.get("chart_label", item_col_name_tab2_chart_viz.replace('_',' ').title()) if item_details_for_chart_viz else item_col_name_tab2_chart_viz.replace('_',' ').title()
                    
                    map_bool_tab2_chart = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                    if item_col_name_tab2_chart_viz in df_confirmed_tab2_chart.columns:
                        bool_s_tab2_chart = pd.to_numeric(df_confirmed_tab2_chart[item_col_name_tab2_chart_viz].astype(str).str.lower().map(map_bool_tab2_chart), errors='coerce')
                        if bool_s_tab2_chart.notna().any():
                            true_c_tab2_chart, total_v_tab2_chart = bool_s_tab2_chart.sum(), bool_s_tab2_chart.notna().sum()
                            if total_v_tab2_chart > 0:
                                checklist_data_tab2_chart.append({"Key Requirement": chart_label_for_item_chart_viz, 
                                                                  "Completion (%)": (true_c_tab2_chart/total_v_tab2_chart)*100})
                if checklist_data_tab2_chart:
                    df_checklist_chart_tab2_final = pd.DataFrame(checklist_data_tab2_chart)
                    if not df_checklist_chart_tab2_final.empty:
                        checklist_fig_tab2_final = px.bar(df_checklist_chart_tab2_final.sort_values("Completion (%)",ascending=True), 
                                                     x="Completion (%)", y="Key Requirement", orientation='h', 
                                                     title="Key Requirement Completion (Confirmed Onboardings)", 
                                                     color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        checklist_fig_tab2_final.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}) # CORRECTED variable name
                        st.plotly_chart(checklist_fig_tab2_final, use_container_width=True)
                else: 
                    st.info("No data available for key requirement completion chart (e.g., no confirmed onboardings with checklist data).")
            else: 
                st.info("No 'confirmed' onboardings in the filtered data, or relevant checklist columns are missing, to show key requirement completion.")
    else: 
        st.info("No data matches current filter criteria to display detailed visuals.")

with tab3_main_content: # Content for "Trends & Distributions" tab
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_tab3_viz = df_filtered.copy()
            df_trend_tab3_viz['onboarding_date_only'] = pd.to_datetime(df_trend_tab3_viz['onboarding_date_only'], errors='coerce')
            df_trend_tab3_viz.dropna(subset=['onboarding_date_only'], inplace=True) 
            
            if not df_trend_tab3_viz.empty:
                span_tab3_viz = (df_trend_tab3_viz['onboarding_date_only'].max() - df_trend_tab3_viz['onboarding_date_only'].min()).days
                freq_tab3_viz = 'D' if span_tab3_viz <= 62 else ('W-MON' if span_tab3_viz <= 365*1.5 else 'ME')
                data_tab3_viz = df_trend_tab3_viz.set_index('onboarding_date_only').resample(freq_tab3_viz).size().reset_index(name='count')
                if not data_tab3_viz.empty:
                    fig_trend_tab3_viz = px.line(data_tab3_viz, x='onboarding_date_only', y='count', markers=True, 
                                      title="Onboardings Over Filtered Period")
                    fig_trend_tab3_viz.update_layout(plotly_base_layout_settings) # CORRECTED variable name
                    st.plotly_chart(fig_trend_tab3_viz, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend after resampling.")
            else: 
                st.info("No valid date data available in filtered set for onboarding trend chart.")
        
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_tab3_viz = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_tab3_viz.empty:
                nbins_tab3_viz = max(10, min(50, int(len(days_data_tab3_viz)/5))) if len(days_data_tab3_viz) > 20 else (len(days_data_tab3_viz.unique()) or 10)
                fig_days_dist_tab3_viz = px.histogram(days_data_tab3_viz, nbins=nbins_tab3_viz, 
                                           title="Days to Confirmation Distribution")
                fig_days_dist_tab3_viz.update_layout(plotly_base_layout_settings) # CORRECTED variable name
                st.plotly_chart(fig_days_dist_tab3_viz, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data in filtered set to plot distribution.")
    else: 
        st.info("No data matches current filter criteria to display Trends & Distributions.")

st.sidebar.markdown("---") # Visual separator in sidebar
st.sidebar.info("Dashboard v2.10 | Secured Access") # App version info in sidebar

