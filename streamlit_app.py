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
from dateutil import tz # For PST conversion

st.set_page_config(
    page_title="Onboarding Performance Dashboard v3.20",
    page_icon="💎",
    layout="wide"
)

# --- Theme and Color Definitions ---
DARK_APP_ACCENT_PRIMARY = "#8458B3"
DARK_APP_ACCENT_SECONDARY = "#d0bdf4"
DARK_APP_ACCENT_MUTED = "#a28089"
DARK_APP_ACCENT_HIGHLIGHT = "#a0d2eb"
DARK_APP_ACCENT_LIGHTEST = "#e5eaf5"
DARK_APP_TEXT_ON_ACCENT = DARK_APP_ACCENT_LIGHTEST
DARK_APP_TEXT_ON_HIGHLIGHT = "#0E1117"
DARK_APP_DL_BUTTON_BG = DARK_APP_ACCENT_HIGHLIGHT
DARK_APP_DL_BUTTON_TEXT = DARK_APP_TEXT_ON_HIGHLIGHT
DARK_APP_DL_BUTTON_HOVER_BG = DARK_APP_ACCENT_LIGHTEST
DARK_PLOTLY_PRIMARY_SEQ = [DARK_APP_ACCENT_PRIMARY, DARK_APP_ACCENT_SECONDARY, DARK_APP_ACCENT_HIGHLIGHT, '#C39BD3', '#76D7C4']
DARK_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
DARK_PLOTLY_SENTIMENT_MAP = { 'positive': DARK_APP_ACCENT_HIGHLIGHT, 'negative': '#E74C3C', 'neutral': DARK_APP_ACCENT_MUTED }

LIGHT_APP_ACCENT_PRIMARY = "#1A73E8"
LIGHT_APP_ACCENT_SECONDARY = "#4285F4"
LIGHT_APP_ACCENT_MUTED = "#89B1F3"
LIGHT_APP_ACCENT_HIGHLIGHT = LIGHT_APP_ACCENT_PRIMARY
LIGHT_APP_ACCENT_LIGHTEST = "#E8F0FE"
LIGHT_APP_TEXT_ON_ACCENT = "#FFFFFF"
LIGHT_APP_TEXT_ON_HIGHLIGHT = "#0E1117"
LIGHT_APP_DL_BUTTON_BG = LIGHT_APP_ACCENT_PRIMARY
LIGHT_APP_DL_BUTTON_TEXT = LIGHT_APP_TEXT_ON_ACCENT
LIGHT_APP_DL_BUTTON_HOVER_BG = "#1765CC"
LIGHT_PLOTLY_PRIMARY_SEQ = ['#1A73E8', '#4285F4', '#89B1F3', '#ADC6F7', '#D2E3FC']
LIGHT_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set2
LIGHT_PLOTLY_SENTIMENT_MAP = { 'positive': '#1A73E8', 'negative': '#D93025', 'neutral': '#78909C' }

THEME = st.get_option("theme.base")
if THEME == "light":
    ACTIVE_ACCENT_PRIMARY = LIGHT_APP_ACCENT_PRIMARY; ACTIVE_ACCENT_SECONDARY = LIGHT_APP_ACCENT_SECONDARY; ACTIVE_ACCENT_MUTED = LIGHT_APP_ACCENT_MUTED; ACTIVE_ACCENT_HIGHLIGHT = LIGHT_APP_ACCENT_HIGHLIGHT; ACTIVE_ACCENT_LIGHTEST = LIGHT_APP_ACCENT_LIGHTEST; ACTIVE_TEXT_ON_ACCENT = LIGHT_APP_TEXT_ON_ACCENT; ACTIVE_DL_BUTTON_BG = LIGHT_APP_DL_BUTTON_BG; ACTIVE_DL_BUTTON_TEXT = LIGHT_APP_DL_BUTTON_TEXT; ACTIVE_DL_BUTTON_HOVER_BG = LIGHT_APP_DL_BUTTON_HOVER_BG; ACTIVE_PLOTLY_PRIMARY_SEQ = LIGHT_PLOTLY_PRIMARY_SEQ; ACTIVE_PLOTLY_QUALITATIVE_SEQ = LIGHT_PLOTLY_QUALITATIVE_SEQ; ACTIVE_PLOTLY_SENTIMENT_MAP = LIGHT_PLOTLY_SENTIMENT_MAP
    DEFAULT_TEXT_COLOR_ON_LIGHT_BG = "#212529"
    DEFAULT_TEXT_COLOR_ON_DARK_BG = "#FFFFFF"
else:
    ACTIVE_ACCENT_PRIMARY = DARK_APP_ACCENT_PRIMARY; ACTIVE_ACCENT_SECONDARY = DARK_APP_ACCENT_SECONDARY; ACTIVE_ACCENT_MUTED = DARK_APP_ACCENT_MUTED; ACTIVE_ACCENT_HIGHLIGHT = DARK_APP_ACCENT_HIGHLIGHT; ACTIVE_ACCENT_LIGHTEST = DARK_APP_ACCENT_LIGHTEST; ACTIVE_TEXT_ON_ACCENT = DARK_APP_TEXT_ON_ACCENT; ACTIVE_DL_BUTTON_BG = DARK_APP_DL_BUTTON_BG; ACTIVE_DL_BUTTON_TEXT = DARK_APP_DL_BUTTON_TEXT; ACTIVE_DL_BUTTON_HOVER_BG = DARK_APP_DL_BUTTON_HOVER_BG; ACTIVE_PLOTLY_PRIMARY_SEQ = DARK_PLOTLY_PRIMARY_SEQ; ACTIVE_PLOTLY_QUALITATIVE_SEQ = DARK_PLOTLY_QUALITATIVE_SEQ; ACTIVE_PLOTLY_SENTIMENT_MAP = DARK_PLOTLY_SENTIMENT_MAP
    DEFAULT_TEXT_COLOR_ON_LIGHT_BG = "#212529"
    DEFAULT_TEXT_COLOR_ON_DARK_BG = "#E1E1E1"

PLOT_BG_COLOR = "rgba(0,0,0,0)"

def get_contrasting_text_color(hex_bg_color):
    try:
        hex_bg_color = hex_bg_color.lstrip('#')
        r, g, b = tuple(int(hex_bg_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return DEFAULT_TEXT_COLOR_ON_DARK_BG if luminance < 0.5 else DEFAULT_TEXT_COLOR_ON_LIGHT_BG
    except:
        return DEFAULT_TEXT_COLOR_ON_LIGHT_BG if THEME == "light" else DEFAULT_TEXT_COLOR_ON_DARK_BG

css_parts = [
    "<style>",
    f"""
    :root {{
        --app-accent-primary: {ACTIVE_ACCENT_PRIMARY}; --app-accent-secondary: {ACTIVE_ACCENT_SECONDARY}; --app-accent-muted: {ACTIVE_ACCENT_MUTED}; --app-accent-highlight: {ACTIVE_ACCENT_HIGHLIGHT}; --app-accent-lightest: {ACTIVE_ACCENT_LIGHTEST}; --app-text-on-accent: {ACTIVE_TEXT_ON_ACCENT};
        --app-dl-button-bg: {ACTIVE_DL_BUTTON_BG}; --app-dl-button-text: {ACTIVE_DL_BUTTON_TEXT}; --app-dl-button-hover-bg: {ACTIVE_DL_BUTTON_HOVER_BG};
        --border-color-fallback: {"#DADCE0" if THEME == "light" else "#3a3f4b"};
    }}
    """,
    """
    .stApp > header { background-color: transparent !important; }
    h1 { color: var(--app-accent-primary); text-align: center; padding-top: 0.8em; padding-bottom: 0.6em; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; font-size: 2.1rem; }
    h2 { color: var(--app-accent-primary); border-bottom: 2px solid var(--app-accent-primary) !important; padding-bottom: 0.3em; margin-top: 2.2em; margin-bottom: 1.5em; font-weight: 600; font-size: 1.7rem; }
    h3 { color: var(--app-accent-primary); border-bottom: 1px dotted var(--app-accent-secondary) !important; padding-bottom: 0.4em; margin-top: 2em; margin-bottom: 1.2em; font-weight: 600; font-size: 1.45rem; }
    h5 { color: var(--app-accent-primary); opacity: 0.95; margin-top: 1.8em; margin-bottom: 0.8em; font-weight: 600; letter-spacing: 0.3px; font-size: 1.2rem; }
    div[data-testid="stMetric"], .metric-card { background-color: var(--secondary-background-color); padding: 1.5em; border-radius: 12px; border: 1px solid var(--border-color, var(--border-color-fallback)); box-shadow: 0 4px 6px rgba(0,0,0,0.04); transition: transform 0.25s ease-in-out, box-shadow 0.25s ease-in-out; }
    div[data-testid="stMetric"]:hover, .metric-card:hover { transform: translateY(-4px); box-shadow: 0 6px 12px rgba(0,0,0,0.06); }
    div[data-testid="stMetricLabel"] > div { color: var(--text-color) !important; opacity: 0.7; font-weight: 500; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetricValue"] > div { color: var(--text-color) !important; font-size: 2.3rem !important; font-weight: 700; line-height: 1.1; }
    div[data-testid="stMetricDelta"] > div { color: var(--text-color) !important; opacity: 0.7; font-weight: 500; font-size: 0.85em; }
    .streamlit-expanderHeader { color: var(--app-accent-primary) !important; font-weight: 600; font-size: 1.1em; }
    .streamlit-expander { border: 1px solid var(--border-color, var(--border-color-fallback)); background-color: var(--secondary-background-color); border-radius: 10px; }
    .streamlit-expander > div > div > p { color: var(--text-color); }
    .stDataFrame { border: 1px solid var(--border-color, var(--border-color-fallback)); border-radius: 10px; }
    div[data-testid="stRadio"] label { padding: 12px 22px; margin: 0 5px; border-radius: 10px 10px 0 0; border: 1px solid transparent; border-bottom: none; background-color: var(--secondary-background-color); color: var(--text-color); opacity: 0.65; transition: background-color 0.3s ease, color 0.3s ease, opacity 0.3s ease, border-color 0.3s ease, border-top-width 0.2s ease; font-weight: 500; font-size: 1.05em; }
    div[data-testid="stRadio"] input:checked + div label { background-color: var(--app-accent-lightest); color: var(--app-accent-primary); font-weight: 600; opacity: 1.0; border-top: 3px solid var(--app-accent-primary); border-left: 1px solid var(--border-color, var(--border-color-fallback)); border-right: 1px solid var(--border-color, var(--border-color-fallback)); box-shadow: 0 -2px 5px rgba(0,0,0,0.05); }
    div[data-testid="stRadio"] { padding-bottom: 0px; border-bottom: 2px solid var(--app-accent-primary); margin-bottom: 15px; }
    div[data-testid="stRadio"] > label > div:first-child { display: none; }
    .transcript-details-section { margin-left: 20px; padding-left: 15px; border-left: 2px solid var(--app-accent-lightest); }
    .transcript-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px; margin-bottom: 25px; color: var(--text-color);}
    .transcript-summary-item strong { color: var(--app-accent-primary); }
    .transcript-summary-item-fullwidth { grid-column: 1 / -1; margin-top: 15px; padding-top: 15px; border-top: 1px dashed var(--app-accent-muted); }
    .requirement-item { margin-bottom: 12px; padding: 10px; border-left: 4px solid var(--app-accent-muted); background-color: color-mix(in srgb, var(--secondary-background-color) 97%, var(--app-accent-lightest) 3%); border-radius: 6px; color: var(--text-color); }
    .requirement-item .type { font-weight: 500; color: var(--app-accent-muted); opacity: 0.8; font-size: 0.85em; margin-left: 8px; }
    .transcript-container { background-color: var(--secondary-background-color); color: var(--text-color); padding: 20px; border-radius: 10px; border: 1px solid var(--border-color, var(--border-color-fallback)); max-height: 450px; overflow-y: auto; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 0.95em; line-height: 1.7; }
    .transcript-line strong { color: var(--app-accent-primary); }
    div[data-testid="stButton"] > button { background-color: var(--app-accent-primary); color: var(--app-text-on-accent); border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }
    div[data-testid="stButton"] > button:hover { background-color: color-mix(in srgb, var(--app-accent-primary) 90%, #000000 10%); color: var(--app-text-on-accent); transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
    div[data-testid="stDownloadButton"] > button { background-color: var(--app-dl-button-bg); color: var(--app-dl-button-text); border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }
    div[data-testid="stDownloadButton"] > button:hover { background-color: var(--app-dl-button-hover-bg); color: var(--app-dl-button-text); transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
    div[data-testid="stSidebarUserContent"] { background-color: var(--secondary-background-color); padding: 1.5em 1em; border-right: 1px solid var(--border-color, var(--border-color-fallback)); }
    div[data-testid="stSidebarUserContent"] h2, div[data-testid="stSidebarUserContent"] h3 { color: var(--app-accent-highlight); border-bottom-color: var(--app-accent-secondary); }
    .footer { font-size: 0.8em; color: var(--text-color); opacity: 0.7; text-align: center; padding: 20px 0; border-top: 1px solid var(--border-color, var(--border-color-fallback)); margin-top: 40px; }
    .active-filters-summary { font-size: 0.9em; color: var(--text-color); opacity: 0.8; margin-top: 0px; margin-bottom: 25px; padding: 10px; background-color: var(--secondary-background-color); border-radius: 8px; border: 1px solid var(--border-color, var(--border-color-fallback)); text-align: center; }
    .no-data-message { text-align: center; padding: 20px; font-size: 1.1em; color: var(--text-color); opacity: 0.7; }
    """,
    "</style>"
]
css_style = "\n".join(css_parts)
st.markdown(css_style, unsafe_allow_html=True)

def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")
    if app_password is None: st.sidebar.warning("APP_ACCESS_KEY not set. Bypassing password."); return True
    if "password_entered" not in st.session_state: st.session_state.password_entered = False
    if st.session_state.password_entered: return True
    with st.form("password_form_main_app_v3_10"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint, key="pwd_input_main_app_v3_10")
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password_attempt == app_password: st.session_state.password_entered = True; st.rerun()
            else: st.error("Incorrect Access Key."); return False
    return False

if not check_password(): st.stop()

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

@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    gcp_secrets = st.secrets.get("gcp_service_account")
    if gcp_secrets is None: st.error("Error: GCP secrets NOT FOUND."); return None
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')): st.error(f"Error: GCP secrets not structured correctly (type: {type(gcp_secrets)})."); return None
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [k for k in required_keys if gcp_secrets.get(k) is None]
    if missing: st.error(f"Error: GCP secrets missing keys: {', '.join(missing)}."); return None
    try: return gspread.service_account_from_dict(dict(gcp_secrets), scopes=SCOPES)
    except Exception as e: st.error(f"Google Auth Error using service_account_from_dict: {e}"); return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and not series.astype(str).str.lower().isin(['','none','nan','nat','null']).all():
        common_formats = [
            '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', 
            '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'
        ]
        for dayfirst_setting in [False, True]:
            for fmt in common_formats:
                try:
                    use_dayfirst = ('%m' in fmt and '%d' in fmt)
                    temp_dates = pd.to_datetime(series, format=fmt, errors='coerce', dayfirst=dayfirst_setting if use_dayfirst else None)
                    if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                    if dates.notnull().all(): break
                except ValueError: continue
            if dates.notnull().all(): break
    return dates

def format_datetime_to_pst_str(dt_series):
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
    if pd.isna(number_str) or number_str == "": return ""
    digits = re.sub(r'\D', '', str(number_str))
    if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(number_str)

def capitalize_name(name_str):
    if pd.isna(name_str) or name_str == "": return ""
    return str(name_str).title()

@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    gc = authenticate_gspread_cached()
    current_time = datetime.now()
    if gc is None: st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config: GOOGLE_SHEET_URL_OR_NAME missing."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    if not ws_name: st.error("Config: GOOGLE_WORKSHEET_NAME missing."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    try:
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url); ws = ss.worksheet(ws_name)
        data = ws.get_all_records(head=1, expected_headers=None)
        st.session_state.last_data_refresh_time = current_time
        if not data: st.warning("Source sheet has no data rows (headers may exist)."); return pd.DataFrame()
        df_loaded_internal = pd.DataFrame(data)
        
        standardized_column_names_map = {col: "".join(str(col).strip().lower().split()) for col in df_loaded_internal.columns}
        df_loaded_internal.rename(columns=standardized_column_names_map, inplace=True)

        column_name_map_to_code = {
            "licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "storename": "storeName",
            "repname": "repName", "onboardingdate": "onboardingDate", "deliverydate": "deliveryDate",
            "confirmationtimestamp": "confirmationTimestamp", "clientsentiment": "clientSentiment",
            "fulltranscript": "fullTranscript", "score": "score", "status": "status", "summary": "summary",
            "contactnumber": "contactNumber", "confirmednumber": "confirmedNumber", "contactname": "contactName"
        }
        for req_key_internal in KEY_REQUIREMENT_DETAILS.keys():
            std_req_key = req_key_internal.lower()
            column_name_map_to_code[std_req_key] = req_key_internal
        
        cols_to_rename_standardized = {}
        current_df_columns_std = list(df_loaded_internal.columns)
        for std_sheet_col in current_df_columns_std:
            if std_sheet_col in column_name_map_to_code:
                target_code_name = column_name_map_to_code[std_sheet_col]
                if std_sheet_col != target_code_name and target_code_name not in cols_to_rename_standardized.values() and target_code_name not in current_df_columns_std:
                    cols_to_rename_standardized[std_sheet_col] = target_code_name
        if cols_to_rename_standardized:
            df_loaded_internal.rename(columns=cols_to_rename_standardized, inplace=True)

        date_cols_map = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
        for original_col, dt_col in date_cols_map.items():
            if original_col in df_loaded_internal:
                df_loaded_internal[dt_col] = robust_to_datetime(df_loaded_internal[original_col].astype(str).str.replace('\n','',regex=False).str.strip())
                df_loaded_internal[original_col] = format_datetime_to_pst_str(df_loaded_internal[dt_col])
            else:
                df_loaded_internal[dt_col] = pd.NaT
            if original_col == 'onboardingDate':
                if dt_col in df_loaded_internal and df_loaded_internal[dt_col].notna().any():
                    df_loaded_internal['onboarding_date_only'] = df_loaded_internal[dt_col].dt.date
                else:
                    df_loaded_internal['onboarding_date_only'] = pd.NaT
        
        if 'deliveryDate_dt' in df_loaded_internal and 'confirmationTimestamp_dt' in df_loaded_internal:
            delivery_dt_for_calc = df_loaded_internal['deliveryDate_dt']
            confirmation_dt_for_calc = df_loaded_internal['confirmationTimestamp_dt']
            def ensure_utc_for_calc(series_dt):
                if pd.api.types.is_datetime64_any_dtype(series_dt) and series_dt.notna().any():
                    if series_dt.dt.tz is None: return series_dt.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
                    else: return series_dt.dt.tz_convert(UTC_TIMEZONE)
                return series_dt
            delivery_utc = ensure_utc_for_calc(delivery_dt_for_calc)
            confirmation_utc = ensure_utc_for_calc(confirmation_dt_for_calc)
            valid_dates_mask = delivery_utc.notna() & confirmation_utc.notna()
            df_loaded_internal['days_to_confirmation'] = pd.NA
            if valid_dates_mask.any():
                df_loaded_internal.loc[valid_dates_mask, 'days_to_confirmation'] = (confirmation_utc[valid_dates_mask] - delivery_utc[valid_dates_mask]).dt.days

        for phone_col in ['contactNumber', 'confirmedNumber']:
            if phone_col in df_loaded_internal.columns:
                df_loaded_internal[phone_col] = df_loaded_internal[phone_col].astype(str).apply(format_phone_number)
        for name_col in ['repName', 'contactName']:
            if name_col in df_loaded_internal.columns:
                df_loaded_internal[name_col] = df_loaded_internal[name_col].astype(str).apply(capitalize_name)

        str_cols_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary', 'contactName', 'contactNumber', 'confirmedNumber', 'onboardingDate', 'deliveryDate', 'confirmationTimestamp']
        for col in str_cols_ensure:
            if col not in df_loaded_internal.columns: df_loaded_internal[col] = ""
            else: df_loaded_internal[col] = df_loaded_internal[col].astype(str).fillna("")
        
        if 'score' not in df_loaded_internal.columns: df_loaded_internal['score'] = pd.NA
        else: df_loaded_internal['score'] = pd.to_numeric(df_loaded_internal['score'], errors='coerce')
        
        checklist_cols_to_ensure = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS + ['onboardingWelcome']
        for col in checklist_cols_to_ensure:
            if col not in df_loaded_internal.columns: df_loaded_internal[col] = pd.NA
        
        cols_to_drop_final = ['deliverydatets', 'onboardingwelcome']
        for col_drop in cols_to_drop_final:
            if col_drop in df_loaded_internal.columns:
                df_loaded_internal = df_loaded_internal.drop(columns=[col_drop])
        
        return df_loaded_internal
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e: st.error(f"Google Sheets Error: {e}. Check URL, name & permissions."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
    except Exception as e: st.error(f"Error Loading Data: {e}"); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()

@st.cache_data
def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8')
def calculate_metrics(df_in):
    if df_in.empty: return 0, 0.0, pd.NA, pd.NA
    total = len(df_in); sr = (df_in[df_in['status'].astype(str).str.lower()=='confirmed'].shape[0]/total*100) if total>0 else 0.0
    avg_s = pd.to_numeric(df_in['score'], errors='coerce').mean(); avg_d = pd.to_numeric(df_in['days_to_confirmation'], errors='coerce').mean()
    return total, sr, avg_s, avg_d
def get_default_date_range(series):
    today = date.today(); s_default = today.replace(day=1); e_default = today; min_d_data, max_d_data = None, None
    if series is not None and not series.empty and series.notna().any():
        dates = pd.to_datetime(series, errors='coerce').dt.date.dropna()
        if not dates.empty:
            min_d_data = dates.min(); max_d_data = dates.max(); s_final = max(s_default, min_d_data); e_final = min(e_default, max_d_data)
            if s_final > e_final: s_final, e_final = min_d_data, max_d_data
            return s_final, e_final, min_d_data, max_d_data
    return s_default, e_default, min_d_data, max_d_data

default_s_init, default_e_init, initial_min_data_date, initial_max_data_date = get_default_date_range(None)

if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'date_range' not in st.session_state or not (isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range) == 2 and isinstance(st.session_state.date_range[0], date) and isinstance(st.session_state.date_range[1], date)): st.session_state.date_range = (default_s_init, default_e_init)

TAB_OVERVIEW = "🌌 Overview"
TAB_DETAILED_ANALYSIS = "📊 Detailed Analysis (Filtered)"
TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]

if 'active_tab' not in st.session_state: st.session_state.active_tab = TAB_OVERVIEW

for f_key in ['repName_filter', 'status_filter', 'clientSentiment_filter']:
    if f_key not in st.session_state: st.session_state[f_key] = []
for s_key_base in ['licenseNumber', 'storeName']:
    if f"{s_key_base}_search" not in st.session_state: st.session_state[f"{s_key_base}_search"] = ""

if 'selected_transcript_key_dialog_global_search' not in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
if 'selected_transcript_key_filtered_analysis' not in st.session_state: st.session_state.selected_transcript_key_filtered_analysis = None

if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = initial_min_data_date
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = initial_max_data_date
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
if 'show_global_search_dialog' not in st.session_state: st.session_state.show_global_search_dialog = False

if not st.session_state.data_loaded and st.session_state.last_data_refresh_time is None:
    df_from_load_func = load_data_from_google_sheet()
    if st.session_state.last_data_refresh_time is None: 
        st.session_state.last_data_refresh_time = datetime.now()
    if not df_from_load_func.empty:
        st.session_state.df_original = df_from_load_func
        st.session_state.data_loaded = True
        ds, de, min_data_date, max_data_date = get_default_date_range(df_from_load_func.get('onboarding_date_only'))
        st.session_state.date_range = (ds, de)
        st.session_state.min_data_date_for_filter = min_data_date
        st.session_state.max_data_date_for_filter = max_data_date
    else:
        st.session_state.df_original = pd.DataFrame()
        st.session_state.data_loaded = False
df_original = st.session_state.df_original

if st.session_state.data_loaded and not df_original.empty:
    st.sidebar.success(f"Data loaded: {len(df_original)} records.")
elif st.session_state.get('last_data_refresh_time') and not st.session_state.data_loaded:
    st.sidebar.warning("Data source read, but no data rows found or an error occurred.")
elif not st.session_state.get('last_data_refresh_time'):
    st.sidebar.info("Initializing data load...")


st.title("🌌 Onboarding Performance Dashboard 🌌")
if not st.session_state.data_loaded and df_original.empty and st.session_state.get('last_data_refresh_time'):
    st.markdown("<div class='no-data-message'>🚧 No data loaded. Check configurations or Google Sheet. Attempted to refresh. 🚧</div>", unsafe_allow_html=True)
elif not st.session_state.data_loaded and df_original.empty and not st.session_state.get('last_data_refresh_time') :
     st.markdown("<div class='no-data-message'>🚧 Data loading... please wait. 🚧</div>", unsafe_allow_html=True)


st.sidebar.header("🌍 Global Search")
st.sidebar.caption("Search across all data. Overrides filters below when active.")
global_search_cols_definition = {"licenseNumber":"License Number", "storeName":"Store Name"}

ln_key = "licenseNumber"
ln_label = global_search_cols_definition[ln_key]
val_license = st.sidebar.text_input(f"Search {ln_label}:", value=st.session_state.get(ln_key+"_search", ""), key=f"{ln_key}_global_search_widget", help="Press Enter to search")
if val_license != st.session_state[ln_key+"_search"]:
    st.session_state[ln_key+"_search"] = val_license
    if val_license: st.session_state.show_global_search_dialog = True
    elif not st.session_state.get("storeName_search", ""): st.session_state.show_global_search_dialog = False
    st.rerun()

sn_key = "storeName"
sn_label = global_search_cols_definition[sn_key]
store_names_options = [""]
if not df_original.empty and sn_key in df_original.columns:
    unique_stores = sorted(df_original[sn_key].astype(str).dropna().unique())
    store_names_options.extend([name for name in unique_stores if name.strip()])
current_store_search = st.session_state.get(sn_key+"_search", "")
if current_store_search not in store_names_options: current_store_search = ""
try:
    current_store_index = store_names_options.index(current_store_search)
except ValueError:
    current_store_index = 0

selected_store = st.sidebar.selectbox(
    f"Search {sn_label}:", options=store_names_options, index=current_store_index,
    key=f"{sn_key}_global_search_widget_select", help="Select a store name to search"
)
if selected_store != st.session_state.get(sn_key+"_search", ""):
    st.session_state[sn_key+"_search"] = selected_store
    if selected_store: st.session_state.show_global_search_dialog = True
    elif not st.session_state.get("licenseNumber_search", ""): st.session_state.show_global_search_dialog = False
    st.rerun()
st.sidebar.markdown("---")
global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))

st.sidebar.header("🔍 Filters")
if global_search_active: st.sidebar.caption("ℹ️ Date and category filters are overridden by active Global Search.")
else: st.sidebar.caption("Apply date and category filters to the data.")

st.sidebar.markdown("##### Date Shortcuts")
s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
if s_col1.button("MTD", key="mtd_button_v3_10", use_container_width=True, disabled=global_search_active):
    if not global_search_active: start_mtd_shortcut = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd_shortcut, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col2.button("YTD", key="ytd_button_v3_10", use_container_width=True, disabled=global_search_active):
    if not global_search_active: start_ytd_shortcut = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd_shortcut, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
if s_col3.button("ALL", key="all_button_v3_10", use_container_width=True, disabled=global_search_active):
    if not global_search_active:
        all_start_shortcut = st.session_state.get('min_data_date_for_filter'); all_end_shortcut = st.session_state.get('max_data_date_for_filter')
        if all_start_shortcut and all_end_shortcut: st.session_state.date_range = (all_start_shortcut, all_end_shortcut)
        else: start_ytd_fallback_shortcut = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd_fallback_shortcut, today_for_shortcuts); st.sidebar.caption("Used YTD for 'ALL' (no data extent).")
        st.session_state.date_filter_is_active = True; st.rerun()
st.sidebar.markdown("---")
if not (isinstance(st.session_state.get('date_range'), tuple) and len(st.session_state.date_range) == 2 and isinstance(st.session_state.date_range[0], date) and isinstance(st.session_state.date_range[1], date)):
    ds_init_filter, de_init_filter, _, _ = get_default_date_range(df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_init_filter, de_init_filter)
current_session_start_dt, current_session_end_dt = st.session_state.date_range
min_dt_widget = st.session_state.get('min_data_date_for_filter'); max_dt_widget = st.session_state.get('max_data_date_for_filter')
value_for_widget_start = current_session_start_dt; value_for_widget_end = current_session_end_dt
if min_dt_widget and value_for_widget_start < min_dt_widget: value_for_widget_start = min_dt_widget
if max_dt_widget and value_for_widget_end > max_dt_widget: value_for_widget_end = max_dt_widget
if value_for_widget_start > value_for_widget_end: value_for_widget_start = value_for_widget_end

sel_range = st.sidebar.date_input("Date Range:", value=(value_for_widget_start, value_for_widget_end), min_value=min_dt_widget, max_value=max_dt_widget, key="date_sel_v3_10_conditional", disabled=global_search_active)
if not global_search_active and isinstance(sel_range, tuple) and len(sel_range) == 2 and isinstance(sel_range[0], date) and isinstance(sel_range[1], date):
    if sel_range != st.session_state.date_range: st.session_state.date_range = sel_range; st.session_state.date_filter_is_active = True; st.rerun()
start_dt, end_dt = st.session_state.date_range
cat_filters_definition = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for k,lbl in cat_filters_definition.items():
    options_df = df_original
    if not options_df.empty and k in options_df.columns and options_df[k].notna().any():
        opts = sorted([v for v in options_df[k].astype(str).dropna().unique() if v.strip()]); sel = st.session_state.get(k+"_filter",[]); current_selection_valid = [s for s in sel if s in opts]
        new_sel = st.sidebar.multiselect(f"Filter by {lbl}:", opts, default=current_selection_valid, key=f"{k}_cat_filter_widget_conditional", disabled=global_search_active)
        if not global_search_active and new_sel != current_selection_valid : st.session_state[k+"_filter"]=new_sel; st.rerun()
        elif global_search_active and sel != new_sel : st.session_state[k+"_filter"]=new_sel
    elif df_original.empty: st.sidebar.multiselect(f"Filter by {lbl}:", [], default=[], key=f"{k}_cat_filter_widget_no_data", help="No data loaded.", disabled=True)
    else: st.sidebar.multiselect(f"Filter by {lbl}:", [], default=[], key=f"{k}_cat_filter_widget_no_opts", help=f"No options for '{lbl}'.", disabled=global_search_active)

def clear_all_filters_and_search():
    ds_clear, de_clear, _, _ = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_clear, de_clear)
    st.session_state.date_filter_is_active = False
    st.session_state.licenseNumber_search = ""
    st.session_state.storeName_search = ""
    st.session_state.show_global_search_dialog = False
    for k_cat in cat_filters_definition: st.session_state[k_cat+"_filter"]=[]
    st.session_state.selected_transcript_key_dialog_global_search = None
    st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state.active_tab = TAB_OVERVIEW

if st.sidebar.button("🧹 Clear All Filters & Search",on_click=clear_all_filters_and_search,use_container_width=True, key="clear_filters_v3_14"):st.rerun()

with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)

if st.session_state.active_tab not in ALL_TABS: st.session_state.active_tab = TAB_OVERVIEW
try:
    current_tab_index = ALL_TABS.index(st.session_state.active_tab)
except ValueError:
    current_tab_index = 0; st.session_state.active_tab = TAB_OVERVIEW

selected_tab_from_radio = st.radio("Navigation:", ALL_TABS, index=current_tab_index, horizontal=True, key="main_tab_selector_v3_14")
if selected_tab_from_radio != st.session_state.active_tab:
    st.session_state.active_tab = selected_tab_from_radio; st.rerun()

summary_message = ""
if global_search_active:
    active_filters_parts = ["Global Search Active:"]
    if st.session_state.get("licenseNumber_search", ""): active_filters_parts.append(f"License Number '{st.session_state['licenseNumber_search']}'")
    if st.session_state.get("storeName_search", ""): active_filters_parts.append(f"Store Name '{st.session_state['storeName_search']}'")
    summary_message = " ".join(active_filters_parts) + ". (Results in pop-up. Other filters overridden)"
else:
    date_display_string = ""; current_filter_start_dt, current_filter_end_dt = st.session_state.date_range
    if isinstance(current_filter_start_dt, date) and isinstance(current_filter_end_dt, date):
        min_data_for_summary = st.session_state.get('min_data_date_for_filter'); max_data_for_summary = st.session_state.get('max_data_date_for_filter')
        is_all_data_range_and_active = False
        if min_data_for_summary and max_data_for_summary and current_filter_start_dt == min_data_for_summary and current_filter_end_dt == max_data_for_summary and st.session_state.get('date_filter_is_active', False): is_all_data_range_and_active = True
        if is_all_data_range_and_active: date_display_string = "🗓️ Dates: ALL"
        elif st.session_state.get('date_filter_is_active', False) or (current_filter_start_dt != default_s_init or current_filter_end_dt != default_e_init) :
             date_display_string = f"🗓️ Dates: {current_filter_start_dt.strftime('%b %d')} - {current_filter_end_dt.strftime('%b %d, %Y')}"
        else: date_display_string = f"🗓️ Dates: {current_filter_start_dt.strftime('%b %d')} - {current_filter_end_dt.strftime('%b %d, %Y')} (default MTD)"
    other_active_filters_list_local = []
    for k_cat, lbl_cat in cat_filters_definition.items():
        if st.session_state.get(k_cat+"_filter",[]): other_active_filters_list_local.append(f"{lbl_cat}: {', '.join(st.session_state[k_cat+'_filter'])}")
    if other_active_filters_list_local or st.session_state.get('date_filter_is_active', False) or (current_filter_start_dt != default_s_init or current_filter_end_dt != default_e_init) :
        final_summary_parts = [date_display_string] + other_active_filters_list_local
        summary_message = f"🔍 Filters Active: {'; '.join(filter(None,final_summary_parts))}. (No global search)"
    else: summary_message = f"Showing data for: {date_display_string}. No other filters active. (No global search)"
st.markdown(f"<div class='active-filters-summary'>{summary_message}</div>", unsafe_allow_html=True)

df_filtered_for_tabs = pd.DataFrame()
df_global_search_results = pd.DataFrame()

if not df_original.empty:
    if global_search_active:
        df_working_gs = df_original.copy()
        license_search_term = st.session_state.get("licenseNumber_search", "")
        store_search_term = st.session_state.get("storeName_search", "")
        if license_search_term and "licenseNumber" in df_working_gs.columns: df_working_gs = df_working_gs[df_working_gs['licenseNumber'].astype(str).str.contains(license_search_term, case=False, na=False)]
        if store_search_term and "storeName" in df_working_gs.columns: df_working_gs = df_working_gs[df_working_gs['storeName'] == store_search_term]
        df_global_search_results = df_working_gs.copy()
        df_filtered_for_tabs = df_global_search_results.copy()
    else:
        df_working_filters = df_original.copy()
        current_filter_start_dt, current_filter_end_dt = st.session_state.date_range
        if isinstance(current_filter_start_dt, date) and isinstance(current_filter_end_dt, date) and 'onboarding_date_only' in df_working_filters.columns and df_working_filters['onboarding_date_only'].notna().any():
            date_objects_for_filtering = pd.to_datetime(df_working_filters['onboarding_date_only'], errors='coerce').dt.date
            valid_dates_mask_filters = date_objects_for_filtering.notna()
            date_filter_mask = pd.Series([False] * len(df_working_filters), index=df_working_filters.index)
            if valid_dates_mask_filters.any(): date_filter_mask[valid_dates_mask_filters] = (date_objects_for_filtering[valid_dates_mask_filters] >= current_filter_start_dt) & (date_objects_for_filtering[valid_dates_mask_filters] <= current_filter_end_dt)
            df_working_filters = df_working_filters[date_filter_mask]
        for col_name, _ in cat_filters_definition.items():
            selected_values = st.session_state.get(f"{col_name}_filter", [])
            if selected_values and col_name in df_working_filters.columns: df_working_filters = df_working_filters[df_working_filters[col_name].astype(str).isin(selected_values)]
        df_filtered_for_tabs = df_working_filters.copy()
else:
    df_filtered_for_tabs = pd.DataFrame(); df_global_search_results = pd.DataFrame()

plotly_base_layout_settings = { "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR, "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":False, "margin": dict(l=40, r=20, t=60, b=40), "font_color": "var(--text-color)", "title_font_color": "var(--app-accent-primary)", "xaxis_title_font_color": "var(--text-color)", "yaxis_title_font_color": "var(--text-color)", "xaxis_tickfont_color": "var(--text-color)", "yaxis_tickfont_color": "var(--text-color)", "legend_font_color": "var(--text-color)", }
today_date_mtd = date.today(); mtd_s = today_date_mtd.replace(day=1); prev_mtd_e = mtd_s - timedelta(days=1); prev_mtd_s = prev_mtd_e.replace(day=1)
df_mtd, df_prev_mtd = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_s_orig = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date; valid_mask_orig = dates_s_orig.notna()
    if valid_mask_orig.any():
        df_valid_orig = df_original[valid_mask_orig].copy(); valid_dates_orig = dates_s_orig[valid_mask_orig]
        mtd_mask_calc = (valid_dates_orig >= mtd_s) & (valid_dates_orig <= today_date_mtd); prev_mask_calc = (valid_dates_orig >= prev_mtd_s) & (valid_dates_orig <= prev_mtd_e)
        df_mtd = df_valid_orig[mtd_mask_calc.values if len(mtd_mask_calc) == len(df_valid_orig) else mtd_mask_calc[df_valid_orig.index]]
        df_prev_mtd = df_valid_orig[prev_mask_calc.values if len(prev_mask_calc) == len(df_valid_orig) else prev_mask_calc[df_valid_orig.index]]
tot_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd); tot_prev,_,_,_ = calculate_metrics(df_prev_mtd)
delta_mtd = tot_mtd - tot_prev if pd.notna(tot_mtd) and pd.notna(tot_prev) else None


def display_data_table_and_details(df_to_display, context_key_prefix=""):
    # --- Styling Functions for DataFrame ---
    # Moved inside to ensure they are in scope, especially for st.dialog
    def style_boolean_cell(val):
        val_str = str(val).strip().lower()
        if val_str in ['true', '1', 'yes']: bg_color = '#D4EFDF'; text_color = "#003300"
        elif val_str in ['false', '0', 'no']: bg_color = '#FADBD8'; text_color = "#500000"
        else: return f'color: {"var(--text-color)"};'
        return f'background-color: {bg_color}; color: {text_color};'

    def style_sentiment_cell(val):
        val_str = str(val).strip().lower()
        bg_color = ""; text_color_override = None
        if val_str == 'positive': bg_color = '#D4EFDF'; text_color_override = "#003300"
        elif val_str == 'negative': bg_color = '#FADBD8'; text_color_override = "#500000"
        elif val_str == 'neutral': bg_color = '#F0F0F0'; text_color_override = "#333333"
        else: return f'color: {"var(--text-color)"};'
        text_color = text_color_override if text_color_override else get_contrasting_text_color(bg_color)
        return f'background-color: {bg_color}; color: {text_color};'

    def style_score_cell(val):
        try:
            score = float(val)
            if pd.isna(score): return f'color: {"var(--text-color)"};'
            if score >= 8: bg_color = '#C8E6C9'
            elif score >= 4: bg_color = '#FFF9C4'
            else: bg_color = '#FFCDD2'
            text_color = get_contrasting_text_color(bg_color)
            return f'background-color: {bg_color}; color: {text_color};'
        except (ValueError, TypeError):
            return f'color: {"var(--text-color)"};'

    def style_days_to_confirmation_cell(val):
        try:
            days = float(val)
            if pd.isna(days): return f'color: {"var(--text-color)"};'
            if days <= 7: bg_color = '#C8E6C9'
            elif days <= 14: bg_color = '#FFF9C4'
            else: bg_color = '#FFCDD2'
            text_color = get_contrasting_text_color(bg_color)
            return f'background-color: {bg_color}; color: {text_color};'
        except (ValueError, TypeError):
            return f'color: {"var(--text-color)"};'
    # --- End of Styling Functions ---

    if df_to_display is None or df_to_display.empty:
        context_name = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')
        if not df_original.empty:
             st.markdown(f"<div class='no-data-message'>📊 No data matches current {context_name} criteria. Try different settings! 📊</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-data-message'>💾 No data loaded to display. Please check data source or refresh. 💾</div>", unsafe_allow_html=True)
        return

    df_display_table = df_to_display.copy().reset_index(drop=True)
    
    preferred_cols_ordered = [
        'onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 
        'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 
        'contactNumber', 'confirmedNumber', 'deliveryDate', 'confirmationTimestamp'
    ] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
    
    cols_for_display_intermediate = [col for col in preferred_cols_ordered if col in df_display_table.columns]
    
    excluded_cols = ['onboardingWelcome', 'deliveryDateTs'] + \
                    [col for col in df_display_table.columns if col.endswith(('_dt', '_utc', '_str_original'))] + \
                    ['fullTranscript', 'summary', 'onboarding_date_only'] 

    final_cols_for_display = [col for col in cols_for_display_intermediate if col not in excluded_cols]
    other_existing_cols = [col for col in df_display_table.columns if col not in final_cols_for_display and col not in excluded_cols]
    final_cols_for_display.extend(other_existing_cols)
    final_cols_for_display = list(dict.fromkeys(final_cols_for_display))
    cols_for_display = [col for col in final_cols_for_display if col in df_display_table.columns]

    if not cols_for_display or df_display_table[cols_for_display].empty:
        context_name = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')
        st.markdown(f"<div class='no-data-message'>📋 No relevant columns to display for the {context_name} data. 📋</div>", unsafe_allow_html=True)
        return

    num_rows = len(df_display_table)
    if num_rows == 0: table_height = 100
    elif num_rows < 9: table_height = (num_rows + 1) * 35 + 20; table_height = max(100, table_height)
    else: table_height = 350

    def style_table_customized(df_to_style):
        styled_df = df_to_style.style
        if 'clientSentiment' in df_to_style.columns: styled_df = styled_df.applymap(style_sentiment_cell, subset=['clientSentiment'])
        if 'score' in df_to_style.columns: styled_df = styled_df.applymap(style_score_cell, subset=['score'])
        if 'days_to_confirmation' in df_to_style.columns: styled_df = styled_df.applymap(style_days_to_confirmation_cell, subset=['days_to_confirmation'])
        boolean_like_cols = [col for col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS if col in df_to_style.columns and col != 'score']
        for col_name_bool in boolean_like_cols: styled_df = styled_df.applymap(style_boolean_cell, subset=[col_name_bool])
        return styled_df

    st.dataframe(style_table_customized(df_display_table[cols_for_display]), use_container_width=True, height=table_height)
    
    st.markdown("---"); st.subheader("🔍 View Full Onboarding Details & Transcript")
    
    transcript_session_key = f"selected_transcript_key_{context_key_prefix}"
    if transcript_session_key not in st.session_state: 
        st.session_state[transcript_session_key] = None

    rerun_for_auto_select = False
    if len(df_display_table) == 1:
        first_row = df_display_table.iloc[0]
        auto_select_key = f"Idx 0: {first_row.get('storeName', 'N/A')} ({first_row.get('onboardingDate', 'N/A')})"
        if st.session_state[transcript_session_key] != auto_select_key:
            st.session_state[transcript_session_key] = auto_select_key
            rerun_for_auto_select = True 

    if rerun_for_auto_select and not st.session_state.get(f"{context_key_prefix}_auto_selected_once", False):
        st.session_state[f"{context_key_prefix}_auto_selected_once"] = True
        st.rerun()
    elif len(df_display_table) != 1:
         st.session_state[f"{context_key_prefix}_auto_selected_once"] = False


    if 'fullTranscript' in df_display_table.columns:
        transcript_options = { f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_table.iterrows() }
        
        if transcript_options:
            options_list_val = [None] + list(transcript_options.keys())
            current_selection_val = st.session_state[transcript_session_key]
            
            try: current_index_val = options_list_val.index(current_selection_val)
            except ValueError: current_index_val = 0; st.session_state[transcript_session_key] = None

            selected_key_display = st.selectbox("Select onboarding to view details:", options=options_list_val, index=current_index_val, format_func=lambda x: "Choose an entry..." if x is None else x, key=f"transcript_selector_{context_key_prefix}")
            
            if selected_key_display != st.session_state[transcript_session_key] : 
                st.session_state[transcript_session_key] = selected_key_display
                st.session_state[f"{context_key_prefix}_auto_selected_once"] = False
                st.rerun()

            if st.session_state[transcript_session_key] :
                selected_idx = transcript_options[st.session_state[transcript_session_key]]; selected_row = df_display_table.loc[selected_idx]
                st.markdown("##### Onboarding Summary:"); summary_html_parts = []
                summary_items = { "Store": selected_row.get('storeName', 'N/A'), "Rep": selected_row.get('repName', 'N/A'), "Score": selected_row.get('score', 'N/A'), "Status": selected_row.get('status', 'N/A'), "Sentiment": selected_row.get('clientSentiment', 'N/A') }
                for item_label, item_value in summary_items.items(): summary_html_parts.append(f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>")
                data_summary_text = selected_row.get('summary', 'N/A'); summary_html_parts.append(f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary:</strong> {data_summary_text}</div>")
                st.markdown("<div class='transcript-summary-grid'>" + "".join(summary_html_parts) + "</div>", unsafe_allow_html=True)
                st.markdown("<div class='transcript-details-section'>", unsafe_allow_html=True); st.markdown("##### Key Requirement Checks:")
                for item_column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                    details = KEY_REQUIREMENT_DETAILS.get(item_column_name)
                    if details: desc = details.get("description", item_column_name.replace('_',' ').title()); item_type = details.get("type", ""); val_str = str(selected_row.get(item_column_name, "")).lower(); met = val_str in ['true', '1', 'yes']; emoji = "✅" if met else "❌"; type_tag = f"<span class='type'>[{item_type}]</span>" if item_type else ""; st.markdown(f"<div class='requirement-item'>{emoji} {desc} {type_tag}</div>", unsafe_allow_html=True)
                st.markdown("---", help="Separator before full transcript"); st.markdown("##### Full Transcript:")
                content = selected_row.get('fullTranscript', "");
                if content and content.strip() != 'NA' and content.strip() :
                    html_transcript = "<div class='transcript-container'>"
                    for line in content.replace('\\n', '\n').split('\n'):
                        line = line.strip();
                        if not line: continue
                        parts = line.split(":", 1); speaker = f"<strong>{parts[0].strip()}:</strong>" if len(parts) == 2 else ""
                        msg = parts[1].strip().replace('\n', '<br>') if len(parts) == 2 else line.replace('\n', '<br>')
                        html_transcript += f"<p class='transcript-line'>{speaker} {msg}</p>"
                    st.markdown(html_transcript + "</div>", unsafe_allow_html=True)
                else: st.info("No transcript available or empty.")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            context_name = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')
            st.markdown(f"<div class='no-data-message'>📋 No entries in the table from {context_name} context to select for details. 📋</div>", unsafe_allow_html=True)
    else:
        context_name = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')
        st.markdown(f"<div class='no-data-message'>📜 No data in table for transcript viewer ('fullTranscript' column missing) in {context_name} context. 📜</div>", unsafe_allow_html=True)
    st.markdown("---"); csv_data = convert_df_to_csv(df_display_table[cols_for_display]); st.download_button(f"📥 Download These {context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','')} Results", csv_data, f'{context_key_prefix}_results.csv', 'text/csv', use_container_width=True, key=f"download_csv_{context_key_prefix}")

# --- Global Search Dialog ---
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("Global Search Results", width="large")
    def show_gs_dialog_content():
        st.markdown("##### Results from your Global Search:")
        if not df_global_search_results.empty:
            display_data_table_and_details(df_global_search_results, context_key_prefix="dialog_global_search")
        else:
            st.info("No results found for your global search terms.")

        if st.button("Close & Clear Search", key="close_gs_dialog_button_v14"):
            st.session_state.show_global_search_dialog = False
            st.session_state.licenseNumber_search = ""
            st.session_state.storeName_search = ""
            if 'selected_transcript_key_dialog_global_search' in st.session_state:
                st.session_state.selected_transcript_key_dialog_global_search = None
            st.session_state["dialog_global_search_auto_selected_once"] = False
            st.rerun()
    show_gs_dialog_content()

# --- Tab Definitions ---
if st.session_state.active_tab == TAB_OVERVIEW:
    with st.container():
        st.header("📈 Month-to-Date (MTD) Overview"); c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("🗓️ Onboardings MTD", tot_mtd if pd.notna(tot_mtd) else "0", f"{delta_mtd:+}" if delta_mtd is not None and pd.notna(delta_mtd) else "N/A vs LY", help="Total onboardings this month to date vs. previous month for the same period.")
        with c2: st.metric("✅ Success Rate MTD", f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A", help="Percentage of onboardings marked 'Confirmed' this month to date.")
        with c3: st.metric("⭐ Avg Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A", help="Average onboarding score (0-10) this month to date.")
        with c4: st.metric("⏳ Avg Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A", help="Average number of days from delivery to confirmation for onboardings confirmed this month to date.")
    with st.container():
        st.header("📊 Filtered Data Overview");
        if not global_search_active:
            if not df_filtered_for_tabs.empty:
                tot_filt, sr_filt, score_filt, days_filt = calculate_metrics(df_filtered_for_tabs)
                fc1,fc2,fc3,fc4 = st.columns(4)
                with fc1: st.metric("📄 Onboardings (Filtered View)", tot_filt if pd.notna(tot_filt) else "0")
                with fc2: st.metric("🎯 Success Rate (Filtered View)", f"{sr_filt:.1f}%" if pd.notna(sr_filt) else "N/A")
                with fc3: st.metric("🌟 Avg Score (Filtered View)", f"{score_filt:.2f}" if pd.notna(score_filt) else "N/A")
                with fc4: st.metric("⏱️ Avg Days Confirm (Filtered View)", f"{days_filt:.1f}" if pd.notna(days_filt) else "N/A")
            else: st.markdown("<div class='no-data-message'>🤷 No data matches current filters for Overview. Try adjusting your selections! 🤷</div>", unsafe_allow_html=True)
        else:
             st.info("Global search is active. Close the search pop-up to see the filtered data overview.")

elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if not global_search_active:
        display_data_table_and_details(df_filtered_for_tabs, context_key_prefix="filtered_analysis")
        st.header("📊 Key Visuals (Based on Date/Category Filters)")
        if not df_filtered_for_tabs.empty:
            c1_charts, c2_charts = st.columns(2)
            with c1_charts:
                if 'status' in df_filtered_for_tabs.columns and df_filtered_for_tabs['status'].notna().any(): status_counts = df_filtered_for_tabs['status'].value_counts().reset_index(); status_fig = px.bar(status_counts, x='status', y='count', color='status', title="Onboarding Status Distribution", color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ); status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📉 Status data unavailable for chart. 📉</div>", unsafe_allow_html=True)
                if 'repName' in df_filtered_for_tabs.columns and df_filtered_for_tabs['repName'].notna().any(): rep_counts = df_filtered_for_tabs['repName'].value_counts().reset_index(); rep_fig = px.bar(rep_counts, x='repName', y='count', color='repName', title="Onboardings by Representative", color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ); rep_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>👥 Rep data unavailable for chart. 👥</div>", unsafe_allow_html=True)
            with c2_charts:
                if 'clientSentiment' in df_filtered_for_tabs.columns and df_filtered_for_tabs['clientSentiment'].notna().any(): sent_counts = df_filtered_for_tabs['clientSentiment'].value_counts().reset_index(); current_sentiment_map = { s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), ACTIVE_ACCENT_MUTED) for s in sent_counts['clientSentiment'].unique() }; sent_fig = px.pie(sent_counts, names='clientSentiment', values='count', hole=0.5, title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=current_sentiment_map); sent_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(sent_fig, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>😊 Sentiment data unavailable for chart. 😊</div>", unsafe_allow_html=True)
                df_conf_chart = df_filtered_for_tabs[df_filtered_for_tabs['status'].astype(str).str.lower() == 'confirmed'].copy()
                actual_key_cols_for_chart = [col for col in ORDERED_CHART_REQUIREMENTS if col in df_conf_chart.columns]
                if not df_conf_chart.empty and actual_key_cols_for_chart:
                    checklist_data_for_chart = []
                    for item_col_name_for_chart in actual_key_cols_for_chart:
                        item_details_obj = KEY_REQUIREMENT_DETAILS.get(item_col_name_for_chart); chart_label_for_bar = item_details_obj.get("chart_label", item_col_name_for_chart.replace('_',' ').title()) if item_details_obj else item_col_name_for_chart.replace('_',' ').title(); map_bool_for_chart = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                        if item_col_name_for_chart in df_conf_chart.columns:
                            bool_series_for_chart = df_conf_chart[item_col_name_for_chart].astype(str).str.lower().map(map_bool_for_chart)
                            bool_series_for_chart = pd.to_numeric(bool_series_for_chart, errors='coerce')
                            if bool_series_for_chart.notna().any():
                                true_count_for_chart = bool_series_for_chart.sum(); total_valid_for_chart = bool_series_for_chart.notna().sum()
                                if total_valid_for_chart > 0: checklist_data_for_chart.append({"Key Requirement": chart_label_for_bar, "Completion (%)": (true_count_for_chart/total_valid_for_chart)*100})
                    if checklist_data_for_chart:
                        df_checklist_bar_chart = pd.DataFrame(checklist_data_for_chart)
                        if not df_checklist_bar_chart.empty: checklist_bar_fig = px.bar(df_checklist_bar_chart.sort_values("Completion (%)",ascending=True), x="Completion (%)", y="Key Requirement", orientation='h', title="Key Requirement Completion (Confirmed Onboardings)", color_discrete_sequence=[ACTIVE_ACCENT_PRIMARY]); checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}); st.plotly_chart(checklist_bar_fig, use_container_width=True)
                        else: st.markdown("<div class='no-data-message'>📊 No data for key requirement chart (confirmed, post-processing). 📊</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='no-data-message'>📊 No data for key requirement chart (confirmed, no checklist items processed). 📊</div>", unsafe_allow_html=True)
                else: st.markdown("<div class='no-data-message'>✅ No 'confirmed' onboardings or relevant checklist columns for requirement chart. ✅</div>", unsafe_allow_html=True)
        elif not df_original.empty : st.markdown("<div class='no-data-message'>🖼️ No data matches current filters for detailed visuals. 🖼️</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>💾 No data loaded to display. Please check data source or refresh. 💾</div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Global Search is active. Results are shown in a pop-up dialog. Close the dialog to use category/date filters for this tab.")

elif st.session_state.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS)
    st.markdown(f"*(Based on {'Global Search Results (Pop-Up)' if global_search_active else 'Filtered Data (Date/Category)'})*")
    if not df_filtered_for_tabs.empty:
        if 'onboarding_date_only' in df_filtered_for_tabs.columns and df_filtered_for_tabs['onboarding_date_only'].notna().any():
            df_trend_for_tab3 = df_filtered_for_tabs.copy(); df_trend_for_tab3['onboarding_date_only'] = pd.to_datetime(df_trend_for_tab3['onboarding_date_only'], errors='coerce'); df_trend_for_tab3.dropna(subset=['onboarding_date_only'], inplace=True)
            if not df_trend_for_tab3.empty:
                span_for_trend_tab3 = (df_trend_for_tab3['onboarding_date_only'].max() - df_trend_for_tab3['onboarding_date_only'].min()).days; freq_for_trend_tab3 = 'D' if span_for_trend_tab3 <= 62 else ('W-MON' if span_for_trend_tab3 <= 365*1.5 else 'ME')
                data_for_trend_tab3 = df_trend_for_tab3.set_index('onboarding_date_only').resample(freq_for_trend_tab3).size().reset_index(name='count')
                if not data_for_trend_tab3.empty: fig_for_trend_tab3 = px.line(data_for_trend_tab3, x='onboarding_date_only', y='count', markers=True, title="Onboardings Over Period", color_discrete_sequence=[ACTIVE_ACCENT_HIGHLIGHT]); fig_for_trend_tab3.update_layout(plotly_base_layout_settings); st.plotly_chart(fig_for_trend_tab3, use_container_width=True)
                else: st.markdown("<div class='no-data-message'>📈 Not enough data for trend plot after resampling. 📈</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='no-data-message'>📅 No valid date data for trend chart after processing. 📅</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>🗓️ Date column ('onboarding_date_only') missing for trend chart. 🗓️</div>", unsafe_allow_html=True)
        if 'days_to_confirmation' in df_filtered_for_tabs.columns and df_filtered_for_tabs['days_to_confirmation'].notna().any():
            days_data_for_hist_tab3 = pd.to_numeric(df_filtered_for_tabs['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist_tab3.empty: nbins_for_hist_tab3 = max(10, min(50, int(len(days_data_for_hist_tab3)/5))) if len(days_data_for_hist_tab3) > 20 else (len(days_data_for_hist_tab3.unique()) or 10); fig_days_dist_hist_tab3 = px.histogram(days_data_for_hist_tab3, nbins=nbins_for_hist_tab3, title="Days to Confirmation Distribution", color_discrete_sequence=[ACTIVE_ACCENT_SECONDARY]); fig_days_dist_hist_tab3.update_layout(plotly_base_layout_settings); st.plotly_chart(fig_days_dist_hist_tab3, use_container_width=True)
            else: st.markdown("<div class='no-data-message'>⏳ No valid 'Days to Confirmation' data for distribution plot. ⏳</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' column missing for distribution plot. ⏱️</div>", unsafe_allow_html=True)
    elif not df_original.empty : st.markdown("<div class='no-data-message'>📉 No data matches current search/filters for Trends & Distributions. 📉</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='no-data-message'>💾 No data loaded to display. Please check data source or refresh. 💾</div>", unsafe_allow_html=True)

st.markdown("---"); st.markdown(f"<div class='footer'>Onboarding Performance Dashboard v3.20 © {datetime.now().year} Nexus Workflow. All Rights Reserved.</div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Data Controls")

if st.sidebar.button("🔄 Refresh Data", key="refresh_data_button_v319"):
    st.cache_data.clear()
    st.session_state.data_loaded = False
    st.session_state.last_data_refresh_time = None
    st.session_state.df_original = pd.DataFrame()
    st.session_state.licenseNumber_search = ""
    st.session_state.storeName_search = ""
    st.session_state.show_global_search_dialog = False
    for f_key_clear in ['repName_filter', 'status_filter', 'clientSentiment_filter']:
        if f_key_clear in st.session_state: st.session_state[f_key_clear] = []
    ds_clear_refresh, de_clear_refresh, _, _ = get_default_date_range(None)
    st.session_state.date_range = (ds_clear_refresh, de_clear_refresh)
    st.session_state.date_filter_is_active = False
    st.session_state.active_tab = TAB_OVERVIEW
    if 'selected_transcript_key_dialog_global_search' in st.session_state:
        st.session_state.selected_transcript_key_dialog_global_search = None
    if 'selected_transcript_key_filtered_analysis' in st.session_state:
        st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state["dialog_global_search_auto_selected_once"] = False
    st.session_state["filtered_analysis_auto_selected_once"] = False
    st.rerun()

if st.session_state.get('last_data_refresh_time'):
    refresh_time_str = st.session_state.last_data_refresh_time.strftime('%b %d, %Y %I:%M %p')
    st.sidebar.caption(f"Last data refresh attempt: {refresh_time_str}")
    if not st.session_state.get('data_loaded', False):
        st.sidebar.caption("⚠️ Data not loaded successfully during the last attempt.")
else:
    st.sidebar.caption("Data not yet loaded or refresh triggered. Automatic load initiated if applicable.")

st.sidebar.markdown("---")
current_theme_from_streamlit = st.get_option("theme.base")
theme_display_name_str = ""
if current_theme_from_streamlit and isinstance(current_theme_from_streamlit, str) and current_theme_from_streamlit.lower() in ["light", "dark"]:
    theme_display_name_str = current_theme_from_streamlit.capitalize()

info_string = f"App Version: 3.20"
if theme_display_name_str:
    info_string += f" ({theme_display_name_str} Mode)"
st.sidebar.info(info_string)