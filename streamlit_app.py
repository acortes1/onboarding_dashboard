# Import necessary libraries
import streamlit as st  # For creating the web application interface
import pandas as pd  # For data manipulation and analysis (DataFrames)
import plotly.express as px  # For creating interactive charts easily
import plotly.graph_objects as go  # For more control over Plotly charts (not heavily used here but good to have)
from datetime import datetime, date, timedelta  # For working with dates and times
from dateutil.relativedelta import relativedelta  # For more complex date calculations (e.g., months ago)
import gspread  # For interacting with Google Sheets API
from google.oauth2.service_account import Credentials  # For authenticating with Google services using a service account
from collections.abc import Mapping  # For robustly checking if an object is dictionary-like
import time  # For time-related functions (not actively used but often useful)
import numpy as np  # For numerical operations, often a dependency for Pandas
import re  # For regular expressions, used here for parsing transcripts
import matplotlib # Imported because pandas styling (e.g., background_gradient) might use it under the hood

# --- Page Configuration ---
# This sets up the basic properties of the web page, like its title in the browser tab,
# the icon, and the layout (wide means it uses the full width of the screen).
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.8", # Version increment for annotation
    page_icon="🧑‍🏫", # Using a teacher emoji to signify explanation
    layout="wide"
)

# --- Custom Styling (CSS) ---
# These are global CSS styles to customize the appearance of the Streamlit app.
# Streamlit allows embedding HTML and CSS using st.markdown with unsafe_allow_html=True.
GOLD_ACCENT_COLOR = "#FFD700"  # Define a gold color for accents
PRIMARY_TEXT_COLOR = "#FFFFFF"  # White text for good contrast on dark backgrounds
SECONDARY_TEXT_COLOR = "#B0B0B0"  # Light gray for less prominent text
BACKGROUND_COLOR = "#0E1117"  # Default dark background color of Streamlit
PLOT_BG_COLOR = "rgba(0,0,0,0)"  # Transparent background for plots

# The st.markdown function is used to render Markdown text.
# By setting unsafe_allow_html=True, we can embed HTML and CSS.
st.markdown(f"""
<style>
    /* Remove background from Streamlit's default header */
    .stApp > header {{ background-color: transparent; }}

    /* Style for the main title (H1) */
    h1 {{ 
        color: {GOLD_ACCENT_COLOR}; 
        text-align: center; 
        padding-top: 0.5em; 
        padding-bottom: 0.5em; 
    }}

    /* Style for sub-headers (H2, H3) */
    h2, h3 {{ 
        color: {GOLD_ACCENT_COLOR}; 
        border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important; /* Gold underline */
        padding-bottom: 0.3em; 
    }}

    /* Style for Streamlit's metric display elements */
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{ 
        color: {PRIMARY_TEXT_COLOR} !important; 
    }}
    div[data-testid="stMetricValue"] > div {{ 
        font-size: 1.85rem; /* Larger font for the metric value */
    }}

    /* Style for expander headers */
    .streamlit-expanderHeader {{ 
        color: {GOLD_ACCENT_COLOR} !important; 
        font-weight: bold; 
    }}

    /* Add a border to DataFrames displayed by Streamlit */
    .stDataFrame {{ 
        border: 1px solid #333; 
    }}

    /* General paragraph text color (selectors might change with Streamlit updates) */
    .css-1d391kg p, .css- F_1U7P p {{ 
        color: {PRIMARY_TEXT_COLOR} !important; 
    }}

    /* Style for tab buttons */
    button[data-baseweb="tab"] {{ 
        background-color: transparent !important; 
        color: {SECONDARY_TEXT_COLOR} !important; 
        border-bottom: 2px solid transparent !important; 
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{ /* Style for the active tab */
        color: {GOLD_ACCENT_COLOR} !important; 
        border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important; 
        font-weight: bold; 
    }}
    
    /* Styles for the transcript viewer section */
    .transcript-summary-grid {{ 
        display: grid; /* Use CSS Grid for layout */
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); /* Responsive columns */
        gap: 10px; 
        margin-bottom: 15px; 
    }}
    .transcript-summary-item strong {{ 
        color: {GOLD_ACCENT_COLOR}; /* Highlight labels in the summary */
    }}
    .requirement-item {{ 
        margin-bottom: 8px; /* Spacing for checklist items in transcript view */
    }}
    .transcript-container {{ 
        background-color: #262730; /* Dark background for the transcript box */
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #333; 
        max-height: 400px; /* Limit height and make it scrollable */
        overflow-y: auto; 
        font-family: monospace; /* Monospace font for better readability of transcripts */
    }}
    .transcript-line {{ 
        margin-bottom: 8px; 
        line-height: 1.4; 
        word-wrap: break-word; /* Wrap long lines */
        white-space: pre-wrap; /* Preserve newlines and spaces */
    }}
    .transcript-line strong {{ 
        color: {GOLD_ACCENT_COLOR}; /* Highlight speaker names */
    }}
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
# This function checks if the user has provided the correct access key (password).
def check_password():
    # Retrieve the correct password and hint from Streamlit's secrets management.
    # st.secrets is a dictionary-like object that holds secrets defined in Streamlit Cloud or a local .streamlit/secrets.toml file.
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.") # Default hint if not set

    # If APP_ACCESS_KEY is not set in secrets (e.g., during local development without secrets file),
    # bypass the password check. This is convenient for development but should be secured for deployment.
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set. Bypassing password.")
        return True # Allow access

    # st.session_state is a way to store variables that persist across reruns of the script (e.g., user interactions).
    # Initialize 'password_entered' in session_state if it doesn't exist.
    if "password_entered" not in st.session_state: 
        st.session_state.password_entered = False

    # If the password has already been entered correctly in the current session, allow access.
    if st.session_state.password_entered: 
        return True

    # If password not yet entered, display a form to get the password.
    # st.form creates a form that groups input widgets; submission happens when the button inside is clicked.
    with st.form("password_form"):
        st.markdown("### 🔐 Access Required") # Title for the password form
        # st.text_input creates a text input field. type="password" hides the input.
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint)
        # st.form_submit_button creates the submit button for the form.
        submitted = st.form_submit_button("Submit")

        if submitted: # If the submit button is clicked
            if password_attempt == app_password: # Check if the entered password is correct
                st.session_state.password_entered = True # Store that password was entered correctly
                st.rerun() # Rerun the script to hide the form and show the main app content
            else:
                st.error("Incorrect Access Key.") # Show an error message
                return False # Deny access
    return False # If form not submitted or password incorrect, deny access

# If check_password() returns False, stop the script execution here.
# The rest of the app will not be rendered.
if not check_password(): 
    st.stop() 

# --- Constants ---
# Define constants used in the application.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'] # Google API scopes needed

# Dictionary mapping internal checklist item column names to their full descriptions for display.
KEY_CHECKLIST_ITEMS_FOR_DISPLAY = {
    'expectationsSet': "Expectations Set: Were client expectations clearly set?",
    'introSelfAndDIME': "Introduce Self & DIME: Warmly introduce yourself and DIME Industries.",
    'confirmKitReceived': "Kit & Order Received: Confirm the reseller received their onboarding kit and initial order.",
    'offerDisplayHelp': "Offer Display Help: Ask whether they need help setting up the in-store display kit.",
    'scheduleTrainingAndPromo': "Schedule Training & Promo: Schedule a budtender-training session and the first promotional event.",
    'providePromoCreditLink': "Provide Promo Credit Link: Provide the link for submitting future promo-credit reimbursement requests."
}
# A list to maintain a specific order when displaying these checklist items.
ORDERED_KEY_CHECKLIST_ITEMS = [
    'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
    'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink'
]


# --- Google Sheets Authentication and Data Loading Functions ---

# Authenticates with Google Sheets API using service account credentials.
def authenticate_gspread():
    # Retrieve GCP service account credentials from Streamlit secrets.
    gcp_secrets = st.secrets.get("gcp_service_account")
    if gcp_secrets is None: 
        st.error("GCP service account secrets ('gcp_service_account') NOT FOUND. App cannot authenticate."); return None
    
    # Check if the retrieved secret behaves like a dictionary (has .get and .keys methods).
    # Streamlit's st.secrets returns an AttrDict for dictionary-like secrets, which should have these.
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"GCP service account secrets ('gcp_service_account') is not structured correctly (type: {type(gcp_secrets)}). App cannot authenticate."); return None
    
    # Ensure all required keys are present in the service account credentials.
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [k for k in required_keys if gcp_secrets.get(k) is None]
    if missing: 
        st.error(f"GCP service account secrets is MISSING values for essential sub-keys: {', '.join(missing)}. App cannot authenticate."); return None
    
    try:
        # Create credentials object from the service account info.
        # Explicitly cast gcp_secrets to dict() for compatibility with the google-auth library.
        creds = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES) 
        # Authorize gspread (Google Sheets Python client) with these credentials.
        return gspread.authorize(creds)
    except Exception as e: 
        st.error(f"Google Sheets Authentication Error: {e}"); return None

# Converts a Pandas Series of date-like strings to datetime objects, trying multiple formats.
def robust_to_datetime(series):
    # First, try Pandas' default datetime conversion.
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    
    # Define a list of common date formats to try if the default fails for many entries.
    common_formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', 
                      '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    # If initial parsing results in many nulls (and the series isn't mostly empty strings), try other formats.
    if not series.empty and dates.isnull().sum() > len(series)*0.7 and \
       not series.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                # If this format results in more successfully parsed dates, use it.
                if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                if dates.notnull().all(): break # Stop if all dates are parsed
            except ValueError: continue # Ignore formats that cause errors for the whole series
    return dates

# Loads data from the specified Google Sheet and worksheet.
# @st.cache_data decorator caches the result of this function. If called again with the same
# arguments, it returns the cached result instead of re-executing, speeding up the app.
# ttl (time-to-live) specifies how long the cache is valid (600 seconds = 10 minutes).
@st.cache_data(ttl=600)
def load_data_from_google_sheet(_url_param, _ws_param): # Parameters are for cache invalidation
    # Get sheet URL and worksheet name from secrets.
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config Error: GOOGLE_SHEET_URL_OR_NAME missing in secrets."); return pd.DataFrame()
    if not ws_name: st.error("Config Error: GOOGLE_WORKSHEET_NAME missing in secrets."); return pd.DataFrame()
    
    gc = authenticate_gspread() # Authenticate with Google
    if gc is None: return pd.DataFrame() # Return empty DataFrame if authentication fails
    
    try:
        # Open the spreadsheet either by URL or by its title (name).
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url) 
        ws = ss.worksheet(ws_name) # Open the specific worksheet (tab).
        data = ws.get_all_records(head=1, expected_headers=None) # Get all data, assuming first row is header.
        
        if not data: st.warning("No data records found in the Google Sheet."); return pd.DataFrame()
        df = pd.DataFrame(data) # Convert the list of dictionaries to a Pandas DataFrame.
        st.sidebar.success(f"Loaded {len(df)} records from '{ws_name}'.") 
        if df.empty: st.warning("DataFrame is empty after loading records."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound: 
        st.error(f"Spreadsheet Not Found: '{url}'. Check URL/Name & service account permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: 
        st.error(f"Worksheet Not Found: '{ws_name}'. Check spelling (case-sensitive)."); return pd.DataFrame()
    except Exception as e: 
        st.error(f"Error Loading Data from Google Sheet: {e}"); return pd.DataFrame()

    # --- Data Cleaning and Preprocessing ---
    df.columns = df.columns.str.strip() # Remove leading/trailing whitespace from column names.
    
    # Define date columns to parse and their new datetime column names.
    date_cols_map = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for original_col, new_dt_col in date_cols_map.items():
        if original_col in df.columns:
            # Clean strings (remove newlines, strip whitespace) before parsing.
            cleaned_series = df[original_col].astype(str).str.replace('\n','',regex=False).str.strip()
            df[new_dt_col] = robust_to_datetime(cleaned_series) # Parse to datetime
            if original_col == 'onboardingDate': # Extract just the date part for 'onboardingDate'
                df['onboarding_date_only'] = df[new_dt_col].dt.date
        else: # If expected date column is missing
            df[new_dt_col] = pd.NaT # Create an empty datetime column (Not a Time)
            if original_col == 'onboardingDate': df['onboarding_date_only'] = pd.NaT
    
    # Calculate 'days_to_confirmation'
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
        # Ensure columns are actual datetime objects before subtraction.
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')
        
        # Helper to convert datetime series to UTC (timezone-aware) for consistent calculations.
        def to_utc(s):
            if pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
                try: return s.dt.tz_localize('UTC') if s.dt.tz is None else s.dt.tz_convert('UTC')
                except Exception: return s # Return original if timezone conversion fails
            return s
        # Calculate difference in days.
        df['days_to_confirmation'] = (to_utc(df['confirmationTimestamp_dt']) - to_utc(df['deliveryDate_dt'])).dt.days
    else: 
        df['days_to_confirmation'] = pd.NA # Pandas' missing value indicator for numbers

    # Ensure other key columns exist and have appropriate default types/values if missing.
    str_cols_to_ensure_exist = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript']
    for col in str_cols_to_ensure_exist:
        if col not in df.columns: df[col] = "" # Default to empty string if missing
        else: df[col] = df[col].astype(str).fillna("") # Convert to string and fill NaNs with empty string

    if 'score' not in df.columns: df['score'] = pd.NA # Default to Pandas NA if 'score' column missing
    df['score'] = pd.to_numeric(df['score'], errors='coerce') # Convert 'score' to numeric, errors become NaT/NaN
    
    # Ensure all defined checklist item columns exist in the DataFrame.
    checklist_cols_to_ensure_exist = ORDERED_KEY_CHECKLIST_ITEMS + ['onboardingWelcome'] 
    for col in checklist_cols_to_ensure_exist:
        if col not in df.columns: df[col] = pd.NA # Default to NA if missing
            
    return df

# --- Helper Functions ---

# Converts a DataFrame to a CSV string for download. Cached for efficiency.
@st.cache_data
def convert_df_to_csv(df_to_convert): 
    return df_to_convert.to_csv(index=False).encode('utf-8')

# Calculates key performance metrics from a given DataFrame.
def calculate_metrics(df_input):
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA # Return defaults if input DataFrame is empty
    
    total_onboardings = len(df_input)
    # Calculate success rate (percentage of 'confirmed' statuses).
    successful_onboardings = df_input[df_input['status'].astype(str).str.lower()=='confirmed'].shape[0]
    success_rate = (successful_onboardings / total_onboardings * 100) if total_onboardings > 0 else 0.0
    
    # Calculate average score.
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean() # .mean() ignores NaNs
    # Calculate average days to confirmation.
    avg_days_to_confirmation = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    
    return total_onboardings, success_rate, avg_score, avg_days_to_confirmation

# Determines a default date range for filters, typically the current month or based on data availability.
def get_default_date_range(date_series):
    today = date.today()
    default_start = today.replace(day=1) # Start of current month
    default_end = today # Today
    min_data_date, max_data_date = None, None # Initialize min/max dates from data
    
    if date_series is not None and not date_series.empty:
        # Convert series to date objects and drop any conversion errors (NaT).
        parsed_dates = pd.to_datetime(date_series, errors='coerce').dt.date.dropna()
        if not parsed_dates.empty:
            min_data_date = parsed_dates.min()
            max_data_date = parsed_dates.max()
            # Adjust default range to be within the actual data's date range.
            default_start = max(default_start, min_data_date)
            default_end = min(default_end, max_data_date)
            # If calculated start is after end (e.g., all data is future), use full data range.
            if default_start > default_end: 
                default_start, default_end = min_data_date, max_data_date
    return default_start, default_end, min_data_date, max_data_date

# --- Initialize Session State ---
# Set up default values for session state variables if they don't already exist.
# This ensures the app has a consistent state when it first loads or after a full rerun.
default_s_date, default_e_date, _, _ = get_default_date_range(None) # Initial default before data load
# Dictionary of session state keys and their default values.
session_state_defaults = {
    'data_loaded_successfully': False,
    'df_original': pd.DataFrame(), # Stores the original, unfiltered DataFrame
    'date_range_filter': (default_s_date, default_e_date),
    'repName_filter': [], 'status_filter': [], 'clientSentiment_filter': [], # For multiselect filters
    'licenseNumber_search': "", 'storeName_search': "", # For text search inputs
    'selected_transcript_key': None # For the transcript viewer selectbox
}
for key, default_value in session_state_defaults.items():
    if key not in st.session_state: 
        st.session_state[key] = default_value

# --- Data Loading Trigger ---
# This block runs if data hasn't been successfully loaded into the session yet.
if not st.session_state.data_loaded_successfully:
    # Get Google Sheet configuration from secrets.
    gs_url_from_secrets = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    gs_worksheet_from_secrets = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    
    if not gs_url_from_secrets or not gs_worksheet_from_secrets:
        st.error("Configuration Error: Google Sheet URL/Name or Worksheet Name missing in Streamlit secrets.")
    else:
        # Show a spinner while data is loading.
        with st.spinner("Loading onboarding data from Google Sheet... This may take a moment."):
            # Call the function to load and process data.
            loaded_df = load_data_from_google_sheet(gs_url_from_secrets, gs_worksheet_from_secrets) 
            if not loaded_df.empty:
                st.session_state.df_original = loaded_df # Store loaded data in session state
                st.session_state.data_loaded_successfully = True
                # Update default date range filter based on the loaded data.
                ds_loaded, de_loaded, _, _ = get_default_date_range(loaded_df.get('onboarding_date_only'))
                st.session_state.date_range_filter = (ds_loaded, de_loaded) if ds_loaded and de_loaded else (default_s_date, default_e_date)
            else: # If loading failed or returned empty DataFrame
                st.session_state.df_original = pd.DataFrame() 
                st.session_state.data_loaded_successfully = False
# Retrieve the original DataFrame from session state for use in the app.
df_original = st.session_state.df_original 

# --- Main Application UI Starts Here ---
st.title("🚀 Onboarding Performance Dashboard v2.7 🚀") # App title

# If data loading failed or resulted in an empty DataFrame, show an error and a refresh button.
if not st.session_state.data_loaded_successfully or df_original.empty:
    st.error("Failed to load data. Please check Google Sheet content, permissions, and secret configurations. You can try refreshing the data.")
    if st.sidebar.button("🔄 Force Refresh Data & Reload App", key="force_refresh_on_fail"):
        st.cache_data.clear() # Clear all cached data
        st.session_state.clear() # Clear all session state
        st.rerun() # Rerun the entire script

# --- Sidebar UI Elements ---

# Expander in the sidebar to explain the scoring system.
with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)

st.sidebar.header("⚙️ Data Controls")
# Button to manually refresh data from Google Sheet.
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_data_main_button"):
    st.cache_data.clear() # Clear cached data to force reload
    st.session_state.clear() # Clear session state to reset filters and loaded data status
    st.rerun() # Rerun the script

st.sidebar.header("🔍 Filters")
# Date range filter setup
onboarding_dates_for_filter_setup = df_original.get('onboarding_date_only') # Get date series safely
def_start_date_filter, def_end_date_filter, min_data_dt, max_data_dt = get_default_date_range(onboarding_dates_for_filter_setup)
# Ensure date_range_filter in session state is valid tuple of dates
if 'date_range_filter' not in st.session_state or \
   not (isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 and \
        all(isinstance(d, date) for d in st.session_state.date_range_filter)):
    st.session_state.date_range_filter = (def_start_date_filter, def_end_date_filter) if def_start_date_filter and def_end_date_filter else (date.today().replace(day=1), date.today())

if min_data_dt and max_data_dt and def_start_date_filter and def_end_date_filter: # Only show date input if valid range exists
    current_val_start, current_val_end = st.session_state.date_range_filter
    # Ensure widget value is within min/max bounds of available data
    widget_val_start = max(min_data_dt, current_val_start) if current_val_start else min_data_dt
    widget_val_end = min(max_data_dt, current_val_end) if current_val_end else max_data_dt
    if widget_val_start and widget_val_end and widget_val_start > widget_val_end: # Handle edge case
        widget_val_start, widget_val_end = min_data_dt, max_data_dt
    
    selected_date_range_from_widget = st.sidebar.date_input(
        "Filter by Onboarding Date Range:", 
        value=(widget_val_start, widget_val_end), 
        min_value=min_data_dt, max_value=max_data_dt, 
        key="date_range_selector_ui_key" 
    )
    # Update session state if widget selection changes
    if selected_date_range_from_widget != st.session_state.date_range_filter:
        st.session_state.date_range_filter = selected_date_range_from_widget
else:
    st.sidebar.warning("Onboarding date data not available for range filter.")
# Unpack the selected date range for filtering
start_date_for_filter, end_date_for_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)

# Text search filters (License Number, Store Name)
search_cols_config = {"licenseNumber":"License Number", "storeName":"Store Name"}
for col_key, display_label in search_cols_config.items():
    if f"{col_key}_search" not in st.session_state: st.session_state[f"{col_key}_search"] = ""
    search_term_input = st.sidebar.text_input(
        f"Search {display_label} (on all data):", 
        value=st.session_state[f"{col_key}_search"], 
        key=f"{col_key}_search_input_widget"
    )
    if search_term_input != st.session_state[f"{col_key}_search"]:
         st.session_state[f"{col_key}_search"] = search_term_input

# Categorical multiselect filters (Rep Name, Status, Client Sentiment)
cat_filters_config = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_name, display_label in cat_filters_config.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        # Get unique, sorted, non-empty string values for filter options.
        options_for_filter = sorted([val for val in df_original[col_name].astype(str).dropna().unique() if val.strip()])
        if f"{col_name}_filter" not in st.session_state: st.session_state[f"{col_name}_filter"] = []
        # Ensure current selection is valid (exists in options).
        current_selection_for_widget = [val for val in st.session_state[f"{col_name}_filter"] if val in options_for_filter]
        
        new_selection_from_widget = st.sidebar.multiselect(
            f"Filter by {display_label}:", 
            options=options_for_filter, 
            default=current_selection_for_widget, 
            key=f"{col_name}_multiselect_widget"
        )
        if new_selection_from_widget != st.session_state[f"{col_name}_filter"]:
            st.session_state[f"{col_name}_filter"] = new_selection_from_widget

# Callback function to clear all active filters.
def clear_all_filters_callback_func():
    # Reset date range to default based on current data.
    ds_cb, de_cb, _, _ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range_filter = (ds_cb, de_cb) if ds_cb and de_cb else (date.today().replace(day=1), date.today())
    # Clear text search inputs.
    for col_key_search in search_cols_config: st.session_state[f"{col_key_search}_search"] = ""
    # Clear multiselect filter selections.
    for col_name_cat in cat_filters_config: st.session_state[f"{col_name_cat}_filter"] = []
    st.session_state.selected_transcript_key = None # Also clear transcript selection

# Button to clear all filters.
if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback_func, use_container_width=True): 
    st.rerun() # Rerun to apply cleared filters and update UI

# --- Filtering Logic ---
# Start with an empty DataFrame if no original data, otherwise copy original.
df_filtered = pd.DataFrame() 
if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    df_working_copy = st.session_state.df_original.copy() # Work on a copy

    # 1. Apply License Number Search (operates on df_original's copy first)
    license_search_val = st.session_state.get("licenseNumber_search", "")
    if license_search_val and "licenseNumber" in df_working_copy.columns:
        df_working_copy = df_working_copy[df_working_copy['licenseNumber'].astype(str).str.contains(license_search_val, case=False, na=False)]

    # 2. Apply Store Name Search (operates on the result of license search)
    store_search_val = st.session_state.get("storeName_search", "")
    if store_search_val and "storeName" in df_working_copy.columns:
        df_working_copy = df_working_copy[df_working_copy['storeName'].astype(str).str.contains(store_search_val, case=False, na=False)]

    # df_working_copy now contains results from license/store search on the original data.
    # Now, apply other filters (date, categorical) to this df_working_copy.

    # 3. Apply date range filter to df_working_copy
    if start_date_for_filter and end_date_for_filter and 'onboarding_date_only' in df_working_copy.columns:
        parsed_dates_for_filter = pd.to_datetime(df_working_copy['onboarding_date_only'], errors='coerce').dt.date
        date_filter_mask_for_working_copy = parsed_dates_for_filter.notna() & \
                                            (parsed_dates_for_filter >= start_date_for_filter) & \
                                            (parsed_dates_for_filter <= end_date_for_filter)
        df_working_copy = df_working_copy[date_filter_mask_for_working_copy]
    
    # 4. Apply categorical multiselect filters to df_working_copy
    for col_name_cat_filter, _ in cat_filters_config.items(): 
        selected_cat_values = st.session_state.get(f"{col_name_cat_filter}_filter", [])
        if selected_cat_values and col_name_cat_filter in df_working_copy.columns: 
            df_working_copy = df_working_copy[df_working_copy[col_name_cat_filter].astype(str).isin(selected_cat_values)]
    
    df_filtered = df_working_copy.copy() # Final filtered DataFrame
else:
    df_filtered = pd.DataFrame() # Ensure df_filtered is an empty DataFrame if no original data

# --- Plotly Layout Configuration ---
# Define a base layout for Plotly charts for consistent styling.
plotly_base_layout = {"plot_bgcolor":PLOT_BG_COLOR, "paper_bgcolor":PLOT_BG_COLOR, "font_color":PRIMARY_TEXT_COLOR, 
                      "title_font_color":GOLD_ACCENT_COLOR, "legend_font_color":PRIMARY_TEXT_COLOR, 
                      "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":False}

# --- MTD Metrics Calculation ---
# Calculate Month-to-Date (MTD) and Previous Month-to-Date metrics.
today_for_mtd = date.today()
current_mtd_start_date = today_for_mtd.replace(day=1)
previous_month_end_date_for_mtd = current_mtd_start_date - timedelta(days=1)
previous_mtd_start_date = previous_month_end_date_for_mtd.replace(day=1)

df_current_mtd_data = pd.DataFrame() 
df_previous_mtd_data = pd.DataFrame() 

if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    onboarding_dates_series_for_mtd = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_dates_mask_for_mtd = onboarding_dates_series_for_mtd.notna()
    
    if valid_dates_mask_for_mtd.any():
        df_with_valid_dates_for_mtd = df_original[valid_dates_mask_for_mtd].copy()
        valid_onboarding_dates_for_mtd = onboarding_dates_series_for_mtd[valid_dates_mask_for_mtd]
        
        current_mtd_period_mask = (valid_onboarding_dates_for_mtd >= current_mtd_start_date) & (valid_onboarding_dates_for_mtd <= today_for_mtd)
        previous_mtd_period_mask = (valid_onboarding_dates_for_mtd >= previous_mtd_start_date) & (valid_onboarding_dates_for_mtd <= previous_month_end_date_for_mtd)
        
        df_current_mtd_data = df_with_valid_dates_for_mtd[current_mtd_period_mask.values]
        df_previous_mtd_data = df_with_valid_dates_for_mtd[previous_mtd_period_mask.values]

total_onboardings_mtd, success_rate_mtd, avg_score_mtd, avg_days_to_confirm_mtd = calculate_metrics(df_current_mtd_data)
total_onboardings_previous_mtd, _, _, _ = calculate_metrics(df_previous_mtd_data) 
delta_onboardings_mtd = total_onboardings_mtd - total_onboardings_previous_mtd if pd.notna(total_onboardings_mtd) and pd.notna(total_onboardings_previous_mtd) else None

# --- Main Content Tabs ---
# Create tabs for different sections of the dashboard.
tab1_overview, tab2_details, tab3_trends = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1_overview: # Content for the "Overview" tab
    st.header("📈 Month-to-Date (MTD) Overview")
    col1_mtd, col2_mtd, col3_mtd, col4_mtd = st.columns(4) # Create 4 columns for MTD metrics
    col1_mtd.metric("Onboardings MTD", total_onboardings_mtd or "0", f"{delta_onboardings_mtd:+}" if delta_onboardings_mtd is not None else "N/A vs Prev. Mth")
    col2_mtd.metric("Success Rate MTD", f"{success_rate_mtd:.1f}%" if pd.notna(success_rate_mtd) else "N/A")
    col3_mtd.metric("Avg Score MTD", f"{avg_score_mtd:.2f}" if pd.notna(avg_score_mtd) else "N/A")
    col4_mtd.metric("Avg Days to Confirm MTD", f"{avg_days_to_confirm_mtd:.1f}" if pd.notna(avg_days_to_confirm_mtd) else "N/A")
    
    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_filtered, success_rate_filtered, avg_score_filtered, avg_days_filtered = calculate_metrics(df_filtered)
        col1_filt, col2_filt, col3_filt, col4_filt = st.columns(4)
        col1_filt.metric("Filtered Onboardings", total_filtered or "0")
        col2_filt.metric("Filtered Success Rate", f"{success_rate_filtered:.1f}%" if pd.notna(success_rate_filtered) else "N/A")
        col3_filt.metric("Filtered Avg Score", f"{avg_score_filtered:.2f}" if pd.notna(avg_score_filtered) else "N/A")
        col4_filt.metric("Filtered Avg Days Confirm", f"{avg_days_filtered:.1f}" if pd.notna(avg_days_filtered) else "N/A")
    else: 
        st.info("No data matches the current filter criteria to display in Overview.")

with tab2_details: # Content for the "Detailed Analysis & Data" tab
    st.header("📋 Filtered Onboarding Data Table")
    # df_display_table is used for the table and transcript viewer. Reset index for easier row selection.
    df_display_table_for_tab2 = df_filtered.copy().reset_index(drop=True) 
    
    # Define columns to show in the main table (excluding fullTranscript initially).
    cols_to_try_in_table = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                            'clientSentiment', 'days_to_confirmation'] + ORDERED_KEY_CHECKLIST_ITEMS
    cols_for_main_table_display = [col for col in cols_to_try_in_table if col in df_display_table_for_tab2.columns]
    # Add any other columns not explicitly listed, excluding derived/internal ones.
    other_cols_for_table = [col for col in df_display_table_for_tab2.columns 
                            if col not in cols_for_main_table_display and 
                               not col.endswith(('_utc', '_str_original', '_dt')) and 
                               col != 'fullTranscript']
    cols_for_main_table_display.extend(other_cols_for_table)

    if not df_display_table_for_tab2.empty:
        # Function to apply conditional background styling to the DataFrame.
        def style_dataframe_for_display(df_to_style): 
            styled = df_to_style.style
            if 'score' in df_to_style.columns: 
                scores_numeric_for_style = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_numeric_for_style.notna().any():
                    styled = styled.background_gradient(subset=['score'],cmap='RdYlGn',low=0.3,high=0.7, gmap=scores_numeric_for_style)
            if 'days_to_confirmation' in df_to_style.columns:
                days_numeric_for_style = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_numeric_for_style.notna().any():
                    styled = styled.background_gradient(subset=['days_to_confirmation'],cmap='RdYlGn_r', gmap=days_numeric_for_style)
            return styled
        # Display the styled DataFrame.
        st.dataframe(style_dataframe_for_display(df_display_table_for_tab2[cols_for_main_table_display]), 
                     use_container_width=True, height=300) # Set a fixed height for the table
        
        # --- Transcript Viewer Section ---
        st.markdown("---") # Visual separator
        st.subheader("🔍 View Full Onboarding Details & Transcript")
        
        if not df_display_table_for_tab2.empty and 'fullTranscript' in df_display_table_for_tab2.columns:
            # Create options for the selectbox: "Index X: Store Name (Date)"
            transcript_options_map = {
                f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx 
                for idx, row in df_display_table_for_tab2.iterrows()
            }
            if transcript_options_map: # If there are rows to select from
                # Use session state for the selectbox to remember the selection.
                if 'selected_transcript_key' not in st.session_state: 
                    st.session_state.selected_transcript_key = None # Initialize if not present

                selected_key_from_widget = st.selectbox(
                    "Select an onboarding to view its details and transcript:",
                    options=[None] + list(transcript_options_map.keys()), # Add a "None" option for placeholder
                    index=0, # Default to the placeholder
                    format_func=lambda x: "Choose an entry..." if x is None else x, # Display text for None
                    key="transcript_selector_main_widget" 
                )
                
                # Update session state if the widget's selection has changed.
                if selected_key_from_widget != st.session_state.selected_transcript_key:
                    st.session_state.selected_transcript_key = selected_key_from_widget
                
                # If a valid entry (not None) is selected in session state:
                if st.session_state.selected_transcript_key :
                    selected_row_index = transcript_options_map[st.session_state.selected_transcript_key]
                    selected_onboarding_row = df_display_table_for_tab2.loc[selected_row_index]
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html_output = "<div class='transcript-summary-grid'>"
                    summary_data_items = {
                        "Store": selected_onboarding_row.get('storeName', 'N/A'), 
                        "Rep": selected_onboarding_row.get('repName', 'N/A'),
                        "Score": selected_onboarding_row.get('score', 'N/A'),
                        "Status": selected_onboarding_row.get('status', 'N/A'),
                        "Sentiment": selected_onboarding_row.get('clientSentiment', 'N/A')
                    }
                    for item_label, item_value in summary_data_items.items():
                        summary_html_output += f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>"
                    summary_html_output += "</div>"
                    st.markdown(summary_html_output, unsafe_allow_html=True)

                    st.markdown("##### Key Requirement Checks:")
                    # Iterate using the predefined ordered list of checklist items.
                    for item_column_name in ORDERED_KEY_CHECKLIST_ITEMS:
                        # Get the full description for the item.
                        item_description = KEY_CHECKLIST_ITEMS_FOR_DISPLAY.get(item_column_name, item_column_name.replace('_',' ').title())
                        # Get the value from the selected row; default to empty string if column missing.
                        item_value_str = str(selected_onboarding_row.get(item_column_name, "")).lower()
                        # Determine if the requirement was met (True/False).
                        is_requirement_met = item_value_str in ['true', '1', 'yes']
                        status_emoji = "✅" if is_requirement_met else "❌"
                        # Display each requirement on a new line.
                        st.markdown(f"<div class='requirement-item'>{status_emoji} {item_description}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---") # Separator before transcript
                    st.markdown("##### Full Transcript:")
                    transcript_content = selected_onboarding_row.get('fullTranscript', "")
                    if transcript_content:
                        html_transcript_output = "<div class='transcript-container'>"
                        # Ensure both literal '\n' and actual newlines are handled for HTML.
                        processed_transcript_content = transcript_content.replace('\\n', '\n') 
                        
                        for line_segment_from_transcript in processed_transcript_content.split('\n'):
                            current_line = line_segment_from_transcript.strip()
                            if not current_line: continue # Skip empty lines
                            
                            # Attempt to identify speaker (text before first colon).
                            parts_of_line = current_line.split(":", 1)
                            speaker_html_part = f"<strong>{parts_of_line[0].strip()}:</strong>" if len(parts_of_line) == 2 else ""
                            # The rest is the message. Replace internal newlines in message with <br>.
                            message_html_part = parts_of_line[1].strip().replace('\n', '<br>') if len(parts_of_line) == 2 else current_line.replace('\n', '<br>')
                            
                            html_transcript_output += f"<p class='transcript-line'>{speaker_html_part} {message_html_part}</p>"
                        html_transcript_output += "</div>"
                        st.markdown(html_transcript_output, unsafe_allow_html=True)
                    else: 
                        st.info("No transcript available for this selection or the transcript is empty.")
        else: 
            st.info("No data in the filtered table to select a transcript from, or 'fullTranscript' column is missing.")
        st.markdown("---") # Separator after transcript viewer

        # Download button for the filtered data.
        csv_data_to_download = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data as CSV", csv_data_to_download, 'filtered_onboarding_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: 
        st.info("No data matches current filter criteria for table display.")
    
    # --- Key Visuals Section ---
    st.header("📊 Key Visuals (Based on Filtered Data)") 
    if not df_filtered.empty:
        col_viz_1, col_viz_2 = st.columns(2) # Create two columns for visuals
        with col_viz_1: # Visuals in the first column
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_fig = px.bar(df_filtered['status'].value_counts().reset_index(), 
                                 x='status', y='count', color='status', title="Onboarding Status Distribution")
                status_fig.update_layout(plotly_base_layout)
                st.plotly_chart(status_fig, use_container_width=True)
            
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_fig = px.bar(df_filtered['repName'].value_counts().reset_index(), 
                              x='repName', y='count', color='repName', title="Onboardings by Representative")
                rep_fig.update_layout(plotly_base_layout)
                st.plotly_chart(rep_fig, use_container_width=True)
        
        with col_viz_2: # Visuals in the second column
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sentiment_counts_df = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map_config = {
                    str(s).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s).lower() else 
                                     ('#2ca02c' if 'positive' in str(s).lower() else 
                                      ('#d62728' if 'negative' in str(s).lower() else None)))
                    for s in sentiment_counts_df['clientSentiment'].unique()
                }
                sentiment_fig = px.pie(sentiment_counts_df, names='clientSentiment', values='count', hole=0.4, 
                                     title="Client Sentiment Breakdown", color='clientSentiment', 
                                     color_discrete_map=sentiment_color_map_config)
                sentiment_fig.update_layout(plotly_base_layout)
                st.plotly_chart(sentiment_fig, use_container_width=True)

            # Checklist Item Completion chart (for 'confirmed' statuses)
            df_confirmed_onboardings = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            # Use the predefined ORDERED_KEY_CHECKLIST_ITEMS for consistency.
            actual_checklist_cols_for_chart = [col for col in ORDERED_KEY_CHECKLIST_ITEMS if col in df_confirmed_onboardings.columns]
            checklist_completion_data = []
            if not df_confirmed_onboardings.empty and actual_checklist_cols_for_chart:
                for item_col_name in actual_checklist_cols_for_chart:
                    # Get the display-friendly description.
                    item_description_for_chart = KEY_CHECKLIST_ITEMS_FOR_DISPLAY.get(item_col_name, item_col_name.replace('_',' ').title())
                    # Map boolean-like values to True/False.
                    map_true_false = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                    if item_col_name in df_confirmed_onboardings.columns: # Ensure column exists
                        boolean_series_for_item = pd.to_numeric(df_confirmed_onboardings[item_col_name].astype(str).str.lower().map(map_true_false), errors='coerce')
                        if boolean_series_for_item.notna().any():
                            count_true = boolean_series_for_item.sum()
                            count_valid_responses = boolean_series_for_item.notna().sum()
                            if count_valid_responses > 0:
                                # Use the shorter part of the description (before colon) for chart labels if too long.
                                chart_label_for_item = item_description_for_chart.split(":")[0] if ":" in item_description_for_chart else item_description_for_chart
                                checklist_completion_data.append({"Key Requirement": chart_label_for_item, 
                                                                  "Completion (%)": (count_true / count_valid_responses) * 100})
                if checklist_completion_data:
                    df_checklist_chart_data = pd.DataFrame(checklist_completion_data)
                    if not df_checklist_chart_data.empty:
                        checklist_fig = px.bar(df_checklist_chart_data.sort_values("Completion (%)", ascending=True), 
                                             x="Completion (%)", y="Key Requirement", orientation='h', 
                                             title="Key Requirement Completion (Confirmed Onboardings)", 
                                             color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        checklist_fig.update_layout(plotly_base_layout, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(checklist_fig, use_container_width=True)
                else: 
                    st.info("No data available for key requirement completion chart (e.g., no confirmed onboardings with checklist data).")
            else: 
                st.info("No 'confirmed' onboardings in the filtered data, or relevant checklist columns are missing, to show key requirement completion.")
    else: 
        st.info("No data matches current filters to display detailed visuals.")

with tab3_trends: # Content for "Trends & Distributions" tab
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time chart
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_analysis = df_filtered.copy()
            df_trend_analysis['onboarding_date_only'] = pd.to_datetime(df_trend_analysis['onboarding_date_only'], errors='coerce')
            df_trend_analysis.dropna(subset=['onboarding_date_only'], inplace=True) # Remove rows where date conversion failed
            
            if not df_trend_analysis.empty:
                date_span_for_trend = (df_trend_analysis['onboarding_date_only'].max() - df_trend_analysis['onboarding_date_only'].min()).days
                resample_frequency = 'D' if date_span_for_trend <= 62 else ('W-MON' if date_span_for_trend <= 365*1.5 else 'ME')
                onboardings_over_time_df = df_trend_analysis.set_index('onboarding_date_only').resample(resample_frequency).size().reset_index(name='count')
                if not onboardings_over_time_df.empty:
                    trend_fig = px.line(onboardings_over_time_df, x='onboarding_date_only', y='count', markers=True, 
                                      title="Onboardings Over Filtered Period")
                    trend_fig.update_layout(plotly_base_layout)
                    st.plotly_chart(trend_fig, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend after resampling.")
            else: 
                st.info("No valid date data available in filtered set for onboarding trend chart.")
        
        # Days to Confirmation Distribution chart
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_histogram = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_histogram.empty:
                num_bins_for_hist = max(10, min(50, int(len(days_data_for_histogram)/5))) if len(days_data_for_histogram) > 20 else (len(days_data_for_histogram.unique()) or 10)
                days_dist_fig = px.histogram(days_data_for_histogram, nbins=num_bins_for_hist, 
                                           title="Days to Confirmation Distribution")
                days_dist_fig.update_layout(plotly_base_layout)
                st.plotly_chart(days_dist_fig, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data in filtered set to plot distribution.")
    else: 
        st.info("No data matches current filter criteria to display Trends & Distributions.")

st.sidebar.markdown("---") # Visual separator in sidebar
st.sidebar.info("Dashboard v2.7 | Secured Access") # App version info