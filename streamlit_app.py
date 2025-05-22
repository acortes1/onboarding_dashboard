# Import necessary libraries.
import streamlit as st  # For creating web apps.
import pandas as pd  # For working with data (like tables).
import plotly.express as px  # For creating interactive charts.
import plotly.graph_objects as go # More tools for charts.
from datetime import datetime, date, timedelta  # For working with dates and times.
import gspread  # To connect and work with Google Sheets.
from google.oauth2.service_account import Credentials  # For Google API security.
import time  # For pausing the code if needed.
import numpy as np  # For numerical operations (often used with pandas).
import re  # For text pattern matching (like phone numbers).
from dateutil import tz  # For handling different time zones.

# --- Page Configuration ---
# Set up the basic look and feel of your Streamlit page.
st.set_page_config(
    page_title="Onboarding Analytics Dashboard", # The title that appears in the browser tab.
    page_icon="📈",  # The small icon (favicon) in the browser tab.
    layout="wide",  # Use the full width of the screen.
    initial_sidebar_state="expanded" # Keep the sidebar open when the app loads.
)

# --- Custom CSS Injection ---
# This function creates and adds custom styles (CSS) to make the app look better.
def load_custom_css():
    """Loads and injects custom CSS for the application."""
    # Get the current theme (light or dark) from Streamlit settings.
    THEME = st.get_option("theme.base")

    # Define color sets for both light and dark themes.
    # These colors will be used to style different parts of the app.
    if THEME == "light":
        SCORE_GOOD_BG = "#DFF0D8"; SCORE_GOOD_TEXT = "#3C763D";
        SCORE_MEDIUM_BG = "#FCF8E3"; SCORE_MEDIUM_TEXT = "#8A6D3B";
        SCORE_BAD_BG = "#F2DEDE"; SCORE_BAD_TEXT = "#A94442";
        SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT;
        SENTIMENT_NEUTRAL_BG = "#F0F2F6"; SENTIMENT_NEUTRAL_TEXT = "#4A5568";
        SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT;
        DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT;
        DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT;
        DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT;
        REQ_MET_BG = "#E7F3E7"; REQ_MET_TEXT = "#256833";
        REQ_NOT_MET_BG = "#F8EAEA"; REQ_NOT_MET_TEXT = "#9E3434";
        REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)";
        TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)";
        TABLE_BORDER_COLOR = "var(--border-color)";
        LOGIN_BOX_BG = "var(--background-color)"; LOGIN_BOX_SHADOW = "0 12px 35px rgba(0,0,0,0.07)";
        LOGOUT_BTN_BG = "#F2DEDE"; LOGOUT_BTN_TEXT = "#A94442"; LOGOUT_BTN_BORDER = "#A94442";
        LOGOUT_BTN_HOVER_BG = "#EBCFCF";
        PRIMARY_BTN_BG = "#6A0DAD"; PRIMARY_BTN_HOVER_BG = "#580A8F";
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#6A0DAD"; DOWNLOAD_BTN_BORDER = "#6A0DAD";
        DOWNLOAD_BTN_HOVER_BG = "#6A0DAD"; DOWNLOAD_BTN_HOVER_TEXT = "#FFFFFF";
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)";
    else: # Dark Theme
        SCORE_GOOD_BG = "#1E4620"; SCORE_GOOD_TEXT = "#A8D5B0";
        SCORE_MEDIUM_BG = "#4A3F22"; SCORE_MEDIUM_TEXT = "#FFE0A2";
        SCORE_BAD_BG = "#5A2222"; SCORE_BAD_TEXT = "#FFBDBD";
        SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT;
        SENTIMENT_NEUTRAL_BG = "#2D3748"; SENTIMENT_NEUTRAL_TEXT = "#A0AEC0";
        SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT;
        DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT;
        DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT;
        DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT;
        REQ_MET_BG = "#1A3A21"; REQ_MET_TEXT = "#A7D7AE";
        REQ_NOT_MET_BG = "#4D1A1A"; REQ_NOT_MET_TEXT = "#FFADAD";
        REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)";
        TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)";
        TABLE_BORDER_COLOR = "var(--border-color)";
        LOGIN_BOX_BG = "var(--secondary-background-color)"; LOGIN_BOX_SHADOW = "0 10px 35px rgba(0,0,0,0.3)";
        LOGOUT_BTN_BG = "#5A2222"; LOGOUT_BTN_TEXT = "#FFBDBD"; LOGOUT_BTN_BORDER = "#FFBDBD";
        LOGOUT_BTN_HOVER_BG = "#6B3333";
        PRIMARY_BTN_BG = "#BE90D4"; PRIMARY_BTN_HOVER_BG = "#A77CBF";
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#BE90D4"; DOWNLOAD_BTN_BORDER = "#BE90D4";
        DOWNLOAD_BTN_HOVER_BG = "#BE90D4"; DOWNLOAD_BTN_HOVER_TEXT = "#1E1E1E";
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)";

    # Define table cell padding and font size.
    TABLE_CELL_PADDING = "0.65em 0.8em";
    TABLE_FONT_SIZE = "0.92rem";

    # Create the CSS code as a long string.
    # It uses f-string formatting to insert the color variables defined above.
    # This CSS targets specific Streamlit elements to change their appearance.
    css = f"""
    <style>
        :root {{ /* Define variables for easy reuse */
            --score-good-bg: {SCORE_GOOD_BG}; --score-good-text: {SCORE_GOOD_TEXT};
            /* ... (many more color variables) ... */
        }}
        body {{ font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }} /* Set a nice font */
        .stApp {{ padding: 0.5rem 1rem; }} /* Add some padding around the app */
        h1 {{ /* Style the main title */
            text-align: center; padding: 0.8em 0.5em; font-size: 2.3rem;
            border-bottom: 2px solid var(--primary-color); margin-bottom: 1.5em;
        }}
        /* ... (many more CSS rules for titles, metrics, buttons, tables, login screen, etc.) ... */
        .custom-styled-table th {{ /* Style table headers */
            background-color: var(--table-header-bg); color: var(--table-header-text);
            position: sticky; top: 0; z-index: 2; /* Make headers stick when scrolling */
        }}
        /* ... (CSS rules for different cell colors based on data) ... */
        .login-container {{ /* Style the login area */
            display: flex; justify-content: center; align-items: center;
        }}
        /* ... (Responsive CSS to make it look good on smaller screens) ... */
        @media (max-width: 768px) {{
             /* Adjust styles for tablets */
        }}
        @media (max-width: 480px) {{
            /* Adjust styles for phones */
        }}
    </style>
    """
    # Use Streamlit's markdown function to inject this CSS into the app's HTML.
    # `unsafe_allow_html=True` is needed but use with caution (only with your own CSS).
    st.markdown(css, unsafe_allow_html=True)

# Call the function to apply our custom styles.
load_custom_css()

# --- Constants & Configuration ---
# Define scopes: These tell Google which services (Sheets, Drive) our app needs access to.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Define key requirements for onboarding calls and their properties.
KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and the Company.", "type": "Secondary", "chart_label": "Intro Self & Company"},
    'confirmKitReceived': {"description": "Confirm kit and initial order received.", "type": "Primary", "chart_label": "Kit & Order Recv'd"},
    'offerDisplayHelp': {"description": "Ask about help setting up in-store display.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule budtender training & first promo.", "type": "Primary", "chart_label": "Sched. Training/Promo"},
    'providePromoCreditLink': {"description": "Provide link for promo-credit requests.", "type": "Secondary", "chart_label": "Promo Credit Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
# Define the order in which requirements should be displayed.
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS # Use the same order for charts.

# Define time zones (PST for display, UTC for internal consistency).
PST_TIMEZONE = tz.gettz('America/Los_Angeles'); UTC_TIMEZONE = tz.tzutc()

# Get the current Streamlit theme again for Plotly chart colors.
THEME_PLOTLY = st.get_option("theme.base")
PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)" # Make chart backgrounds transparent.

# Set Plotly chart colors based on the theme.
if THEME_PLOTLY == "light":
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7' }; TEXT_COLOR_FOR_PLOTLY = "#262730"; PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
else: # Dark Theme
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D' }; TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"; PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"

# Define base settings for all Plotly charts for a consistent look.
plotly_base_layout_settings = {"plot_bgcolor": PLOT_BG_COLOR_PLOTLY, "paper_bgcolor": PLOT_BG_COLOR_PLOTLY, "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":True, "yaxis_gridcolor": 'rgba(128,128,128,0.2)', "margin": dict(l=50, r=30, t=70, b=50), "font_color": TEXT_COLOR_FOR_PLOTLY, "title_font_color": PRIMARY_COLOR_FOR_PLOTLY, "title_font_size": 18, "xaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "xaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "legend_font_color": TEXT_COLOR_FOR_PLOTLY, "legend_title_font_color": PRIMARY_COLOR_FOR_PLOTLY}

# --- Google SSO & Domain Check ---
# This function handles user login and checks if their email belongs to an allowed domain.
def check_login_and_domain():
    """Checks if user is logged in and has the correct domain. Returns status."""
    # Get the allowed domain from Streamlit secrets (if set).
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", None)

    # Check if the user is logged in using Streamlit's built-in user management.
    if not st.user.is_logged_in:
        return 'NOT_LOGGED_IN'

    # Get the user's email.
    user_email = st.user.email
    if not user_email:
        st.error("Could not retrieve user email. Please try logging in again.")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'ERROR'

    # If an allowed domain is set, check if the user's email matches.
    if allowed_domain and not user_email.endswith(f"@{allowed_domain}"):
        st.error(f"🚫 Access Denied. Only users from the '{allowed_domain}' domain are allowed.")
        st.info(f"You are attempting to log in as: {user_email}")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'DOMAIN_MISMATCH'

    # If everything is okay, return 'AUTHORIZED'.
    return 'AUTHORIZED'


# --- Data Loading & Processing Functions ---

# Function to connect to Google Sheets using service account credentials.
# `@st.cache_data` tells Streamlit to store the result of this function.
# If called again with the same inputs, it returns the stored result instead of
# running again, which saves time. `ttl=600` means it expires after 600 seconds (10 mins).
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    """Authenticates with Google Sheets API using cached credentials."""
    # Get Google Cloud Platform (GCP) secrets from Streamlit secrets.
    gcp_secrets_obj = st.secrets.get("gcp_service_account")
    if gcp_secrets_obj is None: st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND."); return None
    try:
        # Convert secrets to a dictionary and check if all required keys are present.
        gcp_secrets_dict = dict(gcp_secrets_obj)
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing_keys = [k for k in required_keys if gcp_secrets_dict.get(k) is None]
        if missing_keys: st.error(f"🚨 Error: GCP secrets dict missing keys: {', '.join(missing_keys)}."); return None
        # Create credentials from the secrets.
        creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
        # Authorize gspread (the Google Sheets library) with these credentials.
        return gspread.authorize(creds)
    except Exception as e:
        # Handle any errors during authentication.
        st.error(f"🚨 Error Processing GCP Secrets or Authenticating: {e}. Check format/permissions."); return None

# Function to convert columns to datetime objects, trying multiple formats.
def robust_to_datetime(series):
    """Tries multiple formats to convert a column (Series) to datetime objects."""
    # First, try pandas' automatic conversion.
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    # If many values failed and the column isn't empty/NA, try specific formats.
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null', 'na']).all():
        common_formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', # Define common date/time formats
                          '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
                          '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
        # Try formats with and without assuming day comes first.
        for dayfirst_setting in [False, True]:
            for fmt in common_formats:
                try:
                    # Try converting with the current format.
                    temp_dates = pd.to_datetime(series, format=fmt, errors='coerce', dayfirst=dayfirst_setting)
                    # If this format worked better, use it.
                    if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                    if dates.notnull().all(): break # Stop if all dates are converted.
                except ValueError: continue # Ignore if a format doesn't work.
            if dates.notnull().all(): break
    return dates

# Function to convert a datetime column to a readable PST string.
def format_datetime_to_pst_str(dt_series):
    """Converts a datetime Series to PST formatted strings."""
    # Check if the input is a datetime series and not empty.
    if not pd.api.types.is_datetime64_any_dtype(dt_series) or dt_series.isnull().all():
        return dt_series # Return as is if not datetime or all null.

    # Function to convert a single datetime value.
    def convert_element(element):
        if pd.isna(element): return None # Handle null values.
        try:
            # Make sure it's UTC, then convert to PST.
            utc_element = element.tz_localize(UTC_TIMEZONE) if element.tzinfo is None else element.tz_convert(UTC_TIMEZONE)
            pst_element = utc_element.tz_convert(PST_TIMEZONE)
            # Format as 'YYYY-MM-DD HH:MM AM/PM PST'.
            return pst_element.strftime('%Y-%m-%d %I:%M %p PST')
        except Exception: return str(element) # Return as string on error.

    # Try converting the whole series at once (faster).
    try:
        utc_series = dt_series.dt.tz_localize(UTC_TIMEZONE) if dt_series.dt.tz is None else dt_series.dt.tz_convert(UTC_TIMEZONE)
        pst_series = utc_series.dt.tz_convert(PST_TIMEZONE)
        return pst_series.apply(lambda x: x.strftime('%Y-%m-%d %I:%M %p PST') if pd.notnull(x) else None)
    except Exception:
        # If the fast way fails, convert each element individually.
        return dt_series.apply(convert_element)

# Function to format phone numbers nicely (e.g., (123) 456-7890).
def format_phone_number(number_str):
    """Formats a string into a standard US phone number format."""
    if pd.isna(number_str) or not str(number_str).strip(): return "" # Handle empty/null values.
    # Remove all non-digit characters.
    digits = re.sub(r'\D', '', str(number_str))
    # Apply formatting based on the number of digits.
    if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(number_str) # Return original if not a standard length.

# Function to capitalize names (e.g., "john doe" -> "John Doe").
def capitalize_name(name_str):
    """Capitalizes each word in a name string."""
    if pd.isna(name_str) or not str(name_str).strip(): return "" # Handle empty/null values.
    return ' '.join(word.capitalize() for word in str(name_str).split())

# Function to load data from the Google Sheet.
# It's cached to avoid re-fetching data too often.
@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet():
    """Loads data from the configured Google Sheet."""
    gc = authenticate_gspread_cached() # Get the authenticated Google Sheets connection.
    current_time = datetime.now(UTC_TIMEZONE) # Note the current time (UTC).
    if gc is None: return pd.DataFrame(), None # Return empty if authentication failed.

    # Get Sheet URL and Worksheet name from secrets.
    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not sheet_url_or_name: st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame(), None
    if not worksheet_name: st.error("🚨 Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame(), None

    try:
        # Open the Google Sheet by URL or by name.
        spreadsheet = gc.open_by_url(sheet_url_or_name) if ("docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name) else gc.open(sheet_url_or_name)
        # Select the specific worksheet.
        worksheet = spreadsheet.worksheet(worksheet_name)
        # Get all data as a list of dictionaries (records).
        data = worksheet.get_all_records(head=1, expected_headers=None)
        if not data: st.warning("⚠️ No data rows in Google Sheet."); return pd.DataFrame(), current_time

        # Convert the data into a pandas DataFrame.
        df = pd.DataFrame(data)

        # --- Data Cleaning and Standardization ---
        # 1. Clean column names (lowercase, no spaces).
        df.rename(columns={col: "".join(str(col).strip().lower().split()) for col in df.columns}, inplace=True)

        # 2. Map potential column names to standard names used in the app.
        column_name_map_to_code = {"licensenumber": "licenseNumber", "storename": "storeName", /* ... many mappings ... */ }
        # Add key requirement columns to the map.
        for req_key_internal in KEY_REQUIREMENT_DETAILS.keys(): column_name_map_to_code[req_key_internal.lower()] = req_key_internal
        # Apply the renaming only for columns that exist and aren't already named correctly.
        cols_to_rename_actual = {std_col: code_col for std_col, code_col in column_name_map_to_code.items() if std_col in df.columns and code_col not in df.columns}
        df.rename(columns=cols_to_rename_actual, inplace=True)

        # 3. Convert date/time columns.
        date_cols_map = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
        for original_col, dt_col in date_cols_map.items():
            if original_col in df.columns:
                df[original_col] = df[original_col].astype(str).str.replace('\n',' ',regex=False).str.strip() # Clean string first.
                df[dt_col] = robust_to_datetime(df[original_col]) # Convert to datetime.
                df[original_col] = format_datetime_to_pst_str(df[dt_col]) # Format back to PST string.
            else: df[dt_col] = pd.NaT # Add empty column if missing.

        # 4. Create a 'date only' column for easier filtering.
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date if 'onboardingDate_dt' in df.columns else pd.NaT

        # 5. Calculate 'days to confirmation'.
        if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
            # Ensure both are UTC before calculating the difference.
            delivery_utc = df['deliveryDate_dt'].dt.tz_localize(UTC_TIMEZONE) # Assume UTC if no timezone
            confirmation_utc = df['confirmationTimestamp_dt'].dt.tz_localize(UTC_TIMEZONE)
            df['days_to_confirmation'] = (confirmation_utc - delivery_utc).dt.days
        else: df['days_to_confirmation'] = pd.NA # Set to NA if columns are missing.

        # 6. Format phone numbers and names.
        for phone_col in ['contactNumber', 'confirmedNumber']:
            if phone_col in df.columns: df[phone_col] = df[phone_col].apply(format_phone_number)
        for name_col in ['repName', 'contactName']:
            if name_col in df.columns: df[name_col] = df[name_col].apply(capitalize_name)

        # 7. Ensure key text columns exist and are strings, replacing 'nan' etc. with empty strings.
        string_cols = ['status', 'clientSentiment', 'repName', 'storeName', /* ... */]
        for col in string_cols: df[col] = df.get(col, "").astype(str).replace(['nan', 'NaN', 'None', 'NaT', '<NA>'], "", regex=False).fillna("")

        # 8. Convert 'score' to a number, handling errors.
        df['score'] = pd.to_numeric(df.get('score'), errors='coerce')

        # 9. Ensure all requirement columns exist.
        for col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS: df[col] = df.get(col, pd.NA)

        # 10. Drop any old/unwanted columns.
        cols_to_drop = [col for col in ['deliverydatets', 'onboardingwelcome'] if col in df.columns]
        if cols_to_drop: df = df.drop(columns=cols_to_drop)

        # Return the cleaned DataFrame and the time it was loaded.
        return df, current_time

    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 GS Error: {e}. Check URL/name & permissions."); return pd.DataFrame(), None
    except Exception as e:
        st.error(f"🌪️ Error loading data: {e}"); return pd.DataFrame(), None

# Function to convert a DataFrame to a CSV format for download.
@st.cache_data
def convert_df_to_csv(df_to_convert):
    """Converts a DataFrame to a CSV string."""
    return df_to_convert.to_csv(index=False).encode('utf-8')

# Function to calculate key metrics from a DataFrame.
def calculate_metrics(df_input):
    """Calculates summary metrics for a given DataFrame."""
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA # Return defaults if empty.
    total = len(df_input) # Total rows.
    # Count rows where status is 'confirmed'.
    confirmed = df_input[df_input['status'].astype(str).str.lower().str.contains('confirmed', na=False)].shape[0]
    # Calculate success rate.
    success_rate = (confirmed / total * 100) if total > 0 else 0.0
    # Calculate average score and days to confirmation.
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    avg_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

# Function to determine the default date range (usually Month-to-Date).
def get_default_date_range(date_series):
    """Calculates the default date range for filters (MTD or based on data)."""
    today = date.today()
    start_of_month = today.replace(day=1)
    # Get min/max dates from the data if available.
    min_date, max_date = (pd.to_datetime(date_series, errors='coerce').dt.date.dropna().min(), pd.to_datetime(date_series, errors='coerce').dt.date.dropna().max()) if date_series is not None and date_series.notna().any() else (None, None)
    # Determine start/end, considering data range and MTD.
    start = max(start_of_month, min_date) if min_date else start_of_month
    end = min(today, max_date) if max_date else today
    return (start, end) if start <= end else ((min_date, max_date) if min_date and max_date else (start_of_month, today))

# --- Main App Logic ---
# First, check if the user is logged in and authorized.
auth_status = check_login_and_domain()

# If not authorized, show the login screen or error message and stop.
if auth_status != 'AUTHORIZED':
    if auth_status == 'NOT_LOGGED_IN':
        st.markdown("""
            <div class='login-container'>
                <div class='login-box'>
                    <div class='login-icon'>🔑</div>
                    <h2>Dashboard Access</h2>
                    <p>Please log in using your <b>authorized</b> Google account to access the dashboard.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        # Center the login button.
        _, login_col, _ = st.columns([1, 1, 1])
        with login_col:
            st.button("Log in with Google 🔑", on_click=st.login, use_container_width=True, key="google_login_main_btn_centered")
    st.stop() # Stop further execution.

# --- If Authorized, Continue ---
# Initialize session state variables. Streamlit's session state holds values
# across reruns (when filters change, etc.), so the app remembers user selections.
default_s_init, default_e_init = get_default_date_range(None) # Get initial default dates.
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
# ... (Initialize many other session state variables for filters, tabs, etc.) ...
st.session_state.setdefault('active_tab', TAB_OVERVIEW) # Set default tab.

# Load data if it hasn't been loaded yet in this session.
if not st.session_state.data_loaded:
    df_loaded, load_time = load_data_from_google_sheet()
    if load_time: # If data loading was attempted.
        st.session_state.last_data_refresh_time = load_time
        if not df_loaded.empty:
            # Store the loaded data and update date ranges in session state.
            st.session_state.df_original = df_loaded
            st.session_state.data_loaded = True
            min_d, max_d = (pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().min(), pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().max()) if 'onboarding_date_only' in df_loaded and df_loaded['onboarding_date_only'].notna().any() else (None, None)
            st.session_state.min_data_date_for_filter = min_d
            st.session_state.max_data_date_for_filter = max_d
            st.session_state.date_range = get_default_date_range(df_loaded.get('onboarding_date_only'))
        else: # Handle case where loading worked but returned no data.
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded = False
    else: # Handle case where loading failed.
        st.session_state.df_original = pd.DataFrame()
        st.session_state.data_loaded = False

# Get the original DataFrame from session state for use.
df_original = st.session_state.df_original

# --- Sidebar ---
# Set up the sidebar with controls and filters.
st.sidebar.header("⚙️ Dashboard Controls"); st.sidebar.markdown("---")

# Global Search section in the sidebar.
st.sidebar.subheader("🔍 Global Search"); st.sidebar.caption("Search all data. Overrides filters below.")
# Add input fields for searching by license number and store name.
ln_search_val = st.sidebar.text_input("Search License Number:", value=st.session_state.get("licenseNumber_search", ""), key="licenseNumber_global_search_widget_v4_3_1", help="Enter license number part.")
# If the search value changes, update session state and rerun the app.
if ln_search_val != st.session_state["licenseNumber_search"]: st.session_state["licenseNumber_search"] = ln_search_val; st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", "")); st.rerun()
# Create a dropdown (selectbox) for store names.
store_names_options = [""]; # Start with a blank option.
if not df_original.empty and 'storeName' in df_original.columns:
    # Populate options with unique store names from the data.
    unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique());
    store_names_options.extend([name for name in unique_stores if str(name).strip()])
# Set the current value of the dropdown.
current_store_search_val = st.session_state.get("storeName_search", "");
try: current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
except ValueError: current_store_idx = 0
# Create the selectbox widget.
selected_store_val = st.sidebar.selectbox("Search Store Name:", options=store_names_options, index=current_store_idx, key="storeName_global_search_widget_select_v4_3_1", help="Select or type store name.")
# If the selection changes, update session state and rerun.
if selected_store_val != st.session_state["storeName_search"]: st.session_state["storeName_search"] = selected_store_val; st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", "")); st.rerun()
st.sidebar.markdown("---"); global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))

# Filters section in the sidebar.
st.sidebar.subheader("📊 Filters"); st.sidebar.caption("Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data.")
st.sidebar.markdown("##### Quick Date Ranges"); s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
# Add buttons for MTD, YTD, and ALL date ranges.
if s_col1.button("MTD", /* ... */ ): # If MTD button clicked...
    # Set date range to MTD and rerun.
    start_mtd = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
# ... (Similar buttons for YTD and ALL) ...

# Add the date input widget for custom date ranges.
selected_date_range_tuple = st.sidebar.date_input("Custom Date Range (Onboarding):", /* ... */)
# If the custom range changes, update session state and rerun.
if not global_search_active and isinstance(selected_date_range_tuple, tuple) and len(selected_date_range_tuple) == 2:
    if selected_date_range_tuple != st.session_state.date_range: st.session_state.date_range = selected_date_range_tuple; st.session_state.date_filter_is_active = True; st.rerun()
start_dt_filter, end_dt_filter = st.session_state.date_range # Get the current date filter.

# Add multiselect widgets for categorical filters (Rep, Status, Sentiment).
category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label_text in category_filters_map.items():
    options_for_multiselect = [];
    # Populate options from unique values in the data.
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any():
        options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).dropna().unique() if str(val).strip()])
    # Get current selection from session state.
    current_selection_for_multiselect = st.session_state.get(f"{col_key}_filter", []);
    # Create the multiselect widget.
    new_selection_multiselect = st.sidebar.multiselect(f"Filter by {label_text}:", /* ... */)
    # If selection changes, update session state and rerun.
    if not global_search_active and new_selection_multiselect != valid_current_selection: st.session_state[f"{col_key}_filter"] = new_selection_multiselect; st.rerun()

# Function to clear all filters and search.
def clear_all_filters_and_search_v4_3_1():
    """Resets all filters and search fields to their defaults."""
    # Reset date range.
    ds_cleared, de_cleared = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_cleared, de_cleared);
    # Clear search fields.
    st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
    # Clear category filters.
    for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
    # Reset selected transcript and tab.
    st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state.active_tab = TAB_OVERVIEW
# Add the 'Clear Filters' button.
if st.sidebar.button("🧹 Clear Filters", on_click=clear_all_filters_and_search_v4_3_1, /* ... */): st.rerun()

# Add an expander to explain the scoring system.
with st.sidebar.expander("ℹ️ Score Breakdown (0-10 pts)", expanded=True):
    st.markdown("""Score (0-10 pts):\n- **Primary (4 pts):** Kit Recv'd (2), Train/Promo Sched. (2).\n- **Secondary (3 pts):** Intro (1), Display Help (1), Promo Link (1).\n- **Bonuses (3 pts):** +1 Positive Sentiment, +1 Expectations Set, +1 Full Checklist Completion.""")

# Add a 'Refresh Data' button.
st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management");
if st.sidebar.button("Refresh Data from Source", /* ... */):
    # Clear caches and session state, then rerun to force a fresh data load.
    st.cache_data.clear(); st.session_state.data_loaded = False; st.session_state.df_original = pd.DataFrame()
    clear_all_filters_and_search_v4_3_1(); st.rerun()

# Display the last data refresh time.
if st.session_state.get('data_loaded', False) and st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE)
    refresh_time_str_display = refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST')
    st.sidebar.caption(f"☁️ Last data sync: {refresh_time_str_display}")
# ... (Handle other refresh status messages) ...

# Display user info and a logout button at the bottom of the sidebar.
st.sidebar.markdown("---")
user_display_name = st.user.email.split('@')[0] if hasattr(st.user, "email") and st.user.email else "User"
st.sidebar.caption(f"👤 {user_display_name}")
st.sidebar.button("Log Out", on_click=st.logout, use_container_width=True, type="secondary", key="logout_button_sidebar_bottom")
st.sidebar.caption(f"Dashboard v4.6.7") # Display app version.

# --- Main Page Content ---
st.title("📈 Onboarding Analytics Dashboard") # Set the main title.

# Handle cases where data isn't loaded or the sheet is empty.
if not st.session_state.data_loaded and df_original.empty:
    st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet... 🚧</div>", unsafe_allow_html=True)
    st.stop() # Stop if no data.
elif df_original.empty: st.markdown("<div class='no-data-message'>✅ Data source connected, but empty... ✅</div>", unsafe_allow_html=True); st.stop()

# Create navigation tabs using a radio button.
selected_tab = st.radio("Navigation:", ALL_TABS, index=current_tab_idx, horizontal=True, key="main_tab_selector_v4_3_1")
# If tab changes, update session state and rerun.
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()

# Display a summary of active filters or search.
# ... (Code to build the summary message based on session state) ...
st.markdown(f"<div class='active-filters-summary'>ℹ️ {final_summary_message}</div>", unsafe_allow_html=True)

# --- Apply Filters / Search to Data ---
df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
if not df_original.empty:
    if global_search_active:
        # If global search is active, filter based on search terms.
        df_temp_gs = df_original.copy();
        ln_term = st.session_state.get("licenseNumber_search", "").strip().lower();
        sn_term = st.session_state.get("storeName_search", "").strip()
        if ln_term: df_temp_gs = df_temp_gs[df_temp_gs['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
        if sn_term: df_temp_gs = df_temp_gs[df_temp_gs['storeName'] == sn_term]
        df_global_search_results_display = df_temp_gs.copy(); df_filtered = df_global_search_results_display.copy()
    else:
        # If no global search, apply date and category filters.
        df_temp_filters = df_original.copy();
        # Apply date filter.
        date_objects_for_filter = pd.to_datetime(df_temp_filters['onboarding_date_only'], errors='coerce').dt.date;
        date_filter_condition = (date_objects_for_filter >= start_dt_filter) & (date_objects_for_filter <= end_dt_filter)
        df_temp_filters = df_temp_filters[date_filter_condition]
        # Apply category filters.
        for col_key, _ in category_filters_map.items():
            selected_values_cat = st.session_state.get(f"{col_key}_filter", [])
            if selected_values_cat: df_temp_filters = df_temp_filters[df_temp_filters[col_key].astype(str).isin(selected_values_cat)]
        df_filtered = df_temp_filters.copy()

# Calculate MTD metrics for the overview.
# ... (Code to filter data for MTD and previous MTD) ...
total_mtd, sr_mtd, score_mtd, days_to_confirm_mtd = calculate_metrics(df_mtd_data);
delta_onboardings_mtd = (total_mtd - total_prev_mtd) if pd.notna(total_mtd) and pd.notna(total_prev_mtd) else None

# --- Table Styling & Display Functions ---
# Function to get the CSS class for a table cell based on its value and column.
def get_cell_style_class(column_name, value):
    """Returns a CSS class name for styling table cells."""
    val_str = str(value).strip().lower()
    if pd.isna(value) or val_str == "" or val_str == "na": return "cell-req-na"
    if column_name == 'score': # Style based on score value.
        try: score_num = float(value)
        except: return ""
        if score_num >= 8: return "cell-score-good"
        elif score_num >= 4: return "cell-score-medium"
        else: return "cell-score-bad"
    # ... (Similar styling for sentiment, days, requirements) ...
    return ""

# Function to display data in a custom-styled HTML table and show details.
def display_html_table_and_details(df_to_display, context_key_prefix=""):
    """Generates and displays an HTML table and a details viewer."""
    if df_to_display is None or df_to_display.empty:
        st.markdown("<div class='no-data-message'>📊 No data to display. Try different filters! 📊</div>", unsafe_allow_html=True); return

    df_display_copy = df_to_display.copy().reset_index(drop=True)
    # Map status to emojis.
    def map_status_to_emoji_html(status_val): /* ... */
    df_display_copy['status_styled'] = df_display_copy['status'].apply(map_status_to_emoji_html)

    # Define the order and selection of columns for the table.
    preferred_cols_order = ['onboardingDate', 'repName', 'storeName', /* ... */]
    final_display_cols = [col for col in preferred_cols_order if col in df_display_copy.columns]
    # ... (Add other existing columns) ...

    # Generate the HTML for the table.
    html_table = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
    column_display_names = {'status_styled': 'Status', /* ... */ } # Friendly names.
    for col_id in final_display_cols: html_table.append(f"<th>{column_display_names.get(col_id, col_id.title())}</th>")
    html_table.append("</tr></thead><tbody>")
    # Add rows with data and styles.
    for index, row in df_display_copy.iterrows():
        html_table.append("<tr>")
        for col_id in final_display_cols:
            cell_value = row.get(col_id, "")
            style_class = get_cell_style_class(col_id, cell_value)
            html_table.append(f"<td class='{style_class}'>{cell_value}</td>")
        html_table.append("</tr>")
    html_table.append("</tbody></table></div>");
    # Display the table using markdown.
    st.markdown("".join(html_table), unsafe_allow_html=True)

    # --- Details Viewer ---
    st.markdown("---"); st.subheader("📄 View Full Record Details")
    # Add a dropdown to select a specific record from the table.
    transcript_options_map = {f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_copy.iterrows()}
    selected_key_from_display = st.selectbox("Select record to view details:", /* ... */)
    # If a record is selected, display its summary, checks, and transcript.
    if st.session_state[transcript_session_key_local]:
        selected_row_details = df_display_copy.loc[selected_original_idx]
        st.markdown("<h5>📋 Onboarding Summary & Checks:</h5>", unsafe_allow_html=True);
        # ... (Display summary items) ...
        st.markdown("<h6>Key Requirement Checks:</h6>", unsafe_allow_html=True)
        # ... (Display requirement checks with emojis) ...
        st.markdown("<h5>🎙️ Full Transcript:</h5>", unsafe_allow_html=True);
        # ... (Display the full transcript in a scrollable box) ...

    # Add a download button for the currently displayed table data.
    csv_data_to_download = convert_df_to_csv(df_display_copy[final_display_cols]);
    st.download_button(label="📥 Download These Results", data=csv_data_to_download, /* ... */)

# --- Global Search Dialog ---
# If global search is active, show the results in a pop-up dialog.
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("🔍 Global Search Results", width="large")
    def show_global_search_dialog_content():
        """Content to display inside the global search dialog."""
        st.markdown("##### Records matching global search criteria:");
        # Use the table display function for the search results.
        display_html_table_and_details(df_global_search_results_display, context_key_prefix="dialog_global_search")
        # Add a button to close the dialog and clear the search.
        if st.button("Close & Clear Search", /* ... */):
            st.session_state.show_global_search_dialog = False; st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""
            st.rerun()
    show_global_search_dialog_content() # Show the dialog.

# --- Tab Content Display ---
# Display content based on which tab is currently selected.

if st.session_state.active_tab == TAB_OVERVIEW:
    st.header("📈 Month-to-Date (MTD) Performance"); cols_mtd_overview = st.columns(4)
    # Display MTD metrics using `st.metric`.
    with cols_mtd_overview[0]: st.metric("🗓️ Onboardings MTD", value=f"{total_mtd:.0f}", delta=f"{delta_onboardings_mtd:+.0f} vs Prev. Month")
    with cols_mtd_overview[1]: st.metric("✅ Success Rate MTD", value=f"{sr_mtd:.1f}%")
    # ... (Other MTD metrics) ...

    st.header("📊 Filtered Data Snapshot")
    if global_search_active: st.info("ℹ️ Global search active...")
    elif not df_filtered.empty:
        # Display metrics based on the currently filtered data.
        total_filtered, sr_filtered, score_filtered, days_filtered = calculate_metrics(df_filtered); cols_filtered_overview = st.columns(4)
        with cols_filtered_overview[0]: st.metric("📄 Onboardings (Filtered)", f"{total_filtered:.0f}")
        # ... (Other filtered metrics) ...
    else: st.markdown("<div class='no-data-message'>🤷 No data matches filters... 🤷</div>", unsafe_allow_html=True)

elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if global_search_active: st.info("ℹ️ Global Search active...")
    else:
        # Display the main data table and details viewer for filtered data.
        display_html_table_and_details(df_filtered, context_key_prefix="filtered_analysis")
        st.divider()
        st.header("🎨 Key Visualizations (Filtered Data)")
        if not df_filtered.empty:
            chart_cols_1, chart_cols_2 = st.columns(2)
            with chart_cols_1:
                # Create and display a bar chart for Onboarding Status.
                status_counts_df = df_filtered['status'].value_counts().reset_index();
                status_fig = px.bar(status_counts_df, x='status', y='count', title="Onboarding Status Distribution");
                st.plotly_chart(status_fig, use_container_width=True)
                # Create and display a bar chart for Reps.
                rep_counts_df = df_filtered['repName'].value_counts().reset_index();
                rep_fig = px.bar(rep_counts_df, x='repName', y='count', title="Onboardings by Representative");
                st.plotly_chart(rep_fig, use_container_width=True)
            with chart_cols_2:
                # Create and display a pie chart for Client Sentiment.
                sent_counts_df = df_filtered['clientSentiment'].value_counts().reset_index();
                sent_fig = px.pie(sent_counts_df, names='clientSentiment', values='count', hole=0.4, title="Client Sentiment Breakdown");
                st.plotly_chart(sent_fig, use_container_width=True)
                # Create and display a horizontal bar chart for Checklist Completion.
                # ... (Code to calculate and plot checklist rates) ...
                st.plotly_chart(checklist_bar_fig, use_container_width=True)
        else: st.markdown("<div class='no-data-message'>🖼️ No data matches filters for visuals... 🖼️</div>", unsafe_allow_html=True)

elif st.session_state.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS);
    if not df_filtered.empty:
        # Create and display a line chart for Onboardings Over Time.
        df_trend_source = df_filtered.copy(); df_trend_source['onboarding_datetime'] = pd.to_datetime(df_trend_source['onboarding_date_only'], errors='coerce');
        trend_data_resampled = df_trend_source.set_index('onboarding_datetime').resample('W-MON').size().reset_index(name='count') # Resample by week
        trend_line_fig = px.line(trend_data_resampled, x='onboarding_datetime', y='count', markers=True, title="Onboardings Over Time");
        st.plotly_chart(trend_line_fig, use_container_width=True)
        # Create and display a histogram for Days to Confirmation.
        days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna();
        days_dist_fig = px.histogram(days_data_for_hist, nbins=20, title="Distribution of Days to Confirmation");
        st.plotly_chart(days_dist_fig, use_container_width=True)
    else: st.markdown("<div class='no-data-message'>📉 No data for Trends... 📉</div>", unsafe_allow_html=True)

# Add a footer.
st.markdown("---"); st.markdown(f"<div class='footer'>Dashboard v4.6.7</div>", unsafe_allow_html=True)