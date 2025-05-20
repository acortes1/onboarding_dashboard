# Import necessary libraries
import streamlit as st  # For creating the web application interface
import pandas as pd  # For data manipulation and analysis (DataFrames)
import plotly.express as px  # For creating interactive charts easily
import plotly.graph_objects as go  # For more control over Plotly charts
from datetime import datetime, date, timedelta  # For working with dates and times
from dateutil.relativedelta import relativedelta  # For more complex date calculations
import gspread  # For interacting with Google Sheets API
from google.oauth2.service_account import Credentials  # For authenticating with Google services
from collections.abc import Mapping  # For robustly checking if an object is dictionary-like
import time  # For time-related functions
import numpy as np  # For numerical operations
import re  # For regular expressions, used for parsing transcripts
import matplotlib # Imported because pandas styling might use it

# --- Page Configuration ---
# Sets up basic properties of the web page.
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.10", # Updated version
    page_icon="📝", # A memo/notes emoji
    layout="wide"
)

# --- Custom Styling (CSS) ---
# Global CSS styles for the app's appearance.
GOLD_ACCENT_COLOR = "#FFD700"
PRIMARY_TEXT_COLOR = "#FFFFFF"
SECONDARY_TEXT_COLOR = "#B0B0B0"
BACKGROUND_COLOR = "#0E1117" 
PLOT_BG_COLOR = "rgba(0,0,0,0)" 

st.markdown(f"""
<style>
    /* General App Styles */
    .stApp > header {{ background-color: transparent; }}
    h1 {{ color: {GOLD_ACCENT_COLOR}; text-align: center; padding-top: 0.5em; padding-bottom: 0.5em; }}
    h2, h3 {{ color: {GOLD_ACCENT_COLOR}; border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important; padding-bottom: 0.3em; }}
    
    /* Metric Widget Styles */
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{ color: {PRIMARY_TEXT_COLOR} !important; }}
    div[data-testid="stMetricValue"] > div {{ font-size: 1.85rem; }}
    
    /* Expander Styles */
    .streamlit-expanderHeader {{ color: {GOLD_ACCENT_COLOR} !important; font-weight: bold; }}
    
    /* DataFrame Styles */
    .stDataFrame {{ border: 1px solid #333; }}
    
    /* Paragraph Text (may need adjustment for future Streamlit versions) */
    .css-1d391kg p, .css- F_1U7P p {{ color: {PRIMARY_TEXT_COLOR} !important; }}
    
    /* Tab Styles */
    button[data-baseweb="tab"] {{ background-color: transparent !important; color: {SECONDARY_TEXT_COLOR} !important; border-bottom: 2px solid transparent !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {GOLD_ACCENT_COLOR} !important; border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important; font-weight: bold; }}
    
    /* Transcript Viewer Specific Styles */
    .transcript-summary-grid {{ 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 12px; 
        margin-bottom: 18px; 
    }}
    .transcript-summary-item strong {{ color: {GOLD_ACCENT_COLOR}; }}
    .transcript-summary-item-fullwidth {{ 
        grid-column: 1 / -1; 
        margin-top: 5px;
    }}
    .requirement-item {{ 
        margin-bottom: 10px; /* Increased spacing for better readability */
        padding-left: 5px;
        border-left: 3px solid #444; /* Subtle left border for visual grouping */
    }}
    .requirement-item .type {{ /* Style for [Primary] / [Secondary] tag */
        font-weight: bold;
        color: {SECONDARY_TEXT_COLOR};
        font-size: 0.9em;
        margin-left: 5px;
    }}
    .transcript-container {{ 
        background-color: #262730; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #333; 
        max-height: 400px; 
        overflow-y: auto; 
        font-family: monospace; 
    }}
    .transcript-line {{ margin-bottom: 8px; line-height: 1.4; word-wrap: break-word; white-space: pre-wrap; }}
    .transcript-line strong {{ color: {GOLD_ACCENT_COLOR}; }}
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
# Checks if the user has provided the correct access key.
def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set. Bypassing password.")
        return True
    if "password_entered" not in st.session_state: st.session_state.password_entered = False
    if st.session_state.password_entered: return True
    with st.form("password_form"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Access Key:", type="password", help=app_hint)
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password_attempt == app_password:
                st.session_state.password_entered = True; st.rerun() 
            else: st.error("Incorrect Access Key."); return False
    return False

if not check_password(): st.stop() 

# --- Constants ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'] 

# Updated constant to store detailed information about each key requirement.
KEY_REQUIREMENT_DETAILS = {
    'expectationsSet': {
        "description": "Client expectations were clearly set.",
        "type": "Bonus Criterion", # Classification for display
        "chart_label": "Expectations Set" # Short label for charts
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
# Maintains the desired order for displaying these checklist items.
ORDERED_KEY_CHECKLIST_ITEMS = [
    'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
    'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink'
]

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
        st.sidebar.success(f"Loaded {len(df)} records from '{ws_name}'.") 
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
    
    checklist_cols_to_ensure = ORDERED_KEY_CHECKLIST_ITEMS + ['onboardingWelcome'] 
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
for k,v in {'data_loaded':False,'df_original':pd.DataFrame(),'date_range':(default_s,default_e)}.items():
    if k not in st.session_state: st.session_state[k]=v
for k in ['repName_filter','status_filter','clientSentiment_filter']: 
    if k not in st.session_state: st.session_state[k]=[]
for k in ['licenseNumber_search','storeName_search','selected_transcript_key']: 
    if k not in st.session_state: st.session_state[k]="" if "search" in k else None

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
            else: st.session_state.df_original = pd.DataFrame(); st.session_state.data_loaded = False
df_original = st.session_state.df_original 

st.title("🚀 Onboarding Performance Dashboard v2.10 🚀") # Updated version in title

if not st.session_state.data_loaded or df_original.empty:
    st.error("Failed to load data. Check sheet, permissions, secrets & refresh.")
    if st.sidebar.button("🔄 Force Refresh", key="refresh_fail"):
        st.cache_data.clear(); st.session_state.clear(); st.rerun()

with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False):
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
if st.sidebar.button("🧹 Clear Filters",on_click=clear_filters_cb,use_container_width=True): st.rerun()

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

plotly_layout = {"plot_bgcolor":PLOT_BG_COLOR, "paper_bgcolor":PLOT_BG_COLOR, "font_color":PRIMARY_TEXT_COLOR, 
                 "title_font_color":GOLD_ACCENT_COLOR, "legend_font_color":PRIMARY_TEXT_COLOR, 
                 "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":False}

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

tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])
with tab1: 
    st.header("📈 Month-to-Date (MTD) Overview")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Onboardings MTD", tot_mtd or "0", f"{delta_mtd:+}" if delta_mtd is not None else "N/A")
    c2.metric("Success Rate MTD", f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A")
    c3.metric("Avg Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    c4.metric("Avg Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")
    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        tot_filt, sr_filt, score_filt, days_filt = calculate_metrics(df_filtered)
        fc1,fc2,fc3,fc4 = st.columns(4)
        fc1.metric("Filtered Onboardings", tot_filt or "0")
        fc2.metric("Filtered Success Rate", f"{sr_filt:.1f}%" if pd.notna(sr_filt) else "N/A")
        fc3.metric("Filtered Avg Score", f"{score_filt:.2f}" if pd.notna(score_filt) else "N/A")
        fc4.metric("Filtered Avg Days Confirm", f"{days_filt:.1f}" if pd.notna(days_filt) else "N/A")
    else: st.info("No data matches filters for Overview.")
with tab2: 
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table = df_filtered.copy().reset_index(drop=True) 
    
    cols_to_try = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                   'clientSentiment', 'days_to_confirmation'] + ORDERED_KEY_CHECKLIST_ITEMS
    cols_for_display = [col for col in cols_to_try if col in df_display_table.columns]
    other_cols = [col for col in df_display_table.columns if col not in cols_for_display and 
                  not col.endswith(('_utc', '_str_original', '_dt')) and col not in ['fullTranscript', 'summary']] # Exclude summary from main table too
    cols_for_display.extend(other_cols)

    if not df_display_table.empty:
        def style_df(df_to_style): 
            s = df_to_style.style
            if 'score' in df_to_style.columns: 
                scores_num = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_num.notna().any():
                    s = s.background_gradient(subset=['score'],cmap='RdYlGn',low=0.3,high=0.7, gmap=scores_num)
            if 'days_to_confirmation' in df_to_style.columns:
                days_num = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_num.notna().any():
                    s = s.background_gradient(subset=['days_to_confirmation'],cmap='RdYlGn_r', gmap=days_num)
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
                selected_key_display = st.selectbox("Select onboarding to view details:",
                    options=[None] + list(transcript_options.keys()), index=0, 
                    format_func=lambda x: "Choose an entry..." if x is None else x, key="transcript_selector_widget")
                if selected_key_display != st.session_state.selected_transcript_key:
                    st.session_state.selected_transcript_key = selected_key_display
                
                if st.session_state.selected_transcript_key :
                    selected_idx = transcript_options[st.session_state.selected_transcript_key]
                    selected_row = df_display_table.loc[selected_idx]
                    
                    st.markdown("##### Onboarding Summary:")
                    summary_html = "<div class='transcript-summary-grid'>"
                    summary_items = { # Key-value pairs for the summary grid
                        "Store": selected_row.get('storeName', 'N/A'), 
                        "Rep": selected_row.get('repName', 'N/A'),
                        "Score": selected_row.get('score', 'N/A'),
                        "Status": selected_row.get('status', 'N/A'),
                        "Sentiment": selected_row.get('clientSentiment', 'N/A')
                    }
                    for item_label, item_value in summary_items.items():
                        summary_html += f"<div class='transcript-summary-item'><strong>{item_label}:</strong> {item_value}</div>"
                    
                    # Add the "summary" field from data, spanning full width
                    data_summary_text = selected_row.get('summary', 'N/A') # Get summary from the selected row
                    summary_html += f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>Call Summary:</strong> {data_summary_text}</div>"
                    
                    summary_html += "</div>" # Close grid
                    st.markdown(summary_html, unsafe_allow_html=True)

                    st.markdown("##### Key Requirement Checks:")
                    # Iterate using the predefined ordered list of checklist items.
                    for item_column_name in ORDERED_KEY_CHECKLIST_ITEMS:
                        # Get the full description and type from the KEY_REQUIREMENT_DETAILS dictionary.
                        details = KEY_REQUIREMENT_DETAILS.get(item_column_name)
                        if details: # If details exist for this item
                            item_description = details.get("description", item_column_name.replace('_',' ').title())
                            item_type = details.get("type", "") # Get Primary/Secondary/Bonus Criterion
                            
                            item_value_str = str(selected_row.get(item_column_name, "")).lower()
                            is_requirement_met = item_value_str in ['true', '1', 'yes']
                            status_emoji = "✅" if is_requirement_met else "❌"
                            
                            # Display each requirement with its type and full description.
                            type_tag = f"<span class='type'>[{item_type}]</span>" if item_type else ""
                            st.markdown(f"<div class='requirement-item'>{status_emoji} {item_description} {type_tag}</div>", unsafe_allow_html=True)
                    
                    st.markdown("---") # Separator before transcript
                    st.markdown("##### Full Transcript:")
                    transcript_content = selected_row.get('fullTranscript', "")
                    if transcript_content:
                        html_transcript = "<div class='transcript-container'>"
                        # Ensure both literal '\n' (escaped) and actual newlines are handled for HTML.
                        processed_transcript_content = transcript_content.replace('\\n', '\n') 
                        
                        for line_segment_from_transcript in processed_transcript_content.split('\n'):
                            current_line = line_segment_from_transcript.strip()
                            if not current_line: continue # Skip empty lines
                            
                            parts_of_line = current_line.split(":", 1)
                            speaker_html_part = f"<strong>{parts_of_line[0].strip()}:</strong>" if len(parts_of_line) == 2 else ""
                            # Replace internal newlines within a message part with <br> for HTML.
                            message_html_part = parts_of_line[1].strip().replace('\n', '<br>') if len(parts_of_line) == 2 else current_line.replace('\n', '<br>')
                            
                            html_transcript += f"<p class='transcript-line'>{speaker_html_part} {message_html_part}</p>"
                        html_transcript += "</div>"
                        st.markdown(html_transcript, unsafe_allow_html=True)
                    else: 
                        st.info("No transcript available for this selection or the transcript is empty.")
        else: 
            st.info("No data in the filtered table to select a transcript from, or 'fullTranscript' column is missing.")
        st.markdown("---") # Separator after transcript viewer

        csv_data_to_download = convert_df_to_csv(df_filtered)
        st.download_button("📥 Download Filtered Data as CSV", csv_data_to_download, 'filtered_onboarding_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: 
        st.info("No data matches current filter criteria for table display.")
    
    st.header("📊 Key Visuals (Based on Filtered Data)") 
    if not df_filtered.empty:
        col_viz1_tab2, col_viz2_tab2 = st.columns(2)
        with col_viz1_tab2:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                status_fig_tab2 = px.bar(df_filtered['status'].value_counts().reset_index(), x='status', y='count', 
                                     color='status', title="Onboarding Status Distribution")
                status_fig_tab2.update_layout(plotly_base_layout_config); st.plotly_chart(status_fig_tab2, use_container_width=True)
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                rep_fig_tab2 = px.bar(df_filtered['repName'].value_counts().reset_index(), x='repName', y='count', 
                                     color='repName', title="Onboardings by Representative")
                rep_fig_tab2.update_layout(plotly_base_layout_config); st.plotly_chart(rep_fig_tab2, use_container_width=True)
        with col_viz2_tab2:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                sent_counts_tab2 = df_filtered['clientSentiment'].value_counts().reset_index()
                color_map_tab2 = {str(s_tab2).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s_tab2).lower() else ('#2ca02c' if 'positive' in str(s_tab2).lower() else ('#d62728' if 'negative' in str(s_tab2).lower() else None))) for s_tab2 in sent_counts_tab2['clientSentiment'].unique()}
                sent_fig_tab2 = px.pie(sent_counts_tab2, names='clientSentiment', values='count', hole=0.4, title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=color_map_tab2)
                sent_fig_tab2.update_layout(plotly_base_layout_config); st.plotly_chart(sent_fig_tab2, use_container_width=True)

            df_confirmed_tab2 = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            actual_key_cols_tab2 = [col_tab2 for col_tab2 in ORDERED_KEY_CHECKLIST_ITEMS if col_tab2 in df_confirmed_tab2.columns]
            checklist_data_tab2 = []
            if not df_confirmed_tab2.empty and actual_key_cols_tab2:
                for item_col_name_tab2_viz in actual_key_cols_tab2:
                    # Use the 'chart_label' from KEY_REQUIREMENT_DETAILS for the chart
                    item_details_for_chart = KEY_REQUIREMENT_DETAILS.get(item_col_name_tab2_viz)
                    chart_label_for_item_viz = item_details_for_chart.get("chart_label", item_col_name_tab2_viz.replace('_',' ').title()) if item_details_for_chart else item_col_name_tab2_viz.replace('_',' ').title()
                    
                    map_bool_tab2 = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                    if item_col_name_tab2_viz in df_confirmed_tab2.columns:
                        bool_s_tab2 = pd.to_numeric(df_confirmed_tab2[item_col_name_tab2_viz].astype(str).str.lower().map(map_bool_tab2), errors='coerce')
                        if bool_s_tab2.notna().any():
                            true_c_tab2, total_v_tab2 = bool_s_tab2.sum(), bool_s_tab2.notna().sum()
                            if total_v_tab2 > 0:
                                checklist_data_tab2.append({"Key Requirement": chart_label_for_item_viz, 
                                                                  "Completion (%)": (true_c_tab2/total_v_tab2)*100})
                if checklist_data_tab2:
                    df_checklist_chart_tab2 = pd.DataFrame(checklist_data_tab2)
                    if not df_checklist_chart_tab2.empty:
                        checklist_fig_tab2 = px.bar(df_checklist_chart_tab2.sort_values("Completion (%)",ascending=True), 
                                                     x="Completion (%)", y="Key Requirement", orientation='h', 
                                                     title="Key Requirement Completion (Confirmed Onboardings)", 
                                                     color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        checklist_fig_tab2.update_layout(plotly_base_layout_config, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(checklist_fig_tab2, use_container_width=True)
                else: st.info("No data for key requirement chart (confirmed).")
            else: st.info("No 'confirmed' onboardings or checklist columns for requirement chart.")
    else: st.info("No data matches filters for detailed visuals.")

with tab3_main: # Trends & Distributions Tab
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            df_trend_tab3 = df_filtered.copy(); df_trend_tab3['onboarding_date_only'] = pd.to_datetime(df_trend_tab3['onboarding_date_only'],errors='coerce'); df_trend_tab3.dropna(subset=['onboarding_date_only'],inplace=True)
            if not df_trend_tab3.empty:
                span_tab3 = (df_trend_tab3['onboarding_date_only'].max() - df_trend_tab3['onboarding_date_only'].min()).days
                freq_tab3 = 'D' if span_tab3 <= 62 else ('W-MON' if span_tab3 <= 365*1.5 else 'ME')
                data_tab3 = df_trend_tab3.set_index('onboarding_date_only').resample(freq_tab3).size().reset_index(name='count')
                if not data_tab3.empty:
                    fig_trend_tab3 = px.line(data_tab3,x='onboarding_date_only',y='count',markers=True,title="Onboardings Over Filtered Period")
                    fig_trend_tab3.update_layout(plotly_base_layout_config); st.plotly_chart(fig_trend_tab3,use_container_width=True)
                else: st.info("Not enough data for trend plot.")
            else: st.info("No valid date data for trend chart.")
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            days_data_tab3 = pd.to_numeric(df_filtered['days_to_confirmation'],errors='coerce').dropna()
            if not days_data_tab3.empty:
                nbins_tab3 = max(10,min(50,int(len(days_data_tab3)/5))) if len(days_data_tab3)>20 else (len(days_data_tab3.unique()) or 10)
                fig_days_dist_tab3 = px.histogram(days_data_tab3,nbins=nbins_tab3,title="Days to Confirmation Distribution")
                fig_days_dist_tab3.update_layout(plotly_base_layout_config); st.plotly_chart(fig_days_dist_tab3,use_container_width=True)
            else: st.info("No valid 'Days to Confirmation' for distribution.")
    else: st.info("No data matches filters for Trends & Distributions.")

st.sidebar.markdown("---") 
st.sidebar.info("Dashboard v2.10 | Secured Access")