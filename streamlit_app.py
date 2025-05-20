import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
from collections.abc import Mapping 
import time
import numpy as np
import re 
import matplotlib

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v3.1", 
    page_icon="💎", # Diamond, for DIME perhaps?
    layout="wide"
)

# --- Color Palette ---
ICE_COLD = "#a0d2eb"        # Light Blue
FREEZE_PURPLE = "#e5eaf5"   # Very Light, almost white purple/blue
MEDIUM_PURPLE = "#d0bdf4"   # Light Lavender
PURPLE_PAIN = "#8458B3"     # Medium-Dark Purple (Primary Accent)
HEAVY_PURPLE = "#a28089"    # Muted, desaturated purplish-pink/mauve (Good for secondary text on light bg)

PLOT_BG_COLOR = "rgba(0,0,0,0)" # Transparent background for plots

# Fallback Dark Theme Specifics (used in var() fallbacks)
DARK_BACKGROUND_FALLBACK = "#1F2128" 
DARK_CARD_BACKGROUND_FALLBACK = "#2C2F3A" 
DARK_TEXT_PRIMARY_FALLBACK = FREEZE_PURPLE
DARK_TEXT_SECONDARY_FALLBACK = MEDIUM_PURPLE


# --- Custom Styling (CSS) ---
st.markdown(f"""
<style>
    /* General App Styles */
    .stApp {{
        background-color: var(--background-color, {DARK_BACKGROUND_FALLBACK}); 
    }}
    .stApp > header {{ 
        background-color: transparent !important; 
    }} 
    h1 {{ 
        color: {PURPLE_PAIN}; 
        text-align: center; 
        padding-top: 1em; 
        padding-bottom: 0.8em; 
        font-weight: 600;
        letter-spacing: 1px;
    }} 
    h2, h3 {{ 
        color: {PURPLE_PAIN}; /* Changed from ICE_COLD for better light/dark contrast */
        border-bottom: 2px solid {PURPLE_PAIN} !important; 
        padding-bottom: 0.4em; 
        margin-top: 1.5em;
        margin-bottom: 1em;
        font-weight: 500;
    }} 
    h5 {{ /* For sub-sections like "Onboarding Summary" */
        color: {PURPLE_PAIN}; /* Changed from MEDIUM_PURPLE */
        opacity: 0.9;
        margin-top: 1em;
        margin-bottom: 0.5em;
        font-weight: 500;
    }}
    
    /* Metric Widget Styles */
    div[data-testid="stMetric"], .metric-card {{
        background-color: var(--secondary-background-color, {DARK_CARD_BACKGROUND_FALLBACK});
        padding: 1.2em 1.5em;
        border-radius: 10px;
        border: 1px solid var(--border-color, #3a3f4b); /* Subtle border */
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); /* Softer shadow */
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }}
    div[data-testid="stMetric"]:hover, .metric-card:hover {{
         transform: translateY(-4px);
         box-shadow: 0 6px 16px rgba(0,0,0,0.18);
    }}
    div[data-testid="stMetricLabel"] > div {{ 
        color: var(--text-color, {DARK_TEXT_SECONDARY_FALLBACK}) !important; 
        font-weight: 500;
        font-size: 0.95em;
        opacity: 0.85;
    }}
    div[data-testid="stMetricValue"] > div {{ 
        color: var(--text-color, {DARK_TEXT_PRIMARY_FALLBACK}) !important; 
        font-size: 2.2rem !important; 
        font-weight: 600;
    }}
    div[data-testid="stMetricDelta"] > div {{ 
        color: var(--text-color, {DARK_TEXT_SECONDARY_FALLBACK}) !important; 
        font-weight: 500;
        opacity: 0.9;
    }}
    
    /* Expander Styles */
    .streamlit-expanderHeader {{ 
        color: {PURPLE_PAIN} !important; /* Changed from MEDIUM_PURPLE */
        font-weight: 500;
        font-size: 1.05em;
    }} 
    .streamlit-expander {{
        border: 1px solid var(--border-color, #444); /* Theme variable for border */
        border-radius: 8px;
    }}
    
    /* DataFrame Styles */
    .stDataFrame {{ 
        border: 1px solid var(--border-color, #444); /* Theme variable for border */
        border-radius: 8px;
    }} 
    
    /* Custom Tab (Radio Button) Styles */
    div[data-testid="stRadio"] label {{ 
        padding: 10px 18px; 
        margin: 0 3px;
        border-radius: 8px 8px 0 0; 
        border: 1px solid transparent;
        border-bottom: none;
        background-color: var(--secondary-background-color, {DARK_CARD_BACKGROUND_FALLBACK});
        color: var(--text-color, {DARK_TEXT_SECONDARY_FALLBACK});
        opacity: 0.7;
        transition: background-color 0.3s ease, color 0.3s ease, opacity 0.3s ease, border-color 0.3s ease;
        font-weight: 500;
    }}
    div[data-testid="stRadio"] input:checked + div label {{ 
        background-color: var(--background-color, {DARK_BACKGROUND_FALLBACK}); 
        color: {PURPLE_PAIN};
        font-weight: 600;
        opacity: 1.0;
        border-top: 2px solid {PURPLE_PAIN};
        border-left: 1px solid var(--border-color, #555); /* Theme variable */
        border-right: 1px solid var(--border-color, #555); /* Theme variable */
    }}
    div[data-testid="stRadio"] {{ 
        padding-bottom: 0px; 
        border-bottom: 2px solid {PURPLE_PAIN}; 
        margin-bottom: 25px; 
    }}
     div[data-testid="stRadio"] > label > div:first-child {{
        display: none; 
    }}
    
    /* Transcript Viewer Specific Styles */
    .transcript-summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px; }}
    .transcript-summary-item strong {{ color: {PURPLE_PAIN}; }} /* Changed from ICE_COLD */
    .transcript-summary-item-fullwidth {{ grid-column: 1 / -1; margin-top: 8px; }}
    .requirement-item {{ margin-bottom: 10px; padding: 8px; border-left: 4px solid {MEDIUM_PURPLE}; background-color: var(--secondary-background-color, #2a2d39); border-radius: 4px; }}
    .requirement-item .type {{ font-weight: 500; color: {HEAVY_PURPLE}; opacity: 0.9; font-size: 0.85em; margin-left: 8px; }} /* Changed from ICE_COLD */
    .transcript-container {{ 
        background-color: var(--secondary-background-color, {DARK_CARD_BACKGROUND_FALLBACK}); 
        color: var(--text-color, {DARK_TEXT_PRIMARY_FALLBACK}); 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid var(--border-color, #444); /* Theme variable */
        max-height: 450px; 
        overflow-y: auto; 
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; 
        font-size: 0.9em;
        line-height: 1.6;
    }}
    .transcript-line {{ margin-bottom: 10px; word-wrap: break-word; white-space: pre-wrap; }}
    .transcript-line strong {{ color: {PURPLE_PAIN}; }}

    /* Button styles */
    div[data-testid="stButton"] > button {{
        background-color: {PURPLE_PAIN};
        color: {FREEZE_PURPLE}; /* Light text for dark purple BG */
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 500;
        transition: background-color 0.3s ease, transform 0.2s ease;
    }}
    div[data-testid="stButton"] > button:hover {{
        background-color: {MEDIUM_PURPLE}; 
        color: {DARK_BACKGROUND_FALLBACK}; /* Dark text for lighter purple BG */
        transform: translateY(-2px);
    }}
    div[data-testid="stDownloadButton"] > button {{
        background-color: {ICE_COLD}; /* Light blue background */
        color: {DARK_BACKGROUND_FALLBACK}; /* Dark text for light button */
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 500;
        transition: background-color 0.3s ease, transform 0.2s ease;
    }}
    div[data-testid="stDownloadButton"] > button:hover {{
        background-color: {FREEZE_PURPLE}; /* Very light on hover */
        color: {DARK_BACKGROUND_FALLBACK};
        transform: translateY(-2px);
    }}

    /* Sidebar styling */
    div[data-testid="stSidebarUserContent"] {{
        background-color: var(--secondary-background-color, {DARK_CARD_BACKGROUND_FALLBACK});
        padding: 1.5em 1em;
    }}
    /* Target specific sidebar headers if needed, otherwise they inherit general h2/h3 */
    div[data-testid="stSidebarUserContent"] h2, 
    div[data-testid="stSidebarUserContent"] h3 {{
        color: {ICE_COLD}; /* Keep sidebar headers distinct if desired */
        border-bottom-color: {MEDIUM_PURPLE};
    }}
</style>
""", unsafe_allow_html=True)

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
    with st.form("password_form_main_app"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint)
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
def authenticate_gspread():
    gcp_secrets = st.secrets.get("gcp_service_account")
    if gcp_secrets is None: st.error("GCP secrets NOT FOUND."); return None
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"GCP secrets not structured correctly (type: {type(gcp_secrets)})."); return None
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing = [k for k in required_keys if gcp_secrets.get(k) is None]
    if missing: st.error(f"GCP secrets missing keys: {', '.join(missing)}."); return None
    try:
        creds = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES) 
        return gspread.authorize(creds)
    except Exception as e: st.error(f"Google Auth Error: {e}"); return None

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
def load_data_from_google_sheet(_url_param, _ws_param):
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame()
    if not ws_name: st.error("Config: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame()
    gc = authenticate_gspread() 
    if gc is None: return pd.DataFrame()
    try:
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url) 
        ws = ss.worksheet(ws_name)
        data = ws.get_all_records(head=1, expected_headers=None)
        if not data: st.warning("No data in sheet."); return pd.DataFrame()
        df = pd.DataFrame(data)
        if df.empty: st.warning("Empty DataFrame after load."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound: st.error(f"Sheet Not Found: '{url}'. Check URL & permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound: st.error(f"Worksheet Not Found: '{ws_name}'."); return pd.DataFrame()
    except Exception as e: st.error(f"Error Loading Data: {e}"); return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_cols = {'onboardingDate':'onboardingDate_dt', 'deliveryDate':'deliveryDate_dt', 'confirmationTimestamp':'confirmationTimestamp_dt'}
    for col, new_col in date_cols.items():
        if col in df: df[new_col] = robust_to_datetime(df[col].astype(str).str.replace('\n','',regex=False).str.strip())
        else: df[new_col] = pd.NaT
        if col == 'onboardingDate': df['onboarding_date_only'] = df[new_col].dt.date
    
    if 'deliveryDate_dt' in df and 'confirmationTimestamp_dt' in df:
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')
        def to_utc(s):
            if pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
                try: return s.dt.tz_localize('UTC') if s.dt.tz is None else s.dt.tz_convert('UTC')
                except Exception: return s
            return s
        df['days_to_confirmation'] = (to_utc(df['confirmationTimestamp_dt']) - to_utc(df['deliveryDate_dt'])).dt.days
    else: df['days_to_confirmation'] = pd.NA
    
    str_cols_ensure = ['status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript', 'summary']
    for col in str_cols_ensure:
        if col not in df.columns: df[col] = ""
        else: df[col] = df[col].astype(str).fillna("")
    if 'score' not in df.columns: df['score'] = pd.NA
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    
    checklist_cols_to_ensure = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS + ['onboardingWelcome'] 
    for col in checklist_cols_to_ensure:
        if col not in df.columns: df[col] = pd.NA 
            
    return df

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
    if series is not None and not series.empty:
        dates = pd.to_datetime(series,errors='coerce').dt.date.dropna()
        if not dates.empty:
            min_d,max_d = dates.min(),dates.max(); s=max(s,min_d); e=min(e,max_d)
            if s > e: s,e = min_d,max_d
    return s,e,min_d,max_d

default_s, default_e, _, _ = get_default_date_range(None)
session_state_defaults = {
    'data_loaded': False, 'df_original': pd.DataFrame(), 'date_range': (default_s, default_e),
    'active_tab': "🌌 Overview", 
    'repName_filter': [], 'status_filter': [], 'clientSentiment_filter': [],
    'licenseNumber_search': "", 'storeName_search': "", 'selected_transcript_key': None
}
for k, v in session_state_defaults.items():
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state.data_loaded:
    url_s, ws_s = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"), st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url_s or not ws_s: st.error("Config Error: Sheet URL/Name missing in secrets.")
    else:
        with st.spinner("Loading data..."):
            df = load_data_from_google_sheet(url_s, ws_s) 
            if not df.empty:
                st.session_state.df_original = df; st.session_state.data_loaded = True
                ds,de,_,_ = get_default_date_range(df.get('onboarding_date_only'))
                st.session_state.date_range = (ds,de) if ds and de else (default_s,default_e)
                # Display success message in sidebar after successful load
                st.sidebar.success(f"Data loaded: {len(df_original)} records.") 
            else: 
                st.session_state.df_original = pd.DataFrame(); st.session_state.data_loaded = False
                st.sidebar.error("Data loading failed or sheet is empty.") # More specific message
df_original = st.session_state.df_original 

st.title("🌌 Onboarding Performance Dashboard 🌌") 

if not st.session_state.data_loaded or df_original.empty:
    # Error message already handled by load_data or initial check, 
    # but this provides a fallback if user lands here with no data.
    if not (st.secrets.get("GOOGLE_SHEET_URL_OR_NAME") and st.secrets.get("GOOGLE_WORKSHEET_NAME")):
        pass # Error about secrets missing is already covered.
    else:
        st.error("Failed to load data. Check sheet, permissions, secrets & refresh.")
    if st.sidebar.button("🔄 Force Refresh", key="refresh_fail"):
        st.cache_data.clear(); st.session_state.clear(); st.rerun()

with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=True): 
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items for completeness: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data", key="refresh_main"):
    st.cache_data.clear(); st.session_state.clear(); st.rerun()
st.sidebar.header("🔍 Filters")
dates_series = df_original.get('onboarding_date_only')
def_s, def_e, min_dt, max_dt = get_default_date_range(dates_series)
if 'date_range' not in st.session_state or not (isinstance(st.session_state.date_range,tuple) and len(st.session_state.date_range)==2):
    st.session_state.date_range = (def_s,def_e) if def_s and def_e else (date.today().replace(day=1),date.today())
if min_dt and max_dt and def_s and def_e:
    val_s,val_e = st.session_state.date_range
    sel_range = st.sidebar.date_input("Date Range:",value=(max(min_dt,val_s) if val_s else min_dt,min(max_dt,val_e) if val_e else max_dt), 
                                      min_value=min_dt,max_value=max_dt,key="date_sel")
    if sel_range != st.session_state.date_range: st.session_state.date_range = sel_range
else: st.sidebar.warning("Date data unavailable for filter.")
start_dt,end_dt = st.session_state.date_range if isinstance(st.session_state.date_range,tuple) and len(st.session_state.date_range)==2 else (None,None)

search_cols_definition = {"licenseNumber":"License Number", "storeName":"Store Name"}
for k,lbl in search_cols_definition.items():
    if k+"_search" not in st.session_state: st.session_state[k+"_search"]=""
    val = st.sidebar.text_input(f"Search {lbl} (on all data):",value=st.session_state[k+"_search"],key=f"{k}_widget")
    if val != st.session_state[k+"_search"]: st.session_state[k+"_search"]=val
cat_filters_definition = {'repName':'Rep(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for k,lbl in cat_filters_definition.items():
    if k in df_original.columns and df_original[k].notna().any():
        opts = sorted([v for v in df_original[k].astype(str).dropna().unique() if v.strip()])
        if k+"_filter" not in st.session_state: st.session_state[k+"_filter"]=[]
        sel = [v for v in st.session_state[k+"_filter"] if v in opts]
        new_sel = st.sidebar.multiselect(f"Filter by {lbl}:",opts,default=sel,key=f"{k}_widget")
        if new_sel != st.session_state[k+"_filter"]: st.session_state[k+"_filter"]=new_sel
def clear_filters_cb():
    ds,de,_,_ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds,de) if ds and de else (date.today().replace(day=1),date.today())
    for k in search_cols_definition: st.session_state[k+"_search"]=""
    for k in cat_filters_definition: st.session_state[k+"_filter"]=[]
    st.session_state.selected_transcript_key = None 
if st.sidebar.button("🧹 Clear All Filters",on_click=clear_filters_cb,use_container_width=True): st.rerun()

df_filtered = pd.DataFrame() 
if 'df_original' in st.session_state and not st.session_state.df_original.empty:
    df_working = st.session_state.df_original.copy()
    license_search_term = st.session_state.get("licenseNumber_search", "")
    if license_search_term and "licenseNumber" in df_working.columns:
        df_working = df_working[df_working['licenseNumber'].astype(str).str.contains(license_search_term, case=False, na=False)]
    store_search_term = st.session_state.get("storeName_search", "")
    if store_search_term and "storeName" in df_working.columns:
        df_working = df_working[df_working['storeName'].astype(str).str.contains(store_search_term, case=False, na=False)]
    if start_dt and end_dt and 'onboarding_date_only' in df_working.columns:
        date_objects_for_filtering = pd.to_datetime(df_working['onboarding_date_only'], errors='coerce').dt.date
        date_filter_mask = date_objects_for_filtering.notna() & \
                           (date_objects_for_filtering >= start_dt) & \
                           (date_objects_for_filtering <= end_dt)
        df_working = df_working[date_filter_mask]
    for col_name, _ in cat_filters_definition.items(): 
        selected_values = st.session_state.get(f"{col_name}_filter", [])
        if selected_values and col_name in df_working.columns: 
            df_working = df_working[df_working[col_name].astype(str).isin(selected_values)]
    df_filtered = df_working.copy() 
else: df_filtered = pd.DataFrame() 

# Updated Plotly Layout with new color scheme and theme variables
plotly_base_layout_settings = {
    "plot_bgcolor": PLOT_BG_COLOR, 
    "paper_bgcolor": PLOT_BG_COLOR, 
    "font_color": "var(--text-color)", # Use Streamlit's theme variable for general text
    "title_font_color": PURPLE_PAIN, 
    "legend_font_color": "var(--text-color)",
    "title_x":0.5, 
    "xaxis_showgrid":False, "yaxis_showgrid":False,
    "xaxis_title_font_color": "var(--text-color)", # Use theme variable
    "yaxis_title_font_color": "var(--text-color)", # Use theme variable
    "xaxis_tickfont_color": "var(--text-color)",   # Use theme variable
    "yaxis_tickfont_color": "var(--text-color)",   # Use theme variable
    "margin": dict(l=40, r=20, t=60, b=40) # Adjust margins for better spacing
}

today_date = date.today(); mtd_s = today_date.replace(day=1)
prev_mtd_e = mtd_s - timedelta(days=1); prev_mtd_s = prev_mtd_e.replace(day=1)
df_mtd, df_prev_mtd = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_s = pd.to_datetime(df_original['onboarding_date_only'],errors='coerce').dt.date
    valid_mask = dates_s.notna()
    if valid_mask.any():
        df_valid = df_original[valid_mask].copy(); valid_dates = dates_s[valid_mask]
        mtd_mask = (valid_dates >= mtd_s) & (valid_dates <= today_date)
        prev_mask = (valid_dates >= prev_mtd_s) & (valid_dates <= prev_mtd_e)
        df_mtd = df_valid[mtd_mask.values]; df_prev_mtd = df_valid[prev_mask.values]
tot_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)
tot_prev,_,_,_ = calculate_metrics(df_prev_mtd) 
delta_mtd = tot_mtd - tot_prev if pd.notna(tot_mtd) and pd.notna(tot_prev) else None

# --- Custom Tab Navigation ---
tab_names = ["🌌 Overview", "📊 Analysis & Transcripts", "📈 Trends & Distributions"] 
if 'active_tab' not in st.session_state: st.session_state.active_tab = tab_names[0]

selected_tab = st.radio(
    "Navigation:", 
    tab_names, 
    index=tab_names.index(st.session_state.active_tab), 
    horizontal=True,
    key="main_tab_selector_v3" 
)
if selected_tab != st.session_state.active_tab:
    st.session_state.active_tab = selected_tab
    st.rerun() 

# --- Display Content Based on Active Tab ---
if st.session_state.active_tab == "🌌 Overview": 
    with st.container(): 
        st.header("📈 Month-to-Date (MTD) Overview")
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Onboardings MTD", tot_mtd or "0", f"{delta_mtd:+}" if delta_mtd is not None else "N/A")
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
        else: st.info("No data matches filters for Overview.")

elif st.session_state.active_tab == "📊 Analysis & Transcripts": 
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table = df_filtered.copy().reset_index(drop=True) 
    
    cols_to_try = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                   'clientSentiment', 'days_to_confirmation'] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS 
    cols_for_display = [col for col in cols_to_try if col in df_display_table.columns]
    other_cols = [col for col in df_display_table.columns if col not in cols_for_display and 
                  not col.endswith(('_utc', '_str_original', '_dt')) and col not in ['fullTranscript', 'summary']] 
    cols_for_display.extend(other_cols)

    if not df_display_table.empty:
        def style_df(df_to_style): 
            s = df_to_style.style
            if 'score' in df_to_style.columns: 
                scores_num = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_num.notna().any():
                    s = s.background_gradient(subset=['score'],cmap='PuBuGn',low=0.3,high=0.7, gmap=scores_num) 
            if 'days_to_confirmation' in df_to_style.columns:
                days_num = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_num.notna().any():
                    s = s.background_gradient(subset=['days_to_confirmation'],cmap='RdPu_r', gmap=days_num) 
            return s
        st.dataframe(style_df(df_display_table[cols_for_display]), use_container_width=True, height=300)
        
        st.markdown("---")
        st.subheader("🔍 View Full Onboarding Details & Transcript")
        
        if not df_display_table.empty and 'fullTranscript' in df_display_table.columns:
            transcript_options = {
                f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx 
                for idx, row in df_display_table.iterrows()
            }
            if transcript_options:
                if 'selected_transcript_key' not in st.session_state: st.session_state.selected_transcript_key = None
                
                selectbox_widget_key = "transcript_selector_widget_main_tab2_ui_v2_12" 
                
                selected_key_display = st.selectbox("Select onboarding to view details:",
                    options=[None] + list(transcript_options.keys()), index=0, 
                    format_func=lambda x: "Choose an entry..." if x is None else x, 
                    key=selectbox_widget_key 
                )
                
                if selected_key_display != st.session_state.selected_transcript_key:
                    st.session_state.selected_transcript_key = selected_key_display
                
                if st.session_state.selected_transcript_key :
                    selected_idx = transcript_options[st.session_state.selected_transcript_key]
                    selected_row = df_display_table.loc[selected_idx]
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html = "<div class='transcript-summary-grid'>"
                    summary_items = { 
                        "Store": selected_row.get('storeName', 'N/A'), "Rep": selected_row.get('repName', 'N/A'),
                        "Score": selected_row.get('score', 'N/A'), "Status": selected_row.get('status', 'N/A'),
                        "Sentiment": selected_row.get('clientSentiment', 'N/A')
                    }
                    for item_label, item_value in summary_items.items():
                        summary_html += f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>"
                    data_summary_text = selected_row.get('summary', 'N/A') 
                    summary_html += f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary:</strong> {data_summary_text}</div>"
                    summary_html += "</div>" 
                    st.markdown(summary_html, unsafe_allow_html=True)

                    st.markdown("##### Key Requirement Checks:")
                    for item_column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                        requirement_details = KEY_REQUIREMENT_DETAILS.get(item_column_name)
                        if requirement_details: 
                            item_description = requirement_details.get("description", item_column_name.replace('_',' ').title())
                            item_type = requirement_details.get("type", "") 
                            item_value_str = str(selected_row.get(item_column_name, "")).lower()
                            is_requirement_met = item_value_str in ['true', '1', 'yes']
                            status_emoji = "✅" if is_requirement_met else "❌"
                            type_tag_html = f"<span class='type'>[{item_type}]</span>" if item_type else ""
                            st.markdown(f"<div class='requirement-item'>{status_emoji} {item_description} {type_tag_html}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---") 
                    st.markdown("##### Full Transcript:")
                    transcript_content = selected_row.get('fullTranscript', "")
                    if transcript_content:
                        html_transcript = "<div class='transcript-container'>"
                        processed_transcript = transcript_content.replace('\\n', '\n') 
                        for line_segment in processed_transcript.split('\n'): 
                            current_line = line_segment.strip()
                            if not current_line: continue 
                            parts = current_line.split(":", 1)
                            speaker_html = f"<strong>{parts[0].strip()}:</strong>" if len(parts) == 2 else ""
                            message_html = parts[1].strip().replace('\n', '<br>') if len(parts) == 2 else current_line.replace('\n', '<br>')
                            html_transcript += f"<p class='transcript-line'>{speaker_html} {message_html}</p>"
                        html_transcript += "</div>"
                        st.markdown(html_transcript, unsafe_allow_html=True)
                    else: st.info("No transcript available or empty.")
        else: st.info("No data in table for transcript viewer, or 'fullTranscript' column missing.")
        st.markdown("---") 

        csv_data = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data", csv_data, 'filtered_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: st.info("No data matches filters for table.")
    
    st.header("📊 Key Visuals (Based on Filtered Data)") 
    if not df_filtered.empty:
        c1_charts, c2_charts = st.columns(2) 
        with c1_charts: 
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_fig = px.bar(df_filtered['status'].value_counts().reset_index(), x='status', y='count', 
                                     color='status', title="Onboarding Status Distribution", color_discrete_sequence=[PURPLE_PAIN, MEDIUM_PURPLE, ICE_COLD])
                status_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(status_fig, use_container_width=True)
            
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_fig = px.bar(df_filtered['repName'].value_counts().reset_index(), x='repName', y='count', 
                                     color='repName', title="Onboardings by Representative", color_discrete_sequence=px.colors.qualitative.Pastel1) 
                rep_fig.update_layout(plotly_base_layout_settings); st.plotly_chart(rep_fig, use_container_width=True)
        
        with c2_charts: 
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sent_counts = df_filtered['clientSentiment'].value_counts().reset_index()
                color_map = {str(s).lower(): (ICE_COLD if 'positive' in str(s).lower() else 
                                             (HEAVY_PURPLE if 'negative' in str(s).lower() else MEDIUM_PURPLE)) 
                             for s in sent_counts['clientSentiment'].unique()}
                sent_fig = px.pie(sent_counts, names='clientSentiment', values='count', hole=0.5, 
                                  title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=color_map)
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
                        bool_series_for_chart = pd.to_numeric(df_conf_chart[item_col_name_for_chart].astype(str).str.lower().map(map_bool_for_chart), errors='coerce')
                        if bool_series_for_chart.notna().any():
                            true_count_for_chart, total_valid_for_chart = bool_series_for_chart.sum(), bool_series_for_chart.notna().sum()
                            if total_valid_for_chart > 0:
                                checklist_data_for_chart.append({"Key Requirement": chart_label_for_bar, "Completion (%)": (true_count_for_chart/total_valid_for_chart)*100})
                if checklist_data_for_chart:
                    df_checklist_bar_chart = pd.DataFrame(checklist_data_for_chart)
                    if not df_checklist_bar_chart.empty:
                        checklist_bar_fig = px.bar(df_checklist_bar_chart.sort_values("Completion (%)",ascending=True), 
                                                     x="Completion (%)", y="Key Requirement", orientation='h', 
                                                     title="Key Requirement Completion (Confirmed Onboardings)", 
                                                     color_discrete_sequence=[PURPLE_PAIN]) 
                        checklist_bar_fig.update_layout(plotly_base_layout_settings, yaxis={'categoryorder':'total ascending'}) 
                        st.plotly_chart(checklist_bar_fig, use_container_width=True)
                else: st.info("No data for key requirement chart (confirmed).")
            else: st.info("No 'confirmed' onboardings or checklist columns for requirement chart.")
    else: st.info("No data matches filters for detailed visuals.")

elif st.session_state.active_tab == "📈 Trends & Distributions": 
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
                                      title="Onboardings Over Filtered Period", color_discrete_sequence=[ICE_COLD])
                    fig_for_trend_tab3.update_layout(plotly_base_layout_settings) 
                    st.plotly_chart(fig_for_trend_tab3, use_container_width=True)
                else: st.info("Not enough data for trend plot.")
            else: st.info("No valid date data for trend chart.")
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_for_hist_tab3 = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist_tab3.empty:
                nbins_for_hist_tab3 = max(10, min(50, int(len(days_data_for_hist_tab3)/5))) if len(days_data_for_hist_tab3) > 20 else (len(days_data_for_hist_tab3.unique()) or 10)
                fig_days_dist_hist_tab3 = px.histogram(days_data_for_hist_tab3, nbins=nbins_for_hist_tab3, 
                                           title="Days to Confirmation Distribution", color_discrete_sequence=[MEDIUM_PURPLE])
                fig_days_dist_hist_tab3.update_layout(plotly_base_layout_settings) 
                st.plotly_chart(fig_days_dist_hist_tab3, use_container_width=True)
            else: st.info("No valid 'Days to Confirmation' for distribution.")
    else: st.info("No data matches filters for Trends & Distributions.")

st.sidebar.markdown("---") 
st.sidebar.info("Dashboard v3.1 | Secured Access") 