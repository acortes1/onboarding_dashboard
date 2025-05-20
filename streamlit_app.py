# Import necessary libraries
import streamlit as st  # For creating the web application interface and UI elements
import pandas as pd  # For data manipulation and analysis, especially using DataFrames
import plotly.express as px  # For creating interactive charts and visualizations easily
import plotly.graph_objects as go  # For more advanced and custom Plotly charts (though not heavily used here)
from datetime import datetime, date, timedelta  # For working with date and time objects
from dateutil.relativedelta import relativedelta  # For more complex date calculations (e.g., adding/subtracting months)
import gspread  # Python client library for Google Sheets API
from google.oauth2.service_account import Credentials  # For authenticating with Google services using a service account
from collections.abc import Mapping  # Abstract Base Class for dictionary-like objects, used for robust type checking
import time  # For time-related functions (not actively used in this version but often useful)
import numpy as np  # For numerical operations; Pandas is built on NumPy
import re  # For regular expression operations, used here for parsing text like transcripts
import matplotlib # Imported because some pandas styling features (e.g., background_gradient) might use it under the hood

# --- Page Configuration ---
# This st.set_page_config() function must be the first Streamlit command in your script, except for comments and blank lines.
# It sets up the basic properties of the web page, such as:
# - page_title: The title that appears in the browser tab.
# - page_icon: The icon (favicon) for the browser tab (can be an emoji or a URL).
# - layout: How the content is arranged on the page. "wide" uses the full width of the screen.
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.11.1", # Updated version for this annotation review
    page_icon="🧑‍🏫", # A teacher emoji, signifying explanation and clarity
    layout="wide"
)

# --- Custom Styling (CSS) ---
# These are global CSS styles to customize the visual appearance of the Streamlit application.
# Streamlit allows embedding HTML (including <style> tags for CSS) using st.markdown
# with the unsafe_allow_html=True parameter. This gives more control over the look and feel.

# Define color constants for easy reuse and theme consistency.
GOLD_ACCENT_COLOR = "#FFD700"
PRIMARY_TEXT_COLOR = "#FFFFFF"
SECONDARY_TEXT_COLOR = "#B0B0B0"
BACKGROUND_COLOR = "#0E1117"  # Streamlit's default dark theme background (for reference)
PLOT_BG_COLOR = "rgba(0,0,0,0)"  # Transparent background for Plotly charts

# Use an f-string to embed the color constants into the CSS string.
st.markdown(f"""
<style>
    /* General App Styles */
    .stApp > header {{ background-color: transparent; }} /* Removes the default Streamlit header bar background */
    h1 {{ color: {GOLD_ACCENT_COLOR}; text-align: center; padding-top: 0.5em; padding-bottom: 0.5em; }} /* Styles for the main dashboard title */
    h2, h3 {{ color: {GOLD_ACCENT_COLOR}; border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important; padding-bottom: 0.3em; }} /* Styles for section headers */
    
    /* Metric Widget Styles - for st.metric displays */
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{ color: {PRIMARY_TEXT_COLOR} !important; }} /* Ensures metric text is white */
    div[data-testid="stMetricValue"] > div {{ font-size: 1.85rem; }} /* Makes the main metric value larger */
    
    /* Expander Styles - for st.expander elements */
    .streamlit-expanderHeader {{ color: {GOLD_ACCENT_COLOR} !important; font-weight: bold; }} /* Styles the title of expanders */
    
    /* DataFrame Styles - for st.dataframe */
    .stDataFrame {{ border: 1px solid #333; }} /* Adds a subtle border around data tables */
    
    /* Paragraph Text (These CSS selectors target general text elements and might need updates if Streamlit changes its internal structure) */
    .css-1d391kg p, .css- F_1U7P p {{ color: {PRIMARY_TEXT_COLOR} !important; }}
    
    /* Tab Styles - for st.tabs */
    button[data-baseweb="tab"] {{ background-color: transparent !important; color: {SECONDARY_TEXT_COLOR} !important; border-bottom: 2px solid transparent !important; }} /* Default style for tab buttons */
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {GOLD_ACCENT_COLOR} !important; border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important; font-weight: bold; }} /* Style for the currently active tab button */
    
    /* Transcript Viewer Specific Styles - for displaying onboarding details and transcripts */
    .transcript-summary-grid {{ 
        display: grid; /* Uses CSS Grid for a flexible layout */
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* Creates responsive columns that adjust to content width */
        gap: 12px; /* Space between grid items */
        margin-bottom: 18px; /* Space below the summary grid */
    }}
    .transcript-summary-item strong {{ color: {GOLD_ACCENT_COLOR}; }} /* Highlights the labels (e.g., "Store:") in the summary */
    .transcript-summary-item-fullwidth {{ /* A special class for summary items that should span the full width of the grid */
        grid-column: 1 / -1; /* Makes the item span all columns */
        margin-top: 5px; /* Adds a little space above full-width items */
    }}
    .requirement-item {{ 
        margin-bottom: 10px; /* Space between individual requirement checklist items */
        padding-left: 5px; /* Indentation for requirement items */
        border-left: 3px solid #444; /* A subtle left border for visual grouping of requirements */
    }}
    .requirement-item .type {{ /* Styles the [Primary] / [Secondary] tag next to requirements */
        font-weight: bold;
        color: {SECONDARY_TEXT_COLOR};
        font-size: 0.9em; /* Slightly smaller font for the type tag */
        margin-left: 5px; /* Space between the description and the type tag */
    }}
    .transcript-container {{ 
        background-color: #262730; /* A slightly lighter dark background for the transcript box */
        padding: 15px; 
        border-radius: 8px; /* Rounded corners */
        border: 1px solid #333; 
        max-height: 400px; /* Limits the height; content will scroll if it exceeds this */
        overflow-y: auto; /* Enables vertical scrolling */
        font-family: monospace; /* Monospace font is good for transcripts for consistent character width */
    }}
    .transcript-line {{ 
        margin-bottom: 8px; /* Space between individual lines of the transcript */
        line-height: 1.4; /* Improves readability by increasing space between lines of text */
        word-wrap: break-word; /* Ensures long words or lines without spaces will wrap to the next line */
        white-space: pre-wrap; /* Preserves newline characters and sequences of spaces from the original transcript text */
    }}
    .transcript-line strong {{ 
        color: {GOLD_ACCENT_COLOR}; /* Highlights speaker names (text before a colon) in the transcript */
    }}
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
# This function defines the password protection mechanism for the dashboard.
def check_password():
    # Retrieve the application's password and hint from Streamlit's secrets management.
    # st.secrets is a dictionary-like object. .get() is used to safely access values,
    # providing a default if the key is not found.
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.") # Default hint if not set in secrets
    
    # If APP_ACCESS_KEY is not defined in secrets (e.g., for local development without a secrets file),
    # this allows bypassing the password check. This is a common pattern for easier local testing.
    # For a deployed app, APP_ACCESS_KEY should always be set in the environment's secrets.
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set in secrets. Bypassing password for local development.")
        return True # Allow access

    # st.session_state is Streamlit's way to store variables that persist across reruns of the script
    # (which happen on every user interaction). We use it to remember if the password was entered correctly.
    if "password_entered" not in st.session_state: 
        st.session_state.password_entered = False # Initialize if not already set

    # If the password has already been successfully entered in the current session, grant access.
    if st.session_state.password_entered: 
        return True

    # If the password hasn't been entered, display a form to collect it.
    # st.form groups input widgets. The form is submitted when a button inside it is clicked.
    with st.form("password_form_main_app"): # A unique key for the form is good practice
        st.markdown("### 🔐 Access Required") # Title for the password section
        # st.text_input creates a field for text input. type="password" hides the characters.
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint)
        # st.form_submit_button creates the button that submits the form.
        submitted = st.form_submit_button("Submit")

        if submitted: # This block executes only when the "Submit" button is pressed
            if password_attempt == app_password: # Check if the entered password matches the correct one
                st.session_state.password_entered = True # Store success in session state
                st.rerun() # Rerun the script immediately to hide the form and show the app's main content
            else: 
                st.error("Incorrect Access Key. Please try again.") # Display an error message
                return False # Deny access
    return False # If the form hasn't been submitted or password was wrong on a previous attempt, deny access

# This is the gatekeeper. If check_password() returns False, the script stops here.
if not check_password(): 
    st.stop() 

# --- Constants ---
# Define constants that are used throughout the application for configuration or clarity.
# SCOPES define the permissions the script requests from Google APIs.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',  # Allows reading and writing to Google Sheets
          'https://www.googleapis.com/auth/drive']         # Allows access to Google Drive files (often needed for Sheets)

# A dictionary that maps internal checklist item column names (keys) to more descriptive information.
# Each item has a full "description", a "type" (Primary, Secondary, etc.), and a "chart_label" for visualizations.
KEY_REQUIREMENT_DETAILS = {
    'expectationsSet': {
        "description": "Client expectations were clearly set.",
        "type": "Bonus Criterion", 
        "chart_label": "Expectations Set" 
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
# A list that defines the desired order for displaying or iterating through these key checklist items.
ORDERED_KEY_CHECKLIST_ITEMS = [
    'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
    'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink'
]

# --- Google Sheets Authentication and Data Loading Functions ---

# This function handles authentication with Google using service account credentials.
def authenticate_gspread():
    # Retrieve the GCP service account credentials stored in Streamlit's secrets.
    gcp_secrets = st.secrets.get("gcp_service_account") 
    if gcp_secrets is None: 
        st.error("GCP service account secrets ('gcp_service_account') NOT FOUND. App cannot authenticate."); return None
    
    # Check if the retrieved secret object behaves like a dictionary (has .get and .keys methods).
    # Streamlit returns an AttrDict for dictionary-like secrets, which should satisfy this.
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"GCP service account secrets ('gcp_service_account') is not structured correctly (type: {type(gcp_secrets)}). App cannot authenticate."); return None
    
    # Ensure all necessary keys (like 'type', 'private_key', etc.) are present in the service account credentials.
    required_keys_for_gcp_auth = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_gcp_auth_keys = [key for key in required_keys_for_gcp_auth if gcp_secrets.get(key) is None]
    if missing_gcp_auth_keys: 
        st.error(f"GCP service account secrets is MISSING values for essential sub-keys: {', '.join(missing_gcp_auth_keys)}. App cannot authenticate."); return None
    
    try:
        # Create a Credentials object from the service account information.
        # It's good practice to explicitly cast gcp_secrets to a dict() here, as the google-auth library
        # strictly expects a dictionary.
        credentials_object = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES) 
        # Authorize the gspread client (for interacting with Google Sheets) using these credentials.
        return gspread.authorize(credentials_object)
    except Exception as e: 
        st.error(f"Google Sheets Authentication Error: {e}"); return None

# This function attempts to convert a Pandas Series of date-like strings into proper datetime objects.
# It tries multiple common date formats to handle variations in the input data.
def robust_to_datetime(date_series_to_parse):
    # First, try Pandas' built-in to_datetime function with smart inference.
    # errors='coerce' will turn unparseable dates into NaT (Not a Time).
    parsed_dates_series = pd.to_datetime(date_series_to_parse, errors='coerce', infer_datetime_format=True)
    
    # Define a list of common date formats to try if the initial attempt fails for many entries.
    common_date_formats_list_for_parsing = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', 
                                            '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    # If a significant portion (>70%) of dates couldn't be parsed initially,
    # and the series isn't just full of empty strings or placeholder nulls, then try alternative formats.
    if not date_series_to_parse.empty and \
       parsed_dates_series.isnull().sum() > len(date_series_to_parse) * 0.7 and \
       not date_series_to_parse.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        for date_format_string_attempt in common_date_formats_list_for_parsing:
            try:
                temp_parsed_dates_with_format = pd.to_datetime(date_series_to_parse, format=date_format_string_attempt, errors='coerce')
                # If this format results in more successfully parsed dates, adopt this result.
                if temp_parsed_dates_with_format.notnull().sum() > parsed_dates_series.notnull().sum(): 
                    parsed_dates_series = temp_parsed_dates_with_format
                if parsed_dates_series.notnull().all(): break # If all dates are parsed, no need to try further formats
            except ValueError: continue # Ignore formats that are completely incompatible with the series
    return parsed_dates_series

# This function loads data from the specified Google Sheet and performs initial preprocessing.
# It's decorated with @st.cache_data to cache its results, improving performance on subsequent runs
# if the input arguments haven't changed. ttl=600 means the cache is valid for 600 seconds (10 minutes).
@st.cache_data(ttl=600)
def load_data_from_google_sheet(_sheet_url_or_name_for_cache_key, _worksheet_name_for_cache_key): # Underscore prefix for args used by cache
    # Retrieve the actual Google Sheet URL and worksheet name from Streamlit secrets.
    # This ensures that if secrets change, the cache is invalidated implicitly on the next run.
    google_sheet_url_from_secrets = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    google_worksheet_name_from_secrets = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    
    if not google_sheet_url_from_secrets: st.error("Configuration Error: GOOGLE_SHEET_URL_OR_NAME missing in secrets."); return pd.DataFrame()
    if not google_worksheet_name_from_secrets: st.error("Configuration Error: GOOGLE_WORKSHEET_NAME missing in secrets."); return pd.DataFrame()
    
    gspread_auth_client = authenticate_gspread() # Authenticate with Google Sheets
    if gspread_auth_client is None: return pd.DataFrame() # Return empty DataFrame if authentication fails
    
    try:
        # Open the Google Spreadsheet by its URL or, if not a URL, by its title/name.
        spreadsheet_gspread_obj = gspread_auth_client.open_by_url(google_sheet_url_from_secrets) if "docs.google.com" in google_sheet_url_from_secrets else gspread_auth_client.open(google_sheet_url_from_secrets) 
        worksheet_gspread_obj = spreadsheet_gspread_obj.worksheet(google_worksheet_name_from_secrets) # Open the specific worksheet (tab)
        raw_data_list_of_dicts = worksheet_gspread_obj.get_all_records(head=1, expected_headers=None) # Get all data rows as a list of dictionaries
        
        if not raw_data_list_of_dicts: st.warning("No data records found in the Google Sheet."); return pd.DataFrame()
        df_loaded_from_sheet = pd.DataFrame(raw_data_list_of_dicts) # Convert the data to a Pandas DataFrame
        st.sidebar.success(f"Successfully loaded {len(df_loaded_from_sheet)} records from '{google_worksheet_name_from_secrets}'.") 
        if df_loaded_from_sheet.empty: st.warning("DataFrame is empty after loading from Google Sheet."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound: 
        st.error(f"Spreadsheet Not Found: '{google_sheet_url_from_secrets}'. Check URL/Name & service account permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: 
        st.error(f"Worksheet Not Found: '{google_worksheet_name_from_secrets}'. Check name (case-sensitive)."); return pd.DataFrame()
    except Exception as e: 
        st.error(f"An error occurred while loading data from Google Sheet: {e}"); return pd.DataFrame()

    # --- Data Cleaning and Preprocessing ---
    df_loaded_from_sheet.columns = df_loaded_from_sheet.columns.str.strip() # Remove leading/trailing whitespace from column names
    
    # Define a mapping for date columns that need parsing and their new datetime column names
    date_columns_to_parse_map = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for original_date_col, new_datetime_col in date_columns_to_parse_map.items():
        if original_date_col in df_loaded_from_sheet.columns:
            # Clean date strings (remove newlines, strip whitespace) before attempting to parse
            cleaned_date_series_for_parsing = df_loaded_from_sheet[original_date_col].astype(str).str.replace('\n','',regex=False).str.strip()
            df_loaded_from_sheet[new_datetime_col] = robust_to_datetime(cleaned_date_series_for_parsing) # Parse to datetime objects
            if original_date_col == 'onboardingDate': # For 'onboardingDate', also create a column with just the date part
                df_loaded_from_sheet['onboarding_date_only'] = df_loaded_from_sheet[new_datetime_col].dt.date
        else: # If an expected date column is missing from the sheet
            df_loaded_from_sheet[new_datetime_col] = pd.NaT # Create an empty datetime column (Not a Time)
            if original_date_col == 'onboardingDate': df_loaded_from_sheet['onboarding_date_only'] = pd.NaT
    
    # Calculate 'days_to_confirmation' if both delivery and confirmation dates are present
    if 'deliveryDate_dt' in df_loaded_from_sheet.columns and 'confirmationTimestamp_dt' in df_loaded_from_sheet.columns:
        # Ensure columns are actual datetime objects before subtraction
        df_loaded_from_sheet['deliveryDate_dt'] = pd.to_datetime(df_loaded_from_sheet['deliveryDate_dt'], errors='coerce')
        df_loaded_from_sheet['confirmationTimestamp_dt'] = pd.to_datetime(df_loaded_from_sheet['confirmationTimestamp_dt'], errors='coerce')
        
        # Helper function to convert datetime series to UTC for consistent timezone handling in calculations
        def convert_datetime_series_to_utc(datetime_series_to_convert): 
            if pd.api.types.is_datetime64_any_dtype(datetime_series_to_convert) and datetime_series_to_convert.notna().any():
                try: 
                    # If timezone naive, localize to UTC. If timezone aware, convert to UTC.
                    return datetime_series_to_convert.dt.tz_localize('UTC') if datetime_series_to_convert.dt.tz is None else datetime_series_to_convert.dt.tz_convert('UTC')
                except Exception: return datetime_series_to_convert # Return original on timezone conversion error
            return datetime_series_to_convert
        # Calculate the difference in days
        df_loaded_from_sheet['days_to_confirmation'] = (convert_datetime_series_to_utc(df_loaded_from_sheet['confirmationTimestamp_dt']) - 
                                                        convert_datetime_series_to_utc(df_loaded_from_sheet['deliveryDate_dt'])).dt.days
    else: 
        df_loaded_from_sheet['days_to_confirmation'] = pd.NA # Use Pandas' missing value indicator for numbers

    # Ensure other essential string columns exist, are of string type, and NaNs are filled with empty strings.
    string_columns_to_ensure_and_clean = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary']
    for string_col_name_to_ensure in string_cols_to_ensure_and_clean:
        if string_col_name_to_ensure not in df_loaded_from_sheet.columns: 
            df_loaded_from_sheet[string_col_name_to_ensure] = "" # Default to empty string if column is missing
        else: 
            df_loaded_from_sheet[string_col_name_to_ensure] = df_loaded_from_sheet[string_col_name_to_ensure].astype(str).fillna("") 
    
    # Ensure 'score' column exists and is numeric; convert errors to NaT/NaN.
    if 'score' not in df_loaded_from_sheet.columns: df_loaded_from_sheet['score'] = pd.NA 
    df_loaded_from_sheet['score'] = pd.to_numeric(df_loaded_from_sheet['score'], errors='coerce')
    
    # Ensure all defined checklist item columns exist in the DataFrame, defaulting to NA if missing.
    # This prevents errors if a sheet is missing an expected boolean-like column.
    checklist_columns_to_ensure_as_na = ORDERED_KEY_CHECKLIST_ITEMS + ['onboardingWelcome'] # 'onboardingWelcome' might not be used in all calcs but ensure it exists
    for checklist_col_name_to_ensure in checklist_cols_to_ensure_as_na:
        if checklist_col_name_to_ensure not in df_loaded_from_sheet.columns: 
            df_loaded_from_sheet[checklist_col_name_to_ensure] = pd.NA 
            
    return df_loaded_from_sheet

# --- Helper Functions ---
@st.cache_data # Cache the result of this function
def convert_df_to_csv(df_for_csv_conversion): 
    # Converts a DataFrame to a CSV formatted string, encoded in UTF-8, ready for download.
    return df_for_csv_conversion.to_csv(index=False).encode('utf-8')

# Calculates key performance metrics from a given DataFrame.
def calculate_metrics(df_input_for_metrics_calc):
    if df_input_for_metrics_calc.empty: return 0, 0.0, pd.NA, pd.NA # Return defaults if input DataFrame is empty
    
    total_records_for_metrics = len(df_input_for_metrics_calc)
    # Calculate success rate: percentage of records where 'status' is 'confirmed' (case-insensitive).
    successful_onboardings_for_metrics = df_input_for_metrics_calc[df_input_for_metrics_calc['status'].astype(str).str.lower()=='confirmed'].shape[0]
    success_rate_calculated = (successful_onboardings_for_metrics / total_records_for_metrics * 100) if total_records_for_metrics > 0 else 0.0
    
    # Calculate average score. pd.to_numeric converts to numbers, errors='coerce' makes unconvertible values NaN. .mean() ignores NaNs.
    avg_score_calculated = pd.to_numeric(df_input_for_metrics_calc['score'], errors='coerce').mean()
    # Calculate average days to confirmation.
    avg_days_calculated = pd.to_numeric(df_input_for_metrics_calc['days_to_confirmation'], errors='coerce').mean()
    
    return total_records_for_metrics, success_rate_calculated, avg_score_calculated, avg_days_calculated

# Determines a default date range for filters, typically the current month or based on data availability.
def get_default_date_range(date_series_for_default_range_calc):
    today_date_for_range_calc = date.today()
    start_date_default_range_calc = today_date_for_range_calc.replace(day=1) # Default: start of current month
    end_date_default_range_calc = today_date_for_range_calc # Default: today
    min_date_in_data_calc, max_date_in_data_calc = None, None # Initialize min/max dates found in data
    
    if date_series_for_default_range_calc is not None and not date_series_for_default_range_calc.empty:
        # Convert series to date objects and drop any conversion errors (NaT).
        parsed_dates_for_range_calculation = pd.to_datetime(date_series_for_default_range_calc, errors='coerce').dt.date.dropna()
        if not parsed_dates_for_range_calculation.empty:
            min_date_in_data_calc = parsed_dates_for_range_calculation.min()
            max_date_in_data_calc = parsed_dates_for_range_calculation.max()
            # Adjust default range to be within the actual data's date range.
            start_date_default_range_calc = max(start_date_default_range_calc, min_date_in_data_calc)
            end_date_default_range_calc = min(end_date_default_range_calc, max_date_in_data_calc)
            # If calculated start is after end (e.g., all data is in the future or a very narrow past range),
            # then use the full extent of the data's date range.
            if start_date_default_range_calc > end_date_default_range_calc: 
                start_date_default_range_calc, end_date_default_range_calc = min_date_in_data_calc, max_date_in_data_calc
    return start_date_default_range_calc, end_date_default_range_calc, min_date_in_data_calc, max_date_in_data_calc

# --- Initialize Session State ---
# Set up default values for variables that need to persist across user interactions and app reruns.
# This ensures the app has a consistent starting state.
default_start_date_for_session_init, default_end_date_for_session_init, _, _ = get_default_date_range(None) # Get initial default date range
# Dictionary of session state keys and their corresponding default values.
session_state_key_default_values_map = {
    'data_loaded_successfully': False,      # Flag to track if data loading was successful
    'df_original': pd.DataFrame(),          # Stores the original, unfiltered DataFrame from Google Sheets
    'date_range_filter': (default_start_date_for_session_init, default_end_date_for_session_init), # Current date range filter
    'repName_filter': [],                   # List of selected reps for filtering
    'status_filter': [],                    # List of selected statuses for filtering
    'clientSentiment_filter': [],           # List of selected client sentiments for filtering
    'licenseNumber_search': "",             # Current search term for license number
    'storeName_search': "",                 # Current search term for store name
    'selected_transcript_key': None         # Stores the key of the currently selected transcript for viewing
}
# Loop through the defaults and initialize them in st.session_state if they don't already exist.
for session_state_key_init, session_state_default_val_init in session_state_key_value_pairs.items():
    if session_state_key_init not in st.session_state: 
        st.session_state[session_state_key_init] = session_state_default_val_init

# --- Data Loading Trigger ---
# This block executes if data hasn't been successfully loaded into the session state yet.
if not st.session_state.data_loaded_successfully:
    # Retrieve Google Sheet configuration details from Streamlit secrets.
    gs_url_secret_for_initial_load = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    gs_worksheet_secret_for_initial_load = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    
    if not gs_url_secret_for_initial_load or not gs_worksheet_secret_for_initial_load: 
        st.error("Configuration Error: Google Sheet URL/Name or Worksheet Name missing in Streamlit secrets. Cannot load data.")
    else:
        # Show a spinner UI element while data is being loaded.
        with st.spinner("Loading onboarding data from Google Sheet... This may take a moment."): 
            main_loaded_df_from_gs = load_data_from_google_sheet(gs_url_secret_for_initial_load, gs_worksheet_secret_for_initial_load) 
            if not main_loaded_df_from_gs.empty:
                st.session_state.df_original = main_loaded_df_from_gs # Store the loaded DataFrame in session state
                st.session_state.data_loaded_successfully = True # Set flag to indicate successful load
                # Update the default date range filter based on the actual dates in the loaded data.
                ds_after_main_load, de_after_main_load, _, _ = get_default_date_range(main_loaded_df_from_gs.get('onboarding_date_only'))
                st.session_state.date_range_filter = (ds_after_main_load, de_after_main_load) if ds_after_main_load and de_after_main_load else (default_start_date_for_session_init, default_end_date_for_session_init)
            else: # If loading failed or returned an empty DataFrame
                st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DataFrame on failure
                st.session_state.data_loaded_successfully = False
# Retrieve the original (unfiltered) DataFrame from session state for use throughout the app.
df_original = st.session_state.df_original 

# --- Main Application UI ---
st.title("🚀 Onboarding Performance Dashboard v2.11.1 🚀") # Display the main title of the dashboard

# If data loading was unsuccessful or the DataFrame is empty, display an error message and a refresh button.
if not st.session_state.data_loaded_successfully or df_original.empty:
    st.error("Failed to load data. Please check Google Sheet content, permissions, and secret configurations. You can try refreshing the data.")
    if st.sidebar.button("🔄 Force Refresh Data", key="refresh_button_on_initial_fail_sidebar"):
        st.cache_data.clear() # Clear all data cached by @st.cache_data
        st.session_state.clear() # Clear all variables stored in session state
        st.rerun() # Rerun the entire script from the beginning

# --- Sidebar UI Elements ---

# Expander in the sidebar to explain the scoring system for onboardings.
with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False): # expanded=False means it's collapsed by default
    st.markdown("""
    The onboarding score is calculated based on several factors:
    - **Primary Requirements (Max 4 points):** - `Confirm Kit Received` (2 points)
        - `Schedule Training & Promo` (2 points)
    - **Secondary Requirements (Max 3 points):** - `Intro Self & DIME` (1 point)
        - `Offer Display Help` (1 point)
        - `Provide Promo Credit Link` (1 point)
    - **Bonuses (Max 3 points):**
        - `+1 point` if Client Sentiment is "Positive".
        - `+1 point` if "Expectations Set" checklist item is true.
        - `+1 point` if all 6 key checklist items* are true (Completeness Bonus).
    
    The final score is rounded to the nearest whole number.
    
    *\*Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)

st.sidebar.header("⚙️ Data Controls")
# Button in the sidebar to manually refresh data from the Google Sheet.
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_data_button_main_sidebar_control"):
    st.cache_data.clear() # Clear cached data to force a reload from source
    st.session_state.clear() # Clear session state to reset all filters and flags
    st.rerun() # Rerun the script

st.sidebar.header("🔍 Filters") # Header for the filter section in the sidebar

# Date range filter setup in the sidebar
onboarding_dates_for_sidebar_date_filter_ui = df_original.get('onboarding_date_only') # Get date series safely
def_start_date_sidebar_ui, def_end_date_sidebar_ui, min_date_sidebar_ui, max_date_sidebar_ui = get_default_date_range(onboarding_dates_for_sidebar_date_filter_ui)
# Ensure date_range_filter in session state is a valid tuple of dates before use
if 'date_range_filter' not in st.session_state or \
   not (isinstance(st.session_state.date_range_filter,tuple) and len(st.session_state.date_range_filter)==2 and \
        all(isinstance(d_val_check, date) for d_val_check in st.session_state.date_range_filter)): # Check if all elements are dates
    st.session_state.date_range_filter = (def_start_date_sidebar_ui,def_end_date_sidebar_ui) if def_start_date_sidebar_ui and def_end_date_sidebar_ui else (date.today().replace(day=1),date.today())

if min_date_sidebar_ui and max_date_sidebar_ui and def_start_date_sidebar_ui and def_end_date_sidebar_ui: # Only show date input if a valid range could be determined
    current_val_start_sidebar_ui, current_val_end_sidebar_ui = st.session_state.date_range_filter
    # Ensure the widget's default value is within the min/max bounds of the available data
    widget_val_start_sidebar_ui = max(min_date_sidebar_ui,current_val_start_sidebar_ui) if current_val_start_sidebar_ui else min_date_sidebar_ui
    widget_val_end_sidebar_ui = min(max_date_sidebar_ui,current_val_end_sidebar_ui) if current_val_end_sidebar_ui else max_date_sidebar_ui
    # Handle edge case where clamped start might be after clamped end
    if widget_val_start_sidebar_ui and widget_val_end_sidebar_ui and widget_val_start_sidebar_ui > widget_val_end_sidebar_ui:
        widget_val_start_sidebar_ui, widget_val_end_sidebar_ui = min_date_sidebar_ui, max_date_sidebar_ui # Fallback to full data range
    
    selected_date_range_from_sidebar_widget = st.sidebar.date_input(
        "Date Range:", # Label for the date input widget
        value=(widget_val_start_sidebar_ui, widget_val_end_sidebar_ui), # Current value for the widget
        min_value=min_date_sidebar_ui, # Minimum selectable date
        max_value=max_date_sidebar_ui, # Maximum selectable date
        key="date_selector_sidebar_main_ui_widget" # Unique key for the widget
    )
    # If the user changes the date range in the widget, update the session state.
    if selected_date_range_from_sidebar_widget != st.session_state.date_range_filter: 
        st.session_state.date_range_filter = selected_date_range_from_sidebar_widget
else: 
    st.sidebar.warning("Onboarding date data not available for range filter.")
# Unpack the currently active date filter values from session state for use in filtering logic.
start_date_filter_active_main_logic, end_date_filter_active_main_logic = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter,tuple) and len(st.session_state.date_range_filter)==2 else (None,None)

# Text search filters (License Number, Store Name) in the sidebar
search_cols_definitions_sidebar_main_ui = {"licenseNumber":"License Number", "storeName":"Store Name"}
for col_key_search_main_ui, display_label_search_main_ui in search_cols_definitions_sidebar_main_ui.items():
    # Initialize session state for each search field if it doesn't exist
    if f"{col_key_search_main_ui}_search" not in st.session_state: st.session_state[f"{col_key_search_main_ui}_search"]=""
    # Create text input widget
    input_val_search_main_ui = st.sidebar.text_input(f"Search {display_label_search_main_ui} (on all data):",
                                           value=st.session_state[f"{col_key_search_main_ui}_search"], # Current value from session state
                                           key=f"{col_key_search_main_ui}_search_input_widget_main_ui") # Unique key
    # Update session state if the input value changes
    if input_val_search_main_ui != st.session_state[f"{col_key_search_main_ui}_search"]: 
        st.session_state[f"{col_key_search_main_ui}_search"]=input_val_search_main_ui

# Categorical multiselect filters (Rep Name, Status, Client Sentiment) in the sidebar
cat_filters_definitions_sidebar_main_ui = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_name_cat_main_ui, display_label_cat_main_ui in cat_filters_definitions_sidebar_main_ui.items():
    # Only show filter if the corresponding column exists in the DataFrame and has data
    if col_name_cat_main_ui in df_original.columns and df_original[col_name_cat_main_ui].notna().any():
        # Get unique, sorted, non-empty string values from the column for filter options.
        options_cat_main_ui = sorted([val_cat_ui for val_cat_ui in df_original[col_name_cat_main_ui].astype(str).dropna().unique() if val_cat_ui.strip()])
        if f"{col_name_cat_main_ui}_filter" not in st.session_state: st.session_state[f"{col_name_cat_main_ui}_filter"]=[]
        # Ensure current selection in session state is valid (values exist in current options).
        current_selection_cat_main_ui = [val_cat_sel_ui for val_cat_sel_ui in st.session_state[f"{col_name_cat_main_ui}_filter"] if val_cat_sel_ui in options_cat_main_ui]
        
        new_selection_cat_main_ui = st.sidebar.multiselect(f"Filter by {display_label_cat_main_ui}:",
                                                 options_cat_main_ui,default=current_selection_cat_main_ui,
                                                 key=f"{col_name_cat_main_ui}_multiselect_widget_main_ui")
        # Update session state if the multiselect selection changes.
        if new_selection_cat_main_ui != st.session_state[f"{col_name_cat_main_ui}_filter"]: 
            st.session_state[f"{col_name_cat_main_ui}_filter"]=new_selection_cat_main_ui

# Callback function for the "Clear All Filters" button.
# This function resets all filter-related session state variables to their defaults.
def clear_all_filters_callback_main_func():
    # Reset date range to default based on current data (or overall default if no data).
    ds_cb_main_func, de_cb_main_func, _, _ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range_filter = (ds_cb_main_func,de_cb_main_func) if ds_cb_main_func and de_cb_main_func else (date.today().replace(day=1),date.today())
    # Clear text search inputs.
    for key_search_main_cb_func in search_cols_definitions_sidebar_main_ui: st.session_state[f"{key_search_main_cb_func}_search"]=""
    # Clear multiselect filter selections.
    for key_cat_main_cb_func in cat_filters_definitions_sidebar_main_ui: st.session_state[f"{key_cat_main_cb_func}_filter"]=[]
    st.session_state.selected_transcript_key = None # Also clear the selected transcript
# Button in the sidebar to clear all active filters.
if st.sidebar.button("🧹 Clear All Filters",on_click=clear_all_filters_callback_main_func,use_container_width=True): 
    st.rerun() # Rerun the script to apply the cleared filters and update the UI

# --- Filtering Logic (Revised for search order) ---
# Initialize df_filtered as an empty DataFrame. It will be populated if df_original has data.
df_filtered = pd.DataFrame() 
if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    # Start with a fresh copy of the original DataFrame for filtering.
    df_working_copy_for_filtering_logic = st.session_state.df_original.copy()

    # 1. Apply License Number Search (operates on the working copy first)
    license_search_term_for_filter_logic = st.session_state.get("licenseNumber_search", "")
    if license_search_term_for_filter_logic and "licenseNumber" in df_working_copy_for_filtering_logic.columns:
        df_working_copy_for_filtering_logic = df_working_copy_for_filtering_logic[
            df_working_copy_for_filtering_logic['licenseNumber'].astype(str).str.contains(license_search_term_for_filter_logic, case=False, na=False)
        ]

    # 2. Apply Store Name Search (operates on the result of the license number search)
    store_search_term_for_filter_logic = st.session_state.get("storeName_search", "")
    if store_search_term_for_filter_logic and "storeName" in df_working_copy_for_filtering_logic.columns:
        df_working_copy_for_filtering_logic = df_working_copy_for_filtering_logic[
            df_working_copy_for_filtering_logic['storeName'].astype(str).str.contains(store_search_term_for_filter_logic, case=False, na=False)
        ]

    # df_working_copy_for_filtering_logic now contains results from license/store name searches on the original data.
    # Next, apply other filters (date, categorical filters) to this intermediate DataFrame.

    # 3. Apply date range filter to the current state of df_working_copy_for_filtering_logic
    if start_date_filter_active_main_logic and end_date_filter_active_main_logic and 'onboarding_date_only' in df_working_copy_for_filtering_logic.columns:
        parsed_dates_for_date_filter_logic = pd.to_datetime(df_working_copy_for_filtering_logic['onboarding_date_only'], errors='coerce').dt.date
        # Create a boolean mask for date filtering. Ensure it's aligned with the current DataFrame's index.
        date_filter_mask_apply_logic = parsed_dates_for_date_filter_logic.notna() & \
                                       (parsed_dates_for_date_filter_logic >= start_date_filter_active_main_logic) & \
                                       (parsed_dates_for_date_filter_logic <= end_date_filter_active_main_logic)
        df_working_copy_for_filtering_logic = df_working_copy_for_filtering_logic[date_filter_mask_apply_logic]
    
    # 4. Apply categorical multiselect filters to the current state of df_working_copy_for_filtering_logic
    for col_name_cat_filter_apply_logic, _ in cat_filters_definitions_sidebar_main_ui.items(): 
        selected_values_cat_filter_apply_logic = st.session_state.get(f"{col_name_cat_filter_apply_logic}_filter", [])
        if selected_values_cat_filter_apply_logic and col_name_cat_filter_apply_logic in df_working_copy_for_filtering_logic.columns: 
            df_working_copy_for_filtering_logic = df_working_copy_for_filtering_logic[
                df_working_copy_for_filtering_logic[col_name_cat_filter_apply_logic].astype(str).isin(selected_values_cat_filter_apply_logic)
            ]
    
    df_filtered = df_working_copy_for_filtering_logic.copy() # This is the final DataFrame after all filters are applied
else: 
    df_filtered = pd.DataFrame() # Ensure df_filtered is an empty DataFrame if there was no original data

# --- Plotly Layout Configuration ---
# Define a base layout dictionary for Plotly charts to ensure consistent styling across all visualizations.
# This was the source of the NameError; ensure this variable name is used consistently.
plotly_base_layout_settings = {"plot_bgcolor":PLOT_BG_COLOR, "paper_bgcolor":PLOT_BG_COLOR, "font_color":PRIMARY_TEXT_COLOR, 
                               "title_font_color":GOLD_ACCENT_COLOR, "legend_font_color":PRIMARY_TEXT_COLOR, 
                               "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":False}

# --- MTD Metrics Calculation ---
# Calculate Month-to-Date (MTD) and Previous Month metrics for the overview.
today_date_for_mtd_metrics_calc = date.today()
current_month_start_date_mtd_calc = today_date_for_mtd_metrics_calc.replace(day=1)
prev_month_end_date_mtd_calc = current_month_start_date_mtd_calc - timedelta(days=1)
prev_month_start_date_mtd_calc = prev_month_end_date_mtd_calc.replace(day=1)

# Initialize DataFrames for MTD calculations.
df_current_month_data_metrics_calc, df_prev_month_data_metrics_calc = pd.DataFrame(), pd.DataFrame() 
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    onboarding_dates_series_for_mtd_calc = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date
    valid_dates_mask_for_mtd_calc = onboarding_dates_series_for_mtd_calc.notna()
    if valid_dates_mask_for_mtd_calc.any():
        # Filter df_original for rows with valid dates first.
        df_with_valid_dates_for_mtd_calc = df_original[valid_dates_mask_for_mtd_calc].copy()
        # Use the corresponding valid dates series for creating period masks.
        valid_onboarding_dates_for_mtd_calc = onboarding_dates_series_for_mtd_calc[valid_dates_mask_for_mtd_calc]
        
        current_month_mask_for_mtd_calc = (valid_onboarding_dates_for_mtd_calc >= current_month_start_date_mtd_calc) & (valid_onboarding_dates_for_mtd_calc <= today_date_for_mtd_metrics_calc)
        previous_month_mask_for_mtd_calc = (valid_onboarding_dates_for_mtd_calc >= prev_month_start_date_mtd_calc) & (valid_onboarding_dates_for_mtd_calc <= prev_month_end_date_mtd_calc)
        
        # Apply masks. .values is used to ensure boolean array indexing if masks are Series.
        df_current_month_data_metrics_calc = df_with_valid_dates_for_mtd_calc[current_month_mask_for_mtd_calc.values]
        df_prev_month_data_metrics_calc = df_with_valid_dates_for_mtd_calc[previous_month_mask_for_mtd_calc.values]

# Calculate metrics for the current and previous MTD periods.
total_mtd_metric_val_final, sr_mtd_metric_val_final, score_mtd_metric_val_final, days_mtd_metric_val_final = calculate_metrics(df_current_month_data_metrics_calc)
total_prev_metric_val_final,_,_,_ = calculate_metrics(df_prev_month_data_metrics_calc) # Only need total for delta
# Calculate delta between current and previous MTD onboardings.
delta_mtd_metric_val_final = total_mtd_metric_val_final - total_prev_metric_val_final if pd.notna(total_mtd_metric_val_final) and pd.notna(total_prev_metric_val_final) else None

# --- Main Content Tabs ---
# Define the main tabs for organizing the dashboard content.
tab1_main_content_ui, tab2_main_content_ui, tab3_main_content_ui = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1_main_content_ui: # Content for the "Overview" tab
    st.header("📈 Month-to-Date (MTD) Overview")
    # Use st.columns to create a layout for MTD metric display.
    col1_tab1_metrics_ui, col2_tab1_metrics_ui, col3_tab1_metrics_ui, col4_tab1_metrics_ui = st.columns(4) 
    col1_tab1_metrics_ui.metric("Onboardings MTD", total_mtd_metric_val_final or "0", f"{delta_mtd_metric_val_final:+}" if delta_mtd_metric_val_final is not None else "N/A")
    col2_tab1_metrics_ui.metric("Success Rate MTD", f"{sr_mtd_metric_val_final:.1f}%" if pd.notna(sr_mtd_metric_val_final) else "N/A")
    col3_tab1_metrics_ui.metric("Avg Score MTD", f"{score_mtd_metric_val_final:.2f}" if pd.notna(score_mtd_metric_val_final) else "N/A")
    col4_tab1_metrics_ui.metric("Avg Days to Confirm MTD", f"{days_mtd_metric_val_final:.1f}" if pd.notna(days_mtd_metric_val_final) else "N/A")
    
    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_filtered_metrics_ui, sr_filtered_metrics_ui, score_filtered_metrics_ui, days_filtered_metrics_ui = calculate_metrics(df_filtered)
        fc1_tab1_metrics_ui,fc2_tab1_metrics_ui,fc3_tab1_metrics_ui,fc4_tab1_metrics_ui = st.columns(4)
        fc1_tab1_metrics_ui.metric("Filtered Onboardings", total_filtered_metrics_ui or "0")
        fc2_tab1_metrics_ui.metric("Filtered Success Rate", f"{sr_filtered_metrics_ui:.1f}%" if pd.notna(sr_filtered_metrics_ui) else "N/A")
        fc3_tab1_metrics_ui.metric("Filtered Avg Score", f"{score_filtered_metrics_ui:.2f}" if pd.notna(score_filtered_metrics_ui) else "N/A")
        fc4_tab1_metrics_ui.metric("Filtered Avg Days Confirm", f"{days_filtered_metrics_ui:.1f}" if pd.notna(days_filtered_metrics_ui) else "N/A")
    else: 
        st.info("No data matches current filter criteria to display in Overview.")

with tab2_main_content_ui: # Content for the "Detailed Analysis & Data" tab
    st.header("📋 Filtered Onboarding Data Table")
    # Use a copy of df_filtered for display, reset index for easier row selection by index later.
    df_display_table_for_tab2_content_ui = df_filtered.copy().reset_index(drop=True) 
    
    # Define columns to show in the main table (excluding fullTranscript and summary initially).
    cols_to_try_for_main_table_ui = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                                     'clientSentiment', 'days_to_confirmation'] + ORDERED_KEY_CHECKLIST_ITEMS
    cols_for_main_table_display_final_ui = [col for col in cols_to_try_for_main_table_ui if col in df_display_table_for_tab2_content_ui.columns]
    # Add any other columns not explicitly listed, excluding derived/internal ones and transcript/summary.
    other_cols_for_main_table_ui = [col for col in df_display_table_for_tab2_content_ui.columns 
                                    if col not in cols_for_main_table_display_final_ui and 
                                       not col.endswith(('_utc', '_str_original', '_dt')) and 
                                       col not in ['fullTranscript', 'summary']] 
    cols_for_main_table_display_final_ui.extend(other_cols_for_main_table_ui)

    if not df_display_table_for_tab2_content_ui.empty:
        # Function to apply conditional background styling to the DataFrame for scores and days.
        def style_dataframe_for_tab2_display_ui(df_to_style_in_tab2_ui): 
            styled_df_in_tab2_ui = df_to_style_in_tab2_ui.style
            if 'score' in df_to_style_in_tab2_ui.columns: 
                scores_numeric_for_style_tab2_ui = pd.to_numeric(df_to_style_in_tab2_ui['score'], errors='coerce')
                if scores_numeric_for_style_tab2_ui.notna().any():
                    styled_df_in_tab2_ui = styled_df_in_tab2_ui.background_gradient(subset=['score'],cmap='RdYlGn',low=0.3,high=0.7, gmap=scores_numeric_for_style_tab2_ui)
            if 'days_to_confirmation' in df_to_style_in_tab2_ui.columns:
                days_numeric_for_style_tab2_ui = pd.to_numeric(df_to_style_in_tab2_ui['days_to_confirmation'], errors='coerce')
                if days_numeric_for_style_tab2_ui.notna().any():
                    styled_df_in_tab2_ui = styled_df_in_tab2_ui.background_gradient(subset=['days_to_confirmation'],cmap='RdYlGn_r', gmap=days_numeric_for_style_tab2_ui)
            return styled_df_in_tab2_ui
        # Display the styled DataFrame.
        st.dataframe(style_dataframe_for_tab2_display_ui(df_display_table_for_tab2_content_ui[cols_for_main_table_display_final_ui]), 
                     use_container_width=True, height=300) # Set a fixed height for the table
        
        # --- Transcript Viewer Section ---
        st.markdown("---") # Visual separator
        st.subheader("🔍 View Full Onboarding Details & Transcript")
        
        if not df_display_table_for_tab2_content_ui.empty and 'fullTranscript' in df_display_table_for_tab2_content_ui.columns:
            # Create options for the selectbox: "Idx X: Store Name (Date)"
            transcript_options_map_for_selectbox_ui = {
                f"Idx {idx_for_selectbox_ui}: {row_for_selectbox_ui.get('storeName', 'N/A')} ({row_for_selectbox_ui.get('onboardingDate', 'N/A')})": idx_for_selectbox_ui 
                for idx_for_selectbox_ui, row_for_selectbox_ui in df_display_table_for_tab2_content_ui.iterrows()
            }
            if transcript_options_map_for_selectbox_ui: # If there are rows to select from
                # Use session state for the selectbox to remember the selection.
                if 'selected_transcript_key' not in st.session_state: 
                    st.session_state.selected_transcript_key = None # Initialize if not present

                selected_key_from_transcript_selectbox_ui = st.selectbox(
                    "Select an onboarding to view its details and transcript:",
                    options=[None] + list(transcript_options_map_for_selectbox_ui.keys()), # Add a "None" option for placeholder
                    index=0, # Default to the placeholder
                    format_func=lambda x_select_ui: "Choose an entry..." if x_select_ui is None else x_select_ui, # Display text for None
                    key="transcript_selector_widget_main_tab2_ui" 
                )
                
                # Update session state if the widget's selection has changed.
                if selected_key_from_transcript_selectbox_ui != st.session_state.selected_transcript_key:
                    st.session_state.selected_transcript_key = selected_key_from_transcript_selectbox_ui
                
                # If a valid entry (not None) is selected in session state:
                if st.session_state.selected_transcript_key :
                    selected_row_index_for_transcript_ui = transcript_options_map_for_selectbox_ui[st.session_state.selected_transcript_key]
                    selected_onboarding_row_details_ui = df_display_table_for_tab2_content_ui.loc[selected_row_index_for_transcript_ui]
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html_output_details_ui = "<div class='transcript-summary-grid'>"
                    summary_data_items_details_ui = { # Key-value pairs for the summary grid
                        "Store": selected_onboarding_row_details_ui.get('storeName', 'N/A'), 
                        "Rep": selected_onboarding_row_details_ui.get('repName', 'N/A'),
                        "Score": selected_onboarding_row_details_ui.get('score', 'N/A'),
                        "Status": selected_onboarding_row_details_ui.get('status', 'N/A'),
                        "Sentiment": selected_onboarding_row_details_ui.get('clientSentiment', 'N/A')
                    }
                    for item_label_details_ui, item_value_details_ui in summary_data_items_details_ui.items():
                        summary_html_output_details_ui += f"<div class='transcript-summary-item'><strong>{item_label_details_ui}:</strong> {item_value_details_ui}</div>"
                    
                    # Add the "summary" field from data, spanning full width of the grid.
                    data_summary_text_from_sheet_ui = selected_onboarding_row_details_ui.get('summary', 'N/A') 
                    summary_html_output_details_ui += f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary (from data):</strong> {data_summary_text_from_sheet_ui}</div>"
                    
                    summary_html_output_details_ui += "</div>" # Close grid
                    st.markdown(summary_html_output_details_ui, unsafe_allow_html=True)

                    st.markdown("##### Key Requirement Checks:")
                    # Iterate using the predefined ordered list of checklist items.
                    for item_column_name_details_ui in ORDERED_KEY_CHECKLIST_ITEMS:
                        # Get the full description and type from the KEY_REQUIREMENT_DETAILS dictionary.
                        requirement_details_obj_ui = KEY_REQUIREMENT_DETAILS.get(item_column_name_details_ui)
                        if requirement_details_obj_ui: # If details exist for this item
                            item_description_details_ui = requirement_details_obj_ui.get("description", item_column_name_details_ui.replace('_',' ').title())
                            item_type_details_ui = requirement_details_obj_ui.get("type", "") # Get Primary/Secondary/Bonus Criterion
                            
                            item_value_str_details_ui = str(selected_onboarding_row_details_ui.get(item_column_name_details_ui, "")).lower()
                            is_requirement_met_details_ui = item_value_str_details_ui in ['true', '1', 'yes']
                            status_emoji_details_ui = "✅" if is_requirement_met_details_ui else "❌"
                            
                            # Display each requirement with its type and full description.
                            type_tag_html_ui = f"<span class='type'>[{item_type_details_ui}]</span>" if item_type_details_ui else ""
                            st.markdown(f"<div class='requirement-item'>{status_emoji_details_ui} {item_description_details_ui} {type_tag_html_ui}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---") # Separator before transcript
                    st.markdown("##### Full Transcript:")
                    transcript_content_details_ui = selected_onboarding_row_details_ui.get('fullTranscript', "")
                    if transcript_content_details_ui:
                        html_transcript_output_details_ui = "<div class='transcript-container'>"
                        # Ensure both literal '\n' (escaped) and actual newlines are handled for HTML.
                        processed_transcript_content_details_ui = transcript_content_details_ui.replace('\\n', '\n') 
                        
                        for line_segment_from_transcript_details_ui in processed_transcript_content_details_ui.split('\n'):
                            current_line_details_ui = line_segment_from_transcript_details_ui.strip()
                            if not current_line_details_ui: continue # Skip empty lines
                            
                            parts_of_line_details_ui = current_line_details_ui.split(":", 1)
                            speaker_html_part_details_ui = f"<strong>{parts_of_line_details_ui[0].strip()}:</strong>" if len(parts_of_line_details_ui) == 2 else ""
                            # Replace internal newlines within a message part with <br> for HTML.
                            message_html_part_details_ui = parts_of_line_details_ui[1].strip().replace('\n', '<br>') if len(parts_of_line_details_ui) == 2 else current_line_details_ui.replace('\n', '<br>')
                            
                            html_transcript_output_details_ui += f"<p class='transcript-line'>{speaker_html_part_details_ui} {message_html_part_details_ui}</p>"
                        html_transcript_output_details_ui += "</div>"
                        st.markdown(html_transcript_output_details_ui, unsafe_allow_html=True)
                    else: 
                        st.info("No transcript available for this selection or the transcript is empty.")
        else: 
            st.info("No data in the filtered table to select a transcript from, or 'fullTranscript' column is missing.")
        st.markdown("---") # Separator after transcript viewer

        # Download button for the filtered data.
        csv_data_to_download_tab2_final_ui = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data as CSV", csv_data_to_download_tab2_final_ui, 'filtered_onboarding_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: 
        st.info("No data matches current filter criteria for table display.")
    
    # --- Key Visuals Section ---
    st.header("📊 Key Visuals (Based on Filtered Data)") 
    if not df_filtered.empty:
        col_viz1_tab2_charts_ui, col_viz2_tab2_charts_ui = st.columns(2) # Create two columns for visuals
        with col_viz1_tab2_charts_ui: # Visuals in the first column
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_fig_tab2_chart_ui = px.bar(df_filtered['status'].value_counts().reset_index(), x='status', y='count', 
                                     color='status', title="Onboarding Status Distribution")
                status_fig_tab2_chart_ui.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig_tab2_chart_ui, use_container_width=True)
            
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_fig_tab2_chart_ui = px.bar(df_filtered['repName'].value_counts().reset_index(), x='repName', y='count', 
                                     color='repName', title="Onboardings by Representative")
                rep_fig_tab2_chart_ui.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig_tab2_chart_ui, use_container_width=True)
        
        with col_viz2_tab2_charts_ui: # Visuals in the second column
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sentiment_counts_tab2_chart_ui = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map_config_tab2_ui = {
                    str(s_tab2_chart_ui).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s_tab2_chart_ui).lower() else 
                                     ('#2ca02c' if 'positive' in str(s_tab2_chart_ui).lower() else 
                                      ('#d62728' if 'negative' in str(s_tab2_chart_ui).lower() else None)))
                    for s_tab2_chart_ui in sentiment_counts_tab2_chart_ui['clientSentiment'].unique()
                }
                sentiment_fig_tab2_chart_ui = px.pie(sentiment_counts_tab2_chart_ui, names='clientSentiment', values='count', hole=0.4, 
                                     title="Client Sentiment Breakdown", color='clientSentiment', 
                                     color_discrete_map=sentiment_color_map_config_tab2_ui)
                sentiment_fig_tab2_chart_ui.update_layout(plotly_base_layout_settings); st.plotly_chart(sentiment_fig_tab2_chart_ui, use_container_width=True)

            # Checklist Item Completion chart (for 'confirmed' statuses)
            df_confirmed_tab2_chart_ui = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            actual_key_cols_tab2_chart_ui = [col_tab2_chart_ui for col_tab2_chart_ui in ORDERED_KEY_CHECKLIST_ITEMS if col_tab2_chart_ui in df_confirmed_tab2_chart_ui.columns]
            checklist_data_tab2_chart_ui = []
            if not df_confirmed_tab2_chart_ui.empty and actual_key_cols_tab2_chart_ui:
                for item_col_name_tab2_chart_viz_ui in actual_key_cols_tab2_chart_ui:
                    item_details_for_chart_viz_ui = KEY_REQUIREMENT_DETAILS.get(item_col_name_tab2_chart_viz_ui)
                    chart_label_for_item_chart_viz_ui = item_details_for_chart_viz_ui.get("chart_label", item_col_name_tab2_chart_viz_ui.replace('_',' ').title()) if item_details_for_chart_viz_ui else item_col_name_tab2_chart_viz_ui.replace('_',' ').title()
                    
                    map_bool_tab2_chart_ui = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                    if item_col_name_tab2_chart_viz_ui in df_confirmed_tab2_chart_ui.columns:
                        bool_s_tab2_chart_ui = pd.to_numeric(df_confirmed_tab2_chart_ui[item_col_name_tab2_chart_viz_ui].astype(str).str.lower().map(map_bool_tab2_chart_ui), errors='coerce')
                        if bool_s_tab2_chart_ui.notna().any():
                            true_c_tab2_chart_ui, total_v_tab2_chart_ui = bool_s_tab2_chart_ui.sum(), bool_s_tab2_chart_ui.notna().sum()
                            if total_v_tab2_chart_ui > 0:
                                checklist_data_tab2_chart_ui.append({"Key Requirement": chart_label_for_item_chart_viz_ui, 
                                                                  "Completion (%)": (true_c_tab2_chart_ui/total_v_tab2_chart_ui)*100})
                if checklist_data_tab2_chart_ui:
                    df_checklist_chart_tab2_final_ui = pd.DataFrame(checklist_data_tab2_chart_ui)
                    if not df_checklist_chart_tab2_final_ui.empty:
                        checklist_fig_tab2_final_ui = px.bar(df_checklist_chart_tab2_final_ui.sort_values("Completion (%)",ascending=True), 
                                                     x="Completion (%)", y="Key Requirement", orientation='h', 
                                                     title="Key Requirement Completion (Confirmed Onboardings)", 
                                                     color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        checklist_fig_tab2_final_ui.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}) 
                        st.plotly_chart(checklist_fig_tab2_final_ui, use_container_width=True)
                else: 
                    st.info("No data available for key requirement completion chart (e.g., no confirmed onboardings with checklist data).")
            else: 
                st.info("No 'confirmed' onboardings in the filtered data, or relevant checklist columns are missing, to show key requirement completion.")
    else: 
        st.info("No data matches current filter criteria to display detailed visuals.")

with tab3_main_content_ui: # Content for "Trends & Distributions" tab
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time chart
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_tab3_viz_ui = df_filtered.copy()
            df_trend_tab3_viz_ui['onboarding_date_only'] = pd.to_datetime(df_trend_tab3_viz_ui['onboarding_date_only'], errors='coerce')
            df_trend_tab3_viz_ui.dropna(subset=['onboarding_date_only'], inplace=True) 
            
            if not df_trend_tab3_viz_ui.empty:
                span_tab3_viz_ui = (df_trend_tab3_viz_ui['onboarding_date_only'].max() - df_trend_tab3_viz_ui['onboarding_date_only'].min()).days
                freq_tab3_viz_ui = 'D' if span_tab3_viz_ui <= 62 else ('W-MON' if span_tab3_viz_ui <= 365*1.5 else 'ME')
                data_tab3_viz_ui = df_trend_tab3_viz_ui.set_index('onboarding_date_only').resample(freq_tab3_viz_ui).size().reset_index(name='count')
                if not data_tab3_viz_ui.empty:
                    fig_trend_tab3_viz_ui = px.line(data_tab3_viz_ui, x='onboarding_date_only', y='count', markers=True, 
                                      title="Onboardings Over Filtered Period")
                    fig_trend_tab3_viz_ui.update_layout(plotly_base_layout_settings) 
                    st.plotly_chart(fig_trend_tab3_viz_ui, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend after resampling.")
            else: 
                st.info("No valid date data available in filtered set for onboarding trend chart.")
        
        # Days to Confirmation Distribution chart
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_tab3_viz_ui = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_tab3_viz_ui.empty:
                nbins_tab3_viz_ui = max(10, min(50, int(len(days_data_tab3_viz_ui)/5))) if len(days_data_tab3_viz_ui) > 20 else (len(days_data_tab3_viz_ui.unique()) or 10)
                fig_days_dist_tab3_viz_ui = px.histogram(days_data_tab3_viz_ui, nbins=nbins_tab3_viz_ui, 
                                           title="Days to Confirmation Distribution")
                fig_days_dist_tab3_viz_ui.update_layout(plotly_base_layout_settings) 
                st.plotly_chart(fig_days_dist_tab3_viz_ui, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data in filtered set to plot distribution.")
    else: 
        st.info("No data matches current filter criteria to display Trends & Distributions.")

st.sidebar.markdown("---") # Visual separator in sidebar
st.sidebar.info("Dashboard v2.11.1 | Secured Access") # App version info in sidebar