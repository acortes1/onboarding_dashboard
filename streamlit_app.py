# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time
import numpy as np
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v3.6", # Incremented version
    page_icon="💎",
    layout="wide"
)

# --- Color Palette Definitions ---

# Dark Theme (Original Basis)
DARK_BACKGROUND_MAIN = "#0E1117"
DARK_BACKGROUND_SECONDARY = "#262730"
DARK_TEXT_PRIMARY = "#FAFAFA"
DARK_TEXT_SECONDARY = "#B0B8C4" # Softer than previous light blue
DARK_BORDER_COLOR = "#3a3f4b"

DARK_ACCENT_PRIMARY = "#8458B3"
DARK_ACCENT_SECONDARY = "#d0bdf4"
DARK_ACCENT_MUTED = "#a28089"
DARK_ACCENT_HIGHLIGHT = "#a0d2eb" # Light Blue for sidebar headers etc.
DARK_ACCENT_LIGHTEST = "#e5eaf5"

DARK_TEXT_ON_ACCENT_PRIMARY = DARK_ACCENT_LIGHTEST
DARK_TEXT_ON_ACCENT_HIGHLIGHT = DARK_BACKGROUND_MAIN # Dark text on light blue

DARK_DL_BUTTON_BG = DARK_ACCENT_HIGHLIGHT
DARK_DL_BUTTON_TEXT = DARK_TEXT_ON_ACCENT_HIGHLIGHT
DARK_DL_BUTTON_HOVER_BG = DARK_ACCENT_LIGHTEST
DARK_DL_BUTTON_HOVER_TEXT = DARK_TEXT_ON_ACCENT_HIGHLIGHT

# Plotly Dark Theme Colors
DARK_PLOTLY_PRIMARY_SEQ = [DARK_ACCENT_PRIMARY, DARK_ACCENT_SECONDARY, DARK_ACCENT_HIGHLIGHT, '#C39BD3', '#76D7C4']
DARK_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1 # Existing choice, generally okay
DARK_PLOTLY_SENTIMENT_MAP = {
    'positive': DARK_ACCENT_HIGHLIGHT, # Light Blue
    'negative': '#E74C3C', # A clear red
    'neutral': DARK_ACCENT_MUTED
}


# New Light Theme Palette (Rebuilt from scratch)
LIGHT_BACKGROUND_MAIN = "#FFFFFF"
LIGHT_BACKGROUND_SECONDARY = "#F7F9FC" # Very light cool grey for cards/sidebar
LIGHT_TEXT_PRIMARY = "#202124" # Standard dark grey text (Google style)
LIGHT_TEXT_SECONDARY = "#5F6368" # Standard medium grey text
LIGHT_BORDER_COLOR = "#DADCE0" # Standard light grey border

LIGHT_ACCENT_PRIMARY = "#1A73E8" # Google Blue - for primary actions, headers
LIGHT_ACCENT_SECONDARY = "#4285F4" # Lighter, vibrant blue
LIGHT_ACCENT_MUTED = "#89B1F3" # Softer blue for less critical accents
LIGHT_ACCENT_HIGHLIGHT = "#1A73E8" # Primary blue for sidebar headers
LIGHT_ACCENT_LIGHTEST = "#E8F0FE" # Very light blue for hovers, subtle backgrounds

LIGHT_TEXT_ON_ACCENT_PRIMARY = "#FFFFFF"
LIGHT_TEXT_ON_ACCENT_HIGHLIGHT = "#FFFFFF"

LIGHT_DL_BUTTON_BG = LIGHT_ACCENT_PRIMARY # Primary blue for download
LIGHT_DL_BUTTON_TEXT = LIGHT_TEXT_ON_ACCENT_PRIMARY
LIGHT_DL_BUTTON_HOVER_BG = "#1765CC" # Darker blue for hover
LIGHT_DL_BUTTON_HOVER_TEXT = LIGHT_TEXT_ON_ACCENT_PRIMARY

# Plotly Light Theme Colors
LIGHT_PLOTLY_PRIMARY_SEQ = ['#1A73E8', '#4285F4', '#89B1F3', '#ADC6F7', '#D2E3FC'] # Shades of Google Blue
LIGHT_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set2 # Generally good for light backgrounds
LIGHT_PLOTLY_SENTIMENT_MAP = {
    'positive': '#1A73E8', # Google Blue
    'negative': '#D93025', # Google Red
    'neutral': '#78909C'  # A neutral grey-blue
}

# --- Determine Active Theme and Set Colors ---
THEME = st.get_option("theme.base")

if THEME == "light":
    ACTIVE_BG_MAIN = LIGHT_BACKGROUND_MAIN
    ACTIVE_BG_SECONDARY = LIGHT_BACKGROUND_SECONDARY
    ACTIVE_TEXT_PRIMARY = LIGHT_TEXT_PRIMARY
    ACTIVE_TEXT_SECONDARY = LIGHT_TEXT_SECONDARY
    ACTIVE_BORDER_COLOR = LIGHT_BORDER_COLOR
    ACTIVE_ACCENT_PRIMARY = LIGHT_ACCENT_PRIMARY
    ACTIVE_ACCENT_SECONDARY = LIGHT_ACCENT_SECONDARY
    ACTIVE_ACCENT_MUTED = LIGHT_ACCENT_MUTED
    ACTIVE_ACCENT_HIGHLIGHT = LIGHT_ACCENT_HIGHLIGHT
    ACTIVE_ACCENT_LIGHTEST = LIGHT_ACCENT_LIGHTEST
    ACTIVE_TEXT_ON_PRIMARY = LIGHT_TEXT_ON_ACCENT_PRIMARY
    ACTIVE_TEXT_ON_HIGHLIGHT = LIGHT_TEXT_ON_ACCENT_HIGHLIGHT
    ACTIVE_DL_BUTTON_BG = LIGHT_DL_BUTTON_BG
    ACTIVE_DL_BUTTON_TEXT = LIGHT_DL_BUTTON_TEXT
    ACTIVE_DL_BUTTON_HOVER_BG = LIGHT_DL_BUTTON_HOVER_BG
    ACTIVE_DL_BUTTON_HOVER_TEXT = LIGHT_DL_BUTTON_HOVER_TEXT
    # Plotly active colors
    ACTIVE_PLOTLY_PRIMARY_SEQ = LIGHT_PLOTLY_PRIMARY_SEQ
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = LIGHT_PLOTLY_QUALITATIVE_SEQ
    ACTIVE_PLOTLY_SENTIMENT_MAP = LIGHT_PLOTLY_SENTIMENT_MAP
else: # Default to Dark Theme
    ACTIVE_BG_MAIN = DARK_BACKGROUND_MAIN
    ACTIVE_BG_SECONDARY = DARK_BACKGROUND_SECONDARY
    ACTIVE_TEXT_PRIMARY = DARK_TEXT_PRIMARY
    ACTIVE_TEXT_SECONDARY = DARK_TEXT_SECONDARY
    ACTIVE_BORDER_COLOR = DARK_BORDER_COLOR
    ACTIVE_ACCENT_PRIMARY = DARK_ACCENT_PRIMARY
    ACTIVE_ACCENT_SECONDARY = DARK_ACCENT_SECONDARY
    ACTIVE_ACCENT_MUTED = DARK_ACCENT_MUTED
    ACTIVE_ACCENT_HIGHLIGHT = DARK_ACCENT_HIGHLIGHT
    ACTIVE_ACCENT_LIGHTEST = DARK_ACCENT_LIGHTEST
    ACTIVE_TEXT_ON_PRIMARY = DARK_TEXT_ON_ACCENT_PRIMARY
    ACTIVE_TEXT_ON_HIGHLIGHT = DARK_TEXT_ON_ACCENT_HIGHLIGHT
    ACTIVE_DL_BUTTON_BG = DARK_DL_BUTTON_BG
    ACTIVE_DL_BUTTON_TEXT = DARK_DL_BUTTON_TEXT
    ACTIVE_DL_BUTTON_HOVER_BG = DARK_DL_BUTTON_HOVER_BG
    ACTIVE_DL_BUTTON_HOVER_TEXT = DARK_DL_BUTTON_HOVER_TEXT
    # Plotly active colors
    ACTIVE_PLOTLY_PRIMARY_SEQ = DARK_PLOTLY_PRIMARY_SEQ
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = DARK_PLOTLY_QUALITATIVE_SEQ
    ACTIVE_PLOTLY_SENTIMENT_MAP = DARK_PLOTLY_SENTIMENT_MAP

PLOT_BG_COLOR = "rgba(0,0,0,0)"

# --- Custom Styling (CSS) ---
css_parts = [
    "<style>",
    f"""
    :root {{
        --theme-bg-main: {ACTIVE_BG_MAIN};
        --theme-bg-secondary: {ACTIVE_BG_SECONDARY};
        --theme-text-primary: {ACTIVE_TEXT_PRIMARY};
        --theme-text-secondary: {ACTIVE_TEXT_SECONDARY};
        --theme-border-color: {ACTIVE_BORDER_COLOR};

        --theme-accent-primary: {ACTIVE_ACCENT_PRIMARY};
        --theme-accent-secondary: {ACTIVE_ACCENT_SECONDARY};
        --theme-accent-muted: {ACTIVE_ACCENT_MUTED};
        --theme-accent-highlight: {ACTIVE_ACCENT_HIGHLIGHT};
        --theme-accent-lightest: {ACTIVE_ACCENT_LIGHTEST};

        --theme-text-on-primary: {ACTIVE_TEXT_ON_PRIMARY};
        --theme-text-on-highlight: {ACTIVE_TEXT_ON_HIGHLIGHT};

        --theme-dl-button-bg: {ACTIVE_DL_BUTTON_BG};
        --theme-dl-button-text: {ACTIVE_DL_BUTTON_TEXT};
        --theme-dl-button-hover-bg: {ACTIVE_DL_BUTTON_HOVER_BG};
        --theme-dl-button-hover-text: {ACTIVE_DL_BUTTON_HOVER_TEXT};
    }}
    """,
    """
    /* General App Styles */
    .stApp {
        background-color: var(--background-color, var(--theme-bg-main));
    }
    .stApp > header { background-color: transparent !important; }
    h1 { color: var(--theme-accent-primary); text-align: center; padding-top: 1em; padding-bottom: 0.8em; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
    h2, h3 { color: var(--theme-accent-primary); border-bottom: 2px solid var(--theme-accent-primary) !important; padding-bottom: 0.4em; margin-top: 2em; margin-bottom: 1.2em; font-weight: 600; }
    h5 { color: var(--theme-accent-primary); opacity: 0.95; margin-top: 1.2em; margin-bottom: 0.6em; font-weight: 600; letter-spacing: 0.5px; }

    /* Metric Widget Styles */
    div[data-testid="stMetric"], .metric-card {
        background-color: var(--secondary-background-color, var(--theme-bg-secondary));
        padding: 1.5em; border-radius: 12px; border: 1px solid var(--border-color, var(--theme-border-color));
        box-shadow: 0 4px 6px rgba(0,0,0,0.04); /* Softer shadow for light theme */
        transition: transform 0.25s ease-in-out, box-shadow 0.25s ease-in-out;
    }
    div[data-testid="stMetric"]:hover, .metric-card:hover {
         transform: translateY(-4px); box-shadow: 0 6px 12px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetricLabel"] > div { color: var(--text-color, var(--theme-text-secondary)) !important; opacity: 0.9; font-weight: 500; font-size: 1em; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetricValue"] > div { color: var(--text-color, var(--theme-text-primary)) !important; font-size: 2.5rem !important; font-weight: 700; line-height: 1.1; }
    div[data-testid="stMetricDelta"] > div { color: var(--text-color, var(--theme-text-secondary)) !important; opacity: 0.9; font-weight: 500; font-size: 0.9em; }

    /* Expander Styles */
    .streamlit-expanderHeader { color: var(--theme-accent-primary) !important; font-weight: 600; font-size: 1.1em; }
    .streamlit-expander { border: 1px solid var(--border-color, var(--theme-border-color)); border-radius: 10px; background-color: var(--secondary-background-color, var(--theme-bg-secondary)); }
    .streamlit-expander > div > div > p { color: var(--text-color, var(--theme-text-primary)); }

    /* DataFrame Styles */
    .stDataFrame { border: 1px solid var(--border-color, var(--theme-border-color)); border-radius: 10px; }

    /* Custom Tab (Radio Button) Styles */
    div[data-testid="stRadio"] label {
        padding: 10px 18px; margin: 0 3px; border-radius: 8px 8px 0 0; /* Slightly smaller tabs */
        border: 1px solid transparent; border-bottom: none;
        background-color: var(--secondary-background-color, var(--theme-bg-secondary));
        color: var(--text-color, var(--theme-text-secondary)); opacity: 0.80;
        transition: background-color 0.3s ease, color 0.3s ease, opacity 0.3s ease, border-color 0.3s ease;
        font-weight: 500;
    }
    div[data-testid="stRadio"] input:checked + div label {
        background-color: var(--theme-accent-lightest); /* Use lightest accent for active tab BG */
        color: var(--theme-accent-primary); font-weight: 600; opacity: 1.0;
        border-top: 2px solid var(--theme-accent-primary);
        border-left: 1px solid var(--border-color, var(--theme-border-color));
        border-right: 1px solid var(--border-color, var(--theme-border-color));
    }
    div[data-testid="stRadio"] { padding-bottom: 0px; border-bottom: 2px solid var(--theme-accent-primary); margin-bottom: 30px; }
    div[data-testid="stRadio"] > label > div:first-child { display: none; }

    /* Transcript Viewer Specific Styles */
    .transcript-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px; margin-bottom: 25px; color: var(--text-color, var(--theme-text-primary));}
    .transcript-summary-item strong { color: var(--theme-accent-primary); }
    .requirement-item {
        margin-bottom: 12px; padding: 10px; border-left: 4px solid var(--theme-accent-muted); /* Muted accent for border */
        background-color: color-mix(in srgb, var(--secondary-background-color, var(--theme-bg-secondary)) 97%, var(--theme-accent-lightest) 3%); /* Very subtle tint */
        border-radius: 6px; color: var(--text-color, var(--theme-text-primary));
    }
    .requirement-item .type { font-weight: 500; color: var(--theme-accent-muted); opacity: 0.8; font-size: 0.85em; margin-left: 8px; }
    .transcript-container {
        background-color: var(--secondary-background-color, var(--theme-bg-secondary));
        color: var(--text-color, var(--theme-text-primary));
        padding: 20px; border-radius: 10px; border: 1px solid var(--border-color, var(--theme-border-color));
        max-height: 450px; overflow-y: auto; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
        font-size: 0.95em; line-height: 1.7;
    }
    .transcript-line strong { color: var(--theme-accent-primary); }

    /* Button styles */
    div[data-testid="stButton"] > button {
        background-color: var(--theme-accent-primary); color: var(--theme-text-on-primary);
        border: none; padding: 10px 20px; border-radius: 6px; /* Slightly smaller buttons */
        font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }
    div[data-testid="stButton"] > button:hover {
        background-color: color-mix(in srgb, var(--theme-accent-primary) 90%, #000000 10%); /* Darken slightly */
        color: var(--theme-text-on-primary); transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    div[data-testid="stDownloadButton"] > button {
        background-color: var(--theme-dl-button-bg); color: var(--theme-dl-button-text);
        border: none; padding: 10px 20px; border-radius: 6px;
        font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: var(--theme-dl-button-hover-bg); color: var(--theme-dl-button-hover-text);
        transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }

    /* Sidebar styling */
    div[data-testid="stSidebarUserContent"] {
        background-color: var(--secondary-background-color, var(--theme-bg-secondary));
        padding: 1.5em 1em; border-right: 1px solid var(--border-color, var(--theme-border-color));
    }
    div[data-testid="stSidebarUserContent"] h2,
    div[data-testid="stSidebarUserContent"] h3 {
        color: var(--theme-accent-highlight); border-bottom-color: var(--theme-accent-secondary);
    }
    """,
    "</style>"
]
css_style = "\n".join(css_parts)
st.markdown(css_style, unsafe_allow_html=True)


# --- Application Access Control ---
def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set. Bypassing password.")
        return True
    if "password_entered" not in st.session_state:
        st.session_state.password_entered = False
    if st.session_state.password_entered:
        return True
    with st.form("password_form_main_app_v3_6"): # Unique key
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint, key="pwd_input_main_app_v3_6")
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password_attempt == app_password:
                st.session_state.password_entered = True; st.rerun()
            else:
                st.error("Incorrect Access Key."); return False
    return False

if not check_password():
    st.stop()

# --- Constants ---
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

# --- Google Sheets Authentication and Data Loading Functions ---
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    gcp_secrets = st.secrets.get("gcp_service_account")
    if gcp_secrets is None: print("Error: GCP secrets NOT FOUND."); return None
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')): print(f"Error: GCP secrets not structured correctly (type: {type(gcp_secrets)})."); return None
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [k for k in required_keys if gcp_secrets.get(k) is None]
    if missing: print(f"Error: GCP secrets missing keys: {', '.join(missing)}."); return None
    try:
        creds = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e: print(f"Google Auth Error: {e}"); return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    common_formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
                      '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    if not series.empty and dates.isnull().sum() > len(series)*0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                if dates.notnull().all(): break
            except ValueError: continue
    return dates

@st.cache_data(ttl=600)
def load_data_from_google_sheet(): # Removed unused param
    gc = authenticate_gspread_cached()
    if gc is None: st.error("Google Sheets authentication failed. Cannot load data."); return pd.DataFrame()
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame()
    if not ws_name: st.error("Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame()
    try:
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url)
        ws = ss.worksheet(ws_name)
        data = ws.get_all_records(head=1, expected_headers=None)
        if not data: st.warning("No data in sheet."); return pd.DataFrame()
        df_loaded_internal = pd.DataFrame(data)
        if df_loaded_internal.empty: st.warning("Empty DataFrame after load."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound: st.error(f"Sheet Not Found: '{url}'. Check URL & permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: st.error(f"Worksheet Not Found: '{ws_name}'."); return pd.DataFrame()
    except Exception as e: st.error(f"Error Loading Data: {e}"); return pd.DataFrame()

    df_loaded_internal.columns = df_loaded_internal.columns.str.strip()
    date_cols = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for col, new_col in date_cols.items():
        if col in df_loaded_internal: df_loaded_internal[new_col] = robust_to_datetime(df_loaded_internal[col].astype(str).str.replace('\n','',regex=False).str.strip())
        else: df_loaded_internal[new_col] = pd.NaT
        if col == 'onboardingDate': df_loaded_internal['onboarding_date_only'] = df_loaded_internal[new_col].dt.date
    if 'deliveryDate_dt' in df_loaded_internal and 'confirmationTimestamp_dt' in df_loaded_internal:
        df_loaded_internal['deliveryDate_dt'] = pd.to_datetime(df_loaded_internal['deliveryDate_dt'], errors='coerce')
        df_loaded_internal['confirmationTimestamp_dt'] = pd.to_datetime(df_loaded_internal['confirmationTimestamp_dt'], errors='coerce')
        def to_utc(s):
            if pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
                try: return s.dt.tz_localize('UTC') if s.dt.tz is None else s.dt.tz_convert('UTC')
                except Exception: return s
            return s
        df_loaded_internal['days_to_confirmation'] = (to_utc(df_loaded_internal['confirmationTimestamp_dt']) - to_utc(df_loaded_internal['deliveryDate_dt'])).dt.days
    else: df_loaded_internal['days_to_confirmation'] = pd.NA
    str_cols_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary']
    for col in str_cols_ensure:
        if col not in df_loaded_internal.columns: df_loaded_internal[col] = ""
        else: df_loaded_internal[col] = df_loaded_internal[col].astype(str).fillna("")
    if 'score' not in df_loaded_internal.columns: df_loaded_internal['score'] = pd.NA
    df_loaded_internal['score'] = pd.to_numeric(df_loaded_internal['score'], errors='coerce')
    checklist_cols_to_ensure = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS + ['onboardingWelcome']
    for col in checklist_cols_to_ensure:
        if col not in df_loaded_internal.columns: df_loaded_internal[col] = pd.NA
    return df_loaded_internal

@st.cache_data
def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_in):
    if df_in.empty: return 0, 0.0, pd.NA, pd.NA
    total = len(df_in)
    sr = (df_in[df_in['status'].astype(str).str.lower()=='confirmed'].shape[0]/total*100) if total>0 else 0.0
    avg_s = pd.to_numeric(df_in['score'], errors='coerce').mean()
    avg_d = pd.to_numeric(df_in['days_to_confirmation'], errors='coerce').mean()
    return total, sr, avg_s, avg_d

def get_default_date_range(series):
    today=date.today(); s=today.replace(day=1); e=today; min_d,max_d = None,None
    if series is not None and not series.empty and series.notna().any():
        dates = pd.to_datetime(series,errors='coerce').dt.date.dropna()
        if not dates.empty:
            min_d_series, max_d_series = dates.min(), dates.max()
            min_d = min_d_series; max_d = max_d_series
            s = max(s, min_d_series); e = min(e, max_d_series)
            if s > e : s,e = min_d_series,max_d_series
    return s,e,min_d,max_d

# --- Initialize Session State ---
default_s_init, default_e_init, _, _ = get_default_date_range(None)
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'date_range' not in st.session_state: st.session_state.date_range = (default_s_init, default_e_init)
if 'active_tab' not in st.session_state: st.session_state.active_tab = "🌌 Overview"
# Initialize all filter-related session state keys
for f_key in ['repName_filter', 'status_filter', 'clientSentiment_filter']:
    if f_key not in st.session_state: st.session_state[f_key] = []
for s_key in ['licenseNumber_search', 'storeName_search', 'selected_transcript_key']:
    if s_key not in st.session_state: st.session_state[s_key] = "" if "search" in s_key else None

# --- Data Loading Trigger ---
if not st.session_state.data_loaded:
    df_from_load_func = load_data_from_google_sheet()
    if not df_from_load_func.empty:
        st.session_state.df_original = df_from_load_func
        st.session_state.data_loaded = True
        ds,de,min_data_date,max_data_date = get_default_date_range(df_from_load_func.get('onboarding_date_only'))
        st.session_state.date_range = (ds,de)
        st.session_state.min_data_date_for_filter = min_data_date
        st.session_state.max_data_date_for_filter = max_data_date
        st.sidebar.success(f"Data loaded: {len(df_from_load_func)} records.")
    else:
        st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF
        st.session_state.data_loaded = False
df_original = st.session_state.df_original

st.title("🌌 Onboarding Performance Dashboard 🌌")

if not st.session_state.data_loaded or df_original.empty:
    st.warning("No data loaded or data is empty. Check configurations or try refreshing.")
    if st.sidebar.button("🔄 Attempt Data Reload", key="refresh_fail_button_v3_6"):
        st.cache_data.clear(); st.session_state.data_loaded = False; st.rerun()

with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=True):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data", key="refresh_main_button_v3_6"):
    st.cache_data.clear(); st.session_state.data_loaded = False; st.rerun()

st.sidebar.header("🔍 Filters")
min_dt_filter = st.session_state.get('min_data_date_for_filter', default_s_init)
max_dt_filter = st.session_state.get('max_data_date_for_filter', default_e_init)
current_date_range_start, current_date_range_end = st.session_state.date_range
if min_dt_filter and current_date_range_start < min_dt_filter: current_date_range_start = min_dt_filter
if max_dt_filter and current_date_range_end > max_dt_filter: current_date_range_end = max_dt_filter
if current_date_range_start > current_date_range_end:
    current_date_range_start = min_dt_filter if min_dt_filter else default_s_init
    current_date_range_end = max_dt_filter if max_dt_filter else default_e_init

if min_dt_filter and max_dt_filter :
    sel_range = st.sidebar.date_input("Date Range:", value=(current_date_range_start, current_date_range_end),
                                      min_value=min_dt_filter, max_value=max_dt_filter, key="date_sel_v3_6")
    if sel_range != st.session_state.date_range: st.session_state.date_range = sel_range; st.rerun()
else:
    st.sidebar.warning("Date data for filtering is not fully available. Defaulting range.")
    sel_range_fallback = st.sidebar.date_input("Date Range:", value=(default_s_init, default_e_init), key="date_sel_fallback_v3_6")
    if sel_range_fallback != st.session_state.date_range: st.session_state.date_range = sel_range_fallback; st.rerun()
start_dt,end_dt = st.session_state.date_range

search_cols_definition = {"licenseNumber":"License Number", "storeName":"Store Name"}
for k,lbl in search_cols_definition.items():
    val = st.sidebar.text_input(f"Search {lbl} (on all data):",value=st.session_state[k+"_search"],key=f"{k}_widget_v3_6")
    if val != st.session_state[k+"_search"]: st.session_state[k+"_search"]=val; st.rerun()
cat_filters_definition = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for k,lbl in cat_filters_definition.items():
    if not df_original.empty and k in df_original.columns and df_original[k].notna().any():
        opts = sorted([v for v in df_original[k].astype(str).dropna().unique() if v.strip()])
        sel = [v for v in st.session_state[k+"_filter"] if v in opts]
        new_sel = st.sidebar.multiselect(f"Filter by {lbl}:",opts,default=sel,key=f"{k}_widget_v3_6")
        if new_sel != st.session_state[k+"_filter"]: st.session_state[k+"_filter"]=new_sel; st.rerun()

def clear_filters_cb():
    ds_clear, de_clear, min_d_clear, max_d_clear = get_default_date_range(st.session_state.df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds_clear, de_clear)
    st.session_state.min_data_date_for_filter = min_d_clear; st.session_state.max_data_date_for_filter = max_d_clear
    for k_search in search_cols_definition: st.session_state[k_search+"_search"]=""
    for k_cat in cat_filters_definition: st.session_state[k_cat+"_filter"]=[]
    st.session_state.selected_transcript_key = None
if st.sidebar.button("🧹 Clear All Filters",on_click=clear_filters_cb,use_container_width=True, key="clear_filters_v3_6"): st.rerun()

# --- Data Filtering Logic ---
df_filtered = pd.DataFrame()
if not df_original.empty: # Ensure df_original is not empty before trying to filter
    df_working = df_original.copy()
    license_search_term = st.session_state.get("licenseNumber_search", "")
    if license_search_term and "licenseNumber" in df_working.columns:
        df_working = df_working[df_working['licenseNumber'].astype(str).str.contains(license_search_term, case=False, na=False)]
    store_search_term = st.session_state.get("storeName_search", "")
    if store_search_term and "storeName" in df_working.columns:
        df_working = df_working[df_working['storeName'].astype(str).str.contains(store_search_term, case=False, na=False)]
    if start_dt and end_dt and 'onboarding_date_only' in df_working.columns and df_working['onboarding_date_only'].notna().any():
        date_objects_for_filtering = pd.to_datetime(df_working['onboarding_date_only'], errors='coerce').dt.date
        valid_dates_mask = date_objects_for_filtering.notna()
        date_filter_mask = pd.Series([False] * len(df_working), index=df_working.index)
        if valid_dates_mask.any(): # Apply filter only if there are valid dates to compare
             date_filter_mask[valid_dates_mask] = \
                (date_objects_for_filtering[valid_dates_mask] >= start_dt) & \
                (date_objects_for_filtering[valid_dates_mask] <= end_dt)
        df_working = df_working[date_filter_mask]
    for col_name, _ in cat_filters_definition.items():
        selected_values = st.session_state.get(f"{col_name}_filter", [])
        if selected_values and col_name in df_working.columns:
            df_working = df_working[df_working[col_name].astype(str).isin(selected_values)]
    df_filtered = df_working.copy()

# --- Plotly Base Layout ---
plotly_base_layout_settings = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR, "title_x":0.5,
    "xaxis_showgrid":False, "yaxis_showgrid":False, "margin": dict(l=40, r=20, t=60, b=40),
    "font_color": ACTIVE_TEXT_PRIMARY, "title_font_color": ACTIVE_ACCENT_PRIMARY,
    "xaxis_title_font_color": ACTIVE_TEXT_SECONDARY, "yaxis_title_font_color": ACTIVE_TEXT_SECONDARY,
    "xaxis_tickfont_color": ACTIVE_TEXT_SECONDARY, "yaxis_tickfont_color": ACTIVE_TEXT_SECONDARY,
    "legend_font_color": ACTIVE_TEXT_PRIMARY,
}

# --- MTD Metrics ---
today_date_mtd = date.today(); mtd_s = today_date_mtd.replace(day=1)
prev_mtd_e = mtd_s - timedelta(days=1); prev_mtd_s = prev_mtd_e.replace(day=1)
df_mtd, df_prev_mtd = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_s_orig = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date
    valid_mask_orig = dates_s_orig.notna()
    if valid_mask_orig.any():
        df_valid_orig = df_original[valid_mask_orig].copy(); valid_dates_orig = dates_s_orig[valid_mask_orig]
        mtd_mask_calc = (valid_dates_orig >= mtd_s) & (valid_dates_orig <= today_date_mtd)
        prev_mask_calc = (valid_dates_orig >= prev_mtd_s) & (valid_dates_orig <= prev_mtd_e)
        df_mtd = df_valid_orig[mtd_mask_calc.values]; df_prev_mtd = df_valid_orig[prev_mask_calc.values]
tot_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)
tot_prev,_,_,_ = calculate_metrics(df_prev_mtd)
delta_mtd = tot_mtd - tot_prev if pd.notna(tot_mtd) and pd.notna(tot_prev) else None

# --- Tab Navigation ---
tab_names = ["🌌 Overview", "📊 Analysis & Transcripts", "📈 Trends & Distributions"]
selected_tab = st.radio("Navigation:", tab_names, index=tab_names.index(st.session_state.active_tab),
                        horizontal=True, key="main_tab_selector_v3_6")
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()

# --- Display Content ---
if st.session_state.active_tab == "🌌 Overview":
    # ... (Overview content - unchanged, will use new theme) ...
    with st.container():
        st.header("📈 Month-to-Date (MTD) Overview")
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Onboardings MTD", tot_mtd or "0", f"{delta_mtd:+}" if delta_mtd is not None and pd.notna(delta_mtd) else "N/A")
        with c2: st.metric("Success Rate MTD", f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A")
        with c3: st.metric("Avg Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
        with c4: st.metric("Avg Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")
    with st.container():
        st.header("📊 Filtered Data Overview")
        if not df_filtered.empty:
            tot_filt, sr_filt, score_filt, days_filt = calculate_metrics(df_filtered)
            fc1,fc2,fc3,fc4 = st.columns(4)
            with fc1: st.metric("Filtered Onboardings", tot_filt or "0")
            with fc2: st.metric("Filtered Success Rate", f"{sr_filt:.1f}%" if pd.notna(sr_filt) else "N/A")
            with fc3: st.metric("Filtered Avg Score", f"{score_filt:.2f}" if pd.notna(score_filt) else "N/A")
            with fc4: st.metric("Filtered Avg Days Confirm", f"{days_filt:.1f}" if pd.notna(days_filt) else "N/A")
        else: st.info("No data matches current filters for Overview.")

elif st.session_state.active_tab == "📊 Analysis & Transcripts":
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table = df_filtered.copy().reset_index(drop=True)
    cols_to_try = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score',
                   'clientSentiment', 'days_to_confirmation'] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
    cols_for_display = [col for col in cols_to_try if col in df_display_table.columns]
    other_cols = [col for col in df_display_table.columns if col not in cols_for_display and
                  not col.endswith(('_utc', '_str_original', '_dt')) and col not in ['fullTranscript', 'summary', 'onboarding_date_only']]
    cols_for_display = list(dict.fromkeys(cols_for_display + other_cols))

    if not df_display_table.empty:
        st.dataframe(df_display_table[cols_for_display], use_container_width=True, height=300)
        # ... (Transcript viewer - unchanged, will use new theme) ...
        st.markdown("---")
        st.subheader("🔍 View Full Onboarding Details & Transcript")
        if not df_display_table.empty and 'fullTranscript' in df_display_table.columns:
            transcript_options = { f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_table.iterrows() }
            if transcript_options:
                current_selection = st.session_state.selected_transcript_key
                options_list = [None] + list(transcript_options.keys())
                try:
                    current_index = options_list.index(current_selection)
                except ValueError:
                    current_index = 0 # Default to "Choose an entry..." if current_selection not found

                selected_key_display = st.selectbox("Select onboarding to view details:", options=options_list,
                                                    index=current_index, format_func=lambda x: "Choose an entry..." if x is None else x,
                                                    key="transcript_selector_v3_6")
                if selected_key_display != st.session_state.selected_transcript_key :
                    st.session_state.selected_transcript_key = selected_key_display
                    st.rerun() # Rerun to reflect selection immediately if needed, or remove if content updates without it

                if st.session_state.selected_transcript_key :
                    selected_idx = transcript_options[st.session_state.selected_transcript_key]
                    selected_row = df_display_table.loc[selected_idx]
                    st.markdown("##### Onboarding Summary:")
                    summary_html = "<div class='transcript-summary-grid'>"
                    summary_items = { "Store": selected_row.get('storeName', 'N/A'), "Rep": selected_row.get('repName', 'N/A'),
                                      "Score": selected_row.get('score', 'N/A'), "Status": selected_row.get('status', 'N/A'),
                                      "Sentiment": selected_row.get('clientSentiment', 'N/A')}
                    for item_label, item_value in summary_items.items(): summary_html += f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>"
                    data_summary_text = selected_row.get('summary', 'N/A'); summary_html += f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary:</strong> {data_summary_text}</div></div>"
                    st.markdown(summary_html, unsafe_allow_html=True)
                    st.markdown("##### Key Requirement Checks:")
                    for item_column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                        details = KEY_REQUIREMENT_DETAILS.get(item_column_name)
                        if details:
                            desc = details.get("description", item_column_name.replace('_',' ').title()); item_type = details.get("type", "")
                            val_str = str(selected_row.get(item_column_name, "")).lower(); met = val_str in ['true', '1', 'yes']
                            emoji = "✅" if met else "❌"; type_tag = f"<span class='type'>[{item_type}]</span>" if item_type else ""
                            st.markdown(f"<div class='requirement-item'>{emoji} {desc} {type_tag}</div>", unsafe_allow_html=True)
                    st.markdown("---"); st.markdown("##### Full Transcript:")
                    content = selected_row.get('fullTranscript', "")
                    if content:
                        html_transcript = "<div class='transcript-container'>"
                        for line in content.replace('\\n', '\n').split('\n'):
                            line = line.strip();
                            if not line: continue
                            parts = line.split(":", 1); speaker = f"<strong>{parts[0].strip()}:</strong>" if len(parts) == 2 else ""
                            msg = parts[1].strip().replace('\n', '<br>') if len(parts) == 2 else line.replace('\n', '<br>')
                            html_transcript += f"<p class='transcript-line'>{speaker} {msg}</p>"
                        st.markdown(html_transcript + "</div>", unsafe_allow_html=True)
                    else: st.info("No transcript available or empty.")
            else: st.info("No entries in the filtered table to select for details.")
        else: st.info("No data in table for transcript viewer, or 'fullTranscript' column missing.")
        st.markdown("---")
        csv_data = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data", csv_data, 'filtered_data.csv', 'text/csv', use_container_width=True, key="download_csv_v3_6")
    elif not df_original.empty: st.info("No data matches current filters for table display.")
    else: st.info("No data loaded to display.")

    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        c1_charts, c2_charts = st.columns(2)
        with c1_charts:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_counts = df_filtered['status'].value_counts().reset_index()
                status_fig = px.bar(status_counts, x='status', y='count', color='status', title="Onboarding Status Distribution",
                                     color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ) # Theme-aware
                status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_counts = df_filtered['repName'].value_counts().reset_index()
                rep_fig = px.bar(rep_counts, x='repName', y='count', color='repName', title="Onboardings by Representative",
                                     color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ) # Theme-aware
                rep_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig, use_container_width=True)
        with c2_charts:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sent_counts = df_filtered['clientSentiment'].value_counts().reset_index()
                # Map sentiment to colors from the active theme's sentiment map
                current_sentiment_map = {
                    s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), ACTIVE_ACCENT_MUTED)
                    for s in sent_counts['clientSentiment'].unique()
                }
                sent_fig = px.pie(sent_counts, names='clientSentiment', values='count', hole=0.5, title="Client Sentiment Breakdown",
                                  color='clientSentiment', color_discrete_map=current_sentiment_map) # Theme-aware
                sent_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(sent_fig, use_container_width=True)

            df_conf_chart = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            actual_key_cols_for_chart = [col for col in ORDERED_CHART_REQUIREMENTS if col in df_conf_chart.columns]
            checklist_data_for_chart = []
            if not df_conf_chart.empty and actual_key_cols_for_chart:
                for item_col_name_for_chart in actual_key_cols_for_chart:
                    item_details_obj = KEY_REQUIREMENT_DETAILS.get(item_col_name_for_chart)
                    chart_label_for_bar = item_details_obj.get("chart_label", item_col_name_for_chart.replace('_',' ').title()) if item_details_obj else item_col_name_for_chart.replace('_',' ').title()
                    map_bool_for_chart = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
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
                                                     color_discrete_sequence=[ACTIVE_ACCENT_PRIMARY]) # Use single active accent
                        checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(checklist_bar_fig, use_container_width=True)
                else: st.info("No data for key requirement chart (confirmed).")
            else: st.info("No 'confirmed' onboardings or checklist columns for requirement chart.")
    else: st.info("No data matches current filters for detailed visuals.")

elif st.session_state.active_tab == "📈 Trends & Distributions":
    # ... (Trends content - apply ACTIVE_PLOTLY color sequences) ...
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_for_tab3 = df_filtered.copy()
            df_trend_for_tab3['onboarding_date_only'] = pd.to_datetime(df_trend_for_tab3['onboarding_date_only'], errors='coerce')
            df_trend_for_tab3.dropna(subset=['onboarding_date_only'], inplace=True)
            if not df_trend_for_tab3.empty:
                span_for_trend_tab3 = (df_trend_for_tab3['onboarding_date_only'].max() - df_trend_for_tab3['onboarding_date_only'].min()).days
                freq_for_trend_tab3 = 'D' if span_for_trend_tab3 <= 62 else ('W-MON' if span_for_trend_tab3 <= 365*1.5 else 'ME')
                data_for_trend_tab3 = df_trend_for_tab3.set_index('onboarding_date_only').resample(freq_for_trend_tab3).size().reset_index(name='count')
                if not data_for_trend_tab3.empty:
                    fig_for_trend_tab3 = px.line(data_for_trend_tab3, x='onboarding_date_only', y='count', markers=True,
                                      title="Onboardings Over Filtered Period", color_discrete_sequence=[ACTIVE_ACCENT_HIGHLIGHT]) # Theme-aware
                    fig_for_trend_tab3.update_layout(plotly_base_layout_settings)
                    st.plotly_chart(fig_for_trend_tab3, use_container_width=True)
                else: st.info("Not enough data for trend plot after resampling.")
            else: st.info("No valid date data for trend chart after processing.")
        else: st.info("Date column missing for trend chart.")

        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist_tab3 = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist_tab3.empty:
                nbins_for_hist_tab3 = max(10, min(50, int(len(days_data_for_hist_tab3)/5))) if len(days_data_for_hist_tab3) > 20 else (len(days_data_for_hist_tab3.unique()) or 10)
                fig_days_dist_hist_tab3 = px.histogram(days_data_for_hist_tab3, nbins=nbins_for_hist_tab3,
                                           title="Days to Confirmation Distribution", color_discrete_sequence=[ACTIVE_ACCENT_SECONDARY]) # Theme-aware
                fig_days_dist_hist_tab3.update_layout(plotly_base_layout_settings)
                st.plotly_chart(fig_days_dist_hist_tab3, use_container_width=True)
            else: st.info("No valid 'Days to Confirmation' data for distribution plot.")
        else: st.info("'Days to Confirmation' column missing for distribution plot.")
    else: st.info("No data matches current filters for Trends & Distributions.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v3.6 | Secured Access")