# Import necessary libraries
# These are pre-written collections of code that provide useful functions.

# Streamlit is the main library for creating the web app and its interactive elements.
import streamlit as st
# Pandas is used for working with data in a structured way (like spreadsheets or tables).
import pandas as pd
# Plotly Express is used for creating interactive charts and graphs.
import plotly.express as px
import plotly.graph_objects as go # Another part of Plotly for more custom graphs
# datetime, date, timedelta are for working with dates and times.
from datetime import datetime, date, timedelta
# gspread is for interacting with Google Sheets.
import gspread
# Credentials from google.oauth2.service_account is for authenticating with Google services.
from google.oauth2.service_account import Credentials
# time is for time-related functions, like pausing execution.
import time
# NumPy is for numerical operations, especially with arrays (though not heavily used here).
import numpy as np
# re is for regular expressions, used for advanced text pattern matching.
import re

# --- Page Configuration ---
# This sets up the basic properties of the web page.
# It should be the first Streamlit command in your app, except for comments.
st.set_page_config(
    page_title="Onboarding Performance Dashboard v3.11", # The title that appears in the browser tab.
    page_icon="💎",  # The icon that appears in the browser tab (can be an emoji or URL).
    layout="wide"  # Use the full width of the page for the content.
)

# --- Accent Color & Plotly Palette Definitions ---
# Here, we define sets of color codes (hexadecimal) for different visual themes.
# This helps in easily switching the app's look and feel.

# Dark Theme Accents & Plotly Colors
DARK_APP_ACCENT_PRIMARY = "#8458B3"    # Primary Purple for dark mode
DARK_APP_ACCENT_SECONDARY = "#d0bdf4"  # Light Lavender for dark mode
DARK_APP_ACCENT_MUTED = "#a28089"     # Muted Mauve for dark mode
DARK_APP_ACCENT_HIGHLIGHT = "#a0d2eb"  # Light Blue for highlights in dark mode
DARK_APP_ACCENT_LIGHTEST = "#e5eaf5"   # Very Light Purple/Blue for subtle elements in dark mode
DARK_APP_TEXT_ON_ACCENT = DARK_APP_ACCENT_LIGHTEST # Text color to use on primary accent backgrounds
DARK_APP_TEXT_ON_HIGHLIGHT = "#0E1117" # Text color for highlight backgrounds

DARK_APP_DL_BUTTON_BG = DARK_APP_ACCENT_HIGHLIGHT # Download button background for dark mode
DARK_APP_DL_BUTTON_TEXT = DARK_APP_TEXT_ON_HIGHLIGHT # Download button text color for dark mode
DARK_APP_DL_BUTTON_HOVER_BG = DARK_APP_ACCENT_LIGHTEST # Download button hover background for dark mode

# Color sequences for Plotly charts in dark mode
DARK_PLOTLY_PRIMARY_SEQ = [DARK_APP_ACCENT_PRIMARY, DARK_APP_ACCENT_SECONDARY, DARK_APP_ACCENT_HIGHLIGHT, '#C39BD3', '#76D7C4']
DARK_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1 # A pre-defined sequence from Plotly
DARK_PLOTLY_SENTIMENT_MAP = { 'positive': DARK_APP_ACCENT_HIGHLIGHT, 'negative': '#E74C3C', 'neutral': DARK_APP_ACCENT_MUTED }

# Light Theme Accents & Plotly Colors (Blue-centric, high contrast)
LIGHT_APP_ACCENT_PRIMARY = "#1A73E8"  # Google Blue for light mode
LIGHT_APP_ACCENT_SECONDARY = "#4285F4" # Lighter Google Blue for light mode
LIGHT_APP_ACCENT_MUTED = "#89B1F3"   # Softer Blue for light mode
LIGHT_APP_ACCENT_HIGHLIGHT = LIGHT_APP_ACCENT_PRIMARY # Primary blue also for highlights in light mode
LIGHT_APP_ACCENT_LIGHTEST = "#E8F0FE" # Very Light Blue for subtle elements in light mode
LIGHT_APP_TEXT_ON_ACCENT = "#FFFFFF"  # White text on blue accents for light mode

LIGHT_APP_DL_BUTTON_BG = LIGHT_APP_ACCENT_PRIMARY # Download button background for light mode
LIGHT_APP_DL_BUTTON_TEXT = LIGHT_APP_TEXT_ON_ACCENT # Download button text color for light mode
LIGHT_APP_DL_BUTTON_HOVER_BG = "#1765CC" # Darker blue for download button hover in light mode

# Color sequences for Plotly charts in light mode
LIGHT_PLOTLY_PRIMARY_SEQ = ['#1A73E8', '#4285F4', '#89B1F3', '#ADC6F7', '#D2E3FC']
LIGHT_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set2 # Another pre-defined sequence from Plotly
LIGHT_PLOTLY_SENTIMENT_MAP = { 'positive': '#1A73E8', 'negative': '#D93025', 'neutral': '#78909C' }

# --- Determine Active Theme and Set ACTIVE Accent & Plotly Colors ---
# Streamlit allows users to switch between light and dark themes in its settings.
# This code checks which theme is currently active.
THEME = st.get_option("theme.base") # Returns "light" or "dark"

# Based on the active theme, we select the appropriate set of colors defined above.
# These 'ACTIVE_' variables will then be used throughout the app.
if THEME == "light":
    ACTIVE_ACCENT_PRIMARY = LIGHT_APP_ACCENT_PRIMARY
    ACTIVE_ACCENT_SECONDARY = LIGHT_APP_ACCENT_SECONDARY
    ACTIVE_ACCENT_MUTED = LIGHT_APP_ACCENT_MUTED
    ACTIVE_ACCENT_HIGHLIGHT = LIGHT_APP_ACCENT_HIGHLIGHT
    ACTIVE_ACCENT_LIGHTEST = LIGHT_APP_ACCENT_LIGHTEST
    ACTIVE_TEXT_ON_ACCENT = LIGHT_APP_TEXT_ON_ACCENT
    ACTIVE_DL_BUTTON_BG = LIGHT_APP_DL_BUTTON_BG
    ACTIVE_DL_BUTTON_TEXT = LIGHT_APP_DL_BUTTON_TEXT
    ACTIVE_DL_BUTTON_HOVER_BG = LIGHT_APP_DL_BUTTON_HOVER_BG
    # Plotly active colors
    ACTIVE_PLOTLY_PRIMARY_SEQ = LIGHT_PLOTLY_PRIMARY_SEQ
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = LIGHT_PLOTLY_QUALITATIVE_SEQ
    ACTIVE_PLOTLY_SENTIMENT_MAP = LIGHT_PLOTLY_SENTIMENT_MAP
else: # Default to Dark Theme Accents if theme is not "light" (or if st.get_option fails)
    ACTIVE_ACCENT_PRIMARY = DARK_APP_ACCENT_PRIMARY
    ACTIVE_ACCENT_SECONDARY = DARK_APP_ACCENT_SECONDARY
    ACTIVE_ACCENT_MUTED = DARK_APP_ACCENT_MUTED
    ACTIVE_ACCENT_HIGHLIGHT = DARK_APP_ACCENT_HIGHLIGHT
    ACTIVE_ACCENT_LIGHTEST = DARK_APP_ACCENT_LIGHTEST
    ACTIVE_TEXT_ON_ACCENT = DARK_APP_TEXT_ON_ACCENT
    ACTIVE_DL_BUTTON_BG = DARK_APP_DL_BUTTON_BG
    ACTIVE_DL_BUTTON_TEXT = DARK_APP_DL_BUTTON_TEXT
    ACTIVE_DL_BUTTON_HOVER_BG = DARK_APP_DL_BUTTON_HOVER_BG
    # Plotly active colors
    ACTIVE_PLOTLY_PRIMARY_SEQ = DARK_PLOTLY_PRIMARY_SEQ
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = DARK_PLOTLY_QUALITATIVE_SEQ
    ACTIVE_PLOTLY_SENTIMENT_MAP = DARK_PLOTLY_SENTIMENT_MAP

PLOT_BG_COLOR = "rgba(0,0,0,0)" # Background color for plots (transparent)

# --- Custom Styling (CSS) ---
# CSS (Cascading Style Sheets) is used to control the visual appearance of web pages.
# Streamlit allows injecting custom CSS using st.markdown.
css_parts = [
    "<style>", # HTML tag to start CSS definitions
    # This f-string (formatted string literal) injects the Python color variables into CSS variables.
    # CSS variables (like --app-accent-primary) can be reused throughout the CSS.
    f"""
    :root {{
        --app-accent-primary: {ACTIVE_ACCENT_PRIMARY};
        --app-accent-secondary: {ACTIVE_ACCENT_SECONDARY};
        --app-accent-muted: {ACTIVE_ACCENT_MUTED};
        --app-accent-highlight: {ACTIVE_ACCENT_HIGHLIGHT};
        --app-accent-lightest: {ACTIVE_ACCENT_LIGHTEST};
        --app-text-on-accent: {ACTIVE_TEXT_ON_ACCENT};

        --app-dl-button-bg: {ACTIVE_DL_BUTTON_BG};
        --app-dl-button-text: {ACTIVE_DL_BUTTON_TEXT};
        --app-dl-button-hover-bg: {ACTIVE_DL_BUTTON_HOVER_BG};

        /* Fallback border color if Streamlit's theme doesn't provide one */
        --border-color-fallback: {"#DADCE0" if THEME == "light" else "#3a3f4b"};
    }}
    """,
    # This is a multi-line raw string containing the rest of the CSS rules.
    """
    /* General App Styles */
    /* Streamlit's main app container header (where "View app" might appear) */
    .stApp > header { background-color: transparent !important; }

    /* Styles for different heading levels (h1, h2, h3, h5) */
    h1 { /* Main Dashboard Title */
        color: var(--app-accent-primary); text-align: center;
        padding-top: 0.8em; padding-bottom: 0.6em;
        font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
        font-size: 2.1rem; /* Adjusted size */
    }
    h2 { /* Main Section Headers (Overview, Analysis, Trends) */
        color: var(--app-accent-primary);
        border-bottom: 2px solid var(--app-accent-primary) !important; /* !important overrides other styles */
        padding-bottom: 0.3em;
        margin-top: 2.2em; /* More space above */
        margin-bottom: 1.5em; /* More space below */
        font-weight: 600;
        font-size: 1.7rem; /* Adjusted size */
    }
    h3 { /* Sub-Section Headers (e.g., Filtered Onboarding Data Table) */
        color: var(--app-accent-primary);
        border-bottom: 1px dotted var(--app-accent-secondary) !important; /* Lighter border */
        padding-bottom: 0.4em;
        margin-top: 2em;
        margin-bottom: 1.2em;
        font-weight: 600;
        font-size: 1.45rem; /* Adjusted size */
    }
    h5 { /* Sub-sub headers like "Onboarding Summary:" */
        color: var(--app-accent-primary); opacity: 0.95;
        margin-top: 1.8em; margin-bottom: 0.8em; /* More top margin */
        font-weight: 600; letter-spacing: 0.3px; /* Reduced letter spacing */
        font-size: 1.2rem; /* Adjusted size */
    }

    /* Metric Widget Styles - These are the boxes showing key numbers */
    div[data-testid="stMetric"], .metric-card {
        background-color: var(--secondary-background-color); /* Streamlit's theme variable for card backgrounds */
        padding: 1.5em; border-radius: 12px; border: 1px solid var(--border-color, var(--border-color-fallback));
        box-shadow: 0 4px 6px rgba(0,0,0,0.04); /* Subtle shadow */
        transition: transform 0.25s ease-in-out, box-shadow 0.25s ease-in-out; /* Smooth hover effect */
    }
    div[data-testid="stMetric"]:hover, .metric-card:hover {
         transform: translateY(-4px); box-shadow: 0 6px 12px rgba(0,0,0,0.06); /* Lift effect on hover */
    }
    /* Styling the label, value, and delta (change) parts of a metric */
    div[data-testid="stMetricLabel"] > div { color: var(--text-color) !important; opacity: 0.7; font-weight: 500; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetricValue"] > div { color: var(--text-color) !important; font-size: 2.3rem !important; font-weight: 700; line-height: 1.1; }
    div[data-testid="stMetricDelta"] > div { color: var(--text-color) !important; opacity: 0.7; font-weight: 500; font-size: 0.85em; }

    /* Expander Styles - For collapsible sections */
    .streamlit-expanderHeader { color: var(--app-accent-primary) !important; font-weight: 600; font-size: 1.1em; }
    .streamlit-expander {
        border: 1px solid var(--border-color, var(--border-color-fallback));
        background-color: var(--secondary-background-color);
        border-radius: 10px;
    }
    .streamlit-expander > div > div > p { color: var(--text-color); } /* Text inside expander */

    /* DataFrame Styles - For tables displayed using st.dataframe */
    .stDataFrame { border: 1px solid var(--border-color, var(--border-color-fallback)); border-radius: 10px; }

    /* Custom Tab (Radio Button) Styles - For the main navigation tabs */
    div[data-testid="stRadio"] label { /* Non-active tab style */
        padding: 12px 22px; margin: 0 5px; border-radius: 10px 10px 0 0;
        border: 1px solid transparent; border-bottom: none;
        background-color: var(--secondary-background-color);
        color: var(--text-color); opacity: 0.65;
        transition: background-color 0.3s ease, color 0.3s ease, opacity 0.3s ease, border-color 0.3s ease, border-top-width 0.2s ease;
        font-weight: 500; font-size: 1.05em;
    }
    div[data-testid="stRadio"] input:checked + div label { /* Active tab style */
        background-color: var(--app-accent-lightest); /* Use our lightest accent for active tab background */
        color: var(--app-accent-primary); /* Use our primary accent for active tab text */
        font-weight: 600; opacity: 1.0;
        border-top: 3px solid var(--app-accent-primary); /* Thicker top border for emphasis */
        border-left: 1px solid var(--border-color, var(--border-color-fallback));
        border-right: 1px solid var(--border-color, var(--border-color-fallback));
        box-shadow: 0 -2px 5px rgba(0,0,0,0.05); /* Subtle shadow for depth */
    }
    div[data-testid="stRadio"] { /* Container for the radio buttons (tabs) */
        padding-bottom: 0px;
        border-bottom: 2px solid var(--app-accent-primary); /* Line under the tabs */
        margin-bottom: 15px; /* Space between tabs and content below */
    }
    div[data-testid="stRadio"] > label > div:first-child { display: none; } /* Hide the actual radio button dot */

    /* Transcript Viewer Specific Styles */
    .transcript-details-section { /* For indenting transcript details */
        margin-left: 20px;
        padding-left: 15px;
        border-left: 2px solid var(--app-accent-lightest); /* Subtle left border for indentation */
    }
    .transcript-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px; margin-bottom: 25px; color: var(--text-color);}
    .transcript-summary-item strong { color: var(--app-accent-primary); }
    .transcript-summary-item-fullwidth { /* For the Call Summary part */
        grid-column: 1 / -1; /* Make it span all columns in the grid */
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px dashed var(--app-accent-muted); /* Separator line above Call Summary */
    }
    .requirement-item { /* For individual checklist items */
        margin-bottom: 12px; padding: 10px; border-left: 4px solid var(--app-accent-muted);
        background-color: color-mix(in srgb, var(--secondary-background-color) 97%, var(--app-accent-lightest) 3%); /* Very subtle background tint */
        border-radius: 6px; color: var(--text-color);
    }
    .requirement-item .type { font-weight: 500; color: var(--app-accent-muted); opacity: 0.8; font-size: 0.85em; margin-left: 8px; }
    .transcript-container { /* Box for the full transcript text */
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 20px; border-radius: 10px; border: 1px solid var(--border-color, var(--border-color-fallback));
        max-height: 450px; overflow-y: auto; /* Allow scrolling if transcript is long */
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; /* Monospace font for readability */
        font-size: 0.95em; line-height: 1.7;
    }
    .transcript-line strong { color: var(--app-accent-primary); } /* Speaker names in transcript */

    /* Button styles */
    div[data-testid="stButton"] > button { /* General Streamlit buttons */
        background-color: var(--app-accent-primary);
        color: var(--app-text-on-accent);
        border: none; padding: 10px 20px; border-radius: 6px;
        font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }
    div[data-testid="stButton"] > button:hover {
        background-color: color-mix(in srgb, var(--app-accent-primary) 90%, #000000 10%); /* Darken slightly on hover */
        color: var(--app-text-on-accent); transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    div[data-testid="stDownloadButton"] > button { /* Specific style for download buttons */
        background-color: var(--app-dl-button-bg);
        color: var(--app-dl-button-text);
        border: none; padding: 10px 20px; border-radius: 6px;
        font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: var(--app-dl-button-hover-bg);
        color: var(--app-dl-button-text);
        transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }

    /* Sidebar styling */
    div[data-testid="stSidebarUserContent"] {
        background-color: var(--secondary-background-color);
        padding: 1.5em 1em; border-right: 1px solid var(--border-color, var(--border-color-fallback));
    }
    div[data-testid="stSidebarUserContent"] h2,
    div[data-testid="stSidebarUserContent"] h3 {
        color: var(--app-accent-highlight); /* Use highlight color for sidebar headers */
        border-bottom-color: var(--app-accent-secondary);
    }
    .footer { /* Footer style */
        font-size: 0.8em;
        color: var(--text-color);
        opacity: 0.7;
        text-align: center;
        padding: 20px 0;
        border-top: 1px solid var(--border-color, var(--border-color-fallback));
        margin-top: 40px;
    }
    .active-filters-summary { /* Style for the bar showing active filters */
        font-size: 0.9em;
        color: var(--text-color);
        opacity: 0.8;
        margin-top: 0px; /* Position right below tabs */
        margin-bottom: 25px; /* Space before main content */
        padding: 10px;
        background-color: var(--secondary-background-color);
        border-radius: 8px;
        border: 1px solid var(--border-color, var(--border-color-fallback));
        text-align: center;
    }
    .no-data-message { /* Style for messages when no data is available */
        text-align: center;
        padding: 20px;
        font-size: 1.1em;
        color: var(--text-color);
        opacity: 0.7;
    }
    """,
    "</style>"
]
# Join all CSS parts into a single string and render it using st.markdown.
# unsafe_allow_html=True is necessary to inject custom HTML/CSS.
css_style = "\n".join(css_parts)
st.markdown(css_style, unsafe_allow_html=True)


# --- Application Access Control ---
# This function checks if the user has entered the correct password.
def check_password():
    # Get password from Streamlit secrets (secure way to store sensitive info).
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.") # Optional hint for the password.

    # If no password is set in secrets, bypass the check (useful for local development).
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set. Bypassing password.")
        return True

    # Use session state to remember if the password has been entered correctly.
    # This prevents asking for the password on every page interaction.
    if "password_entered" not in st.session_state:
        st.session_state.password_entered = False # Initialize if not already set.

    if st.session_state.password_entered:
        return True # If already entered, allow access.

    # Create a form for password input. Forms group inputs and have a single submit button.
    # Using a unique key for the form to avoid conflicts if other forms exist.
    with st.form("password_form_main_app_v3_10"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint, key="pwd_input_main_app_v3_10")
        submitted = st.form_submit_button("Submit")

        if submitted: # If the submit button is clicked
            if password_attempt == app_password:
                st.session_state.password_entered = True # Mark password as correct
                st.rerun() # Rerun the script to show the main app content
            else:
                st.error("Incorrect Access Key.") # Show error if password is wrong
                return False
    return False # If form not submitted or password incorrect, deny access for now.

# If password check fails, stop the script execution.
if not check_password():
    st.stop()

# --- Constants & Helper Functions ---
# SCOPES define the level of access the app needs for Google APIs (Sheets and Drive).
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# KEY_REQUIREMENT_DETAILS: A dictionary defining the onboarding checklist items.
# Used for displaying descriptions, types, and chart labels.
KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and DIME Industries.", "type": "Secondary", "chart_label": "Intro Self & DIME"},
    'confirmKitReceived': {"description": "Confirm the reseller has received their onboarding kit and initial order.", "type": "Primary", "chart_label": "Kit & Order Received"},
    'offerDisplayHelp': {"description": "Ask whether they need help setting up the in-store display kit.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule a budtender-training session and the first promotional event.", "type": "Primary", "chart_label": "Schedule Training & Promo"},
    'providePromoCreditLink': {"description": "Provide the link for submitting future promo-credit reimbursement requests.", "type": "Secondary", "chart_label": "Provide Promo Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
# ORDERED_... lists define the display order for these requirements in different parts of the app.
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS

# Function to authenticate with Google Sheets using service account credentials.
# @st.cache_data decorator caches the result of this function, so it doesn't re-authenticate on every script run
# unless the input changes or TTL expires. ttl=600 means cache for 600 seconds (10 minutes).
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    gcp_secrets = st.secrets.get("gcp_service_account") # Get credentials from Streamlit secrets
    if gcp_secrets is None:
        print("Error: GCP secrets NOT FOUND.") # Log error for server-side debugging
        return None # Return None if secrets are missing
    # Check if secrets are structured correctly
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        print(f"Error: GCP secrets not structured correctly (type: {type(gcp_secrets)}).")
        return None
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [k for k in required_keys if gcp_secrets.get(k) is None]
    if missing:
        print(f"Error: GCP secrets missing keys: {', '.join(missing)}.")
        return None
    try:
        # Authorize gspread using the service account dictionary and defined scopes.
        return gspread.service_account_from_dict(dict(gcp_secrets), scopes=SCOPES)
    except Exception as e:
        print(f"Google Auth Error using service_account_from_dict: {e}")
        return None

# Function to convert various date string formats into datetime objects.
# This makes date handling more flexible if the Google Sheet has inconsistent date formats.
def robust_to_datetime(series):
    # First, try pandas' general to_datetime with error coercion.
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    # Define a list of common date formats to try if the general conversion fails for many entries.
    common_formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
                      '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    # If many dates are still NaT (Not a Time), try specific formats.
    if not series.empty and dates.isnull().sum() > len(series)*0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                # If this format results in more valid dates, update the main 'dates' series.
                if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                if dates.notnull().all(): break # Stop if all dates are successfully converted.
            except ValueError: continue # Ignore if a format causes an error and try the next.
    return dates

# Function to load data from the specified Google Sheet.
# Cached to avoid reloading data too frequently.
@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    gc = authenticate_gspread_cached() # Get authenticated gspread client.
    if gc is None: st.error("Google Sheets authentication failed. Cannot load data."); return pd.DataFrame()

    # Get sheet URL and worksheet name from Streamlit secrets.
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame()
    if not ws_name: st.error("Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame()

    try:
        # Open the Google Spreadsheet (by URL or by name).
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url)
        ws = ss.worksheet(ws_name) # Get the specific worksheet.
        data = ws.get_all_records(head=1, expected_headers=None) # Read all data into a list of dictionaries.
        if not data: st.warning("No data in sheet."); return pd.DataFrame()
        df_loaded_internal = pd.DataFrame(data) # Convert to a Pandas DataFrame.
        if df_loaded_internal.empty: st.warning("Empty DataFrame after load."); return pd.DataFrame()
        # Store the time of this successful data refresh in session state.
        st.session_state.last_data_refresh_time = datetime.now()
    except gspread.exceptions.SpreadsheetNotFound: st.error(f"Sheet Not Found: '{url}'. Check URL & permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: st.error(f"Worksheet Not Found: '{ws_name}'."); return pd.DataFrame()
    except Exception as e: st.error(f"Error Loading Data: {e}"); return pd.DataFrame()

    # Standardize column names from the sheet: strip whitespace, convert to lowercase, remove internal spaces.
    standardized_column_names = []
    for col in df_loaded_internal.columns:
        col_str = str(col).strip().lower() 
        col_str = "".join(col_str.split()) 
        standardized_column_names.append(col_str)
    df_loaded_internal.columns = standardized_column_names

    # Map these fully standardized sheet names to the camelCase names used internally in the code.
    column_name_map_to_code = {
        "licensenumber": "licenseNumber", "dcclicense": "licenseNumber", # Handles "dccLicense" from sample
        "storename": "storeName", "repname": "repName",
        "onboardingdate": "onboardingDate", "deliverydate": "deliveryDate",
        "confirmationtimestamp": "confirmationTimestamp", "clientsentiment": "clientSentiment",
        "fulltranscript": "fullTranscript", "score": "score", "status": "status", "summary": "summary"
    }
    # Add checklist item keys to the mapping (e.g., "introselfanddime" -> "introSelfAndDIME")
    for req_key_internal in KEY_REQUIREMENT_DETAILS.keys():
        std_req_key = req_key_internal.lower() # Standardize the key itself
        column_name_map_to_code[std_req_key] = req_key_internal

    cols_to_rename_standardized = {}
    current_df_columns = list(df_loaded_internal.columns) # Use a copy for iteration
    for std_sheet_col in current_df_columns: # Iterate over standardized names from the sheet
        if std_sheet_col in column_name_map_to_code:
            target_code_name = column_name_map_to_code[std_sheet_col]
            # Only rename if the standardized name is different from the target code name
            # AND the target code name isn't already a column (to avoid accidental overwrites if multiple sheet cols map to one target)
            # AND the target code name isn't already in the list of columns we plan to rename to (to avoid duplicate rename targets)
            if std_sheet_col != target_code_name and \
               target_code_name not in cols_to_rename_standardized.values() and \
               target_code_name not in current_df_columns: # Check against original current_df_columns before any renames
                 cols_to_rename_standardized[std_sheet_col] = target_code_name
    
    if cols_to_rename_standardized:
        df_loaded_internal.rename(columns=cols_to_rename_standardized, inplace=True)

    # Process date columns
    date_cols = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for col, new_col in date_cols.items():
        if col in df_loaded_internal: # Check if the standardized column name exists
            df_loaded_internal[new_col] = robust_to_datetime(df_loaded_internal[col].astype(str).str.replace('\n','',regex=False).str.strip())
        else: # If the column doesn't exist after standardization and mapping, create it as NaT
            df_loaded_internal[new_col] = pd.NaT 
        
        # Create 'onboarding_date_only' specifically from 'onboardingDate_dt'
        if col == 'onboardingDate':
            if new_col in df_loaded_internal and df_loaded_internal[new_col].notna().any():
                 df_loaded_internal['onboarding_date_only'] = df_loaded_internal[new_col].dt.date
            else: # If 'onboardingDate_dt' was not created or is all NaT
                 df_loaded_internal['onboarding_date_only'] = pd.NaT # Ensure the column exists as date type

    # Calculate 'days_to_confirmation'
    if 'deliveryDate_dt' in df_loaded_internal and 'confirmationTimestamp_dt' in df_loaded_internal:
        df_loaded_internal['deliveryDate_dt'] = pd.to_datetime(df_loaded_internal['deliveryDate_dt'], errors='coerce')
        df_loaded_internal['confirmationTimestamp_dt'] = pd.to_datetime(df_loaded_internal['confirmationTimestamp_dt'], errors='coerce')
        def to_utc(s): # Helper to convert to UTC, handling potential timezone issues
            if pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
                try: return s.dt.tz_localize('UTC') if s.dt.tz is None else s.dt.tz_convert('UTC')
                except Exception: return s # Return original if tz conversion fails
            return s # Return as is if not datetime or all NaT
        
        valid_dates_mask = df_loaded_internal['confirmationTimestamp_dt'].notna() & df_loaded_internal['deliveryDate_dt'].notna()
        df_loaded_internal['days_to_confirmation'] = pd.NA # Initialize column
        if valid_dates_mask.any(): # Calculate only for rows with valid dates
            df_loaded_internal.loc[valid_dates_mask, 'days_to_confirmation'] = \
                (to_utc(df_loaded_internal.loc[valid_dates_mask, 'confirmationTimestamp_dt']) - \
                 to_utc(df_loaded_internal.loc[valid_dates_mask, 'deliveryDate_dt'])).dt.days

    # Ensure other string and numeric columns exist and have correct types.
    str_cols_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary']
    for col in str_cols_ensure:
        if col not in df_loaded_internal.columns: df_loaded_internal[col] = ""
        else: df_loaded_internal[col] = df_loaded_internal[col].astype(str).fillna("")
    if 'score' not in df_loaded_internal.columns: df_loaded_internal['score'] = pd.NA
    else: df_loaded_internal['score'] = pd.to_numeric(df_loaded_internal['score'], errors='coerce')

    # Ensure checklist item columns exist.
    checklist_cols_to_ensure = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS + ['onboardingWelcome']
    for col in checklist_cols_to_ensure:
        if col not in df_loaded_internal.columns: df_loaded_internal[col] = pd.NA
        
    return df_loaded_internal

# Function to convert a DataFrame to CSV format for download.
@st.cache_data # Cache this conversion to avoid re-doing it unnecessarily.
def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8')

# Function to calculate key performance indicators (KPIs) from a DataFrame.
def calculate_metrics(df_in):
    if df_in.empty: return 0, 0.0, pd.NA, pd.NA # Return defaults if DataFrame is empty.
    total = len(df_in) # Total number of records.
    # Success rate: percentage of 'confirmed' statuses.
    sr = (df_in[df_in['status'].astype(str).str.lower()=='confirmed'].shape[0]/total*100) if total>0 else 0.0
    avg_s = pd.to_numeric(df_in['score'], errors='coerce').mean() # Average score.
    avg_d = pd.to_numeric(df_in['days_to_confirmation'], errors='coerce').mean() # Average days to confirmation.
    return total, sr, avg_s, avg_d

# Function to determine a default date range for filters (e.g., current month).
# Also finds the absolute min and max dates in the provided data series.
def get_default_date_range(series):
    today = date.today()
    s_default = today.replace(day=1) # Default start: first day of current month.
    e_default = today                # Default end: current day.
    min_d_data, max_d_data = None, None # Initialize min/max dates from data as None.

    if series is not None and not series.empty and series.notna().any():
        dates = pd.to_datetime(series, errors='coerce').dt.date.dropna() # Convert series to dates, drop invalid.
        if not dates.empty:
            min_d_data = dates.min()
            max_d_data = dates.max()
            # Adjust default start/end to be within the actual data range if necessary.
            s_final = max(s_default, min_d_data)
            e_final = min(e_default, max_d_data)
            # If calculated start is after end (e.g., MTD for future data), use full data range.
            if s_final > e_final: s_final, e_final = min_d_data, max_d_data
            return s_final, e_final, min_d_data, max_d_data
    # If no series or no valid dates, return system defaults and None for data min/max.
    return s_default, e_default, min_d_data, max_d_data


# --- Initialize Session State ---
# Session state stores variables that persist across user interactions and script reruns.
# Initialize default values for various state variables if they don't already exist.
default_s_init, default_e_init, initial_min_data_date, initial_max_data_date = get_default_date_range(None)

if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()

# Ensure 'date_range' is always a 2-tuple of date objects
if 'date_range' not in st.session_state or \
   not (isinstance(st.session_state.date_range, tuple) and \
        len(st.session_state.date_range) == 2 and \
        isinstance(st.session_state.date_range[0], date) and \
        isinstance(st.session_state.date_range[1], date)):
    st.session_state.date_range = (default_s_init, default_e_init)

if 'active_tab' not in st.session_state: st.session_state.active_tab = "🌌 Overview"
# Initialize filter lists and search terms.
for f_key in ['repName_filter', 'status_filter', 'clientSentiment_filter']:
    if f_key not in st.session_state: st.session_state[f_key] = []
for s_key_base in ['licenseNumber', 'storeName']:
    if f"{s_key_base}_search" not in st.session_state: st.session_state[f"{s_key_base}_search"] = ""
if 'selected_transcript_key' not in st.session_state: st.session_state.selected_transcript_key = None
if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = initial_min_data_date
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = initial_max_data_date
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False # Flag for date filter activity


# --- Data Loading Trigger ---
# Load data if it hasn't been loaded yet in this session.
if not st.session_state.data_loaded:
    df_from_load_func = load_data_from_google_sheet() # Call the data loading function.
    if not df_from_load_func.empty:
        st.session_state.df_original = df_from_load_func # Store loaded data in session state.
        st.session_state.data_loaded = True # Mark data as loaded.
        # Determine date range based on loaded data.
        ds,de,min_data_date,max_data_date = get_default_date_range(df_from_load_func.get('onboarding_date_only'))
        st.session_state.date_range = (ds,de) # Update session state date range.
        st.session_state.min_data_date_for_filter = min_data_date
        st.session_state.max_data_date_for_filter = max_data_date
        st.sidebar.success(f"Data loaded: {len(df_from_load_func)} records.")
    else: # If loading failed or returned empty.
        st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DataFrame.
        st.session_state.data_loaded = False
# Get the original DataFrame from session state for use in the app.
df_original = st.session_state.df_original

# --- Main Page Title ---
st.title("🌌 Onboarding Performance Dashboard 🌌")

# Display message and reload button if data loading failed.
if not st.session_state.data_loaded or df_original.empty:
    st.markdown("<div class='no-data-message'>🚧 No data loaded or data is empty. Check configurations or try refreshing. 🚧</div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Attempt Data Reload", key="refresh_fail_button_v3_10"):
        st.cache_data.clear(); st.session_state.data_loaded = False; st.rerun()

# --- Sidebar UI Elements ---
# Expander for score information.
with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=True):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)
st.sidebar.header("⚙️ Data Controls")
# Button to manually refresh data.
if st.sidebar.button("🔄 Refresh Data", key="refresh_main_button_v3_10"):
    st.cache_data.clear() # Clear all cached data.
    st.session_state.data_loaded = False # Reset loaded flag to trigger reload.
    st.rerun() # Rerun the script.
# Display last data refresh time.
if st.session_state.last_data_refresh_time:
    st.sidebar.caption(f"Last refreshed: {st.session_state.last_data_refresh_time.strftime('%b %d, %Y %I:%M %p')}")
else:
    st.sidebar.caption("Data not yet loaded.")

st.sidebar.header("🔍 Filters")

# --- Date Range Shortcuts ---
st.sidebar.markdown("##### Date Shortcuts")
s_col1, s_col2, s_col3 = st.sidebar.columns(3) # Arrange buttons in 3 columns.
today_for_shortcuts = date.today()

if s_col1.button("MTD", key="mtd_button_v3_10", use_container_width=True):
    start_mtd_shortcut = today_for_shortcuts.replace(day=1)
    st.session_state.date_range = (start_mtd_shortcut, today_for_shortcuts)
    st.session_state.date_filter_is_active = True # Mark date filter as active
    st.rerun()

if s_col2.button("YTD", key="ytd_button_v3_10", use_container_width=True):
    start_ytd_shortcut = today_for_shortcuts.replace(month=1, day=1)
    st.session_state.date_range = (start_ytd_shortcut, today_for_shortcuts)
    st.session_state.date_filter_is_active = True
    st.rerun()

if s_col3.button("ALL", key="all_button_v3_10", use_container_width=True):
    all_start_shortcut = st.session_state.get('min_data_date_for_filter')
    all_end_shortcut = st.session_state.get('max_data_date_for_filter')
    if all_start_shortcut and all_end_shortcut: # If min/max dates from data are available
        st.session_state.date_range = (all_start_shortcut, all_end_shortcut)
    else: # Fallback if no data extent is known (e.g., no data loaded yet)
        start_ytd_fallback_shortcut = today_for_shortcuts.replace(month=1, day=1)
        st.session_state.date_range = (start_ytd_fallback_shortcut, today_for_shortcuts)
        st.sidebar.caption("Used YTD for 'ALL' (no data extent).") # Inform user
    st.session_state.date_filter_is_active = True
    st.rerun()
st.sidebar.markdown("---") # Visual separator

# --- Manual Date Range Input ---
# Defensive check for st.session_state.date_range before unpacking
if not (isinstance(st.session_state.get('date_range'), tuple) and \
        len(st.session_state.date_range) == 2 and \
        isinstance(st.session_state.date_range[0], date) and \
        isinstance(st.session_state.date_range[1], date)):
    ds_init_filter, de_init_filter, _, _ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds_init_filter, de_init_filter)

current_session_start_dt, current_session_end_dt = st.session_state.date_range
min_dt_widget = st.session_state.get('min_data_date_for_filter')
max_dt_widget = st.session_state.get('max_data_date_for_filter')

# Prepare value for st.date_input, ensuring they are valid dates and start <= end
value_for_widget_start = current_session_start_dt
value_for_widget_end = current_session_end_dt

if min_dt_widget and value_for_widget_start < min_dt_widget: value_for_widget_start = min_dt_widget
if max_dt_widget and value_for_widget_end > max_dt_widget: value_for_widget_end = max_dt_widget
if value_for_widget_start > value_for_widget_end: value_for_widget_start = value_for_widget_end

sel_range = st.sidebar.date_input(
    "Date Range:", value=(value_for_widget_start, value_for_widget_end),
    min_value=min_dt_widget, max_value=max_dt_widget, key="date_sel_v3_10"
)
# st.date_input (range mode) returns a 2-tuple of date objects.
if isinstance(sel_range, tuple) and len(sel_range) == 2 and \
   isinstance(sel_range[0], date) and isinstance(sel_range[1], date):
    if sel_range != st.session_state.date_range: # If the user changed the date
        st.session_state.date_range = sel_range
        st.session_state.date_filter_is_active = True # Mark date filter as active
        st.rerun()
# Get the definitive start and end dates for filtering from session state.
start_dt, end_dt = st.session_state.date_range

# --- Text Search Filters ---
search_cols_definition = {"licenseNumber":"License Number", "storeName":"Store Name"}
for k,lbl in search_cols_definition.items():
    val = st.sidebar.text_input(f"Search {lbl}:",value=st.session_state[k+"_search"],key=f"{k}_widget_v3_10")
    if val != st.session_state[k+"_search"]: st.session_state[k+"_search"]=val; st.rerun()

# --- Category Multi-Select Filters ---
cat_filters_definition = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for k,lbl in cat_filters_definition.items():
    if not df_original.empty and k in df_original.columns and df_original[k].notna().any():
        opts = sorted([v for v in df_original[k].astype(str).dropna().unique() if v.strip()])
        sel = [v for v in st.session_state[k+"_filter"] if v in opts] # Ensure current selections are valid options
        new_sel = st.sidebar.multiselect(f"Filter by {lbl}:",opts,default=sel,key=f"{k}_widget_v3_10")
        if new_sel != st.session_state[k+"_filter"]: st.session_state[k+"_filter"]=new_sel; st.rerun()

# --- Clear All Filters Button ---
def clear_filters_cb(): # Callback function for the button
    ds_clear, de_clear, min_d_clear, max_d_clear = get_default_date_range(st.session_state.df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds_clear, de_clear)
    st.session_state.min_data_date_for_filter = min_d_clear
    st.session_state.max_data_date_for_filter = max_d_clear
    st.session_state.date_filter_is_active = False # Reset date filter active flag
    for k_search in search_cols_definition: st.session_state[k_search+"_search"]=""
    for k_cat in cat_filters_definition: st.session_state[k_cat+"_filter"]=[]
    st.session_state.selected_transcript_key = None
if st.sidebar.button("🧹 Clear All Filters",on_click=clear_filters_cb,use_container_width=True, key="clear_filters_v3_10"): st.rerun()


# --- Tab Navigation ---
tab_names = ["🌌 Overview", "📊 Analysis & Transcripts", "📈 Trends & Distributions"]
selected_tab = st.radio("Navigation:", tab_names, index=tab_names.index(st.session_state.active_tab),
                        horizontal=True, key="main_tab_selector_v3_10")
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()

# --- Active Filters Summary Display (below tabs) ---
other_active_filters_list = [] # For search terms and category filters
date_display_string = ""     # For the date part of the summary

# Construct the date display string if start_dt and end_dt are valid dates
if isinstance(start_dt, date) and isinstance(end_dt, date):
    min_data_for_summary = st.session_state.get('min_data_date_for_filter')
    max_data_for_summary = st.session_state.get('max_data_date_for_filter')
    
    is_all_data_range_and_active = False # Flag to check if "ALL" range is active
    if min_data_for_summary and max_data_for_summary and \
       start_dt == min_data_for_summary and end_dt == max_data_for_summary and \
       st.session_state.get('date_filter_is_active', False): # Check if "ALL" was explicitly selected
        is_all_data_range_and_active = True

    if is_all_data_range_and_active:
        date_display_string = "🗓️ Dates: ALL"
    else: # Otherwise, show the specific date range
        date_display_string = f"🗓️ Dates: {start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d, %Y')}"
else: # Fallback if dates are not properly set (should be rare with new logic)
    date_display_string = "🗓️ Dates: Range not set"

# Collect other active filters (search terms, category selections)
for k, lbl in search_cols_definition.items():
    if st.session_state[k+"_search"]:
        other_active_filters_list.append(f"{lbl}: '{st.session_state[k+'_search']}'")
for k, lbl in cat_filters_definition.items():
    if st.session_state[k+"_filter"]:
        other_active_filters_list.append(f"{lbl}: {', '.join(st.session_state[k+'_filter'])}")

# Construct the final summary message
if other_active_filters_list or st.session_state.get('date_filter_is_active', False):
    # If any text/category filters are active OR if the date filter was explicitly touched by the user
    final_summary_parts = [date_display_string] + other_active_filters_list
    summary_message = f"🔍 Active Filters: {'; '.join(final_summary_parts)}"
else:
    # This case means no user interaction with any filters yet (initial load state).
    summary_message = f"Showing data for: {date_display_string} (default range). No other filters active."

st.markdown(f"<div class='active-filters-summary'>{summary_message}</div>", unsafe_allow_html=True)


# --- Data Filtering Logic ---
# This section applies the selected filters to the original DataFrame (df_original)
# to create a filtered DataFrame (df_filtered) for display and analysis.
df_filtered = pd.DataFrame() # Initialize as empty
if not df_original.empty: # Proceed only if data has been loaded
    df_working = df_original.copy() # Work on a copy to preserve the original data.

    # Apply license number search filter
    license_search_term = st.session_state.get("licenseNumber_search", "")
    if license_search_term and "licenseNumber" in df_working.columns:
        df_working = df_working[df_working['licenseNumber'].astype(str).str.contains(license_search_term, case=False, na=False)]
    
    # Apply store name search filter
    store_search_term = st.session_state.get("storeName_search", "")
    if store_search_term and "storeName" in df_working.columns:
        df_working = df_working[df_working['storeName'].astype(str).str.contains(store_search_term, case=False, na=False)]
    
    # Apply date range filter (ensure start_dt and end_dt are valid date objects)
    if isinstance(start_dt, date) and isinstance(end_dt, date) and \
       'onboarding_date_only' in df_working.columns and df_working['onboarding_date_only'].notna().any():
        date_objects_for_filtering = pd.to_datetime(df_working['onboarding_date_only'], errors='coerce').dt.date
        valid_dates_mask = date_objects_for_filtering.notna()
        date_filter_mask = pd.Series([False] * len(df_working), index=df_working.index) # Default to False
        if valid_dates_mask.any(): # Apply filter only if there are valid dates to compare
             date_filter_mask[valid_dates_mask] = \
                (date_objects_for_filtering[valid_dates_mask] >= start_dt) & \
                (date_objects_for_filtering[valid_dates_mask] <= end_dt)
        df_working = df_working[date_filter_mask]
        
    # Apply category filters (Rep Name, Status, Client Sentiment)
    for col_name, _ in cat_filters_definition.items():
        selected_values = st.session_state.get(f"{col_name}_filter", [])
        if selected_values and col_name in df_working.columns: # If filter is set and column exists
            df_working = df_working[df_working[col_name].astype(str).isin(selected_values)]
    df_filtered = df_working.copy() # Final filtered DataFrame

# --- Plotly Base Layout Settings ---
# These settings are common to most Plotly charts in the dashboard.
plotly_base_layout_settings = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR, "title_x":0.5, # Centered title
    "xaxis_showgrid":False, "yaxis_showgrid":False, "margin": dict(l=40, r=20, t=60, b=40),
    "font_color": "var(--text-color)", # Use Streamlit's theme text color for chart fonts
    "title_font_color": "var(--app-accent-primary)", # Use our app's primary accent for chart titles
    "xaxis_title_font_color": "var(--text-color)", "yaxis_title_font_color": "var(--text-color)",
    "xaxis_tickfont_color": "var(--text-color)", "yaxis_tickfont_color": "var(--text-color)",
    "legend_font_color": "var(--text-color)",
}

# --- MTD (Month-to-Date) Metrics Calculation ---
# These metrics are always calculated based on the full, unfiltered df_original.
today_date_mtd = date.today(); mtd_s = today_date_mtd.replace(day=1) # MTD start and end
prev_mtd_e = mtd_s - timedelta(days=1); prev_mtd_s = prev_mtd_e.replace(day=1) # Previous MTD period
df_mtd, df_prev_mtd = pd.DataFrame(), pd.DataFrame() # Initialize empty DataFrames

if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_s_orig = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date
    valid_mask_orig = dates_s_orig.notna()
    if valid_mask_orig.any():
        df_valid_orig = df_original[valid_mask_orig].copy(); valid_dates_orig = dates_s_orig[valid_mask_orig]
        # Filter data for current MTD and previous MTD.
        mtd_mask_calc = (valid_dates_orig >= mtd_s) & (valid_dates_orig <= today_date_mtd)
        prev_mask_calc = (valid_dates_orig >= prev_mtd_s) & (valid_dates_orig <= prev_mtd_e)
        df_mtd = df_valid_orig[mtd_mask_calc.values]; df_prev_mtd = df_valid_orig[prev_mask_calc.values]
# Calculate MTD metrics using the helper function.
tot_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)
tot_prev,_,_,_ = calculate_metrics(df_prev_mtd) # Only need total for delta calculation
# Calculate delta (change) from previous MTD.
delta_mtd = tot_mtd - tot_prev if pd.notna(tot_mtd) and pd.notna(tot_prev) else None

# --- Display Content Based on Active Tab ---
if st.session_state.active_tab == "🌌 Overview":
    with st.container(): # Group MTD metrics
        st.header("📈 Month-to-Date (MTD) Overview")
        c1,c2,c3,c4 = st.columns(4) # Create 4 columns for metrics
        # Display each MTD metric with an icon and help tooltip.
        with c1: st.metric("🗓️ Onboardings MTD", tot_mtd or "0", f"{delta_mtd:+}" if delta_mtd is not None and pd.notna(delta_mtd) else "N/A", help="Total onboardings this month to date vs. previous month for the same period.")
        with c2: st.metric("✅ Success Rate MTD", f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A", help="Percentage of onboardings marked 'Confirmed' this month to date.")
        with c3: st.metric("⭐ Avg Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A", help="Average onboarding score (0-10) this month to date.")
        with c4: st.metric("⏳ Avg Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A", help="Average number of days from delivery to confirmation for onboardings confirmed this month to date.")
    
    with st.container(): # Group Filtered Data Overview metrics
        st.header("📊 Filtered Data Overview")
        if not df_filtered.empty: # If there's data after filtering
            tot_filt, sr_filt, score_filt, days_filt = calculate_metrics(df_filtered)
            fc1,fc2,fc3,fc4 = st.columns(4)
            with fc1: st.metric("📄 Filtered Onboardings", tot_filt or "0")
            with fc2: st.metric("🎯 Filtered Success Rate", f"{sr_filt:.1f}%" if pd.notna(sr_filt) else "N/A")
            with fc3: st.metric("🌟 Filtered Avg Score", f"{score_filt:.2f}" if pd.notna(score_filt) else "N/A")
            with fc4: st.metric("⏱️ Filtered Avg Days Confirm", f"{days_filt:.1f}" if pd.notna(days_filt) else "N/A")
        else: # If no data matches filters
            st.markdown("<div class='no-data-message'>🤷 No data matches current filters for Overview. Try adjusting your selections! 🤷</div>", unsafe_allow_html=True)

elif st.session_state.active_tab == "📊 Analysis & Transcripts":
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table = df_filtered.copy().reset_index(drop=True) # Use filtered data, reset index for display
    
    # Define which columns to try displaying in the table and their order.
    cols_to_try = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score',
                   'clientSentiment', 'days_to_confirmation'] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
    # Select only columns that actually exist in the DataFrame.
    cols_for_display = [col for col in cols_to_try if col in df_display_table.columns]
    # Add any other remaining columns, excluding helper/internal columns.
    other_cols = [col for col in df_display_table.columns if col not in cols_for_display and
                  not col.endswith(('_utc', '_str_original', '_dt')) and col not in ['fullTranscript', 'summary', 'onboarding_date_only']]
    cols_for_display = list(dict.fromkeys(cols_for_display + other_cols)) # Ensure unique columns, preserve order

    if not df_display_table.empty:
        # Function to style the DataFrame table (e.g., add in-cell bar charts).
        def style_table_with_bars(df):
            styled_df = df.style # Get a Styler object.
            if 'score' in df.columns: # If 'score' column exists
                # Add a bar chart to the 'score' column.
                styled_df = styled_df.bar(subset=['score'], align='mid', color=[ACTIVE_ACCENT_MUTED, ACTIVE_ACCENT_SECONDARY], vmin=0, vmax=10)
            if 'days_to_confirmation' in df.columns: # If 'days_to_confirmation' exists
                df_numeric_days = pd.to_numeric(df['days_to_confirmation'], errors='coerce')
                min_days = df_numeric_days.min() if df_numeric_days.notna().any() else 0
                max_days = df_numeric_days.max() if df_numeric_days.notna().any() else 30 # Sensible default max
                # Add a bar chart to this column.
                styled_df = styled_df.bar(subset=['days_to_confirmation'], align='zero', color=ACTIVE_ACCENT_HIGHLIGHT, vmin=min_days, vmax=max_days)
            return styled_df
        # Display the styled DataFrame.
        st.dataframe(style_table_with_bars(df_display_table[cols_for_display]), use_container_width=True, height=350)
        st.markdown("---") # Visual separator
        st.subheader("🔍 View Full Onboarding Details & Transcript")

        if not df_display_table.empty and 'fullTranscript' in df_display_table.columns:
            # Create options for the selectbox from the displayed table.
            transcript_options = { f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_table.iterrows() }
            if transcript_options:
                current_selection = st.session_state.selected_transcript_key
                options_list = [None] + list(transcript_options.keys()) # Add a "None" option.
                try: current_index = options_list.index(current_selection) # Find index of current selection.
                except ValueError: current_index = 0 # Default to first option if not found.

                selected_key_display = st.selectbox("Select onboarding to view details:", options=options_list,
                                                    index=current_index, format_func=lambda x: "Choose an entry..." if x is None else x,
                                                    key="transcript_selector_v3_10") # Unique key for the widget.
                # If selection changes, update session state and rerun to reflect the change.
                if selected_key_display != st.session_state.selected_transcript_key :
                    st.session_state.selected_transcript_key = selected_key_display
                    st.rerun()

                if st.session_state.selected_transcript_key : # If an onboarding is selected
                    selected_idx = transcript_options[st.session_state.selected_transcript_key]
                    selected_row = df_display_table.loc[selected_idx] # Get the selected row data.
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html_parts = [] # Build HTML for summary items.
                    summary_items = {
                        "Store": selected_row.get('storeName', 'N/A'), "Rep": selected_row.get('repName', 'N/A'),
                        "Score": selected_row.get('score', 'N/A'), "Status": selected_row.get('status', 'N/A'),
                        "Sentiment": selected_row.get('clientSentiment', 'N/A')
                    }
                    for item_label, item_value in summary_items.items():
                        summary_html_parts.append(f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>")
                    
                    data_summary_text = selected_row.get('summary', 'N/A')
                    # Add Call Summary at the end of the grid.
                    summary_html_parts.append(f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary:</strong> {data_summary_text}</div>")
                    
                    st.markdown("<div class='transcript-summary-grid'>" + "".join(summary_html_parts) + "</div>", unsafe_allow_html=True)

                    # Indented section for Key Requirements and Full Transcript
                    st.markdown("<div class='transcript-details-section'>", unsafe_allow_html=True)
                    st.markdown("##### Key Requirement Checks:")
                    for item_column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                        details = KEY_REQUIREMENT_DETAILS.get(item_column_name)
                        if details:
                            desc = details.get("description", item_column_name.replace('_',' ').title()); item_type = details.get("type", "")
                            val_str = str(selected_row.get(item_column_name, "")).lower(); met = val_str in ['true', '1', 'yes']
                            emoji = "✅" if met else "❌"; type_tag = f"<span class='type'>[{item_type}]</span>" if item_type else ""
                            st.markdown(f"<div class='requirement-item'>{emoji} {desc} {type_tag}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---", help="Separator before full transcript") # help text for Streamlit UI
                    st.markdown("##### Full Transcript:")
                    content = selected_row.get('fullTranscript', "")
                    if content:
                        html_transcript = "<div class='transcript-container'>"
                        for line in content.replace('\\n', '\n').split('\n'): # Handle escaped newlines
                            line = line.strip();
                            if not line: continue
                            parts = line.split(":", 1); speaker = f"<strong>{parts[0].strip()}:</strong>" if len(parts) == 2 else ""
                            msg = parts[1].strip().replace('\n', '<br>') if len(parts) == 2 else line.replace('\n', '<br>')
                            html_transcript += f"<p class='transcript-line'>{speaker} {msg}</p>"
                        st.markdown(html_transcript + "</div>", unsafe_allow_html=True)
                    else: st.info("No transcript available or empty.")
                    st.markdown("</div>", unsafe_allow_html=True) # Close transcript-details-section

            else: st.markdown("<div class='no-data-message'>📋 No entries in the filtered table to select for details. 📋</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>📜 No data in table for transcript viewer, or 'fullTranscript' column missing. 📜</div>", unsafe_allow_html=True)
        st.markdown("---")
        csv_data = convert_df_to_csv(df_filtered) # Get CSV data for download.
        st.download_button("📥 Download Filtered Data", csv_data, 'filtered_data.csv', 'text/csv', use_container_width=True, key="download_csv_v3_10")
    elif not df_original.empty: st.markdown("<div class='no-data-message'>📊 No data matches current filters for table display. Try different filter settings! 📊</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>💾 No data loaded to display. Please check data source or refresh. 💾</div>", unsafe_allow_html=True)


    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        c1_charts, c2_charts = st.columns(2) # Layout charts in two columns.
        with c1_charts:
            # Onboarding Status Distribution Chart
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_counts = df_filtered['status'].value_counts().reset_index()
                status_fig = px.bar(status_counts, x='status', y='count', color='status', title="Onboarding Status Distribution",
                                     color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ) # Use theme-aware colors
                status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>📉 Status data unavailable for chart. 📉</div>", unsafe_allow_html=True)

            # Onboardings by Representative Chart
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_counts = df_filtered['repName'].value_counts().reset_index()
                rep_fig = px.bar(rep_counts, x='repName', y='count', color='repName', title="Onboardings by Representative",
                                     color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ) # Use theme-aware colors
                rep_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>👥 Rep data unavailable for chart. 👥</div>", unsafe_allow_html=True)

        with c2_charts:
            # Client Sentiment Breakdown Chart
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sent_counts = df_filtered['clientSentiment'].value_counts().reset_index()
                current_sentiment_map = { # Map sentiment values to theme-aware colors
                    s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), ACTIVE_ACCENT_MUTED)
                    for s in sent_counts['clientSentiment'].unique()
                }
                sent_fig = px.pie(sent_counts, names='clientSentiment', values='count', hole=0.5, title="Client Sentiment Breakdown",
                                  color='clientSentiment', color_discrete_map=current_sentiment_map)
                sent_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(sent_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>😊 Sentiment data unavailable for chart. 😊</div>", unsafe_allow_html=True)

            # Key Requirement Completion Chart
            df_conf_chart = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed'] # Use only confirmed onboardings
            actual_key_cols_for_chart = [col for col in ORDERED_CHART_REQUIREMENTS if col in df_conf_chart.columns]
            if not df_conf_chart.empty and actual_key_cols_for_chart:
                checklist_data_for_chart = []
                for item_col_name_for_chart in actual_key_cols_for_chart:
                    item_details_obj = KEY_REQUIREMENT_DETAILS.get(item_col_name_for_chart)
                    chart_label_for_bar = item_details_obj.get("chart_label", item_col_name_for_chart.replace('_',' ').title()) if item_details_obj else item_col_name_for_chart.replace('_',' ').title()
                    map_bool_for_chart = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False} # Map string booleans
                    if item_col_name_for_chart in df_conf_chart.columns:
                        bool_series_for_chart = df_conf_chart[item_col_name_for_chart].astype(str).str.lower().map(map_bool_for_chart)
                        bool_series_for_chart = pd.to_numeric(bool_series_for_chart, errors='coerce')
                        if bool_series_for_chart.notna().any():
                            true_count_for_chart = bool_series_for_chart.sum()
                            total_valid_for_chart = bool_series_for_chart.notna().sum()
                            if total_valid_for_chart > 0:
                                checklist_data_for_chart.append({"Key Requirement": chart_label_for_bar, "Completion (%)": (true_count_for_chart/total_valid_for_chart)*100})
                if checklist_data_for_chart:
                    df_checklist_bar_chart = pd.DataFrame(checklist_data_for_chart)
                    if not df_checklist_bar_chart.empty:
                        checklist_bar_fig = px.bar(df_checklist_bar_chart.sort_values("Completion (%)",ascending=True),
                                                     x="Completion (%)", y="Key Requirement", orientation='h',
                                                     title="Key Requirement Completion (Confirmed Onboardings)",
                                                     color_discrete_sequence=[ACTIVE_ACCENT_PRIMARY]) # Use single theme accent color
                        checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(checklist_bar_fig, use_container_width=True)
                    else: st.markdown("<div class='no-data-message'>📊 No data for key requirement chart (confirmed). 📊</div>", unsafe_allow_html=True)
                else: st.markdown("<div class='no-data-message'>📊 No data for key requirement chart (confirmed). 📊</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='no-data-message'>✅ No 'confirmed' onboardings or checklist columns for requirement chart. ✅</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>🖼️ No data matches current filters for detailed visuals. 🖼️</div>", unsafe_allow_html=True)


elif st.session_state.active_tab == "📈 Trends & Distributions":
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        # Onboardings Over Time Chart
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_for_tab3 = df_filtered.copy()
            df_trend_for_tab3['onboarding_date_only'] = pd.to_datetime(df_trend_for_tab3['onboarding_date_only'], errors='coerce')
            df_trend_for_tab3.dropna(subset=['onboarding_date_only'], inplace=True)
            if not df_trend_for_tab3.empty:
                span_for_trend_tab3 = (df_trend_for_tab3['onboarding_date_only'].max() - df_trend_for_tab3['onboarding_date_only'].min()).days
                # Determine resampling frequency based on data span (Day, Week, Month)
                freq_for_trend_tab3 = 'D' if span_for_trend_tab3 <= 62 else ('W-MON' if span_for_trend_tab3 <= 365*1.5 else 'ME')
                data_for_trend_tab3 = df_trend_for_tab3.set_index('onboarding_date_only').resample(freq_for_trend_tab3).size().reset_index(name='count')
                if not data_for_trend_tab3.empty:
                    fig_for_trend_tab3 = px.line(data_for_trend_tab3, x='onboarding_date_only', y='count', markers=True,
                                      title="Onboardings Over Filtered Period", color_discrete_sequence=[ACTIVE_ACCENT_HIGHLIGHT]) # Theme-aware color
                    fig_for_trend_tab3.update_layout(plotly_base_layout_settings)
                    st.plotly_chart(fig_for_trend_tab3, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📈 Not enough data for trend plot after resampling. 📈</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='no-data-message'>📅 No valid date data for trend chart after processing. 📅</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>🗓️ Date column missing for trend chart. 🗓️</div>", unsafe_allow_html=True)

        # Days to Confirmation Distribution Chart
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist_tab3 = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist_tab3.empty:
                nbins_for_hist_tab3 = max(10, min(50, int(len(days_data_for_hist_tab3)/5))) if len(days_data_for_hist_tab3) > 20 else (len(days_data_for_hist_tab3.unique()) or 10)
                fig_days_dist_hist_tab3 = px.histogram(days_data_for_hist_tab3, nbins=nbins_for_hist_tab3,
                                           title="Days to Confirmation Distribution", color_discrete_sequence=[ACTIVE_ACCENT_SECONDARY]) # Theme-aware color
                fig_days_dist_hist_tab3.update_layout(plotly_base_layout_settings)
                st.plotly_chart(fig_days_dist_hist_tab3, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>⏳ No valid 'Days to Confirmation' data for distribution plot. ⏳</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' column missing for distribution plot. ⏱️</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>📉 No data matches current filters for Trends & Distributions. 📉</div>", unsafe_allow_html=True)

# --- Footer ---
st.markdown("---") # Visual separator
st.markdown(
    f"<div class='footer'>Onboarding Performance Dashboard v3.11 © {datetime.now().year} Nexus Workflow. All Rights Reserved.</div>",
    unsafe_allow_html=True
)

st.sidebar.markdown("---")
# Robustly display theme mode in sidebar info, or just version if theme is unknown
theme_display_name = THEME.capitalize() if isinstance(THEME, str) and THEME else ""
info_string = f"App Version: 3.11"
if theme_display_name: # Only add theme if known
    info_string += f" ({theme_display_name} Mode)"
st.sidebar.info(info_string)
