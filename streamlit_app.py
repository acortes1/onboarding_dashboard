# onboarding_dashboard/streamlit_app.py
# streamlit_app.py - v6.1.0 (Visually Revamped - Embedded CSS)
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
from dateutil import tz  # For PST conversion
from pathlib import Path

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Dashboard v6.1.0",
    page_icon="💎", # Changed icon
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Embedded CSS ---
def get_dashboard_css():
    """Returns the full CSS string for the dashboard."""
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Playfair+Display:wght@700&display=swap');

    /* --- Base Variables & Font Setup --- */
    :root {
        --font-body: 'Inter', sans-serif;
        --font-display: 'Playfair Display', serif;

        --border-radius-sm: 4px;
        --border-radius-md: 8px;
        --border-radius-lg: 16px;
        --border-radius-xl: 20px;

        --spacing-xs: 4px;
        --spacing-sm: 8px;
        --spacing-md: 16px;
        --spacing-lg: 24px;
        --spacing-xl: 32px;

        --transition-speed: 150ms;
        --box-shadow-soft: 0 4px 12px rgba(0, 0, 0, 0.05);
        --box-shadow-medium: 0 8px 24px rgba(0, 0, 0, 0.1);
    }

    /* --- Light Theme Variables --- */
    [data-theme="light"] {
        --color-background: #FFFFFF;
        --color-surface: #F9FAFB;
        --color-primary: #0A4B44;
        --color-secondary: #00A08C;
        --color-accent: #0A4B44;
        --color-success: #10B981;
        --color-warning: #F59E0B;
        --color-error: #EF4444;
        --color-text-primary: #1F2937;
        --color-text-secondary: #6B7280;
        --color-border: #E5E7EB;
        --color-table-cell-bg: #FFFFFF;
        --color-table-cell-text: #1F2937;
        --color-table-hover-bg: #F3F4F6;
        --color-scrollbar-thumb: #D1D5DB;
        --color-scrollbar-track: #F9FAFB;
        --color-glass-bg: rgba(255, 255, 255, 0.6);
        --color-kpi-border: rgba(10, 75, 68, 0.4);
    }

    /* --- Dark Theme Variables --- */
    [data-theme="dark"] {
        --color-background: #0D0D0F;
        --color-surface: #1A1A1C;
        --color-primary: #00E0B6;
        --color-secondary: #00A08C;
        --color-accent: #00E0B6;
        --color-success: #34D399;
        --color-warning: #FBBF24;
        --color-error: #F87171;
        --color-text-primary: #F9FAFB;
        --color-text-secondary: #9CA3AF;
        --color-border: #374151;
        --color-table-cell-bg: #1A1A1C;
        --color-table-cell-text: #F9FAFB;
        --color-table-hover-bg: #2d2d30;
        --color-scrollbar-thumb: #4B5563;
        --color-scrollbar-track: #1A1A1C;
        --color-glass-bg: rgba(26, 26, 28, 0.6);
        --color-kpi-border: rgba(0, 224, 182, 0.4);
    }

    /* --- Base Styles --- */
    body, .stApp {
        font-family: var(--font-body);
        background-color: var(--color-background);
        color: var(--color-text-primary);
        transition: background-color var(--transition-speed) ease-in-out, color var(--transition-speed) ease-in-out;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        letter-spacing: 0.2px;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-display);
        color: var(--color-primary) !important; /* Use important if needed */
        font-weight: 700;
    }

    .main-title {
        font-family: var(--font-display);
        color: var(--color-primary);
        font-size: 2.8rem;
        text-align: center;
        border-bottom: 2px solid var(--color-primary);
        padding-bottom: 0.6em;
        margin-bottom: 1em !important;
    }

    h2 {
        font-size: 1.8rem;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 0.4em;
        margin-top: var(--spacing-lg);
        margin-bottom: var(--spacing-md);
        color: var(--color-secondary) !important;
    }
    h5 { font-family: var(--font-body); font-weight: 600; color: var(--color-primary) !important; }
    h6 { font-family: var(--font-body); font-weight: 600; color: var(--color-secondary) !important; }

    /* --- Layout --- */
    .main .block-container {
        max-width: 1600px;
        padding: var(--spacing-md) var(--spacing-lg) var(--spacing-xl);
    }

    /* --- KPI Cards --- */
    div[data-testid="stMetric"] {
        background: var(--color-glass-bg);
        backdrop-filter: blur(10px) saturate(150%);
        -webkit-backdrop-filter: blur(10px) saturate(150%);
        border-radius: var(--border-radius-lg);
        border: 2px solid var(--color-kpi-border);
        box-shadow: var(--box-shadow-soft);
        padding: 1.5em 1.8em;
        transition: transform var(--transition-speed) ease-out, box-shadow var(--transition-speed) ease-out;
        will-change: transform;
        margin-bottom: var(--spacing-md);
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: var(--box-shadow-medium);
    }

    div[data-testid="stMetricLabel"] > div {
        font-family: var(--font-body);
        font-size: 1rem;
        font-weight: 600;
        color: var(--color-text-secondary);
        opacity: 0.9;
        text-transform: uppercase;
    }

    div[data-testid="stMetricValue"] > div, div[data-testid="stMetricValue"] {
        font-family: var(--font-display);
        font-size: 3rem !important;
        color: var(--color-primary) !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricDelta"] > div {
        color: var(--color-text-secondary) !important;
        opacity: 0.8;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricDelta"] span[data-testid="metric-delta-indicator-up"] { color: var(--color-success) !important; }
    div[data-testid="stMetricDelta"] span[data-testid="metric-delta-indicator-down"] { color: var(--color-error) !important; }


    /* --- Sidebar --- */
    div[data-testid="stSidebar"] {
        background-color: var(--color-surface);
        border-right: 1px solid var(--color-border);
        padding: var(--spacing-md);
    }
    div[data-testid="stSidebar"] h1,
    div[data-testid="stSidebar"] h2,
    div[data-testid="stSidebar"] h3 {
        color: var(--color-primary) !important;
    }
    div[data-testid="stSidebar"] .stButton > button {
        background-color: var(--color-primary);
        color: var(--color-background);
        border: 1px solid var(--color-primary);
        border-radius: var(--border-radius-md);
        transition: background-color var(--transition-speed), transform var(--transition-speed);
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: var(--color-secondary);
        border: 1px solid var(--color-secondary);
        transform: translateY(-2px);
    }

    /* --- Buttons --- */
    div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
        border-radius: var(--border-radius-md);
        font-weight: 600;
        transition: transform var(--transition-speed) ease-out, box-shadow var(--transition-speed) ease-out, background-color var(--transition-speed), color var(--transition-speed);
        border: 2px solid var(--color-primary);
        background-color: transparent;
        color: var(--color-primary);
        padding: var(--spacing-sm) var(--spacing-md);
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        background-color: var(--color-primary);
        color: var(--color-background); /* White or Black depending on theme */
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: var(--color-primary);
        color: var(--color-background);
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: var(--color-secondary);
        border-color: var(--color-secondary);
    }

    /* --- Tables --- */
    .custom-table-container {
        border-radius: var(--border-radius-lg);
        box-shadow: var(--box-shadow-soft);
        border: 1px solid var(--color-border);
        overflow: hidden;
        background-color: var(--color-surface);
        margin-bottom: var(--spacing-lg);
    }
    .custom-styled-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
        color: var(--color-table-cell-text);
    }
    .custom-styled-table th {
        background-color: var(--color-surface);
        color: var(--color-primary);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 2px solid var(--color-primary);
        padding: var(--spacing-md) var(--spacing-sm);
        text-align: left;
    }
    .custom-styled-table td {
        border-bottom: 1px solid var(--color-border);
        padding: var(--spacing-sm) var(--spacing-sm);
        vertical-align: middle;
    }
    .custom-styled-table tbody tr:last-child td {
        border-bottom: none;
    }
    .custom-styled-table tbody tr:hover {
        background-color: var(--color-table-hover-bg);
    }

    /* --- Status Chips --- */
    .status-chip {
        display: inline-flex;
        align-items: center;
        padding: var(--spacing-xs) var(--spacing-sm);
        border-radius: 12px; /* Pill shape */
        font-size: 0.8rem;
        font-weight: 600;
        line-height: 1;
        white-space: nowrap;
    }

    .status-chip::before {
        content: '';
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: var(--spacing-sm);
        display: inline-block;
    }

    .status-confirmed { background-color: color-mix(in srgb, var(--color-success) 15%, transparent); color: var(--color-success); }
    .status-confirmed::before { background-color: var(--color-success); }
    .status-unconfirmed { background-color: color-mix(in srgb, var(--color-warning) 15%, transparent); color: var(--color-warning); }
    .status-unconfirmed::before { background-color: var(--color-warning); }
    .status-error { background-color: color-mix(in srgb, var(--color-error) 15%, transparent); color: var(--color-error); }
    .status-error::before { background-color: var(--color-error); }
    .status-unknown { background-color: color-mix(in srgb, var(--color-text-secondary) 15%, transparent); color: var(--color-text-secondary); }
    .status-unknown::before { background-color: var(--color-text-secondary); }

    /* --- Charts --- */
    .stPlotlyChart {
        border-radius: var(--border-radius-lg);
        padding: 1em;
        background: var(--color-surface);
        box-shadow: var(--box-shadow-soft);
        border: 1px solid var(--color-border);
    }

    /* --- Filter Summary & Misc --- */
    .active-filters-summary {
        padding: 1em 1.5em;
        margin-bottom: var(--spacing-lg);
        border-radius: var(--border-radius-md);
        border: 1px solid var(--color-border);
        background-color: var(--color-surface);
        font-size: 0.9rem;
        color: var(--color-text-secondary);
    }

    /* --- Login --- */
    .login-container { text-align: center; margin-top: 5vh; }
    .login-box {
        background: var(--color-surface);
        border-radius: var(--border-radius-xl);
        box-shadow: var(--box-shadow-medium);
        border: 1px solid var(--color-border);
        padding: var(--spacing-xl);
        max-width: 450px;
        margin: auto;
    }
    .login-container h2 { color: var(--color-primary); margin-bottom: var(--spacing-md); }
    .login-container p { color: var(--color-text-secondary); margin-bottom: var(--spacing-lg); }
    .login-container .stButton > button {
        background-color: var(--color-primary) !important;
        color: var(--color-background) !important;
    }

    /* --- Transcript/Details --- */
    .transcript-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md); background-color: var(--color-surface); padding: var(--spacing-md); border-radius: var(--border-radius-md); margin-bottom: var(--spacing-md); }
    .transcript-summary-item { font-size: 0.95rem; }
    .transcript-summary-item strong { color: var(--color-primary); }
    .transcript-details-section { background-color: var(--color-surface); padding: var(--spacing-md); border-radius: var(--border-radius-md); margin-bottom: var(--spacing-md); }
    .requirement-item { margin-bottom: var(--spacing-xs); font-size: 0.9rem; }
    .requirement-item .type { font-size: 0.75rem; background-color: var(--color-border); color: var(--color-text-secondary); padding: 2px 6px; border-radius: var(--border-radius-sm); margin-left: var(--spacing-sm); }
    .transcript-container { background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--border-radius-md); padding: var(--spacing-md); max-height: 400px; overflow-y: auto; font-size: 0.85rem; line-height: 1.6; }
    .transcript-line { margin-bottom: var(--spacing-sm); }
    .transcript-line strong { color: var(--color-primary); }

    /* --- Footer --- */
    .footer { text-align: center; padding: var(--spacing-md) 0; color: var(--color-text-secondary); font-size: 0.8rem; border-top: 1px solid var(--color-border); margin-top: var(--spacing-xl); }

    /* --- Scrollbars --- */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--color-scrollbar-track); border-radius: 4px; }
    ::-webkit-scrollbar-thumb { background: var(--color-scrollbar-thumb); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--color-secondary); }

    /* Reduce Motion */
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }
    """

def load_and_inject_css():
    """Loads and injects the custom CSS for the application."""
    st.markdown(f"<style>{get_dashboard_css()}</style>", unsafe_allow_html=True)

load_and_inject_css()

# --- Constants & Configuration ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and the Company.", "type": "Secondary", "chart_label": "Intro Self & Company"},
    'confirmKitReceived': {"description": "Confirm kit and initial order received.", "type": "Primary", "chart_label": "Kit & Order Recv'd"},
    'offerDisplayHelp': {"description": "Ask about help setting up in-store display.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule budtender training & first promo.", "type": "Primary", "chart_label": "Sched. Training/Promo"},
    'providePromoCreditLink': {"description": "Provide link for promo-credit requests.", "type": "Secondary", "chart_label": "Promo Credit Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
PST_TIMEZONE = tz.gettz('America/Los_Angeles'); UTC_TIMEZONE = tz.tzutc()

# Color definitions (Ensure these match theme.css for Plotly)
GOLD_ACCENT_DARK = "#00E0B6"
GOLD_ACCENT_LIGHT = "#0A4B44"

PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)"
THEME_PLOTLY = st.get_option("theme.base")
TEXT_COLOR_FOR_PLOTLY = "#FFFFFF" if THEME_PLOTLY == "dark" else "#0D0D0F"
GOLD_ACCENT = GOLD_ACCENT_DARK if THEME_PLOTLY == "dark" else GOLD_ACCENT_LIGHT
ACTIVE_PLOTLY_PRIMARY_SEQ = [GOLD_ACCENT, '#00A08C', '#34D399', '#FBBF24', '#F87171'] # Updated Palette
ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Plotly # Using a standard one
ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#34D399', 'negative': '#F87171', 'neutral': '#9CA3AF' } # Updated Palette

plotly_base_layout_settings = {"plot_bgcolor": PLOT_BG_COLOR_PLOTLY, "paper_bgcolor": PLOT_BG_COLOR_PLOTLY, "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":True, "yaxis_gridcolor": 'rgba(0, 224, 182, 0.15)', "margin": dict(l=50, r=30, t=70, b=50), "font_color": TEXT_COLOR_FOR_PLOTLY, "title_font_color": GOLD_ACCENT, "title_font_size": 18, "xaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "xaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "legend_font_color": TEXT_COLOR_FOR_PLOTLY, "legend_title_font_color": GOLD_ACCENT}

# --- Google SSO & Domain Check ---
def check_login_and_domain():
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", None)
    if not st.user.is_logged_in:
        st.markdown("""
            <div class='login-container'>
                <div class='login-box'>
                    <h2>🔑 Dashboard Access</h2>
                    <p>Please log in using your <b>authorized</b> Google account to access the Onboarding Dashboard.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        return False
    user_email = st.user.email
    if not user_email:
        st.error("Could not retrieve user email. Please try logging in again.")
        st.button("Log out", on_click=st.logout, type="secondary")
        return False
    if allowed_domain and not user_email.endswith(f"@{allowed_domain}"):
        st.error(f"🚫 Access Denied. Only users from the '{allowed_domain}' domain are allowed.")
        st.info(f"You are attempting to log in as: {user_email}")
        st.button("Log out", on_click=st.logout, type="secondary")
        return False
    return True

# --- Data Loading & Processing Functions ---
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    gcp_secrets_obj = st.secrets.get("gcp_service_account")
    if gcp_secrets_obj is None: st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND."); return None
    try:
        gcp_secrets_dict = dict(gcp_secrets_obj)
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing_keys = [k for k in required_keys if gcp_secrets_dict.get(k) is None]
        if missing_keys: st.error(f"🚨 Error: GCP secrets dict missing keys: {', '.join(missing_keys)}."); return None
        creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except (TypeError, ValueError, Exception) as e:
        st.error(f"🚨 Error Processing GCP Secrets or Authenticating: {e}. Check format/permissions."); return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null', 'na']).all():
        common_formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
        for dayfirst_setting in [False, True]:
            for fmt in common_formats:
                try:
                    use_dayfirst_for_fmt = ('%m' in fmt and '%d' in fmt and dayfirst_setting)
                    temp_dates = pd.to_datetime(series, format=fmt, errors='coerce', dayfirst=use_dayfirst_for_fmt)
                    if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                    if dates.notnull().all(): break
                except ValueError: continue
            if dates.notnull().all(): break
    return dates

def format_datetime_to_pst_str(dt_series):
    if not pd.api.types.is_datetime64_any_dtype(dt_series) or dt_series.isnull().all():
        return dt_series
    def convert_element(element):
        if pd.isna(element): return None
        try:
            if element.tzinfo is None:
                utc_element = element.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
            else:
                utc_element = element.tz_convert(UTC_TIMEZONE)
            pst_element = utc_element.tz_convert(PST_TIMEZONE)
            return pst_element.strftime('%Y-%m-%d %I:%M %p PST')
        except Exception: return str(element)
    try:
        if dt_series.dt.tz is None:
            utc_series = dt_series.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
        else:
            utc_series = dt_series.dt.tz_convert(UTC_TIMEZONE)
        pst_series = utc_series.dt.tz_convert(PST_TIMEZONE)
        return pst_series.apply(lambda x: x.strftime('%Y-%m-%d %I:%M %p PST') if pd.notnull(x) else None)
    except Exception:
        return dt_series.apply(convert_element)

def format_phone_number(number_str):
    if pd.isna(number_str) or not str(number_str).strip(): return ""
    digits = re.sub(r'\D', '', str(number_str))
    if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(number_str)

def capitalize_name(name_str):
    if pd.isna(name_str) or not str(name_str).strip(): return ""
    return ' '.join(word.capitalize() for word in str(name_str).split())

@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet():
    gc = authenticate_gspread_cached()
    current_time = datetime.now(UTC_TIMEZONE)
    st.session_state.last_data_refresh_time = current_time
    if gc is None: return pd.DataFrame()
    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not sheet_url_or_name: st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame()
    if not worksheet_name: st.error("🚨 Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame()
    try:
        spreadsheet = gc.open_by_url(sheet_url_or_name) if ("docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name) else gc.open(sheet_url_or_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1, expected_headers=None)
        if not data: st.warning("⚠️ No data rows in Google Sheet."); return pd.DataFrame()
        df = pd.DataFrame(data)
        df.rename(columns={col: "".join(str(col).strip().lower().split()) for col in df.columns}, inplace=True)
        column_name_map_to_code = {"licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "dcc": "licenseNumber", "storename": "storeName", "accountname": "storeName", "repname": "repName", "representative": "repName", "onboardingdate": "onboardingDate", "deliverydate": "deliveryDate", "confirmationtimestamp": "confirmationTimestamp", "confirmedat": "confirmationTimestamp", "clientsentiment": "clientSentiment", "sentiment": "clientSentiment", "fulltranscript": "fullTranscript", "transcript": "fullTranscript", "score": "score", "onboardingscore": "score", "status": "status", "onboardingstatus": "status", "summary": "summary", "callsummary": "summary", "contactnumber": "contactNumber", "phone": "contactNumber", "confirmednumber": "confirmedNumber", "verifiednumber":"confirmedNumber", "contactname": "contactName", "clientcontact": "contactName"}
        for req_key_internal in KEY_REQUIREMENT_DETAILS.keys(): column_name_map_to_code[req_key_internal.lower()] = req_key_internal
        cols_to_rename_actual = {std_col: code_col for std_col, code_col in column_name_map_to_code.items() if std_col in df.columns and code_col not in df.columns}
        df.rename(columns=cols_to_rename_actual, inplace=True)
        date_cols_map = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
        for original_col, dt_col in date_cols_map.items():
            if original_col in df.columns:
                df[original_col] = df[original_col].astype(str).str.replace('\n',' ',regex=False).str.strip()
                df[dt_col] = robust_to_datetime(df[original_col])
                df[original_col] = format_datetime_to_pst_str(df[dt_col])
            else: df[dt_col] = pd.NaT
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date if 'onboardingDate_dt' in df.columns else pd.NaT
        if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
            def ensure_utc_for_calc(series_dt):
                if pd.api.types.is_datetime64_any_dtype(series_dt) and series_dt.notna().any():
                    if series_dt.dt.tz is None:
                        return series_dt.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
                    else:
                        return series_dt.dt.tz_convert(UTC_TIMEZONE)
                return series_dt.fillna(pd.NaT)
            delivery_utc = ensure_utc_for_calc(df['deliveryDate_dt'])
            confirmation_utc = ensure_utc_for_calc(df['confirmationTimestamp_dt'])
            df['days_to_confirmation'] = (confirmation_utc - delivery_utc).dt.days
        else: df['days_to_confirmation'] = pd.NA
        for phone_col in ['contactNumber', 'confirmedNumber']:
            if phone_col in df.columns: df[phone_col] = df[phone_col].apply(format_phone_number)
        for name_col in ['repName', 'contactName']:
            if name_col in df.columns: df[name_col] = df[name_col].apply(capitalize_name)
        string_cols = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary', 'contactName', 'contactNumber', 'confirmedNumber', 'onboardingDate', 'deliveryDate', 'confirmationTimestamp']
        for col in string_cols: df[col] = df.get(col, "").astype(str).replace(['nan', 'NaN', 'None', 'NaT', '<NA>'], "", regex=False).fillna("")

        # Map 'Pending' to 'Unconfirmed' and 'Failed' to 'Error'
        df['status'] = df['status'].str.lower().replace({'pending': 'unconfirmed', 'failed': 'error'}, regex=False)
        df['status'] = df['status'].apply(lambda x: x.capitalize() if isinstance(x, str) else x)


        df['score'] = pd.to_numeric(df.get('score'), errors='coerce')
        for col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS: df[col] = df.get(col, pd.NA)
        cols_to_drop = [col for col in ['deliverydatets', 'onboardingwelcome'] if col in df.columns]
        if cols_to_drop: df = df.drop(columns=cols_to_drop)
        return df
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 GS Error: {e}. Check URL/name & permissions."); return pd.DataFrame()
    except Exception as e:
        st.error(f"🌪️ Error loading data: {e}"); return pd.DataFrame()

@st.cache_data
def convert_df_to_csv(df_to_convert): return df_to_convert.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input):
    if df_input.empty: return 0, 0.0, pd.NA, pd.NA
    total = len(df_input)
    # Using 'Confirmed' for success rate, ensure it's case-insensitive
    confirmed = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
    success_rate = (confirmed / total * 100) if total > 0 else 0.0
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    avg_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

def get_default_date_range(date_series):
    today = date.today()
    start_of_month = today.replace(day=1)
    min_date, max_date = (pd.to_datetime(date_series, errors='coerce').dt.date.dropna().min(), pd.to_datetime(date_series, errors='coerce').dt.date.dropna().max()) if date_series is not None and date_series.notna().any() else (None, None)
    start = max(start_of_month, min_date) if min_date else start_of_month
    end = min(today, max_date) if max_date else today
    return (start, end) if start <= end else ((min_date, max_date) if min_date and max_date else (start_of_month, today))

# --- Main App Logic ---
is_logged_in_and_authorized = check_login_and_domain()
if not is_logged_in_and_authorized:
    if not st.user.is_logged_in:
        _, login_col, _ = st.columns([1, 1.5, 1])
        with login_col:
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Log in with Google 🔑", on_click=st.login, use_container_width=True, key="google_login_main_btn")
    st.stop()

# --- Session State Initialization ---
default_s_init, default_e_init = get_default_date_range(None)
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'date_range' not in st.session_state: st.session_state.date_range = (default_s_init, default_e_init)
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = None
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = None
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
categorical_filter_keys = ['repName_filter', 'status_filter', 'clientSentiment_filter']
for f_key in categorical_filter_keys: st.session_state.setdefault(f_key, [])
search_field_keys = ['licenseNumber_search', 'storeName_search']
for s_key in search_field_keys: st.session_state.setdefault(s_key, "")
TAB_OVERVIEW = "📊 Overview"; TAB_DETAILED_ANALYSIS = "🔎 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
st.session_state.setdefault('active_tab', TAB_OVERVIEW)
st.session_state.setdefault('selected_transcript_key_dialog_global_search', None)
st.session_state.setdefault('selected_transcript_key_filtered_analysis', None)
st.session_state.setdefault('show_global_search_dialog', False)

# --- Data Loading Trigger ---
if not st.session_state.data_loaded:
    df_loaded = load_data_from_google_sheet()
    if not df_loaded.empty:
        st.session_state.df_original = df_loaded
        st.session_state.data_loaded = True
        min_d, max_d = (pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().min(), pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce').dt.date.dropna().max()) if 'onboarding_date_only' in df_loaded and df_loaded['onboarding_date_only'].notna().any() else (None, None)
        st.session_state.min_data_date_for_filter = min_d
        st.session_state.max_data_date_for_filter = max_d
        st.session_state.date_range = get_default_date_range(df_loaded.get('onboarding_date_only'))
    else:
        st.session_state.df_original = pd.DataFrame()
df_original = st.session_state.df_original

# --- Sidebar ---
user_display_name = "User"
if hasattr(st.user, "email") and st.user.email:
    user_email_prefix = st.user.email.split('@')[0]
    user_display_name = user_email_prefix
    if hasattr(st.user, "name") and st.user.name and st.user.name.strip():
        try: first_name = st.user.name.split()[0]; user_display_name = first_name
        except IndexError: user_display_name = st.user.name
    st.sidebar.header(f"👤 Welcome, {user_display_name}")
    st.sidebar.caption(st.user.email)
else: st.sidebar.header(f"👤 Welcome!")
st.sidebar.button("🔓 Log Out", on_click=st.logout, use_container_width=True, type="secondary", key="logout_button_sidebar")
st.sidebar.markdown("---")
st.sidebar.markdown("🎨 **Theme**: Use Streamlit's menu (☰ → Settings) to toggle Light/Dark mode.")
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Dashboard Controls"); st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Global Search"); st.sidebar.caption("Search all data. Overrides filters below.")
global_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
ln_search_val = st.sidebar.text_input(f"Search {global_search_cols['licenseNumber']}:", value=st.session_state.get("licenseNumber_search", ""), key="licenseNumber_global_search_widget_v4_3_1", help="Enter license number part.")
if ln_search_val != st.session_state["licenseNumber_search"]: st.session_state["licenseNumber_search"] = ln_search_val; st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", "")); st.rerun()
store_names_options = [""];
if not df_original.empty and 'storeName' in df_original.columns: unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique()); store_names_options.extend([name for name in unique_stores if str(name).strip()])
current_store_search_val = st.session_state.get("storeName_search", "");
try: current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
except ValueError: current_store_idx = 0
selected_store_val = st.sidebar.selectbox(f"Search {global_search_cols['storeName']}:", options=store_names_options, index=current_store_idx, key="storeName_global_search_widget_select_v4_3_1", help="Select or type store name.")
if selected_store_val != st.session_state["storeName_search"]: st.session_state["storeName_search"] = selected_store_val; st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", "")); st.rerun()
st.sidebar.markdown("---"); global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))
st.sidebar.subheader("📊 Filters"); st.sidebar.caption("Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data.")
st.sidebar.markdown("##### Quick Date Ranges"); s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
if s_col1.button("MTD", key="mtd_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active: start_mtd = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col2.button("YTD", key="ytd_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active: start_ytd = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col3.button("ALL", key="all_button_v4_3_1", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active:
        all_start = st.session_state.get('min_data_date_for_filter', today_for_shortcuts.replace(year=today_for_shortcuts.year-1)); all_end = st.session_state.get('max_data_date_for_filter', today_for_shortcuts)
        if all_start and all_end: st.session_state.date_range = (all_start, all_end); st.session_state.date_filter_is_active = True; st.rerun()
current_session_start, current_session_end = st.session_state.date_range; min_dt_for_widget = st.session_state.get('min_data_date_for_filter'); max_dt_for_widget = st.session_state.get('max_data_date_for_filter')
val_start_widget = current_session_start;
if min_dt_for_widget and current_session_start < min_dt_for_widget: val_start_widget = min_dt_for_widget
val_end_widget = current_session_end;
if max_dt_for_widget and current_session_end > max_dt_for_widget: val_end_widget = max_dt_for_widget
if val_start_widget > val_end_widget : val_start_widget = val_end_widget
selected_date_range_tuple = st.sidebar.date_input("Custom Date Range (Onboarding):", value=(val_start_widget, val_end_widget), min_value=min_dt_for_widget, max_value=max_dt_for_widget, key="date_selector_custom_v4_3_1", disabled=global_search_active, help="Select start/end dates.")
if not global_search_active and isinstance(selected_date_range_tuple, tuple) and len(selected_date_range_tuple) == 2:
    if selected_date_range_tuple != st.session_state.date_range: st.session_state.date_range = selected_date_range_tuple; st.session_state.date_filter_is_active = True; st.rerun()
start_dt_filter, end_dt_filter = st.session_state.date_range
category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label_text in category_filters_map.items():
    options_for_multiselect = [];
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any():
        options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).dropna().unique() if str(val).strip()])

    current_selection_for_multiselect = st.session_state.get(f"{col_key}_filter", []); valid_current_selection = [s for s in current_selection_for_multiselect if s in options_for_multiselect]
    new_selection_multiselect = st.sidebar.multiselect(f"Filter by {label_text}:", options=options_for_multiselect, default=valid_current_selection, key=f"{col_key}_category_filter_widget_v4_3_1", disabled=global_search_active or not options_for_multiselect, help=f"Select {label_text}." if options_for_multiselect else f"No {label_text} data.")
    if not global_search_active and new_selection_multiselect != valid_current_selection: st.session_state[f"{col_key}_filter"] = new_selection_multiselect; st.rerun()
    elif global_search_active and st.session_state.get(f"{col_key}_filter") != new_selection_multiselect: st.session_state[f"{col_key}_filter"] = new_selection_multiselect

def clear_all_filters_and_search_v4_3_1():
    ds_cleared, de_cleared = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_cleared, de_cleared); st.session_state.date_filter_is_active = False
    st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
    for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
    st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state.active_tab = TAB_OVERVIEW
if st.sidebar.button("🧹 Clear Filters", on_click=clear_all_filters_and_search_v4_3_1, use_container_width=True, key="clear_filters_button_v4_3_1", type="primary"): st.rerun()
with st.sidebar.expander("ℹ️ Score Breakdown (0-10 pts)", expanded=False):
    st.markdown("""Score (0-10 pts):\n- **Primary (4 pts):** Kit Recv'd (2), Train/Promo Sched. (2).\n- **Secondary (3 pts):** Intro (1), Display Help (1), Promo Link (1).\n- **Bonuses (3 pts):** +1 Positive Sentiment, +1 Expectations Set, +1 Full Checklist Completion.""")
st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management");
if st.sidebar.button("Refresh Data from Source", key="refresh_data_button_v4_3_1", use_container_width=True, type="primary"):
    st.cache_data.clear(); st.session_state.data_loaded = False; st.session_state.last_data_refresh_time = None; st.session_state.df_original = pd.DataFrame()
    clear_all_filters_and_search_v4_3_1(); st.rerun()
if st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE); refresh_time_str_display = refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST'); st.sidebar.caption(f"☁️ Last sync: {refresh_time_str_display}")
    if not st.session_state.get('data_loaded', False) and st.session_state.df_original.empty : st.sidebar.caption("⚠️ No data loaded.")
else: st.sidebar.caption("⏳ Data not yet loaded.")
st.sidebar.markdown("---");
st.sidebar.caption(f"Dashboard v6.1.0")


# --- Main Area ---
st.markdown("<h1 class='main-title'>Onboarding Performance Dashboard</h1>", unsafe_allow_html=True)

if not st.session_state.data_loaded and df_original.empty:
    if st.session_state.get('last_data_refresh_time'): st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh. 🚧</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>⏳ Initializing data... If persists, check configurations. ⏳</div>", unsafe_allow_html=True)
    st.stop()
elif df_original.empty: st.markdown("<div class='no-data-message'>✅ Data source connected, but empty. Add data to Google Sheet. ✅</div>", unsafe_allow_html=True); st.stop()
if st.session_state.active_tab not in ALL_TABS: st.session_state.active_tab = TAB_OVERVIEW
try: current_tab_idx = ALL_TABS.index(st.session_state.active_tab)
except ValueError: current_tab_idx = 0; st.session_state.active_tab = TAB_OVERVIEW
selected_tab = st.radio("Navigation:", ALL_TABS, index=current_tab_idx, horizontal=True, key="main_tab_selector_v4_3_1")
if selected_tab != st.session_state.active_tab: st.session_state.active_tab = selected_tab; st.rerun()
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

# --- Data Filtering ---
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

        for col_key, _ in category_filters_map.items():
            selected_values_cat = st.session_state.get(f"{col_key}_filter", [])
            if selected_values_cat and col_key in df_temp_filters.columns:
                 df_temp_filters = df_temp_filters[df_temp_filters[col_key].astype(str).isin(selected_values_cat)]

        df_filtered = df_temp_filters.copy()
else: df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()

# --- MTD Calculation ---
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

# --- HTML Table & Details (Updated with Status Chips & New Styling) ---
def map_status_to_chip_html(status_val):
    """Maps status to a styled HTML chip."""
    status_str = str(status_val).strip().lower()
    if status_str == 'confirmed':
        return f"<span class='status-chip status-confirmed'>Confirmed</span>"
    elif status_str == 'unconfirmed': # Includes 'pending'
        return f"<span class='status-chip status-unconfirmed'>Unconfirmed</span>"
    elif status_str == 'error': # Includes 'failed'
        return f"<span class='status-chip status-error'>Error</span>"
    return f"<span class='status-chip status-unknown'>{status_val}</span>" if status_val else ""

def display_html_table_and_details(df_to_display, context_key_prefix=""):
    if df_to_display is None or df_to_display.empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','');
        if not df_original.empty: st.markdown(f"<div class='no-data-message'>📊 No data for {context_name_display}. Try different filters! 📊</div>", unsafe_allow_html=True)
        return
    df_display_copy = df_to_display.copy().reset_index(drop=True)

    if 'status' in df_display_copy.columns:
        df_display_copy['status_styled'] = df_display_copy['status'].apply(map_status_to_chip_html)
    else: df_display_copy['status_styled'] = ""

    preferred_cols_order = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status_styled', 'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 'contactNumber']
    cols_present_in_df = df_display_copy.columns.tolist(); final_display_cols = [col for col in preferred_cols_order if col in cols_present_in_df]
    excluded_suffixes = ('_dt', '_utc', '_str_original', '_date_only')
    other_existing_cols_for_display = [col for col in cols_present_in_df if col not in final_display_cols and not any(col.endswith(s) for s in excluded_suffixes) and col not in ['fullTranscript', 'summary', 'status', 'onboardingWelcome', 'deliveryDate', 'confirmationTimestamp', 'confirmedNumber'] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS]
    final_display_cols.extend(other_existing_cols_for_display); final_display_cols = list(dict.fromkeys(final_display_cols))
    if not final_display_cols or df_display_copy[final_display_cols].empty:
        context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog',''); st.markdown(f"<div class='no-data-message'>📋 No columns/data for {context_name_display}. 📋</div>", unsafe_allow_html=True); return

    html_table = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
    column_display_names = {'status_styled': 'Status', 'onboardingDate': 'Onboarding Date', 'repName': 'Rep Name', 'storeName': 'Store Name', 'licenseNumber': 'License No.', 'clientSentiment': 'Sentiment', 'days_to_confirmation': 'Days to Confirm', 'contactName': 'Contact Name', 'contactNumber': 'Contact No.', 'score': 'Score'}

    for col_id in final_display_cols:
        display_name = column_display_names.get(col_id, col_id.replace("_", " ").title());
        html_table.append(f"<th>{display_name}</th>")
    html_table.append("</tr></thead><tbody>")

    for index, row in df_display_copy.iterrows():
        html_table.append("<tr>")
        for col_id in final_display_cols:
            cell_value = row.get(col_id, "")
            if col_id == 'status_styled':
                cell_display = cell_value # Already HTML
            elif col_id == 'score' and pd.notna(cell_value):
                cell_display = f"{cell_value:.1f}"
            elif col_id == 'days_to_confirmation' and pd.notna(cell_value):
                cell_display = f"{cell_value:.0f}"
            else:
                cell_display = st.markdown._repr_html_(cell_value).strip().replace('<p>', '').replace('</p>', '')

            html_table.append(f"<td>{cell_display}</td>")
        html_table.append("</tr>")
    html_table.append("</tbody></table></div>"); st.markdown("".join(html_table), unsafe_allow_html=True)

    # --- Details Section ---
    st.markdown("---"); st.markdown("<h2>📄 View Full Record Details</h2>", unsafe_allow_html=True)
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
            selected_key_from_display = st.selectbox("Select record to view details:", options=options_list_for_select, index=current_index_for_select, format_func=lambda x: "📄 Choose an entry..." if x is None else x, key=f"transcript_selector_{context_key_prefix}_widget_v4_3_1")
            if selected_key_from_display != st.session_state[transcript_session_key_local]: st.session_state[transcript_session_key_local] = selected_key_from_display; st.session_state[auto_selected_once_key] = False; st.rerun()
            if st.session_state[transcript_session_key_local]:
                selected_original_idx = transcript_options_map[st.session_state[transcript_session_key_local]]; selected_row_details = df_display_copy.loc[selected_original_idx]
                st.markdown("<h5>📋 Onboarding Summary & Checks:</h5>", unsafe_allow_html=True); summary_html_parts_list = ["<div class='transcript-summary-grid'>"]
                # Display status using the chip in details view as well
                status_chip_detail = map_status_to_chip_html(selected_row_details.get('status'))
                summary_items_to_display = {"Store": selected_row_details.get('storeName', "N/A"), "Rep": selected_row_details.get('repName', "N/A"), "Score": f"{selected_row_details.get('score', 'N/A'):.1f}" if pd.notna(selected_row_details.get('score')) else "N/A", "Status": status_chip_detail, "Sentiment": selected_row_details.get('clientSentiment', "N/A")}
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
    st.markdown("---"); csv_data_to_download = convert_df_to_csv(df_to_display); download_label = f"📥 Download These {context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')} Results"
    st.download_button(label=download_label, data=csv_data_to_download, file_name=f'{context_key_prefix}_results_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', mime='text/csv', use_container_width=True, key=f"download_csv_{context_key_prefix}_button_v4_3_1")


# --- Global Search Dialog ---
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("🔍 Global Search Results", width="large")
    def show_global_search_dialog_content():
        st.markdown("<h2>Search Results</h2>", unsafe_allow_html=True);
        if not df_global_search_results_display.empty: display_html_table_and_details(df_global_search_results_display, context_key_prefix="dialog_global_search")
        else: st.info("ℹ️ No results for global search. Try broadening terms.")
        if st.button("Close & Clear Search", key="close_gs_dialog_clear_button_v4_3_1"):
            st.session_state.show_global_search_dialog = False; st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""
            if 'selected_transcript_key_dialog_global_search' in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
            if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
            st.rerun()
    show_global_search_dialog_content()

# --- Tab Content ---
if st.session_state.active_tab == TAB_OVERVIEW:
    st.markdown("<h2>MTD Performance</h2>", unsafe_allow_html=True)
    cols_mtd_overview = st.columns(4)
    with cols_mtd_overview[0]: st.metric("Onboardings MTD", value=f"{total_mtd:.0f}" if pd.notna(total_mtd) else "0", delta=f"{delta_onboardings_mtd:+.0f} vs Prev." if delta_onboardings_mtd is not None and pd.notna(delta_onboardings_mtd) else None, help="Total onboardings MTD vs. same period last month.")
    with cols_mtd_overview[1]: st.metric("Success Rate MTD", value=f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A", help="Confirmed onboardings MTD.")
    with cols_mtd_overview[2]: st.metric("Avg. Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A", help="Average score (0-10) MTD.")
    with cols_mtd_overview[3]: st.metric("Avg. Days to Confirm MTD", value=f"{days_to_confirm_mtd:.1f}" if pd.notna(days_to_confirm_mtd) else "N/A", help="Avg days delivery to confirmation MTD.")

    st.markdown("<h2>Filtered Data Snapshot</h2>", unsafe_allow_html=True)
    if global_search_active: st.info("ℹ️ Global search active. Close pop-up or clear search for filtered overview.")
    elif not df_filtered.empty:
        total_filtered, sr_filtered, score_filtered, days_filtered = calculate_metrics(df_filtered); cols_filtered_overview = st.columns(4)
        with cols_filtered_overview[0]: st.metric("Onboardings (Filtered)", f"{total_filtered:.0f}" if pd.notna(total_filtered) else "0")
        with cols_filtered_overview[1]: st.metric("Success Rate (Filtered)", f"{sr_filtered:.1f}%" if pd.notna(sr_filtered) else "N/A")
        with cols_filtered_overview[2]: st.metric("Avg. Score (Filtered)", f"{score_filtered:.2f}" if pd.notna(score_filtered) else "N/A")
        with cols_filtered_overview[3]: st.metric("Avg. Days Confirm (Filtered)", f"{days_filtered:.1f}" if pd.notna(days_filtered) else "N/A")
    else: st.markdown("<div class='no-data-message'>🤷 No data matches filters for Overview. Adjust selections! 🤷</div>", unsafe_allow_html=True)

elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.markdown(f"<h2>{TAB_DETAILED_ANALYSIS}</h2>", unsafe_allow_html=True)
    if global_search_active: st.info("ℹ️ Global Search active. Results in pop-up. Close/clear search for category/date filters here.")
    else:
        display_html_table_and_details(df_filtered, context_key_prefix="filtered_analysis")

elif st.session_state.active_tab == TAB_TRENDS:
    st.markdown(f"<h2>{TAB_TRENDS}</h2>", unsafe_allow_html=True)
    st.markdown(f"*(Visuals based on {'Global Search (Pop-Up)' if global_search_active else 'Filtered Data'})*")

    if not df_filtered.empty:
        st.markdown("<h3>Key Visualizations</h3>", unsafe_allow_html=True)
        with st.container():
                chart_cols_1, chart_cols_2 = st.columns(2)
                with chart_cols_1:
                    if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                        status_counts_df = df_filtered['status'].value_counts().reset_index(); status_counts_df.columns = ['status', 'count']
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
                            if not df_checklist_plotly.empty: checklist_bar_fig = px.bar(df_checklist_plotly.sort_values("Completion (%)", ascending=True), x="Completion (%)", y="Key Requirement", orientation='h', title="Key Req Completion (Confirmed Only)", color_discrete_sequence=[GOLD_ACCENT]); checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}, xaxis_ticksuffix="%"); st.plotly_chart(checklist_bar_fig, use_container_width=True)
                            else: st.markdown("<div class='no-data-message'>📊 No data for key req chart (confirmed, post-proc).</div>", unsafe_allow_html=True)
                        else: st.markdown("<div class='no-data-message'>📊 No valid checklist items for req chart.</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='no-data-message'>✅ No 'Confirmed' onboardings or relevant columns for req chart.</div>", unsafe_allow_html=True)

        st.markdown("<h3>Trends Over Time</h3>", unsafe_allow_html=True)
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
            else: st.markdown("<div class'no-data-message'>📅 No valid date data for trend.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>🗓️ 'onboarding_date_only' missing for trend.</div>", unsafe_allow_html=True)
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna();
            if not days_data_for_hist.empty:
                num_bins_hist = max(10, min(30, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else (len(days_data_for_hist.unique()) or 10); days_dist_fig = px.histogram(days_data_for_hist, nbins=num_bins_hist, title="Distribution of Days to Confirmation", color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[1]]); days_dist_fig.update_layout(plotly_base_layout_settings, xaxis_title="Days to Confirmation", yaxis_title="Frequency"); st.plotly_chart(days_dist_fig, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>⏳ No 'Days to Confirmation' data.</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' missing.</div>", unsafe_allow_html=True)
    elif not df_original.empty : st.markdown("<div class='no-data-message'>📉 No data for Trends. Adjust filters. 📉</div>", unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
footer_time = "Not Synced Yet"
if st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE)
    footer_time = refresh_time_pst.strftime('%Y-%m-%d %I:%M %p PST')

st.markdown(f"""
<div class='footer'>
    <div class='footer-content'>
        <span>Onboarding Dashboard v6.1.0</span>
        <span> | </span>
        <span>Last Refresh: {footer_time}</span>
    </div>
</div>
""", unsafe_allow_html=True)