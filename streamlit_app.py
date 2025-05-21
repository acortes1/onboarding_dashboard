# acortes1/onboarding_dashboard/onboarding_dashboard-main/streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials # Keep this import
import time
import numpy as np
import re
from dateutil import tz # For PST conversion

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Dashboard v4.1", # Updated Version
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS Injection ---
def load_custom_css():
    """Loads and injects custom CSS for the application."""
    css = """
    <style>
        /* --- General Styles & Resets --- */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Modern sans-serif font */
        }

        /* --- Font & Spacing --- */
        .stApp {
            /* Streamlit's theme variables will handle background and text color */
        }

        h1, h2, h3, h4, h5, h6 {
            font-weight: 600; /* Bolder headings */
            color: var(--primary-color); /* Use Streamlit's primary color for main headings */
        }

        h1 {
            text-align: center;
            padding-top: 0.5em;
            padding-bottom: 0.5em;
            font-size: 2.2rem; /* Slightly larger main title */
            letter-spacing: 1px;
            border-bottom: 2px solid var(--primary-color);
            margin-bottom: 1em;
        }

        h2 {
            font-size: 1.8rem;
            margin-top: 1.8em;
            margin-bottom: 1em;
            padding-bottom: 0.3em;
            border-bottom: 1px solid var(--border-color);
        }

        h3 {
            font-size: 1.5rem;
            margin-top: 1.5em;
            margin-bottom: 0.8em;
        }

        h5 { /* Used for sidebar section titles in original code */
            color: var(--text-color);
            opacity: 0.9;
            margin-top: 1.5em;
            margin-bottom: 0.7em;
            font-weight: 500;
            letter-spacing: 0.2px;
            font-size: 1.1rem;
        }


        /* --- Card Styling for Metrics --- */
        div[data-testid="stMetric"], .metric-card {
            background-color: var(--secondary-background-color);
            padding: 1.2em 1.5em; /* Adjusted padding */
            border-radius: 12px; /* More rounded corners */
            border: 1px solid var(--border-color);
            box-shadow: 0 6px 12px rgba(0,0,0,0.08); /* Softer, more modern shadow */
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            margin-bottom: 1em; /* Add some space between metric cards */
        }

        div[data-testid="stMetric"]:hover, .metric-card:hover {
            transform: translateY(-5px); /* Slightly more lift on hover */
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }

        div[data-testid="stMetricLabel"] > div { /* Metric Label */
            color: var(--text-color);
            opacity: 0.75; /* Slightly more visible */
            font-weight: 500;
            font-size: 0.9rem; /* Adjusted size */
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-bottom: 0.3em; /* Space between label and value */
        }

        div[data-testid="stMetricValue"] > div { /* Metric Value */
            color: var(--text-color);
            font-size: 2.4rem !important; /* Larger metric value */
            font-weight: 700;
            line-height: 1.2;
        }

        div[data-testid="stMetricDelta"] > div { /* Metric Delta */
            color: var(--text-color);
            opacity: 0.7;
            font-weight: 500;
            font-size: 0.9rem;
        }

        /* --- Sidebar Styling --- */
        div[data-testid="stSidebarUserContent"] {
            padding: 1.5em 1.2em; /* Adjusted padding */
            background-color: var(--secondary-background-color);
        }
        div[data-testid="stSidebarUserContent"] h2,
        div[data-testid="stSidebarUserContent"] h3 {
             color: var(--primary-color); /* Consistent heading color */
             border-bottom-color: var(--border-color);
        }
         div[data-testid="stSidebarNavItems"] { /* Sidebar Navigation */
            padding-top: 1em;
        }


        /* --- Button Styling --- */
        div[data-testid="stButton"] > button {
            background-color: var(--primary-color);
            color: white; /* Ensuring contrast */
            border: none;
            padding: 10px 22px; /* Slightly larger padding */
            border-radius: 8px; /* Consistent rounded corners */
            font-weight: 600;
            transition: background-color 0.25s ease, transform 0.15s ease, box-shadow 0.25s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.07);
        }

        div[data-testid="stButton"] > button:hover {
            /* Darken primary color on hover - using a general approach */
            background-color: color-mix(in srgb, var(--primary-color) 85%, black);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        div[data-testid="stButton"] > button:active {
            transform: translateY(0px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.07);
        }


        div[data-testid="stDownloadButton"] > button {
            background-color: var(--secondary-background-color);
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
            padding: 9px 20px;
            border-radius: 8px;
            font-weight: 600;
            transition: background-color 0.25s ease, color 0.25s ease, transform 0.15s ease;
        }

        div[data-testid="stDownloadButton"] > button:hover {
            background-color: var(--primary-color);
            color: white;
            transform: translateY(-2px);
        }

        /* --- Expander Styling --- */
        .streamlit-expanderHeader {
            color: var(--text-color) !important; /* Use default text color for better theme adaptability */
            font-weight: 600;
            font-size: 1.05em;
            padding: 0.8em 0.5em; /* Adjust padding */
        }
        .streamlit-expander {
            border: 1px solid var(--border-color);
            background-color: var(--background-color); /* Match app background for cleaner look */
            border-radius: 10px;
            margin-bottom: 1em; /* Space below expanders */
        }
         .streamlit-expander > div > div > p {
            color: var(--text-color);
        }


        /* --- Dataframe and Table Styling --- */
        .stDataFrame { /* Main container for st.dataframe */
            border: 1px solid var(--border-color);
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            overflow: hidden; /* Ensures border radius is respected by inner table */
        }
        /* More specific styling might be needed if default dataframe styles clash */


        /* --- Tab (Radio Button) Styling --- */
        div[data-testid="stRadio"] label { /* Individual radio button label */
            padding: 10px 20px;
            margin: 0 4px;
            border-radius: 8px 8px 0 0; /* Rounded top corners */
            border: 1px solid transparent;
            border-bottom: none;
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            opacity: 0.7;
            transition: all 0.3s ease;
            font-weight: 500;
            font-size: 1rem;
        }

        div[data-testid="stRadio"] input:checked + div label { /* Selected radio button label */
            background-color: var(--background-color); /* Match page background */
            color: var(--primary-color);
            font-weight: 600;
            opacity: 1.0;
            border-top: 3px solid var(--primary-color);
            border-left: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            box-shadow: 0 -3px 6px rgba(0,0,0,0.04);
        }

        div[data-testid="stRadio"] { /* Container for radio buttons */
            padding-bottom: 0px;
            border-bottom: 2px solid var(--primary-color);
            margin-bottom: 20px;
        }
        div[data-testid="stRadio"] > label > div:first-child { /* Hide the actual radio input circle */
            display: none;
        }

        /* --- Transcript and Details Section Styling --- */
        .transcript-details-section {
            margin-left: 15px; /* Reduced margin */
            padding-left: 15px;
            border-left: 3px solid var(--primary-color); /* Thicker, primary color border */
            margin-top: 1em;
        }

        .transcript-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* Responsive columns */
            gap: 1em; /* Consistent gap */
            margin-bottom: 1.5em;
            color: var(--text-color);
        }
        .transcript-summary-item {
            background-color: var(--secondary-background-color);
            padding: 0.8em 1em;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .transcript-summary-item strong {
            color: var(--primary-color);
            font-weight: 600; /* Bolder emphasis */
        }
        .transcript-summary-item-fullwidth {
            grid-column: 1 / -1; /* Span full width */
            margin-top: 1em;
            padding-top: 1em;
            border-top: 1px dashed var(--border-color); /* Softer separator */
        }

        .requirement-item {
            margin-bottom: 0.8em; /* Spacing between items */
            padding: 0.8em 1em;
            border-left: 4px solid var(--primary-color); /* Primary color accent */
            background-color: var(--secondary-background-color);
            border-radius: 6px;
            color: var(--text-color);
            font-size: 0.95rem; /* Slightly larger text */
        }
        .requirement-item .type {
            font-weight: 500;
            color: var(--text-color);
            opacity: 0.7;
            font-size: 0.8em;
            margin-left: 8px;
            background-color: var(--background-color); /* Ensure readability */
            padding: 2px 6px;
            border-radius: 4px;
        }

        .transcript-container {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 1.5em; /* More padding */
            border-radius: 10px;
            border: 1px solid var(--border-color);
            max-height: 500px; /* Increased height */
            overflow-y: auto;
            font-family: 'Consolas', 'Monaco', 'Menlo', monospace; /* Monospaced font for transcripts */
            font-size: 0.9rem; /* Slightly smaller for density */
            line-height: 1.6; /* Better readability */
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.03); /* Inner shadow */
        }
        .transcript-line strong { /* Speaker name */
            color: var(--primary-color);
            font-weight: 600;
        }

        /* --- Footer --- */
        .footer {
            font-size: 0.85em; /* Slightly larger footer text */
            color: var(--text-color);
            opacity: 0.65; /* More subtle */
            text-align: center;
            padding: 25px 0;
            border-top: 1px solid var(--border-color);
            margin-top: 50px; /* More space before footer */
        }

        /* --- Active Filters Summary --- */
        .active-filters-summary {
            font-size: 0.9rem;
            color: var(--text-color);
            opacity: 0.85;
            margin-top: 0px;
            margin-bottom: 1.8em; /* More space below */
            padding: 0.8em 1.2em; /* Adjust padding */
            background-color: var(--secondary-background-color);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }

        /* --- No Data Message --- */
        .no-data-message {
            text-align: center;
            padding: 25px; /* More padding */
            font-size: 1.1rem;
            color: var(--text-color);
            opacity: 0.7;
            background-color: var(--secondary-background-color);
            border-radius: 8px;
            border: 1px dashed var(--border-color); /* Dashed border for distinction */
            margin-top: 1em;
        }

        /* --- Input Field Styling (General) --- */
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stSelectbox"] div[role="combobox"],
        div[data-testid="stMultiSelect"] div[role="combobox"] {
            border-radius: 6px !important; /* More consistent border radius */
            border: 1px solid var(--border-color) !important;
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        div[data-testid="stSelectbox"] div[role="combobox"]:focus-within,
        div[data-testid="stMultiSelect"] div[role="combobox"]:focus-within {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 20%, transparent) !important;
        }


        /* --- Dialog Styling --- */
        div[data-testid="stModal"] > div { /* Modal main content area */
            border-radius: 12px !important; /* Rounded corners for dialog */
            box-shadow: 0 8px 24px rgba(0,0,0,0.15) !important;
        }
        div[data-testid="stModalHeader"] {
            font-size: 1.4rem;
            color: var(--primary-color);
            padding-bottom: 0.7em;
            border-bottom: 1px solid var(--border-color);
        }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_custom_css()


# --- Password Protection ---
def check_password():
    """Checks if the user has entered the correct password."""
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")

    if app_password is None:
        st.sidebar.warning("🔑 APP_ACCESS_KEY not set. Access granted (dev mode).")
        return True

    if "password_entered" not in st.session_state:
        st.session_state.password_entered = False

    if st.session_state.password_entered:
        return True

    st.title("🔐 Secure Access Required")
    st.markdown("---")
    col1, col2 = st.columns([1,2])

    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2921/2921032.png", width=150)
    with col2:
        with st.form("password_form_main_app_v4_1"): # Changed key for v4.1
            st.markdown("#### Enter Access Key")
            password_attempt = st.text_input(
                "Access Key:",
                type="password",
                help=app_hint,
                key="pwd_input_main_app_v4_1", # Changed key
                placeholder="Enter your key here"
            )
            submitted = st.form_submit_button("🔓 Unlock Dashboard")

            if submitted:
                if password_attempt == app_password:
                    st.session_state.password_entered = True
                    st.rerun()
                else:
                    st.error("🚫 Incorrect Access Key. Please try again.")
                    return False
    return False

if not check_password():
    st.stop()

# --- Constants & Configuration ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and DIME Industries.", "type": "Secondary", "chart_label": "Intro Self & DIME"},
    'confirmKitReceived': {"description": "Confirm the reseller has received their onboarding kit and initial order.", "type": "Primary", "chart_label": "Kit & Order Received"},
    'offerDisplayHelp': {"description": "Ask whether they need help setting up the in-store display kit.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule a budtender-training session and the first promotional event.", "type": "Primary", "chart_label": "Schedule Training & Promo"},
    'providePromoCreditLink': {"description": "Provide the link for submitting future promo-credit reimbursement requests.", "type": "Secondary", "chart_label": "Provide Promo Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS

PST_TIMEZONE = tz.gettz('America/Los_Angeles')
UTC_TIMEZONE = tz.tzutc()

# --- Plotly Configuration ---
THEME = st.get_option("theme.base")
PLOT_BG_COLOR = "rgba(0,0,0,0)"

if THEME == "light":
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7' }
    TEXT_COLOR_FOR_PLOTLY = "#262730"
    PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
else:
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D' }
    TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"
    PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"

plotly_base_layout_settings = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":True,
    "yaxis_gridcolor": 'rgba(128,128,128,0.2)',
    "margin": dict(l=50, r=30, t=70, b=50),
    "font_color": TEXT_COLOR_FOR_PLOTLY, "title_font_color": PRIMARY_COLOR_FOR_PLOTLY,
    "title_font_size": 18, "xaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY,
    "yaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "xaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY,
    "yaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "legend_font_color": TEXT_COLOR_FOR_PLOTLY,
    "legend_title_font_color": PRIMARY_COLOR_FOR_PLOTLY,
}


# --- Authentication & Data Loading ---
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    """Authenticates with Google Sheets API using secrets."""
    gcp_secrets_obj = st.secrets.get("gcp_service_account") # This might be AttrDict

    if gcp_secrets_obj is None:
        st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND in Streamlit secrets.")
        return None

    # Convert AttrDict to a standard dict if necessary
    # The error occurs because from_service_account_info expects a dict.
    if not isinstance(gcp_secrets_obj, dict):
        try:
            # Attempt to convert to dict. This is the key fix.
            gcp_secrets_dict = dict(gcp_secrets_obj)
        except (TypeError, ValueError) as e:
            st.error(f"🚨 Error: Could not convert GCP secrets to a dictionary. Type was {type(gcp_secrets_obj)}. Error: {e}")
            return None
    else:
        gcp_secrets_dict = gcp_secrets_obj


    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_keys = [k for k in required_keys if gcp_secrets_dict.get(k) is None]
    if missing_keys:
        st.error(f"🚨 Error: GCP secrets dictionary missing keys: {', '.join(missing_keys)}.")
        return None

    try:
        # Use the gcp_secrets_dict which is confirmed or converted to a dict
        creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🔑 Google Authentication Error using from_service_account_info: {e}. Please check your GCP service account credentials and API permissions.")
        return None

def robust_to_datetime(series):
    """Converts a Pandas Series to datetime objects with robust parsing."""
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null', 'na']).all():
        common_formats = [
            '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'
        ]
        for dayfirst_setting in [False, True]:
            for fmt in common_formats:
                try:
                    use_dayfirst_for_fmt = ('%m' in fmt and '%d' in fmt and dayfirst_setting)
                    temp_dates = pd.to_datetime(series, format=fmt, errors='coerce', dayfirst=use_dayfirst_for_fmt)
                    if temp_dates.notnull().sum() > dates.notnull().sum():
                        dates = temp_dates
                    if dates.notnull().all(): break
                except ValueError:
                    continue
            if dates.notnull().all(): break
    return dates

def format_datetime_to_pst_str(dt_series):
    """Formats a datetime Series to a PST string if it's a datetime type."""
    if not pd.api.types.is_datetime64_any_dtype(dt_series) or dt_series.isnull().all():
        return dt_series

    def convert_element_to_pst(element):
        if pd.isna(element): return None
        try:
            if element.tzinfo is None: aware_element = element.replace(tzinfo=UTC_TIMEZONE)
            else: aware_element = element.astimezone(UTC_TIMEZONE)
            pst_element = aware_element.astimezone(PST_TIMEZONE)
            return pst_element.strftime('%Y-%m-%d %I:%M %p PST')
        except Exception: return str(element)

    try:
        if dt_series.dt.tz is None: utc_series = dt_series.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
        else: utc_series = dt_series.dt.tz_convert(UTC_TIMEZONE)
        pst_series = utc_series.dt.tz_convert(PST_TIMEZONE)
        return pst_series.apply(lambda x: x.strftime('%Y-%m-%d %I:%M %p PST') if pd.notnull(x) else None)
    except AttributeError: return dt_series.apply(convert_element_to_pst)
    except Exception: return dt_series.apply(convert_element_to_pst)


def format_phone_number(number_str):
    """Formats a string of digits into a standard phone number format."""
    if pd.isna(number_str) or str(number_str).strip() == "": return ""
    digits = re.sub(r'\D', '', str(number_str))
    if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(number_str)

def capitalize_name(name_str):
    """Capitalizes each word in a name string."""
    if pd.isna(name_str) or str(name_str).strip() == "": return ""
    return ' '.join(word.capitalize() for word in str(name_str).split())


@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet():
    """Loads and processes data from the configured Google Sheet."""
    gc = authenticate_gspread_cached()
    current_time = datetime.now(UTC_TIMEZONE)

    if gc is None:
        st.session_state.last_data_refresh_time = current_time
        return pd.DataFrame()

    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")

    if not sheet_url_or_name:
        st.error("🚨 Config Error: GOOGLE_SHEET_URL_OR_NAME is missing in Streamlit secrets.")
        st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    if not worksheet_name:
        st.error("🚨 Config Error: GOOGLE_WORKSHEET_NAME is missing in Streamlit secrets.")
        st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()

    try:
        if "docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        else:
            spreadsheet = gc.open(sheet_url_or_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1, expected_headers=None)
        st.session_state.last_data_refresh_time = current_time

        if not data:
            st.warning("⚠️ No data rows found in the Google Sheet (though headers might exist).")
            return pd.DataFrame()
        df = pd.DataFrame(data)

        standardized_column_names = {col: "".join(str(col).strip().lower().split()) for col in df.columns}
        df.rename(columns=standardized_column_names, inplace=True)

        column_name_map_to_code = {
            "licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "dcc": "licenseNumber",
            "storename": "storeName", "accountname": "storeName",
            "repname": "repName", "representative": "repName",
            "onboardingdate": "onboardingDate", "deliverydate": "deliveryDate",
            "confirmationtimestamp": "confirmationTimestamp", "confirmedat": "confirmationTimestamp",
            "clientsentiment": "clientSentiment", "sentiment": "clientSentiment",
            "fulltranscript": "fullTranscript", "transcript": "fullTranscript",
            "score": "score", "onboardingscore": "score", "status": "status", "onboardingstatus": "status",
            "summary": "summary", "callsummary": "summary", "contactnumber": "contactNumber", "phone": "contactNumber",
            "confirmednumber": "confirmedNumber", "verifiednumber":"confirmedNumber",
            "contactname": "contactName", "clientcontact": "contactName"
        }
        for req_key_internal in KEY_REQUIREMENT_DETAILS.keys():
            std_req_key = req_key_internal.lower()
            column_name_map_to_code[std_req_key] = req_key_internal

        cols_to_rename_actual = {}
        current_df_columns_std_list = list(df.columns)
        for standardized_sheet_col_name in current_df_columns_std_list:
            if standardized_sheet_col_name in column_name_map_to_code:
                target_code_col_name = column_name_map_to_code[standardized_sheet_col_name]
                if standardized_sheet_col_name != target_code_col_name and \
                   target_code_col_name not in cols_to_rename_actual.values() and \
                   target_code_col_name not in current_df_columns_std_list:
                    cols_to_rename_actual[standardized_sheet_col_name] = target_code_col_name
        if cols_to_rename_actual: df.rename(columns=cols_to_rename_actual, inplace=True)

        date_cols_map = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
        for original_col, dt_col in date_cols_map.items():
            if original_col in df.columns:
                df[original_col] = df[original_col].astype(str).str.replace('\n',' ',regex=False).str.strip()
                df[dt_col] = robust_to_datetime(df[original_col])
                df[original_col] = format_datetime_to_pst_str(df[dt_col])
            else: df[dt_col] = pd.NaT
            if original_col == 'onboardingDate':
                if dt_col in df.columns and df[dt_col].notna().any(): df['onboarding_date_only'] = df[dt_col].dt.date
                else: df['onboarding_date_only'] = pd.NaT

        if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
            def ensure_utc_for_calc(series_dt):
                if pd.api.types.is_datetime64_any_dtype(series_dt) and series_dt.notna().any():
                    if series_dt.dt.tz is None: return series_dt.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
                    else: return series_dt.dt.tz_convert(UTC_TIMEZONE)
                return series_dt
            delivery_utc = ensure_utc_for_calc(df['deliveryDate_dt']); confirmation_utc = ensure_utc_for_calc(df['confirmationTimestamp_dt'])
            valid_dates_mask = delivery_utc.notna() & confirmation_utc.notna()
            df['days_to_confirmation'] = pd.NA
            if valid_dates_mask.any(): df.loc[valid_dates_mask, 'days_to_confirmation'] = (confirmation_utc[valid_dates_mask] - delivery_utc[valid_dates_mask]).dt.days
        else: df['days_to_confirmation'] = pd.NA

        for phone_col in ['contactNumber', 'confirmedNumber']:
            if phone_col in df.columns: df[phone_col] = df[phone_col].astype(str).apply(format_phone_number)
        for name_col in ['repName', 'contactName']:
            if name_col in df.columns: df[name_col] = df[name_col].astype(str).apply(capitalize_name)

        string_columns_to_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary', 'contactName', 'contactNumber', 'confirmedNumber', 'onboardingDate', 'deliveryDate', 'confirmationTimestamp']
        for col in string_columns_to_ensure:
            if col not in df.columns: df[col] = ""
            else: df[col] = df[col].astype(str).replace(['nan', 'NaN', 'None', 'NaT', '<NA>'], "", regex=False).fillna("")

        if 'score' not in df.columns: df['score'] = pd.NA
        else: df['score'] = pd.to_numeric(df['score'], errors='coerce')

        checklist_cols_to_ensure = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS + ['onboardingWelcome']
        for col in checklist_cols_to_ensure:
            if col not in df.columns: df[col] = pd.NA

        cols_to_drop_final = ['deliverydatets', 'onboardingwelcome']
        for col_to_drop in cols_to_drop_final:
            if col_to_drop in df.columns: df = df.drop(columns=[col_to_drop])
        return df
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 Google Sheets Error: {e}. Check sheet URL/name & permissions."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    except Exception as e: st.error(f"🌪️ Unexpected error loading data: {e}"); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()


# --- Utility Functions ---
@st.cache_data
def convert_df_to_csv(df_to_convert): return df_to_convert.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input):
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA
    total_onboardings = len(df_input)
    confirmed_onboardings = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
    success_rate = (confirmed_onboardings / total_onboardings * 100) if total_onboardings > 0 else 0.0
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    avg_days_to_confirmation = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    return total_onboardings, success_rate, avg_score, avg_days_to_confirmation

def get_default_date_range(date_series_for_min_max):
    today = date.today(); start_of_month_default = today.replace(day=1); end_of_month_default = today
    min_data_date, max_data_date = None, None
    if date_series_for_min_max is not None and not date_series_for_min_max.empty and date_series_for_min_max.notna().any():
        valid_dates = pd.to_datetime(date_series_for_min_max, errors='coerce').dt.date.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min(); max_data_date = valid_dates.max()
            final_start_default = max(start_of_month_default, min_data_date) if min_data_date else start_of_month_default
            final_end_default = min(end_of_month_default, max_data_date) if max_data_date else end_of_month_default
            if final_start_default > final_end_default and min_data_date and max_data_date: final_start_default, final_end_default = min_data_date, max_data_date
            elif final_start_default > final_end_default: final_start_default, final_end_default = start_of_month_default, end_of_month_default
            return final_start_default, final_end_default, min_data_date, max_data_date
    return start_of_month_default, end_of_month_default, min_data_date, max_data_date


# --- Initialize Session State ---
default_s_init, default_e_init, initial_min_data_date, initial_max_data_date = get_default_date_range(None)
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'date_range' not in st.session_state or \
   not (isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range) == 2 and
        isinstance(st.session_state.date_range[0], date) and isinstance(st.session_state.date_range[1], date)):
    st.session_state.date_range = (default_s_init, default_e_init)
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = initial_min_data_date
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = initial_max_data_date
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
categorical_filter_keys = ['repName_filter', 'status_filter', 'clientSentiment_filter']
for f_key in categorical_filter_keys:
    if f_key not in st.session_state: st.session_state[f_key] = []
search_field_keys = ['licenseNumber_search', 'storeName_search']
for s_key in search_field_keys:
    if s_key not in st.session_state: st.session_state[s_key] = ""
TAB_OVERVIEW = "🌌 Overview"; TAB_DETAILED_ANALYSIS = "📊 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
if 'active_tab' not in st.session_state: st.session_state.active_tab = TAB_OVERVIEW
if 'selected_transcript_key_dialog_global_search' not in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
if 'selected_transcript_key_filtered_analysis' not in st.session_state: st.session_state.selected_transcript_key_filtered_analysis = None
if 'show_global_search_dialog' not in st.session_state: st.session_state.show_global_search_dialog = False

# --- Initial Data Load ---
if not st.session_state.data_loaded and st.session_state.last_data_refresh_time is None:
    df_loaded = load_data_from_google_sheet()
    if st.session_state.last_data_refresh_time is None: st.session_state.last_data_refresh_time = datetime.now(UTC_TIMEZONE)
    if not df_loaded.empty:
        st.session_state.df_original = df_loaded; st.session_state.data_loaded = True
        ds, de, min_d, max_d = get_default_date_range(df_loaded.get('onboarding_date_only'))
        st.session_state.date_range = (ds, de); st.session_state.min_data_date_for_filter = min_d; st.session_state.max_data_date_for_filter = max_d
    else: st.session_state.df_original = pd.DataFrame(); st.session_state.data_loaded = False
df_original = st.session_state.df_original


# --- Sidebar ---
st.sidebar.header("🛠️ Dashboard Controls"); st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Global Search"); st.sidebar.caption("Search all data. Overrides filters below when active.")
global_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
ln_search_val = st.sidebar.text_input(f"Search {global_search_cols['licenseNumber']}:", value=st.session_state.get("licenseNumber_search", ""), key="licenseNumber_global_search_widget", help="Enter part of a license number and press Enter.")
if ln_search_val != st.session_state["licenseNumber_search"]: st.session_state["licenseNumber_search"] = ln_search_val; st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", "")); st.rerun()
store_names_options = [""];
if not df_original.empty and 'storeName' in df_original.columns: unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique()); store_names_options.extend([name for name in unique_stores if str(name).strip()])
current_store_search_val = st.session_state.get("storeName_search", "");
try: current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
except ValueError: current_store_idx = 0
selected_store_val = st.sidebar.selectbox(f"Search {global_search_cols['storeName']}:", options=store_names_options, index=current_store_idx, key="storeName_global_search_widget_select", help="Select or type a store name.")
if selected_store_val != st.session_state["storeName_search"]: st.session_state["storeName_search"] = selected_store_val; st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", "")); st.rerun()
st.sidebar.markdown("---"); global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))
st.sidebar.subheader("🔍 Filters"); filter_caption = "ℹ️ Date and category filters are overridden by active Global Search." if global_search_active else "Apply filters to the dashboard data."; st.sidebar.caption(filter_caption)
st.sidebar.markdown("##### Quick Date Ranges"); s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
if s_col1.button("MTD", key="mtd_button_v4_1", use_container_width=True, disabled=global_search_active): # Key updated
    if not global_search_active: start_mtd = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col2.button("YTD", key="ytd_button_v4_1", use_container_width=True, disabled=global_search_active): # Key updated
    if not global_search_active: start_ytd = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col3.button("ALL", key="all_button_v4_1", use_container_width=True, disabled=global_search_active): # Key updated
    if not global_search_active:
        all_start = st.session_state.get('min_data_date_for_filter', today_for_shortcuts.replace(year=today_for_shortcuts.year-1)); all_end = st.session_state.get('max_data_date_for_filter', today_for_shortcuts)
        if all_start and all_end: st.session_state.date_range = (all_start, all_end); st.session_state.date_filter_is_active = True; st.rerun()
current_session_start, current_session_end = st.session_state.date_range; min_dt_for_widget = st.session_state.get('min_data_date_for_filter'); max_dt_for_widget = st.session_state.get('max_data_date_for_filter')
val_start_widget = current_session_start;
if min_dt_for_widget and current_session_start < min_dt_for_widget: val_start_widget = min_dt_for_widget
val_end_widget = current_session_end;
if max_dt_for_widget and current_session_end > max_dt_for_widget: val_end_widget = max_dt_for_widget
if val_start_widget > val_end_widget : val_start_widget = val_end_widget
selected_date_range_tuple = st.sidebar.date_input("Custom Date Range (Onboarding):", value=(val_start_widget, val_end_widget), min_value=min_dt_for_widget, max_value=max_dt_for_widget, key="date_selector_custom_v4_1", disabled=global_search_active, help="Select start/end dates.") # Key updated
if not global_search_active and isinstance(selected_date_range_tuple, tuple) and len(selected_date_range_tuple) == 2:
    if selected_date_range_tuple != st.session_state.date_range: st.session_state.date_range = selected_date_range_tuple; st.session_state.date_filter_is_active = True; st.rerun()
start_dt_filter, end_dt_filter = st.session_state.date_range
category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label_text in category_filters_map.items():
    options_for_multiselect = [];
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any(): options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).dropna().unique() if str(val).strip()])
    current_selection_for_multiselect = st.session_state.get(f"{col_key}_filter", []); valid_current_selection = [s for s in current_selection_for_multiselect if s in options_for_multiselect]
    new_selection_multiselect = st.sidebar.multiselect(f"Filter by {label_text}:", options=options_for_multiselect, default=valid_current_selection, key=f"{col_key}_category_filter_widget_v4_1", disabled=global_search_active or not options_for_multiselect, help=f"Select {label_text} to filter by." if options_for_multiselect else f"No {label_text} data.") # Key updated
    if not global_search_active and new_selection_multiselect != valid_current_selection: st.session_state[f"{col_key}_filter"] = new_selection_multiselect; st.rerun()
    elif global_search_active and st.session_state.get(f"{col_key}_filter") != new_selection_multiselect: st.session_state[f"{col_key}_filter"] = new_selection_multiselect
def clear_all_filters_and_search_v4_1(): # Renamed function
    ds_cleared, de_cleared, _, _ = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_cleared, de_cleared); st.session_state.date_filter_is_active = False
    st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
    for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
    st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
    if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
    if "filtered_analysis_auto_selected_once" in st.session_state: st.session_state.filtered_analysis_auto_selected_once = False
    st.session_state.active_tab = TAB_OVERVIEW
if st.sidebar.button("🧹 Clear All Filters & Search", on_click=clear_all_filters_and_search_v4_1, use_container_width=True, key="clear_filters_button_v4_1"): st.rerun() # Key and function updated
with st.sidebar.expander("💡 Understanding The Score (0-10 pts)", expanded=False):
    st.markdown("""Score (0-10 pts):\n- **🔑 Primary (4 pts):** `Kit Recvd` (2), `Train & Promo Sched` (2).\n- **เสริม Secondary (3 pts):** `Intro` (1), `Display Help` (1), `Promo Link` (1).\n- **🏆 Bonuses (3 pts):** `+1` Positive `Sentiment`, `+1` `Expectations Set`, `+1` Full Checklist Completion.""")
st.sidebar.markdown("---"); st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet", key="refresh_data_button_v4_1", use_container_width=True): # Key updated
    st.cache_data.clear(); st.session_state.data_loaded = False; st.session_state.last_data_refresh_time = None; st.session_state.df_original = pd.DataFrame()
    clear_all_filters_and_search_v4_1(); st.rerun() # Use updated clear function
if st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE); refresh_time_str_display = refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST'); st.sidebar.caption(f"☁️ Last data sync: {refresh_time_str_display}")
    if not st.session_state.get('data_loaded', False) and st.session_state.df_original.empty : st.sidebar.caption("⚠️ No data loaded in last sync.")
else: st.sidebar.caption("⏳ Data not yet loaded.")
st.sidebar.markdown("---"); current_theme_display = st.get_option("theme.base").capitalize(); st.sidebar.info(f"**Onboarding Dashboard v4.1**\n\n*Mode: {current_theme_display}*\n\n© {datetime.now().year} Nexus Workflow")


# --- Main Page Content ---
st.title("✨ Onboarding Performance Dashboard ✨")
if not st.session_state.data_loaded and df_original.empty:
    if st.session_state.get('last_data_refresh_time'): st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh. 🚧</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>⏳ Initializing data... If persists, check configurations. ⏳</div>", unsafe_allow_html=True)
    st.stop()
elif df_original.empty: st.markdown("<div class='no-data-message'>✅ Data source connected, but empty. Add data to Google Sheet. ✅</div>", unsafe_allow_html=True); st.stop()
if st.session_state.active_tab not in ALL_TABS: st.session_state.active_tab = TAB_OVERVIEW
try: current_tab_idx = ALL_TABS.index(st.session_state.active_tab)
except ValueError: current_tab_idx = 0; st.session_state.active_tab = TAB_OVERVIEW
selected_tab = st.radio("Navigation:", ALL_TABS, index=current_tab_idx, horizontal=True, key="main_tab_selector_v4_1") # Key updated
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()
summary_parts = []
if global_search_active:
    search_terms = [];
    if st.session_state.get("licenseNumber_search", ""): search_terms.append(f"License: '{st.session_state['licenseNumber_search']}'")
    if st.session_state.get("storeName_search", ""): search_terms.append(f"Store: '{st.session_state['storeName_search']}'")
    summary_parts.append(f"🌍 Global Search: {'; '.join(search_terms)}"); summary_parts.append("(Filters overridden. Results in pop-up.)")
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
st.markdown(f"<div class='active-filters-summary'>🔍 {final_summary_message}</div>", unsafe_allow_html=True)
df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
if not df_original.empty:
    if global_search_active:
        df_temp_gs = df_original.copy(); ln_term = st.session_state.get("licenseNumber_search", "").strip().lower(); sn_term = st.session_state.get("storeName_search", "").strip()
        if ln_term and "licenseNumber" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
        if sn_term and "storeName" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['storeName'] == sn_term]
        df_global_search_results_display = df_temp_gs.copy(); df_filtered = df_global_search_results_display.copy()
    else:
        df_temp_filters = df_original.copy();
        if 'onboarding_date_only' in df_temp_filters.columns and df_temp_filters['onboarding_date_only'].notna().any():
            date_objects_for_filter = pd.to_datetime(df_temp_filters['onboarding_date_only'], errors='coerce').dt.date; valid_dates_mask = date_objects_for_filter.notna(); date_filter_condition = pd.Series([False] * len(df_temp_filters), index=df_temp_filters.index)
            if valid_dates_mask.any(): date_filter_condition[valid_dates_mask] = (date_objects_for_filter[valid_dates_mask] >= start_dt_filter) & (date_objects_for_filter[valid_dates_mask] <= end_dt_filter)
            df_temp_filters = df_temp_filters[date_filter_condition]
        for col_name_cat, _ in category_filters_map.items():
            selected_values_cat = st.session_state.get(f"{col_name_cat}_filter", []);
            if selected_values_cat and col_name_cat in df_temp_filters.columns: df_temp_filters = df_temp_filters[df_temp_filters[col_name_cat].astype(str).isin(selected_values_cat)]
        df_filtered = df_temp_filters.copy()
else: df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
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

def display_data_table_and_details(df_to_display, context_key_prefix=""):
    if df_to_display is None or df_to_display.empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','');
        if not df_original.empty: st.markdown(f"<div class='no-data-message'>📊 No data for {context_name_display}. Try different filters! 📊</div>", unsafe_allow_html=True)
        return
    df_display_copy = df_to_display.copy().reset_index(drop=True)
    def map_status_to_emoji(status_val):
        status_str = str(status_val).strip().lower();
        if status_str == 'confirmed': return "✅ Confirmed";
        if status_str == 'pending': return "⏳ Pending";
        if status_str == 'failed': return "❌ Failed";
        return status_val
    if 'status' in df_display_copy.columns: df_display_copy['status'] = df_display_copy['status'].apply(map_status_to_emoji)
    preferred_cols_order = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 'contactNumber', 'confirmedNumber', 'deliveryDate', 'confirmationTimestamp']
    preferred_cols_order.extend(ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS)
    cols_present_in_df = df_display_copy.columns.tolist(); final_display_cols = [col for col in preferred_cols_order if col in cols_present_in_df]
    excluded_suffixes = ('_dt', '_utc', '_str_original', '_date_only')
    other_existing_cols_for_display = [col for col in cols_present_in_df if col not in final_display_cols and not col.endswith(excluded_suffixes) and col not in ['fullTranscript', 'summary']]
    final_display_cols.extend(other_existing_cols_for_display); final_display_cols = list(dict.fromkeys(final_display_cols))
    if not final_display_cols or df_display_copy[final_display_cols].empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog',''); st.markdown(f"<div class='no-data-message'>📋 No columns/data for {context_name_display}. 📋</div>", unsafe_allow_html=True); return
    num_rows_display = len(df_display_copy);
    if num_rows_display == 0: table_height_calc = 100
    elif num_rows_display < 10: table_height_calc = (num_rows_display + 1) * 38 + 20
    else: table_height_calc = 400
    table_height_calc = max(150, table_height_calc)
    st.dataframe(df_display_copy[final_display_cols], use_container_width=True, height=table_height_calc, hide_index=True)
    st.markdown("---"); st.subheader("🔍 View Full Onboarding Details & Transcript")
    transcript_session_key_local = f"selected_transcript_key_{context_key_prefix}";
    if transcript_session_key_local not in st.session_state: st.session_state[transcript_session_key_local] = None
    auto_selected_this_run = False
    if len(df_display_copy) == 1:
        first_row_details = df_display_copy.iloc[0]; auto_select_option_key = f"Idx 0: {first_row_details.get('storeName', 'N/A')} ({first_row_details.get('onboardingDate', 'N/A')})"
        if st.session_state[transcript_session_key_local] != auto_select_option_key: st.session_state[transcript_session_key_local] = auto_select_option_key; auto_selected_this_run = True
    auto_selected_once_key = f"{context_key_prefix}_auto_selected_once"
    if auto_selected_this_run and not st.session_state.get(auto_selected_once_key, False): st.session_state[auto_selected_once_key] = True; st.rerun()
    elif len(df_display_copy) != 1: st.session_state[auto_selected_once_key] = False
    if 'fullTranscript' in df_display_copy.columns or 'summary' in df_display_copy.columns:
        transcript_options_map = {f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_copy.iterrows()}
        if transcript_options_map:
            options_list_for_select = [None] + list(transcript_options_map.keys()); current_selection_for_select = st.session_state[transcript_session_key_local]
            try: current_index_for_select = options_list_for_select.index(current_selection_for_select)
            except ValueError: current_index_for_select = 0; st.session_state[transcript_session_key_local] = None
            selected_key_from_display = st.selectbox("Select onboarding to view details:", options=options_list_for_select, index=current_index_for_select, format_func=lambda x: "📜 Choose an entry..." if x is None else x, key=f"transcript_selector_{context_key_prefix}_widget_v4_1") # Key Updated
            if selected_key_from_display != st.session_state[transcript_session_key_local]: st.session_state[transcript_session_key_local] = selected_key_from_display; st.session_state[auto_selected_once_key] = False; st.rerun()
            if st.session_state[transcript_session_key_local]:
                selected_original_idx = transcript_options_map[st.session_state[transcript_session_key_local]]; selected_row_details = df_display_copy.loc[selected_original_idx]
                st.markdown("##### 📋 Onboarding Summary & Checks:"); summary_html_parts_list = ["<div class='transcript-summary-grid'>"]
                summary_items_to_display = {"Store": selected_row_details.get('storeName', "N/A"), "Rep": selected_row_details.get('repName', "N/A"), "Score": f"{selected_row_details.get('score', 'N/A'):.1f}" if pd.notna(selected_row_details.get('score')) else "N/A", "Status": selected_row_details.get('status', "N/A").replace("✅","").replace("⏳","").replace("❌","").strip(), "Sentiment": selected_row_details.get('clientSentiment', "N/A")}
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
                        emoji_char = "✅" if is_met else ("❌" if pd.notna(val_from_row) else "❔"); type_tag_html = f"<span class='type'>[{item_type_text}]</span>" if item_type_text else ""; st.markdown(f"<div class='requirement-item'>{emoji_char} {desc_text} {type_tag_html}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---"); st.markdown("<h5>📜 Full Transcript:</h5>", unsafe_allow_html=True); transcript_content = selected_row_details.get('fullTranscript', "").strip()
                if transcript_content and transcript_content.lower() not in ['na', 'n/a', '']:
                    html_transcript_parts = ["<div class='transcript-container'>"]; processed_transcript_content = transcript_content.replace('\\n', '\n')
                    for line_item in processed_transcript_content.split('\n'):
                        line_item_stripped = line_item.strip();
                        if not line_item_stripped: continue
                        parts_of_line = line_item_stripped.split(":", 1); speaker_html = f"<strong>{parts_of_line[0].strip()}:</strong>" if len(parts_of_line) == 2 else ""
                        message_text = parts_of_line[1].strip() if len(parts_of_line) == 2 else line_item_stripped; html_transcript_parts.append(f"<p class='transcript-line'>{speaker_html} {message_text}</p>")
                    html_transcript_parts.append("</div>"); st.markdown("".join(html_transcript_parts), unsafe_allow_html=True)
                else: st.info("ℹ️ No transcript available or empty for this record.")
        else: context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog',''); st.markdown(f"<div class='no-data-message'>📋 No entries in table from {context_name_display} to select details. 📋</div>", unsafe_allow_html=True)
    else: context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog',''); st.markdown(f"<div class='no-data-message'>📜 Necessary columns ('fullTranscript'/'summary') missing for details viewer in {context_name_display}. 📜</div>", unsafe_allow_html=True)
    st.markdown("---"); csv_data_to_download = convert_df_to_csv(df_display_copy[final_display_cols]); download_label = f"📥 Download These {context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')} Results as CSV"
    st.download_button(label=download_label, data=csv_data_to_download, file_name=f'{context_key_prefix}_results_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', mime='text/csv', use_container_width=True, key=f"download_csv_{context_key_prefix}_button_v4_1") # Key Updated

# --- Global Search Dialog ---
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("🌍 Global Search Results", width="large")
    def show_global_search_dialog_content():
        st.markdown("##### Records matching global search:");
        if not df_global_search_results_display.empty: display_data_table_and_details(df_global_search_results_display, context_key_prefix="dialog_global_search")
        else: st.info("ℹ️ No results for global search. Try broadening terms.")
        if st.button("Close & Clear Search", key="close_gs_dialog_clear_button_v4_1"): # Key Updated
            st.session_state.show_global_search_dialog = False; st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""
            if 'selected_transcript_key_dialog_global_search' in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
            if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
            st.rerun()
    show_global_search_dialog_content()

# --- Tab Content ---
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
elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if global_search_active: st.info("ℹ️ Global Search active. Results in pop-up. Close/clear search for category/date filters here.")
    else:
        display_data_table_and_details(df_filtered, context_key_prefix="filtered_analysis")
        st.header("🎨 Key Visualizations (Filtered Data)")
        if not df_filtered.empty:
            chart_cols_1, chart_cols_2 = st.columns(2)
            with chart_cols_1:
                if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                    status_counts_df = df_filtered['status'].apply(lambda x: str(x).replace("✅","").replace("⏳","").replace("❌","").strip()).value_counts().reset_index(); status_counts_df.columns = ['status', 'count']
                    status_fig = px.bar(status_counts_df, x='status', y='count', color='status', title="Onboarding Status Distribution", color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ); status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📉 Status data unavailable.</div>", unsafe_allow_html=True)
                if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                    rep_counts_df = df_filtered['repName'].value_counts().reset_index(); rep_counts_df.columns = ['repName', 'count']
                    rep_fig = px.bar(rep_counts_df, x='repName', y='count', color='repName', title="Onboardings by Representative", color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ); rep_fig.update_layout(plotly_base_layout_settings, xaxis_title="Representative", yaxis_title="Number of Onboardings"); st.plotly_chart(rep_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>👥 Rep data unavailable.</div>", unsafe_allow_html=True)
            with chart_cols_2:
                if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                    sent_counts_df = df_filtered['clientSentiment'].value_counts().reset_index(); sent_counts_df.columns = ['clientSentiment', 'count']
                    current_sentiment_map_plot = {s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), '#808080') for s in sent_counts_df['clientSentiment'].unique()}
                    sent_fig = px.pie(sent_counts_df, names='clientSentiment', values='count', hole=0.4, title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=current_sentiment_map_plot); sent_fig.update_layout(plotly_base_layout_settings); sent_fig.update_traces(textinfo='percent+label', textfont_size=12); st.plotly_chart(sent_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>😊 Sentiment data unavailable.</div>", unsafe_allow_html=True)
                df_confirmed_for_chart = df_filtered[df_filtered['status'].astype(str).str.contains('Confirmed', case=False, na=False)].copy(); actual_key_cols_for_checklist_chart = [col for col in ORDERED_CHART_REQUIREMENTS if col in df_confirmed_for_chart.columns]
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
                        else: st.markdown("<div class='no-data-message'>📊 No data for key req chart (confirmed, post-proc).</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='no-data-message'>📊 No valid checklist items for req chart.</div>", unsafe_allow_html=True)
                else: st.markdown("<div class='no-data-message'>✅ No 'Confirmed' onboardings or relevant columns for req chart.</div>", unsafe_allow_html=True)
        elif not df_original.empty : st.markdown("<div class='no-data-message'>🖼️ No data matches filters for visuals. Change selections. 🖼️</div>", unsafe_allow_html=True)
elif st.session_state.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS); st.markdown(f"*(Visuals based on {'Global Search (Pop-Up)' if global_search_active else 'Filtered Data'})*")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_source = df_filtered.copy(); df_trend_source['onboarding_datetime'] = pd.to_datetime(df_trend_source['onboarding_date_only'], errors='coerce'); df_trend_source.dropna(subset=['onboarding_datetime'], inplace=True)
            if not df_trend_source.empty:
                date_span_days = (df_trend_source['onboarding_datetime'].max() - df_trend_source['onboarding_datetime'].min()).days; resample_freq = 'D';
                if date_span_days > 90: resample_freq = 'W-MON';
                if date_span_days > 730: resample_freq = 'ME'
                trend_data_resampled = df_trend_source.set_index('onboarding_datetime').resample(resample_freq).size().reset_index(name='count')
                if not trend_data_resampled.empty:
                    trend_line_fig = px.line(trend_data_resampled, x='onboarding_datetime', y='count', markers=True, title=f"Onboardings Over Time ({resample_freq} Trend)", color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[0]]); trend_line_fig.update_layout(plotly_base_layout_settings, xaxis_title="Date", yaxis_title="Number of Onboardings"); st.plotly_chart(trend_line_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📈 Not enough data for trend plot.</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='no-data-message'>📅 No valid date data for trend.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>🗓️ 'onboarding_date_only' missing for trend.</div>", unsafe_allow_html=True)
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna();
            if not days_data_for_hist.empty:
                num_bins_hist = max(10, min(30, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else (len(days_data_for_hist.unique()) or 10); days_dist_fig = px.histogram(days_data_for_hist, nbins=num_bins_hist, title="Distribution of Days to Confirmation", color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[1]]); days_dist_fig.update_layout(plotly_base_layout_settings, xaxis_title="Days to Confirmation", yaxis_title="Frequency"); st.plotly_chart(days_dist_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>⏳ No 'Days to Confirmation' data.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' missing.</div>", unsafe_allow_html=True)
    elif not df_original.empty : st.markdown("<div class='no-data-message'>📉 No data for Trends. Adjust filters. 📉</div>", unsafe_allow_html=True)
st.markdown("---"); st.markdown(f"<div class='footer'>Onboarding Dashboard v4.1 © {datetime.now().year} Nexus Workflow. All Rights Reserved.</div>", unsafe_allow_html=True)