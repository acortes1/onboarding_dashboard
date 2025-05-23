# streamlit_app.py
# Import necessary libraries. These are the tools we need.
import streamlit as st  # For creating the web app interface.
import pandas as pd  # For handling and manipulating data in tables (DataFrames).
import plotly.express as px  # For creating easy interactive charts.
import plotly.graph_objects as go # For creating more complex interactive charts.
from datetime import datetime, date, timedelta  # For working with dates and times.
import gspread  # To connect and interact with Google Sheets.
from google.oauth2.service_account import Credentials  # For secure Google API authentication.
import time  # Provides time-related functions (though not heavily used here).
import numpy as np  # For numerical operations, often used with pandas.
import re  # For regular expressions, used here for text pattern matching (like phone numbers).
from dateutil import tz  # For handling different time zones, specifically PST and UTC.

# --- Page Configuration ---
# Set up the basic properties of your Streamlit page (browser tab title, icon, etc.).
st.set_page_config(
    page_title="Onboarding Analytics Dashboard", # Title shown in the browser tab.
    page_icon="📈",  # Icon shown in the browser tab (favicon).
    layout="wide",  # Use the full width of the screen for the layout.
    initial_sidebar_state="expanded" # Ensure the sidebar is open when the app first loads.
)

# --- Custom CSS Injection ---
# This function defines and injects custom CSS to style the app's appearance.
def load_custom_css():
    """Loads and injects custom CSS for a polished look and feel."""
    # Get the currently active theme (light or dark) from Streamlit.
    THEME = st.get_option("theme.base")

    # Define color palettes for both light and dark themes.
    # We use these variables to make the CSS dynamic based on the theme.
    if THEME == "light":
        SCORE_GOOD_BG = "#DFF0D8"; SCORE_GOOD_TEXT = "#3C763D"; # Greenish for good scores
        SCORE_MEDIUM_BG = "#FCF8E3"; SCORE_MEDIUM_TEXT = "#8A6D3B"; # Yellowish for medium scores
        SCORE_BAD_BG = "#F2DEDE"; SCORE_BAD_TEXT = "#A94442"; # Reddish for bad scores
        SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT; # Map sentiment to score colors
        SENTIMENT_NEUTRAL_BG = "#F0F2F6"; SENTIMENT_NEUTRAL_TEXT = "#4A5568";
        SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT;
        DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT; # Map days to score colors
        DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT;
        DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT;
        REQ_MET_BG = "#E7F3E7"; REQ_MET_TEXT = "#256833"; # Colors for requirements met/not met
        REQ_NOT_MET_BG = "#F8EAEA"; REQ_NOT_MET_TEXT = "#9E3434";
        REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)"; # NA = Not Applicable
        TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)";
        TABLE_BORDER_COLOR = "var(--border-color)";
        LOGIN_BOX_BG = "var(--background-color)"; LOGIN_BOX_SHADOW = "0 12px 35px rgba(0,0,0,0.07)";
        LOGOUT_BTN_BG = "#F2DEDE"; LOGOUT_BTN_TEXT = "#A94442"; LOGOUT_BTN_BORDER = "#A94442";
        LOGOUT_BTN_HOVER_BG = "#EBCFCF";
        PRIMARY_BTN_BG = "#6A0DAD"; PRIMARY_BTN_HOVER_BG = "#580A8F"; # Main button color (Purple)
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#6A0DAD"; DOWNLOAD_BTN_BORDER = "#6A0DAD";
        DOWNLOAD_BTN_HOVER_BG = "#6A0DAD"; DOWNLOAD_BTN_HOVER_TEXT = "#FFFFFF";
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)"; # Google login button
    else: # Dark Theme Colors
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
        PRIMARY_BTN_BG = "#BE90D4"; PRIMARY_BTN_HOVER_BG = "#A77CBF"; # Lighter purple for dark theme
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#BE90D4"; DOWNLOAD_BTN_BORDER = "#BE90D4";
        DOWNLOAD_BTN_HOVER_BG = "#BE90D4"; DOWNLOAD_BTN_HOVER_TEXT = "#1E1E1E";
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)";

    # Define some table layout constants.
    TABLE_CELL_PADDING = "0.65em 0.8em";
    TABLE_FONT_SIZE = "0.92rem";

    # Build the main CSS string using an f-string to embed our color variables.
    css = f"""
    <style>
        :root {{ /* CSS variables make it easy to reuse colors */
            --score-good-bg: {SCORE_GOOD_BG}; --score-good-text: {SCORE_GOOD_TEXT};
            --score-medium-bg: {SCORE_MEDIUM_BG}; --score-medium-text: {SCORE_MEDIUM_TEXT};
            --score-bad-bg: {SCORE_BAD_BG}; --score-bad-text: {SCORE_BAD_TEXT};
            --sentiment-positive-bg: {SENTIMENT_POSITIVE_BG}; --sentiment-positive-text: {SENTIMENT_POSITIVE_TEXT};
            --sentiment-neutral-bg: {SENTIMENT_NEUTRAL_BG}; --sentiment-neutral-text: {SENTIMENT_NEUTRAL_TEXT};
            --sentiment-negative-bg: {SENTIMENT_NEGATIVE_BG}; --sentiment-negative-text: {SENTIMENT_NEGATIVE_TEXT};
            --days-good-bg: {DAYS_GOOD_BG}; --days-good-text: {DAYS_GOOD_TEXT};
            --days-medium-bg: {DAYS_MEDIUM_BG}; --days-medium-text: {DAYS_MEDIUM_TEXT};
            --days-bad-bg: {DAYS_BAD_BG}; --days-bad-text: {DAYS_BAD_TEXT};
            --req-met-bg: {REQ_MET_BG}; --req-met-text: {REQ_MET_TEXT};
            --req-not-met-bg: {REQ_NOT_MET_BG}; --req-not-met-text: {REQ_NOT_MET_TEXT};
            --req-na-bg: {REQ_NA_BG}; --req-na-text: {REQ_NA_TEXT};
            --table-header-bg: {TABLE_HEADER_BG}; --table-header-text: {TABLE_HEADER_TEXT};
            --table-border-color: {TABLE_BORDER_COLOR}; --table-cell-padding: {TABLE_CELL_PADDING};
            --table-font-size: {TABLE_FONT_SIZE};
            --login-box-bg: {LOGIN_BOX_BG}; --login-box-shadow: {LOGIN_BOX_SHADOW};
            --logout-btn-bg: {LOGOUT_BTN_BG}; --logout-btn-text: {LOGOUT_BTN_TEXT};
            --logout-btn-border: {LOGOUT_BTN_BORDER}; --logout-btn-hover-bg: {LOGOUT_BTN_HOVER_BG};
            --primary-btn-bg: {PRIMARY_BTN_BG}; --primary-btn-hover-bg: {PRIMARY_BTN_HOVER_BG};
            --download-btn-bg: {DOWNLOAD_BTN_BG}; --download-btn-text: {DOWNLOAD_BTN_TEXT};
            --download-btn-border: {DOWNLOAD_BTN_BORDER}; --download-btn-hover-bg: {DOWNLOAD_BTN_HOVER_BG};
            --download-btn-hover-text: {DOWNLOAD_BTN_HOVER_TEXT};
            --google-btn-bg: {GOOGLE_BTN_BG}; --google-btn-hover-bg: {GOOGLE_BTN_HOVER_BG}; --google-btn-shadow: {GOOGLE_BTN_SHADOW};
        }}
        /* General body and heading styles */
        body {{ font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .stApp {{ padding: 0.5rem 1rem; }}
        h1, h2, h3, h4, h5, h6 {{ font-weight: 600; color: var(--primary-color); }}
        h1 {{ text-align: center; padding: 0.8em 0.5em; font-size: 2.3rem; letter-spacing: 0.5px; border-bottom: 2px solid var(--primary-color); margin-bottom: 1.5em; font-weight: 700; }}
        h2 {{ font-size: 1.7rem; margin-top: 2.2em; margin-bottom: 1.3em; padding-bottom: 0.5em; border-bottom: 1px solid var(--border-color); font-weight: 600; }}
        h3 {{ font-size: 1.4rem; margin-top: 2em; margin-bottom: 1.1em; font-weight: 600; color: var(--text-color); opacity: 0.9; }}
        h5 {{ color: var(--text-color); opacity: 0.95; margin-top: 1.8em; margin-bottom: 0.9em; font-weight: 500; letter-spacing: 0.1px; font-size: 1.1rem; }}
        /* Style Streamlit's metric displays */
        div[data-testid="stMetric"], .metric-card {{ background-color: var(--secondary-background-color); padding: 1.4em 1.7em; border-radius: 10px; border: 1px solid var(--border-color); box-shadow: 0 5px 12px rgba(0,0,0,0.06); transition: transform 0.2s ease-out, box-shadow 0.2s ease-out; margin-bottom: 1.3em; }}
        div[data-testid="stMetric"]:hover, .metric-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.08); }}
        div[data-testid="stMetricLabel"] > div {{ font-size: 0.95rem; }}
        div[data-testid="stMetricValue"] > div {{ font-size: 2.5rem !important; }}
        /* Style buttons */
        div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {{
            border: none; padding: 10px 22px; border-radius: 8px; font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.07);
        }}
        div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {{
            transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        /* ... (More button styles for primary, secondary, download) ... */
        /* Style expanders, radio buttons, transcript viewers, etc. */
        .streamlit-expanderHeader {{ font-size: 1.1em; }}
        .transcript-pane-container {{ overflow-x: auto; border: 1px solid var(--table-border-color); border-radius: 10px; max-height: 400px; padding: 1.5em; background-color: var(--secondary-background-color); }}
        .transcript-container {{ max-height: 350px; overflow-y: auto; }}
        /* Style our custom HTML table */
        .custom-table-container {{ overflow-x: auto; border: 1px solid var(--table-border-color); border-radius: 10px; max-height: 500px; }}
        .custom-styled-table {{ width: 100%; border-collapse: collapse; font-size: var(--table-font-size); }}
        .custom-styled-table th, .custom-styled-table td {{ padding: var(--table-cell-padding); text-align: left; border-bottom: 1px solid var(--table-border-color); border-right: 1px solid var(--table-border-color); white-space: nowrap; }}
        .custom-styled-table th {{ background-color: var(--table-header-bg); position: sticky; top: 0; z-index: 2; }} /* Sticky headers */
        .custom-styled-table tbody tr:hover {{ background-color: color-mix(in srgb, var(--secondary-background-color) 75%, var(--primary-color) 8%); }}
        /* Cell styles based on data values (good/bad scores, sentiment, etc.) */
        .cell-score-good {{ background-color: var(--score-good-bg); color: var(--score-good-text); }}
        .cell-score-medium {{ background-color: var(--score-medium-bg); color: var(--score-medium-text); }}
        .cell-score-bad {{ background-color: var(--score-bad-bg); color: var(--score-bad-text); }}
        .cell-sentiment-positive {{ background-color: var(--sentiment-positive-bg); color: var(--sentiment-positive-text); }}
        .cell-sentiment-neutral {{ background-color: var(--sentiment-neutral-bg); color: var(--sentiment-neutral-text); }}
        .cell-sentiment-negative {{ background-color: var(--sentiment-negative-bg); color: var(--sentiment-negative-text); }}
        .cell-days-good {{ background-color: var(--days-good-bg); color: var(--days-good-text); }}
        .cell-days-medium {{ background-color: var(--days-medium-bg); color: var(--days-medium-text); }}
        .cell-days-bad {{ background-color: var(--days-bad-bg); color: var(--days-bad-text); }}
        .cell-req-met {{ background-color: var(--req-met-bg); color: var(--req-met-text); }}
        .cell-req-not-met {{ background-color: var(--req-not-met-bg); color: var(--req-not-met-text); }}
        .cell-req-na {{ background-color: var(--req-na-bg); color: var(--req-na-text); }}
        /* Login screen styles */
        .login-container {{ display: flex; justify-content: center; align-items: center; min-height: 60vh; flex-direction: column; text-align: center; padding: 1em; }}
        .login-box {{ background-color: var(--login-box-bg); padding: 2.5em 3em; border-radius: 15px; box-shadow: var(--login-box-shadow); max-width: 450px; width: 100%; }}
        /* Responsive styles for smaller screens */
        @media (max-width: 768px) {{ /* Tablet sizes */
            h1 {{ font-size: 1.8rem; }}
            .custom-styled-table th, .custom-styled-table td {{ white-space: normal; }} /* Allow text wrapping */
        }}
        @media (max-width: 480px) {{ /* Phone sizes */
            h1 {{ font-size: 1.5rem; }}
        }}
    </style>
    """
    # Inject the CSS into the Streamlit app's HTML head.
    st.markdown(css, unsafe_allow_html=True)

# Call the function to load our custom styles when the app starts.
load_custom_css()

# --- Constants & Configuration ---
# Define the permissions our app needs from Google (Sheets and Drive APIs).
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Define the key requirements we track for each onboarding, including descriptions and types.
KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and the Company.", "type": "Secondary", "chart_label": "Intro Self & Company"},
    'confirmKitReceived': {"description": "Confirm kit and initial order received.", "type": "Primary", "chart_label": "Kit & Order Recv'd"},
    'offerDisplayHelp': {"description": "Ask about help setting up in-store display.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule budtender training & first promo.", "type": "Primary", "chart_label": "Sched. Training/Promo"},
    'providePromoCreditLink': {"description": "Provide link for promo-credit requests.", "type": "Secondary", "chart_label": "Promo Credit Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
# Define the order for displaying these requirements in the details view and charts.
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS

# Define time zones: PST for display and UTC for internal calculations.
PST_TIMEZONE = tz.gettz('America/Los_Angeles'); UTC_TIMEZONE = tz.tzutc()

# Get the current theme again to set Plotly chart colors.
THEME_PLOTLY = st.get_option("theme.base")
PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)" # Use a transparent background for plots.

# Define Plotly color sequences and maps based on the theme.
if THEME_PLOTLY == "light":
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7' }; TEXT_COLOR_FOR_PLOTLY = "#262730"; PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
else: # Dark Theme
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D' }; TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"; PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"

# Define a base dictionary for Plotly chart layout settings to ensure consistency.
plotly_base_layout_settings = {"plot_bgcolor": PLOT_BG_COLOR_PLOTLY, "paper_bgcolor": PLOT_BG_COLOR_PLOTLY, "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":True, "yaxis_gridcolor": 'rgba(128,128,128,0.2)', "margin": dict(l=50, r=30, t=70, b=50), "font_color": TEXT_COLOR_FOR_PLOTLY, "title_font_color": PRIMARY_COLOR_FOR_PLOTLY, "title_font_size": 18, "xaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "xaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "legend_font_color": TEXT_COLOR_FOR_PLOTLY, "legend_title_font_color": PRIMARY_COLOR_FOR_PLOTLY}

# --- Google SSO & Domain Check ---
# This function checks if the user is logged in via Google SSO and optionally checks their email domain.
def check_login_and_domain():
    """Checks login status and, if configured, email domain. Returns authorization status."""
    # Get the allowed domain from secrets (it might not be set).
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", None)

    # Check if the user is currently logged in.
    if not st.user.is_logged_in:
        return 'NOT_LOGGED_IN'

    # Get the user's email address.
    user_email = st.user.email
    if not user_email: # Handle cases where email couldn't be retrieved.
        st.error("Could not retrieve user email. Please try logging in again.")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'ERROR'

    # If an allowed domain is specified, check if the user's email ends with it.
    if allowed_domain and not user_email.endswith(f"@{allowed_domain}"):
        st.error(f"🚫 Access Denied. Only users from the '{allowed_domain}' domain are allowed.")
        st.info(f"You are attempting to log in as: {user_email}")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'DOMAIN_MISMATCH'

    # If all checks pass, the user is authorized.
    return 'AUTHORIZED'


# --- Data Loading & Processing Functions ---

# Function to authenticate with Google Sheets using service account credentials.
# It uses Streamlit's caching to avoid re-authenticating on every app interaction.
@st.cache_data(ttl=600) # Cache the result for 600 seconds (10 minutes).
def authenticate_gspread_cached():
    """Authenticates with Google Sheets API and caches the connection."""
    # Retrieve GCP service account credentials from Streamlit's secrets.
    gcp_secrets_obj = st.secrets.get("gcp_service_account")
    if gcp_secrets_obj is None: st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND."); return None
    try:
        # Convert secrets to a dictionary and ensure all necessary keys are present.
        gcp_secrets_dict = dict(gcp_secrets_obj)
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing_keys = [k for k in required_keys if gcp_secrets_dict.get(k) is None]
        if missing_keys: st.error(f"🚨 Error: GCP secrets dict missing keys: {', '.join(missing_keys)}."); return None
        # Create Google credentials using the secrets and defined scopes.
        creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
        # Authorize the gspread library to use these credentials.
        return gspread.authorize(creds)
    except Exception as e:
        # Show an error if authentication fails.
        st.error(f"🚨 Error Processing GCP Secrets or Authenticating: {e}. Check format/permissions."); return None

# Function to robustly convert a column to datetime objects, trying multiple formats.
def robust_to_datetime(series):
    """Tries various formats to convert a pandas Series to datetime objects."""
    # Try pandas' automatic conversion first (often works).
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    # If many values failed, and it's not just an empty/NA column, try specific formats.
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null', 'na']).all():
        common_formats = [ # List common date formats found in data.
            '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'
        ]
        # Iterate through formats and dayfirst settings.
        for dayfirst_setting in [False, True]:
            for fmt in common_formats:
                try:
                    use_dayfirst_for_fmt = ('%m' in fmt and '%d' in fmt and dayfirst_setting)
                    temp_dates = pd.to_datetime(series, format=fmt, errors='coerce', dayfirst=use_dayfirst_for_fmt)
                    # If the current format converted more dates, keep it.
                    if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                    if dates.notnull().all(): break # Stop if all are converted.
                except ValueError: continue # Ignore formats that don't match.
            if dates.notnull().all(): break
    return dates

# Function to convert a datetime column to a readable PST string.
def format_datetime_to_pst_str(dt_series):
    """Converts a datetime Series to PST formatted strings for display."""
    # Only process if it's a datetime column with actual data.
    if not pd.api.types.is_datetime64_any_dtype(dt_series) or dt_series.isnull().all():
        return dt_series

    # Inner function to convert a single datetime element.
    def convert_element(element):
        if pd.isna(element): return None # Pass through nulls.
        try:
            # Ensure it's UTC, then convert to PST and format.
            utc_element = element.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT') if element.tzinfo is None else element.tz_convert(UTC_TIMEZONE)
            pst_element = utc_element.tz_convert(PST_TIMEZONE)
            return pst_element.strftime('%Y-%m-%d %I:%M %p PST')
        except Exception: return str(element) # Fallback to string on error.

    # Try converting the whole series efficiently; if fails, use the element-wise approach.
    try:
        utc_series = dt_series.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT') if dt_series.dt.tz is None else dt_series.dt.tz_convert(UTC_TIMEZONE)
        pst_series = utc_series.dt.tz_convert(PST_TIMEZONE)
        return pst_series.apply(lambda x: x.strftime('%Y-%m-%d %I:%M %p PST') if pd.notnull(x) else None)
    except Exception:
        return dt_series.apply(convert_element)

# Function to format phone numbers into a standard US format.
def format_phone_number(number_str):
    """Formats a string into (XXX) XXX-XXXX or +1 (XXX) XXX-XXXX."""
    if pd.isna(number_str) or not str(number_str).strip(): return "" # Handle blanks.
    digits = re.sub(r'\D', '', str(number_str)) # Extract only digits.
    if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(number_str) # Return original if not standard format.

# Function to capitalize names (e.g., "john doe" -> "John Doe").
def capitalize_name(name_str):
    """Capitalizes each word in a string."""
    if pd.isna(name_str) or not str(name_str).strip(): return "" # Handle blanks.
    return ' '.join(word.capitalize() for word in str(name_str).split())

# Function to load and process data from the Google Sheet.
# It uses caching and shows a spinner message while loading.
@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet():
    """Loads, cleans, and standardizes data from the Google Sheet."""
    gc = authenticate_gspread_cached() # Get authenticated connection.
    current_time = datetime.now(UTC_TIMEZONE)
    if gc is None: return pd.DataFrame(), None # Bail out if auth failed.

    # Get Sheet URL and Worksheet name from secrets.
    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not sheet_url_or_name: st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame(), None
    if not worksheet_name: st.error("🚨 Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame(), None

    try:
        # Open the Google Sheet and select the worksheet.
        spreadsheet = gc.open_by_url(sheet_url_or_name) if ("docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name) else gc.open(sheet_url_or_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1, expected_headers=None) # Read data.
        if not data: st.warning("⚠️ No data rows in Google Sheet."); return pd.DataFrame(), current_time

        # Convert to a pandas DataFrame.
        df = pd.DataFrame(data)

        # --- Data Cleaning and Standardization ---
        # 1. Standardize column names (lowercase, no spaces).
        df.rename(columns={col: "".join(str(col).strip().lower().split()) for col in df.columns}, inplace=True)

        # 2. Map various possible column names to our standard internal names.
        column_name_map_to_code = {
            "licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "dcc": "licenseNumber",
            "storename": "storeName", "accountname": "storeName",
            "repname": "repName", "representative": "repName",
            "onboardingdate": "onboardingDate",
            "deliverydate": "deliveryDate",
            "confirmationtimestamp": "confirmationTimestamp", "confirmedat": "confirmationTimestamp",
            "clientsentiment": "clientSentiment", "sentiment": "clientSentiment",
            "fulltranscript": "fullTranscript", "transcript": "fullTranscript",
            "score": "score", "onboardingscore": "score",
            "status": "status", "onboardingstatus": "status",
            "summary": "summary", "callsummary": "summary",
            "contactnumber": "contactNumber", "phone": "contactNumber",
            "confirmednumber": "confirmedNumber", "verifiednumber":"confirmedNumber",
            "contactname": "contactName", "clientcontact": "contactName"
        }
        for req_key_internal in KEY_REQUIREMENT_DETAILS.keys(): column_name_map_to_code[req_key_internal.lower()] = req_key_internal
        cols_to_rename_actual = {std_col: code_col for std_col, code_col in column_name_map_to_code.items() if std_col in df.columns and code_col not in df.columns}
        df.rename(columns=cols_to_rename_actual, inplace=True)

        # 3. Process date columns: clean, convert to datetime, format to PST string.
        date_cols_map = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
        for original_col, dt_col in date_cols_map.items():
            if original_col in df.columns:
                df[original_col] = df[original_col].astype(str).str.replace('\n',' ',regex=False).str.strip()
                df[dt_col] = robust_to_datetime(df[original_col])
                df[original_col] = format_datetime_to_pst_str(df[dt_col])
            else: df[dt_col] = pd.NaT

        # 4. Create a 'date only' column for easier date filtering.
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date if 'onboardingDate_dt' in df.columns else pd.NaT

        # 5. Calculate 'days to confirmation' if possible.
        if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
            def ensure_utc_for_calc(series_dt): # Helper to ensure UTC timezone.
                if pd.api.types.is_datetime64_any_dtype(series_dt) and series_dt.notna().any():
                    if series_dt.dt.tz is None: return series_dt.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
                    else: return series_dt.dt.tz_convert(UTC_TIMEZONE)
                return series_dt.fillna(pd.NaT)
            delivery_utc = ensure_utc_for_calc(df['deliveryDate_dt'])
            confirmation_utc = ensure_utc_for_calc(df['confirmationTimestamp_dt'])
            df['days_to_confirmation'] = (confirmation_utc - delivery_utc).dt.days
        else: df['days_to_confirmation'] = pd.NA

        # 6. Format phone numbers and names.
        for phone_col in ['contactNumber', 'confirmedNumber']:
            if phone_col in df.columns: df[phone_col] = df[phone_col].apply(format_phone_number)
        for name_col in ['repName', 'contactName']:
            if name_col in df.columns: df[name_col] = df[name_col].apply(capitalize_name)

        # 7. Clean up string columns, ensuring they are strings and replacing NAs.
        string_cols = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary', 'contactName', 'contactNumber', 'confirmedNumber', 'onboardingDate', 'deliveryDate', 'confirmationTimestamp']
        for col in string_cols: df[col] = df.get(col, "").astype(str).replace(['nan', 'NaN', 'None', 'NaT', '<NA>'], "", regex=False).fillna("")

        # 8. Convert score to number.
        df['score'] = pd.to_numeric(df.get('score'), errors='coerce')
        # 9. Ensure requirement columns exist.
        for col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS: df[col] = df.get(col, pd.NA)
        # 10. Drop any old columns.
        cols_to_drop = [col for col in ['deliverydatets', 'onboardingwelcome'] if col in df.columns]
        if cols_to_drop: df = df.drop(columns=cols_to_drop)

        # Return the final DataFrame and load time.
        return df, current_time
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 GS Error: {e}. Check URL/name & permissions."); return pd.DataFrame(), None
    except Exception as e:
        st.error(f"🌪️ Error loading data: {e}"); return pd.DataFrame(), None

# Function to convert a DataFrame to CSV, cached for performance.
@st.cache_data
def convert_df_to_csv(df_to_convert):
    """Converts a DataFrame to a UTF-8 encoded CSV string for download."""
    return df_to_convert.to_csv(index=False).encode('utf-8')

# Function to calculate summary metrics for a given DataFrame.
def calculate_metrics(df_input):
    """Calculates total count, success rate, avg score, and avg days."""
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA # Return defaults for empty input.
    total = len(df_input)
    confirmed = df_input[df_input['status'].astype(str).str.lower().str.contains('confirmed', na=False)].shape[0]
    success_rate = (confirmed / total * 100) if total > 0 else 0.0
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    avg_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

# Function to get the default date range for the date filter.
def get_default_date_range(date_series):
    """Calculates a default date range (MTD or based on data min/max)."""
    today = date.today()
    start_of_month = today.replace(day=1)
    min_date, max_date = (pd.to_datetime(date_series, errors='coerce').dt.date.dropna().min(), pd.to_datetime(date_series, errors='coerce').dt.date.dropna().max()) if date_series is not None and date_series.notna().any() else (None, None)
    start = max(start_of_month, min_date) if min_date else start_of_month
    end = min(today, max_date) if max_date else today
    return (start, end) if start <= end else ((min_date, max_date) if min_date and max_date else (start_of_month, today))

# --- Main App Logic ---
# Check the user's login status and domain.
auth_status = check_login_and_domain()

# If the user is not authorized, show the login screen or an error and stop.
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
        _, login_col, _ = st.columns([1, 1, 1]) # Center the button.
        with login_col:
            st.button("Log in with Google 🔑", on_click=st.login, use_container_width=True, key="google_login_main_btn_centered")
    st.stop() # Stop the script execution here if not authorized.

# --- If Authorized, Continue ---
# Initialize Streamlit's session state variables. These hold values across reruns,
# maintaining the state of filters, selected tabs, etc.
default_s_init, default_e_init = get_default_date_range(None)
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'date_range' not in st.session_state: st.session_state.date_range = (default_s_init, default_e_init)
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = None
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = None
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
categorical_filter_keys = ['repName_filter', 'status_filter', 'clientSentiment_filter']
for f_key in categorical_filter_keys: st.session_state.setdefault(f_key, []) # Initialize filters as empty lists.
search_field_keys = ['licenseNumber_search', 'storeName_search']
for s_key in search_field_keys: st.session_state.setdefault(s_key, "") # Initialize search as empty strings.
TAB_OVERVIEW = "📊 Overview"; TAB_DETAILED_ANALYSIS = "🔎 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
st.session_state.setdefault('active_tab', TAB_OVERVIEW) # Default tab is Overview.
st.session_state.setdefault('selected_transcript_key_dialog_global_search', None)
st.session_state.setdefault('selected_transcript_key_filtered_analysis', None)
st.session_state.setdefault('show_global_search_dialog', False)

# Load data if it hasn't been loaded in the current session.
if not st.session_state.data_loaded:
    df_loaded, load_time = load_data_from_google_sheet()
    if load_time: # Check if loading was attempted.
        st.session_state.last_data_refresh_time = load_time
        if not df_loaded.empty: # If data was loaded successfully.
            st.session_state.df_original = df_loaded
            st.session_state.data_loaded = True
            # Determine and store min/max dates from the loaded data.
            min_d, max_d = (pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().min(), pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().max()) if 'onboarding_date_only' in df_loaded and df_loaded['onboarding_date_only'].notna().any() else (None, None)
            st.session_state.min_data_date_for_filter = min_d
            st.session_state.max_data_date_for_filter = max_d
            st.session_state.date_range = get_default_date_range(df_loaded.get('onboarding_date_only'))
        else: # If loading returned no data.
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded = False
    else: # If loading failed entirely.
        st.session_state.df_original = pd.DataFrame()
        st.session_state.data_loaded = False

# Get the main DataFrame from session state.
df_original = st.session_state.df_original

# --- Sidebar ---
# Build the sidebar with controls.
st.sidebar.header("⚙️ Dashboard Controls"); st.sidebar.markdown("---")

# Global Search section.
st.sidebar.subheader("🔍 Global Search"); st.sidebar.caption("Search all data. Overrides filters below.")
global_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
ln_search_val = st.sidebar.text_input(f"Search {global_search_cols['licenseNumber']}:", value=st.session_state.get("licenseNumber_search", ""), key="licenseNumber_global_search_widget_v4_3_1", help="Enter license number part.")
# If search value changes, update state and rerun.
if ln_search_val != st.session_state["licenseNumber_search"]: st.session_state["licenseNumber_search"] = ln_search_val; st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", "")); st.rerun()
store_names_options = [""];
if not df_original.empty and 'storeName' in df_original.columns: unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique()); store_names_options.extend([name for name in unique_stores if str(name).strip()])
current_store_search_val = st.session_state.get("storeName_search", "");
try: current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
except ValueError: current_store_idx = 0
selected_store_val = st.sidebar.selectbox(f"Search {global_search_cols['storeName']}:", options=store_names_options, index=current_store_idx, key="storeName_global_search_widget_select_v4_3_1", help="Select or type store name.")
if selected_store_val != st.session_state["storeName_search"]: st.session_state["storeName_search"] = selected_store_val; st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", "")); st.rerun()
st.sidebar.markdown("---"); global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))

# Filters section.
st.sidebar.subheader("📊 Filters"); st.sidebar.caption("Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data.")
st.sidebar.markdown("##### Quick Date Ranges"); s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
# MTD Button - sets date range to Month-to-Date.
if s_col1.button("MTD", key="mtd_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active: start_mtd = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
# YTD Button - sets date range to Year-to-Date.
if s_col2.button("YTD", key="ytd_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active: start_ytd = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
# ALL Button - sets date range to cover all available data.
if s_col3.button("ALL", key="all_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active:
        all_start = st.session_state.get('min_data_date_for_filter', today_for_shortcuts.replace(year=today_for_shortcuts.year-1)); all_end = st.session_state.get('max_data_date_for_filter', today_for_shortcuts)
        if all_start and all_end: st.session_state.date_range = (all_start, all_end); st.session_state.date_filter_is_active = True; st.rerun()
# Get date values for the date input widget.
current_session_start, current_session_end = st.session_state.date_range; min_dt_for_widget = st.session_state.get('min_data_date_for_filter'); max_dt_for_widget = st.session_state.get('max_data_date_for_filter')
val_start_widget = current_session_start;
if min_dt_for_widget and current_session_start < min_dt_for_widget: val_start_widget = min_dt_for_widget
val_end_widget = current_session_end;
if max_dt_for_widget and current_session_end > max_dt_for_widget: val_end_widget = max_dt_for_widget
if val_start_widget > val_end_widget : val_start_widget = val_end_widget
# The custom date range input widget.
selected_date_range_tuple = st.sidebar.date_input("Custom Date Range (Onboarding):", value=(val_start_widget, val_end_widget), min_value=min_dt_for_widget, max_value=max_dt_for_widget, key="date_selector_custom_v4_3_1", disabled=global_search_active, help="Select start/end dates.")
# Update state if custom range changes.
if not global_search_active and isinstance(selected_date_range_tuple, tuple) and len(selected_date_range_tuple) == 2:
    if selected_date_range_tuple != st.session_state.date_range: st.session_state.date_range = selected_date_range_tuple; st.session_state.date_filter_is_active = True; st.rerun()
start_dt_filter, end_dt_filter = st.session_state.date_range # Store the active date range.

# Create multiselect widgets for category filters.
category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label_text in category_filters_map.items():
    options_for_multiselect = [];
    # Populate options with unique values from the data, handling 'status' specially.
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any():
        if col_key == 'status': options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().dropna().unique() if str(val).strip()])
        else: options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).dropna().unique() if str(val).strip()])
    # Get the current selection and create the multiselect widget.
    current_selection_for_multiselect = st.session_state.get(f"{col_key}_filter", []); valid_current_selection = [s for s in current_selection_for_multiselect if s in options_for_multiselect]
    new_selection_multiselect = st.sidebar.multiselect(f"Filter by {label_text}:", options=options_for_multiselect, default=valid_current_selection, key=f"{col_key}_category_filter_widget_v4_3_1", disabled=global_search_active or not options_for_multiselect, help=f"Select {label_text}." if options_for_multiselect else f"No {label_text} data.")
    # Update state if the selection changes.
    if not global_search_active and new_selection_multiselect != valid_current_selection: st.session_state[f"{col_key}_filter"] = new_selection_multiselect; st.rerun()
    elif global_search_active and st.session_state.get(f"{col_key}_filter") != new_selection_multiselect: st.session_state[f"{col_key}_filter"] = new_selection_multiselect

# Function to clear all filters and search fields.
def clear_all_filters_and_search_v4_3_1():
    """Resets all filters, search, and selected items to defaults."""
    ds_cleared, de_cleared = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_cleared, de_cleared); st.session_state.date_filter_is_active = False
    st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
    for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
    st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state.active_tab = TAB_OVERVIEW
# The "Clear Filters" button.
if st.sidebar.button("🧹 Clear Filters", on_click=clear_all_filters_and_search_v4_3_1, use_container_width=True, key="clear_filters_button_v4_3_1", type="primary"): st.rerun()

# Display the score breakdown information.
with st.sidebar.expander("ℹ️ Score Breakdown (0-10 pts)", expanded=True):
    st.markdown("""Score (0-10 pts):\n- **Primary (4 pts):** Kit Recv'd (2), Train/Promo Sched. (2).\n- **Secondary (3 pts):** Intro (1), Display Help (1), Promo Link (1).\n- **Bonuses (3 pts):** +1 Positive Sentiment, +1 Expectations Set, +1 Full Checklist Completion.""")

# Data Management section with Refresh button.
st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management");
if st.sidebar.button("Refresh Data from Source", key="refresh_data_button_v4_3_1", use_container_width=True, type="primary"):
    st.cache_data.clear(); st.session_state.data_loaded = False; st.session_state.last_data_refresh_time = None; st.session_state.df_original = pd.DataFrame()
    clear_all_filters_and_search_v4_3_1(); st.rerun() # Clear cache, state, and rerun.

# Display data refresh status.
if st.session_state.get('data_loaded', False) and st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE)
    refresh_time_str_display = refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST')
    st.sidebar.caption(f"☁️ Last data sync: {refresh_time_str_display}")
elif st.session_state.get('last_data_refresh_time'):
     st.sidebar.caption("⚠️ No data found in last sync. Check Sheet or Refresh.")
else:
    st.sidebar.caption("⏳ Data not yet loaded.")

# Display user info and logout button at the bottom of the sidebar.
st.sidebar.markdown("---")
user_display_name = "User"
if hasattr(st.user, "email") and st.user.email:
    user_email_prefix = st.user.email.split('@')[0]
    user_display_name = user_email_prefix
    if hasattr(st.user, "name") and st.user.name and st.user.name.strip():
        try: first_name = st.user.name.split()[0]; user_display_name = first_name
        except IndexError: user_display_name = st.user.name
    st.sidebar.caption(f"👤 {user_display_name} ({st.user.email})")
else: st.sidebar.caption("👤 Welcome!")
st.sidebar.button("Log Out", on_click=st.logout, use_container_width=True, type="secondary", key="logout_button_sidebar_bottom")
st.sidebar.caption(f"Dashboard v4.6.7")

# --- Main Page Content ---
st.title("📈 Onboarding Analytics Dashboard")

# Show messages if data isn't loaded or the source is empty, and stop.
if not st.session_state.data_loaded and df_original.empty:
    if st.session_state.get('last_data_refresh_time'): st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh. 🚧</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>⏳ Initializing data... If persists, check configurations. ⏳</div>", unsafe_allow_html=True)
    st.stop()
elif df_original.empty: st.markdown("<div class='no-data-message'>✅ Data source connected, but empty. Add data to Google Sheet. ✅</div>", unsafe_allow_html=True); st.stop()

# Create the main navigation tabs using a radio button.
if st.session_state.active_tab not in ALL_TABS: st.session_state.active_tab = TAB_OVERVIEW
try: current_tab_idx = ALL_TABS.index(st.session_state.active_tab)
except ValueError: current_tab_idx = 0; st.session_state.active_tab = TAB_OVERVIEW
selected_tab = st.radio("Navigation:", ALL_TABS, index=current_tab_idx, horizontal=True, key="main_tab_selector_v4_3_1")
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()

# Build and display a summary of the currently active filters.
summary_parts = []
if global_search_active:
    search_terms = [];
    if st.session_state.get("licenseNumber_search", ""): search_terms.append(f"License: '{st.session_state['licenseNumber_search']}'")
    if st.session_state.get("storeName_search", ""): search_terms.append(f"Store: '{st.session_state['storeName_search']}'")
    summary_parts.append(f"🔍 Global Search: {'; '.join(search_terms)}"); summary_parts.append("(Filters overridden. Results in pop-up.)")
else:
    start_display, end_display = start_dt_filter.strftime('%b %d, %Y'), end_dt_filter.strftime('%b %d, %Y'); min_data_dt_summary, max_data_dt_summary = st.session_state.get('min_data_date_for_filter'), st.session_state.get('max_data_date_for_filter'); is_all_dates_active = False
    if min_data_dt_summary and max_data_dt_summary and start_dt_filter == min_data_dt_summary and end_dt_filter == max_data_dt_summary and st.session_state.get('date_filter_is_active', False): is_all_dates_active = True
    if is_all_dates_active: summary_parts.append("🗓️ Dates: ALL Data")
    elif st.session_state.get('date_filter_is_active', False) or (start_dt_filter != default_s_init or end_dt_filter != default_e_init): summary_parts.append(f"🗓️ Dates: {start_display} to {end_display}")
    else: summary_parts.append(f"🗓️ Dates: {start_display} to {end_display} (Default MTD)")
    active_cat_filters = [];
    for col_key, label_text in category_filters_map.items():
        selected_vals = st.session_state.get(f"{col_key}_filter", []);
        if selected_vals: active_cat_filters.append(f"{label_text.replace('(s)','').strip()}: {', '.join(selected_vals)}")
    if active_cat_filters: summary_parts.append(" | ".join(active_cat_filters))
    if not any(st.session_state.get(f"{key}_filter") for key in category_filters_map) and not (st.session_state.get('date_filter_is_active', False) or (start_dt_filter != default_s_init or end_dt_filter != default_e_init)): summary_parts.append("No category filters.")
final_summary_message = " | ".join(filter(None, summary_parts));
if not final_summary_message: final_summary_message = "Displaying data (default date range)."
st.markdown(f"<div class='active-filters-summary'>ℹ️ {final_summary_message}</div>", unsafe_allow_html=True)

# --- Apply Filters / Search to Data ---
df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
if not df_original.empty:
    if global_search_active:
        # Apply global search if active.
        df_temp_gs = df_original.copy(); ln_term = st.session_state.get("licenseNumber_search", "").strip().lower(); sn_term = st.session_state.get("storeName_search", "").strip()
        if ln_term and "licenseNumber" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
        if sn_term and "storeName" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['storeName'] == sn_term]
        df_global_search_results_display = df_temp_gs.copy(); df_filtered = df_global_search_results_display.copy()
    else:
        # Apply sidebar filters if global search is not active.
        df_temp_filters = df_original.copy();
        # Apply date filter.
        if 'onboarding_date_only' in df_temp_filters.columns and df_temp_filters['onboarding_date_only'].notna().any():
            date_objects_for_filter = pd.to_datetime(df_temp_filters['onboarding_date_only'], errors='coerce').dt.date; valid_dates_mask = date_objects_for_filter.notna(); date_filter_condition = pd.Series([False] * len(df_temp_filters), index=df_temp_filters.index)
            if valid_dates_mask.any(): date_filter_condition[valid_dates_mask] = (date_objects_for_filter[valid_dates_mask] >= start_dt_filter) & (date_objects_for_filter[valid_dates_mask] <= end_dt_filter)
            df_temp_filters = df_temp_filters[date_filter_condition]
        # Apply category filters.
        for col_name_cat, _ in category_filters_map.items():
            # *** FIX: Use col_name_cat here instead of col_key ***
            selected_values_cat = st.session_state.get(f"{col_name_cat}_filter", [])
            if selected_values_cat and col_name_cat in df_temp_filters.columns:
                if col_name_cat == 'status': # Special handling for 'status' (remove emojis before check).
                    df_temp_filters = df_temp_filters[df_temp_filters[col_name_cat].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().isin(selected_values_cat)]
                else: # Standard 'isin' check for other filters.
                    df_temp_filters = df_temp_filters[df_temp_filters[col_name_cat].astype(str).isin(selected_values_cat)]
        df_filtered = df_temp_filters.copy()
else: df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()

# Calculate MTD metrics for the overview tab.
today_mtd_calc = date.today(); mtd_start_calc = today_mtd_calc.replace(day=1); prev_month_end_calc = mtd_start_calc - timedelta(days=1); prev_month_start_calc = prev_month_end_calc.replace(day=1)
df_mtd_data, df_prev_mtd_data = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_original_for_calc = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date; valid_mask_original_calc = dates_original_for_calc.notna()
    if valid_mask_original_calc.any():
        df_valid_dates_original = df_original[valid_mask_original_calc].copy(); valid_dates_series_original = dates_original_for_calc[valid_mask_original_calc]
        mtd_mask = (valid_dates_series_original >= mtd_start_calc) & (valid_dates_series_original <= today_mtd_calc); prev_mtd_mask = (valid_dates_series_original >= prev_month_start_calc) & (valid_dates_series_original <= prev_month_end_calc)
        df_mtd_data = df_valid_dates_original[mtd_mask.values if len(mtd_mask) == len(df_valid_dates_original) else mtd_mask[df_valid_dates_original.index]]
        df_prev_mtd_data = df_valid_dates_original[prev_mtd_mask.values if len(prev_mtd_mask) == len(df_valid_dates_original) else prev_mtd_mask[df_valid_dates_original.index]]
total_mtd, sr_mtd, score_mtd, days_to_confirm_mtd = calculate_metrics(df_mtd_data); total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_data)
delta_onboardings_mtd = (total_mtd - total_prev_mtd) if pd.notna(total_mtd) and pd.notna(total_prev_mtd) else None

# --- Table Styling & Display Functions ---
# Function to return a CSS class for table cells based on their content.
def get_cell_style_class(column_name, value):
    """Returns a CSS class for styling table cells based on value."""
    val_str = str(value).strip().lower()
    if pd.isna(value) or val_str == "" or val_str == "na": return "cell-req-na"
    if column_name == 'score':
        try: score_num = float(value)
        except: return ""
        if score_num >= 8: return "cell-score-good"
        elif score_num >= 4: return "cell-score-medium"
        else: return "cell-score-bad"
    elif column_name == 'clientSentiment':
        if val_str == 'positive': return "cell-sentiment-positive"
        elif val_str == 'neutral': return "cell-sentiment-neutral"
        elif val_str == 'negative': return "cell-sentiment-negative"
    elif column_name == 'days_to_confirmation':
        try: days_num = float(value)
        except: return ""
        if days_num <= 7: return "cell-days-good"
        elif days_num <= 14: return "cell-days-medium"
        else: return "cell-days-bad"
    elif column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
        if val_str in ['true', '1', 'yes', 'x', 'completed', 'done']: return "cell-req-met"
        elif val_str in ['false', '0', 'no']: return "cell-req-not-met"
    elif column_name == 'status': return "cell-status"
    return ""

# Function to display data in our custom HTML table and show record details below.
def display_html_table_and_details(df_to_display, context_key_prefix=""):
    """Generates and displays an HTML table and a record details viewer."""
    if df_to_display is None or df_to_display.empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','');
        if not df_original.empty: st.markdown(f"<div class='no-data-message'>📊 No data for {context_name_display}. Try different filters! 📊</div>", unsafe_allow_html=True)
        return

    df_display_copy = df_to_display.copy().reset_index(drop=True)
    def map_status_to_emoji_html(status_val): # Helper to add emojis to status.
        status_str = str(status_val).strip().lower();
        if status_str == 'confirmed': return "✅ Confirmed";
        if status_str == 'pending': return "⏳ Pending";
        if status_str == 'failed': return "❌ Failed";
        return status_val
    if 'status' in df_display_copy.columns: df_display_copy['status_styled'] = df_display_copy['status'].apply(map_status_to_emoji_html)
    else: df_display_copy['status_styled'] = ""

    # Define the order of columns in the table and select those present.
    preferred_cols_order = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status_styled', 'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 'contactNumber', 'confirmedNumber', 'deliveryDate', 'confirmationTimestamp']
    preferred_cols_order.extend(ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS)
    cols_present_in_df = df_display_copy.columns.tolist(); final_display_cols = [col for col in preferred_cols_order if col in cols_present_in_df]
    excluded_suffixes = ('_dt', '_utc', '_str_original', '_date_only', '_styled')
    other_existing_cols_for_display = [col for col in cols_present_in_df if col not in final_display_cols and not col.endswith(excluded_suffixes) and col not in ['fullTranscript', 'summary', 'status', 'onboardingWelcome']]
    final_display_cols.extend(other_existing_cols_for_display); final_display_cols = list(dict.fromkeys(final_display_cols))
    if not final_display_cols or df_display_copy[final_display_cols].empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog',''); st.markdown(f"<div class='no-data-message'>📋 No columns/data for {context_name_display}. 📋</div>", unsafe_allow_html=True); return

    # Build the HTML table string.
    html_table = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
    column_display_names = { # Define user-friendly column headers.
        'status_styled': 'Status', 'onboardingDate': 'Onboarding Date', 'repName': 'Rep Name', 'storeName': 'Store Name',
        'licenseNumber': 'License No.', 'clientSentiment': 'Sentiment', 'days_to_confirmation': 'Days to Confirm',
        'contactName': 'Contact Name', 'contactNumber': 'Contact No.', 'confirmedNumber': 'Confirmed No.',
        'deliveryDate': 'Delivery Date', 'confirmationTimestamp': 'Confirmation Time'
    }
    for req_key, details in KEY_REQUIREMENT_DETAILS.items(): column_display_names[req_key] = details.get("chart_label", req_key)
    for col_id in final_display_cols: display_name = column_display_names.get(col_id, col_id.replace("_", " ").title()); html_table.append(f"<th>{display_name}</th>")
    html_table.append("</tr></thead><tbody>")
    # Add table rows (<td>) with data and apply CSS classes.
    for index, row in df_display_copy.iterrows():
        html_table.append("<tr>")
        for col_id in final_display_cols:
            original_col_for_styling = 'status' if col_id == 'status_styled' else col_id; cell_value = row.get(col_id, "")
            style_class = get_cell_style_class(original_col_for_styling, row.get(original_col_for_styling, cell_value))
            if col_id == 'score' and pd.notna(cell_value): cell_value = f"{cell_value:.1f}" # Format numbers.
            elif col_id == 'days_to_confirmation' and pd.notna(cell_value): cell_value = f"{cell_value:.0f}"
            html_table.append(f"<td class='{style_class}'>{cell_value}</td>")
        html_table.append("</tr>")
    html_table.append("</tbody></table></div>");
    # Render the HTML table using Streamlit's markdown.
    st.markdown("".join(html_table), unsafe_allow_html=True)

    # --- Details Viewer ---
    st.markdown("---"); st.subheader("📄 View Full Record Details")
    transcript_session_key_local = f"selected_transcript_key_{context_key_prefix}";
    if transcript_session_key_local not in st.session_state: st.session_state[transcript_session_key_local] = None
    auto_selected_this_run = False
    if len(df_display_copy) == 1: # Auto-select if only one row.
        first_row_details = df_display_copy.iloc[0]; auto_select_option_key = f"Idx 0: {first_row_details.get('storeName', 'N/A')} ({first_row_details.get('onboardingDate', 'N/A')})"
        if st.session_state[transcript_session_key_local] != auto_select_option_key: st.session_state[transcript_session_key_local] = auto_select_option_key; auto_selected_this_run = True
    auto_selected_once_key = f"{context_key_prefix}_auto_selected_once"
    if auto_selected_this_run and not st.session_state.get(auto_selected_once_key, False): st.session_state[auto_selected_once_key] = True; st.rerun() # Rerun once on auto-select.
    elif len(df_display_copy) != 1: st.session_state[auto_selected_once_key] = False

    # Check if we have data for the details viewer.
    if 'fullTranscript' in df_display_copy.columns or 'summary' in df_display_copy.columns:
        transcript_options_map = {f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_copy.iterrows()}
        if transcript_options_map:
            # Create the selectbox for choosing a record.
            options_list_for_select = [None] + list(transcript_options_map.keys()); current_selection_for_select = st.session_state[transcript_session_key_local]
            try: current_index_for_select = options_list_for_select.index(current_selection_for_select)
            except ValueError: current_index_for_select = 0; st.session_state[transcript_session_key_local] = None
            selected_key_from_display = st.selectbox("Select record to view details:", options=options_list_for_select, index=current_index_for_select, format_func=lambda x: "📄 Choose an entry..." if x is None else x, key=f"transcript_selector_{context_key_prefix}_widget_v4_3_1")
            if selected_key_from_display != st.session_state[transcript_session_key_local]: st.session_state[transcript_session_key_local] = selected_key_from_display; st.session_state[auto_selected_once_key] = False; st.rerun()
            # If a record is selected, display its details.
            if st.session_state[transcript_session_key_local]:
                selected_original_idx = transcript_options_map[st.session_state[transcript_session_key_local]]; selected_row_details = df_display_copy.loc[selected_original_idx]
                st.markdown("<h5>📋 Onboarding Summary & Checks:</h5>", unsafe_allow_html=True); summary_html_parts_list = ["<div class='transcript-summary-grid'>"]
                summary_items_to_display = {"Store": selected_row_details.get('storeName', "N/A"), "Rep": selected_row_details.get('repName', "N/A"), "Score": f"{selected_row_details.get('score', 'N/A'):.1f}" if pd.notna(selected_row_details.get('score')) else "N/A", "Status": selected_row_details.get('status_styled', "N/A"), "Sentiment": selected_row_details.get('clientSentiment', "N/A")}
                for item_label, item_val in summary_items_to_display.items(): summary_html_parts_list.append(f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_val}</div>")
                call_summary_text = selected_row_details.get('summary', '').strip();
                if call_summary_text and call_summary_text.lower() not in ['na', 'n/a', '']: summary_html_parts_list.append(f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>📝 Call Summary:</strong> {call_summary_text}</div>")
                summary_html_parts_list.append("</div>"); st.markdown("".join(summary_html_parts_list), unsafe_allow_html=True)
                st.markdown("<div class='transcript-details-section'>", unsafe_allow_html=True); st.markdown("<h6>Key Requirement Checks:</h6>", unsafe_allow_html=True)
                for item_col_name_req in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                    details_obj = KEY_REQUIREMENT_DETAILS.get(item_col_name_req);
                    if details_obj:
                        desc_text = details_obj.get("description", item_col_name_req.replace('_',' ').title()); item_type_text = details_obj.get("type", ""); val_from_row = selected_row_details.get(item_col_name_req, pd.NA)
                        val_str_lower = str(val_from_row).strip().lower(); is_met = val_str_lower in ['true', '1', 'yes', 'x', 'completed', 'done']
                        emoji_char = "✅" if is_met else ("❌" if pd.notna(val_from_row) and val_str_lower != "" else "➖"); type_tag_html = f"<span class='type'>[{item_type_text}]</span>" if item_type_text else ""; st.markdown(f"<div class='requirement-item'>{emoji_char} {desc_text} {type_tag_html}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---"); st.markdown("<h5>🎙️ Full Transcript:</h5>", unsafe_allow_html=True); transcript_content = selected_row_details.get('fullTranscript', "").strip()
                if transcript_content and transcript_content.lower() not in ['na', 'n/a', '']:
                    html_transcript_parts = ["<div class='transcript-pane-container'><div class='transcript-container'>"]; processed_transcript_content = transcript_content.replace('\\n', '\n')
                    for line_item in processed_transcript_content.split('\n'):
                        line_item_stripped = line_item.strip();
                        if not line_item_stripped: continue
                        parts_of_line = line_item_stripped.split(":", 1); speaker_html = f"<strong>{parts_of_line[0].strip()}:</strong>" if len(parts_of_line) == 2 else ""
                        message_text = parts_of_line[1].strip() if len(parts_of_line) == 2 else line_item_stripped; html_transcript_parts.append(f"<p class='transcript-line'>{speaker_html} {message_text}</p>")
                    html_transcript_parts.append("</div></div>"); st.markdown("".join(html_transcript_parts), unsafe_allow_html=True)
                else: st.info("ℹ️ No transcript available or empty for this record.")
        else: st.markdown("<div class='no-data-message'>📋 No entries in table to select details. 📋</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>📜 Necessary columns ('fullTranscript'/'summary') missing. 📜</div>", unsafe_allow_html=True)
    # Add a download button for the current table's data.
    st.markdown("---"); csv_data_to_download = convert_df_to_csv(df_display_copy[final_display_cols]); download_label = f"📥 Download These {context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')} Results"
    st.download_button(label=download_label, data=csv_data_to_download, file_name=f'{context_key_prefix}_results_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', mime='text/csv', use_container_width=True, key=f"download_csv_{context_key_prefix}_button_v4_3_1")

# --- Global Search Dialog ---
# If global search is active, show the results in a pop-up dialog.
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("🔍 Global Search Results", width="large")
    def show_global_search_dialog_content():
        """Defines the content of the global search results dialog."""
        st.markdown("##### Records matching global search criteria:");
        if not df_global_search_results_display.empty: display_html_table_and_details(df_global_search_results_display, context_key_prefix="dialog_global_search")
        else: st.info("ℹ️ No results for global search. Try broadening terms.")
        if st.button("Close & Clear Search", key="close_gs_dialog_clear_button_v4_3_1"):
            st.session_state.show_global_search_dialog = False; st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""
            if 'selected_transcript_key_dialog_global_search' in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
            if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
            st.rerun() # Rerun to close dialog and apply changes.
    show_global_search_dialog_content() # Call the function to show the dialog.

# --- Tab Content Display ---
# Display content based on which main tab is currently selected.

# Overview Tab: Shows MTD metrics and a snapshot of filtered metrics.
if st.session_state.active_tab == TAB_OVERVIEW:
    st.header("📈 Month-to-Date (MTD) Performance"); cols_mtd_overview = st.columns(4)
    with cols_mtd_overview[0]: st.metric("🗓️ Onboardings MTD", value=f"{total_mtd:.0f}" if pd.notna(total_mtd) else "0", delta=f"{delta_onboardings_mtd:+.0f} vs Prev. Month" if delta_onboardings_mtd is not None and pd.notna(delta_onboardings_mtd) else "N/A", help="Total onboardings MTD vs. same period last month.")
    with cols_mtd_overview[1]: st.metric("✅ Success Rate MTD", value=f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A", help="Confirmed onboardings MTD.")
    with cols_mtd_overview[2]: st.metric("⭐ Avg. Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A", help="Average score (0-10) MTD.")
    with cols_mtd_overview[3]: st.metric("⏳ Avg. Days to Confirm MTD", value=f"{days_to_confirm_mtd:.1f}" if pd.notna(days_to_confirm_mtd) else "N/A", help="Avg days delivery to confirmation MTD.")
    st.header("📊 Filtered Data Snapshot")
    if global_search_active: st.info("ℹ️ Global search active. Close pop-up or clear search for filtered overview.")
    elif not df_filtered.empty:
        total_filtered, sr_filtered, score_filtered, days_filtered = calculate_metrics(df_filtered); cols_filtered_overview = st.columns(4)
        with cols_filtered_overview[0]: st.metric("📄 Onboardings (Filtered)", f"{total_filtered:.0f}" if pd.notna(total_filtered) else "0")
        with cols_filtered_overview[1]: st.metric("🎯 Success Rate (Filtered)", f"{sr_filtered:.1f}%" if pd.notna(sr_filtered) else "N/A")
        with cols_filtered_overview[2]: st.metric("🌟 Avg. Score (Filtered)", f"{score_filtered:.2f}" if pd.notna(score_filtered) else "N/A")
        with cols_filtered_overview[3]: st.metric("⏱️ Avg. Days Confirm (Filtered)", f"{days_filtered:.1f}" if pd.notna(days_filtered) else "N/A")
    else: st.markdown("<div class='no-data-message'>🤷 No data matches filters for Overview. Adjust selections! 🤷</div>", unsafe_allow_html=True)

# Detailed Analysis Tab: Shows the main table and charts based on filters.
elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if global_search_active: st.info("ℹ️ Global Search active. Results in pop-up. Close/clear search for category/date filters here.")
    else:
        display_html_table_and_details(df_filtered, context_key_prefix="filtered_analysis")
        st.divider()
        st.header("🎨 Key Visualizations (Filtered Data)")
        if not df_filtered.empty:
            with st.container():
                chart_cols_1, chart_cols_2 = st.columns(2) # Arrange charts in two columns.
                with chart_cols_1:
                    # Status Distribution Chart.
                    if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                        status_counts_df = df_filtered['status'].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().value_counts().reset_index(); status_counts_df.columns = ['status', 'count']
                        status_fig = px.bar(status_counts_df, x='status', y='count', color='status', title="Onboarding Status Distribution", color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ); status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
                    else: st.markdown("<div class='no-data-message'>📉 Status data unavailable.</div>", unsafe_allow_html=True)
                    # Onboardings by Rep Chart.
                    if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                        rep_counts_df = df_filtered['repName'].value_counts().reset_index(); rep_counts_df.columns = ['repName', 'count']
                        rep_fig = px.bar(rep_counts_df, x='repName', y='count', color='repName', title="Onboardings by Representative", color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ); rep_fig.update_layout(plotly_base_layout_settings, xaxis_title="Representative", yaxis_title="Number of Onboardings"); st.plotly_chart(rep_fig, use_container_width=True)
                    else: st.markdown("<div class='no-data-message'>👥 Rep data unavailable.</div>", unsafe_allow_html=True)
                with chart_cols_2:
                    # Client Sentiment Pie Chart.
                    if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                        sent_counts_df = df_filtered['clientSentiment'].value_counts().reset_index(); sent_counts_df.columns = ['clientSentiment', 'count']
                        current_sentiment_map_plot = {s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), '#808080') for s in sent_counts_df['clientSentiment'].unique()}
                        sent_fig = px.pie(sent_counts_df, names='clientSentiment', values='count', hole=0.4, title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=current_sentiment_map_plot); sent_fig.update_layout(plotly_base_layout_settings); sent_fig.update_traces(textinfo='percent+label', textfont_size=12); st.plotly_chart(sent_fig, use_container_width=True)
                    else: st.markdown("<div class='no-data-message'>😊 Sentiment data unavailable.</div>", unsafe_allow_html=True)
                    # Key Requirement Completion Chart (only for 'Confirmed' records).
                    df_confirmed_for_chart = df_filtered[df_filtered['status'].astype(str).str.contains('confirmed', case=False, na=False)].copy(); actual_key_cols_for_checklist_chart = [col for col in ORDERED_CHART_REQUIREMENTS if col in df_confirmed_for_chart.columns]
                    if not df_confirmed_for_chart.empty and actual_key_cols_for_checklist_chart:
                        checklist_data_for_plotly = [];
                        for item_col_name_chart in actual_key_cols_for_checklist_chart:
                            item_details_chart = KEY_REQUIREMENT_DETAILS.get(item_col_name_chart); chart_label_bar = item_details_chart.get("chart_label", item_col_name_chart.replace('_',' ').title()) if item_details_chart else item_col_name_chart.replace('_',' ').title()
                            if item_col_name_chart in df_confirmed_for_chart.columns:
                                raw_series = df_confirmed_for_chart[item_col_name_chart].astype(str).str.lower(); bool_series_chart = raw_series.isin(['true', '1', 'yes', 'x', 'completed', 'done']); total_valid_for_item = df_confirmed_for_chart[item_col_name_chart].notna().sum(); true_count_for_item = bool_series_chart.sum()
                                if total_valid_for_item > 0: checklist_data_for_plotly.append({"Key Requirement": chart_label_bar, "Completion (%)": (true_count_for_item / total_valid_for_item) * 100})
                        if checklist_data_for_plotly:
                            df_checklist_plotly = pd.DataFrame(checklist_data_for_plotly);
                            if not df_checklist_plotly.empty: checklist_bar_fig = px.bar(df_checklist_plotly.sort_values("Completion (%)", ascending=True), x="Completion (%)", y="Key Requirement", orientation='h', title="Key Req Completion (Confirmed Only)", color_discrete_sequence=[PRIMARY_COLOR_FOR_PLOTLY]); checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}, xaxis_ticksuffix="%"); st.plotly_chart(checklist_bar_fig, use_container_width=True)
                            else: st.markdown("<div class='no-data-message'>📊 No data for key req chart.</div>", unsafe_allow_html=True)
                        else: st.markdown("<div class='no-data-message'>📊 No valid checklist items for req chart.</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='no-data-message'>✅ No 'Confirmed' onboardings for req chart.</div>", unsafe_allow_html=True)
        elif not df_original.empty : st.markdown("<div class='no-data-message'>🖼️ No data matches filters for visuals. 🖼️</div>", unsafe_allow_html=True)

# Trends Tab: Shows time series and distribution plots.
elif st.session_state.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS); st.markdown(f"*(Visuals based on {'Global Search (Pop-Up)' if global_search_active else 'Filtered Data'})*")
    if not df_filtered.empty:
        # Onboardings Over Time Line Chart.
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_source = df_filtered.copy(); df_trend_source['onboarding_datetime'] = pd.to_datetime(df_trend_source['onboarding_date_only'], errors='coerce'); df_trend_source.dropna(subset=['onboarding_datetime'], inplace=True)
            if not df_trend_source.empty:
                date_span_days = (df_trend_source['onboarding_datetime'].max() - df_trend_source['onboarding_datetime'].min()).days; resample_freq = 'D'; # Default to daily.
                if date_span_days > 90: resample_freq = 'W-MON'; # Use weekly if > 3 months.
                if date_span_days > 730: resample_freq = 'ME' # Use monthly (Month-End) if > 2 years.
                trend_data_resampled = df_trend_source.set_index('onboarding_datetime').resample(resample_freq).size().reset_index(name='count')
                if not trend_data_resampled.empty:
                    trend_line_fig = px.line(trend_data_resampled, x='onboarding_datetime', y='count', markers=True, title=f"Onboardings Over Time ({resample_freq} Trend)", color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[0]]); trend_line_fig.update_layout(plotly_base_layout_settings, xaxis_title="Date", yaxis_title="Number of Onboardings"); st.plotly_chart(trend_line_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📈 Not enough data for trend plot.</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='no-data-message'>📅 No valid date data for trend.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>🗓️ 'onboarding_date_only' missing for trend.</div>", unsafe_allow_html=True)
        # Days to Confirmation Histogram.
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna();
            if not days_data_for_hist.empty:
                num_bins_hist = max(10, min(30, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else (len(days_data_for_hist.unique()) or 10); days_dist_fig = px.histogram(days_data_for_hist, nbins=num_bins_hist, title="Distribution of Days to Confirmation", color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[1]]); days_dist_fig.update_layout(plotly_base_layout_settings, xaxis_title="Days to Confirmation", yaxis_title="Frequency"); st.plotly_chart(days_dist_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>⏳ No 'Days to Confirmation' data.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' missing.</div>", unsafe_allow_html=True)
    elif not df_original.empty : st.markdown("<div class='no-data-message'>📉 No data for Trends. Adjust filters. 📉</div>", unsafe_allow_html=True)

# Add a footer at the bottom of the page.
st.markdown("---"); st.markdown(f"<div class='footer'>Dashboard v4.6.7</div>", unsafe_allow_html=True)