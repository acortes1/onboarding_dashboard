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
import re # For parsing transcripts
import matplotlib # Required for pandas styler background_gradient

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.4", # Version increment
    page_icon="📋",
    layout="wide"
)

# --- Custom Styling (Gold Accents) ---
GOLD_ACCENT_COLOR = "#FFD700" 
PRIMARY_TEXT_COLOR = "#FFFFFF" 
SECONDARY_TEXT_COLOR = "#B0B0B0" 
BACKGROUND_COLOR = "#0E1117" 
PLOT_BG_COLOR = "rgba(0,0,0,0)" 

st.markdown(f"""
<style>
    .stApp > header {{
        background-color: transparent;
    }}
    h1 {{
        color: {GOLD_ACCENT_COLOR};
        text-align: center;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
    }}
    h2, h3 {{
        color: {GOLD_ACCENT_COLOR};
        border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important;
        padding-bottom: 0.3em;
    }}
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{
        color: {PRIMARY_TEXT_COLOR} !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        font-size: 1.85rem;
    }}
    .streamlit-expanderHeader {{
        color: {GOLD_ACCENT_COLOR} !important;
        font-weight: bold;
    }}
    .stDataFrame {{
        border: 1px solid #333;
    }}
    .css-1d391kg p, .css- F_1U7P p {{ 
        color: {PRIMARY_TEXT_COLOR} !important;
    }}
    button[data-baseweb="tab"] {{
        background-color: transparent !important;
        color: {SECONDARY_TEXT_COLOR} !important;
        border-bottom: 2px solid transparent !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {GOLD_ACCENT_COLOR} !important;
        border-bottom: 2px solid {GOLD_ACCENT_COLOR} !important;
        font-weight: bold;
    }}
    /* Style for transcript display */
    .transcript-container {{
        background-color: #262730; /* Slightly lighter than default dark background */
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #333;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap; /* Ensures lines wrap and formatting is respected */
        word-wrap: break-word;
        font-family: monospace; /* Good for transcripts */
    }}
    .transcript-line strong {{
        color: {GOLD_ACCENT_COLOR}; /* Speaker name in gold */
    }}
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
def check_password():
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set in secrets. Bypassing password for local development.")
        return True
    if "password_entered" not in st.session_state: st.session_state.password_entered = False
    if st.session_state.password_entered: return True
    with st.form("password_form"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Enter Access Key:", type="password", help=app_hint)
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password_attempt == app_password:
                st.session_state.password_entered = True
                st.rerun() 
            else:
                st.error("Incorrect Access Key. Please try again.")
                return False
    return False

if not check_password(): st.stop() 

# --- Google Sheets Authentication and Data Loading ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def authenticate_gspread():
    gcp_secrets = st.secrets.get("gcp_service_account")
    if gcp_secrets is None:
        st.error("GCP service account secrets ('gcp_service_account') NOT FOUND. App cannot authenticate.")
        return None
    if not (hasattr(gcp_secrets, 'get') and hasattr(gcp_secrets, 'keys')):
        st.error(f"GCP secrets ('gcp_service_account') not structured correctly (type: {type(gcp_secrets)}).")
        return None
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_keys = [key for key in required_keys if gcp_secrets.get(key) is None]
    if missing_keys:
        st.error(f"GCP secrets missing essential sub-keys: {', '.join(missing_keys)}.")
        return None
    try:
        creds = Credentials.from_service_account_info(dict(gcp_secrets), scopes=SCOPES) 
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Sheets Auth Error: {e}")
        return None

def robust_to_datetime(series):
    dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
    common_formats = [
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %I:%M:%S %p', '%m/%d/%Y %I:%M:%S %p',
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
    ]
    if not series.empty and dates.isnull().sum() > len(series) * 0.7 and \
       not series.astype(str).str.lower().isin(['', 'none', 'nan', 'nat', 'null']).all():
        for fmt in common_formats:
            try:
                temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
                if temp_dates.notnull().sum() > dates.notnull().sum(): dates = temp_dates
                if dates.notnull().all(): break
            except ValueError: continue 
    return dates

@st.cache_data(ttl=600)
def load_data_from_google_sheet(_sheet_url_or_name_param, _worksheet_name_param):
    url = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    ws_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url: st.error("Config Error: GOOGLE_SHEET_URL_OR_NAME missing."); return pd.DataFrame()
    if not ws_name: st.error("Config Error: GOOGLE_WORKSHEET_NAME missing."); return pd.DataFrame()
    gc = authenticate_gspread() 
    if gc is None: return pd.DataFrame()
    try:
        ss = gc.open_by_url(url) if "docs.google.com" in url else gc.open(url) 
        ws = ss.worksheet(ws_name)
        data = ws.get_all_records(head=1, expected_headers=None)
        if not data: st.warning("No data records found in sheet."); return pd.DataFrame()
        df = pd.DataFrame(data)
        st.sidebar.success(f"Loaded {len(df)} records from '{ws_name}'.") 
        if df.empty: st.warning("Empty DataFrame after loading."); return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet Not Found: '{url}'. Check URL/Name & permissions."); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet Not Found: '{ws_name}'."); return pd.DataFrame()
    except Exception as e: st.error(f"Error Loading Data: {e}"); return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_cols = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
    for orig_col, new_col in date_cols.items():
        if orig_col in df.columns:
            df[new_col] = robust_to_datetime(df[orig_col].astype(str).str.replace('\n', '', regex=False).str.strip())
            if orig_col == 'onboardingDate': df['onboarding_date_only'] = df[new_col].dt.date
        else: df[new_col] = pd.NaT; df['onboarding_date_only'] = pd.NaT
    
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')
        def to_utc(s):
            if pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
                try: return s.dt.tz_localize('UTC') if s.dt.tz is None else s.dt.tz_convert('UTC')
                except Exception: return s
            return s
        df['days_to_confirmation'] = (to_utc(df['confirmationTimestamp_dt']) - to_utc(df['deliveryDate_dt'])).dt.days
    else: df['days_to_confirmation'] = pd.NA
    for col in ['status', 'score', 'fullTranscript']:
        if col not in df.columns: df[col] = pd.NA if col != 'fullTranscript' else ""
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df['fullTranscript'] = df['fullTranscript'].astype(str).fillna("")
    return df

@st.cache_data
def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_in):
    if df_in.empty: return 0, 0.0, pd.NA, pd.NA 
    total = len(df_in)
    success_rate = (df_in[df_in['status'].astype(str).str.lower() == 'confirmed'].shape[0] / total * 100) if total > 0 else 0.0
    avg_score = pd.to_numeric(df_in['score'], errors='coerce').mean()
    avg_days = pd.to_numeric(df_in['days_to_confirmation'], errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

def get_default_date_range(series):
    today = date.today(); start = today.replace(day=1); end = today
    min_d, max_d = None, None
    if series is not None and not series.empty:
        dates = pd.to_datetime(series, errors='coerce').dt.date.dropna()
        if not dates.empty:
            min_d, max_d = dates.min(), dates.max()
            start = max(start, min_d); end = min(end, max_d)
            if start > end: start, end = min_d, max_d
    return start, end, min_d, max_d

default_start, default_end, _, _ = get_default_date_range(None)
for k, v in {'data_loaded': False, 'df_original': pd.DataFrame(), 
             'date_range': (default_start, default_end)}.items():
    if k not in st.session_state: st.session_state[k] = v
for k in ['repName_filter', 'status_filter', 'clientSentiment_filter']: 
    if k not in st.session_state: st.session_state[k] = []
for k in ['licenseNumber_search', 'storeName_search', 'selected_transcript_index']: 
    if k not in st.session_state: st.session_state[k] = "" if "search" in k else None


if not st.session_state.data_loaded:
    url_s = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME"); ws_s = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not url_s or not ws_s: st.error("Config Error: Sheet URL/Name missing in secrets.")
    else:
        with st.spinner("Loading data..."):
            df = load_data_from_google_sheet(url_s, ws_s) 
            if not df.empty:
                st.session_state.df_original = df; st.session_state.data_loaded = True
                ds, de, _, _ = get_default_date_range(df.get('onboarding_date_only'))
                st.session_state.date_range = (ds, de) if ds and de else (default_start, default_end)
            else: st.session_state.df_original = pd.DataFrame(); st.session_state.data_loaded = False
df_original = st.session_state.df_original 

st.title("🚀 Onboarding Performance Dashboard v2.4 🚀")

if not st.session_state.data_loaded or df_original.empty:
    st.error("Failed to load data. Check sheet, permissions, secrets & refresh.")
    if st.sidebar.button("🔄 Force Refresh", key="refresh_fail"):
        st.cache_data.clear(); st.session_state.clear(); st.rerun()

with st.sidebar.expander("ℹ️ Understanding The Score (0-10 pts)", expanded=False):
    st.markdown("""
    - **Primary (Max 4 pts):** `Confirm Kit Received` (2), `Schedule Training & Promo` (2).
    - **Secondary (Max 3 pts):** `Intro Self & DIME` (1), `Offer Display Help` (1), `Provide Promo Credit Link` (1).
    - **Bonuses (Max 3 pts):** `+1` for Positive `clientSentiment`, `+1` if `expectationsSet` is true, `+1` for Completeness (all 6 key checklist items true).
    *Key checklist items: Expectations Set, Intro Self & DIME, Confirm Kit Received, Offer Display Help, Schedule Training & Promo, Provide Promo Credit Link.*
    """)
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data", key="refresh_main"):
    st.cache_data.clear(); st.session_state.clear(); st.rerun()
st.sidebar.header("🔍 Filters")
dates_series = df_original.get('onboarding_date_only')
def_s, def_e, min_dt, max_dt = get_default_date_range(dates_series)
if 'date_range' not in st.session_state or not (isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range)==2):
    st.session_state.date_range = (def_s, def_e) if def_s and def_e else (date.today().replace(day=1), date.today())
if min_dt and max_dt and def_s and def_e:
    val_s, val_e = st.session_state.date_range
    sel_range = st.sidebar.date_input("Date Range:", value=(max(min_dt, val_s) if val_s else min_dt, min(max_dt, val_e) if val_e else max_dt), 
                                      min_value=min_dt, max_value=max_dt, key="date_sel")
    if sel_range != st.session_state.date_range: st.session_state.date_range = sel_range
else: st.sidebar.warning("Date data unavailable for filter.")
start_dt, end_dt = st.session_state.date_range if isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range)==2 else (None,None)

search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
for k, label in search_cols.items():
    if k+"_search" not in st.session_state: st.session_state[k+"_search"] = ""
    val = st.sidebar.text_input(f"Search {label}:", value=st.session_state[k+"_search"], key=f"{k}_widget")
    if val != st.session_state[k+"_search"]: st.session_state[k+"_search"] = val
cat_filters = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for k, label in cat_filters.items():
    if k in df_original.columns and df_original[k].notna().any():
        opts = sorted([v for v in df_original[k].astype(str).dropna().unique() if v.strip()])
        if k+"_filter" not in st.session_state: st.session_state[k+"_filter"] = []
        sel = [v for v in st.session_state[k+"_filter"] if v in opts]
        new_sel = st.sidebar.multiselect(f"Select {label}:", opts, default=sel, key=f"{k}_widget")
        if new_sel != st.session_state[k+"_filter"]: st.session_state[k+"_filter"] = new_sel
def clear_filters_cb():
    ds, de, _, _ = get_default_date_range(df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds,de) if ds and de else (date.today().replace(day=1), date.today())
    for k in search_cols: st.session_state[k+"_search"] = ""
    for k in cat_filters: st.session_state[k+"_filter"] = []
if st.sidebar.button("🧹 Clear Filters", on_click=clear_filters_cb, use_container_width=True): st.rerun()

df_filtered = df_original.copy() if not df_original.empty else pd.DataFrame()
if not df_filtered.empty:
    if start_dt and end_dt and 'onboarding_date_only' in df_filtered.columns:
        dates = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
        df_filtered = df_filtered[dates.notna() & (dates >= start_dt) & (dates <= end_dt)]
    for k in search_cols:
        term = st.session_state.get(f"{k}_search", "")
        if term and k in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[k].astype(str).str.contains(term, case=False, na=False)]
    for k in cat_filters:
        sel = st.session_state.get(f"{k}_filter", [])
        if sel and k in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[k].astype(str).isin(sel)]

plotly_layout = {"plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR, "font_color": PRIMARY_TEXT_COLOR, 
                 "title_font_color": GOLD_ACCENT_COLOR, "legend_font_color": PRIMARY_TEXT_COLOR, 
                 "title_x": 0.5, "xaxis_showgrid": False, "yaxis_showgrid": False}
mtd_start = date.today().replace(day=1); prev_mtd_end = mtd_start - timedelta(days=1)
prev_mtd_start = prev_mtd_end.replace(day=1)
df_mtd, df_prev_mtd = pd.DataFrame(), pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates_orig = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date.dropna()
    df_orig_valid = df_original[dates_orig.index] # Use .loc if dates_orig is filtered
    df_mtd = df_orig_valid[(dates_orig >= mtd_start) & (dates_orig <= date.today())]
    df_prev_mtd = df_orig_valid[(dates_orig >= prev_mtd_start) & (dates_orig <= prev_mtd_end)]
total_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)
total_prev, _, _, _ = calculate_metrics(df_prev_mtd)
delta_mtd = total_mtd - total_prev if pd.notna(total_mtd) and pd.notna(total_prev) else None

tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])
with tab1:
    st.header("📈 Month-to-Date (MTD) Overview")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Onboardings MTD", total_mtd or "0", f"{delta_mtd:+}" if delta_mtd else "N/A")
    c2.metric("Success Rate MTD", f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A")
    c3.metric("Avg Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    c4.metric("Avg Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")
    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        tot_filt, sr_filt, score_filt, days_filt = calculate_metrics(df_filtered)
        fc1,fc2,fc3,fc4 = st.columns(4)
        fc1.metric("Total Filtered Onboardings", tot_filt or "0")
        fc2.metric("Filtered Success Rate", f"{sr_filt:.1f}%" if pd.notna(sr_filt) else "N/A")
        fc3.metric("Filtered Average Score", f"{score_filt:.2f}" if pd.notna(score_filt) else "N/A")
        fc4.metric("Filtered Avg Days to Confirm", f"{days_filt:.1f}" if pd.notna(days_filt) else "N/A")
    else: st.info("No data matches filters for Overview.")
with tab2:
    st.header("📋 Filtered Onboarding Data Table")
    df_display_table = df_filtered.copy().reset_index(drop=True) # Use reset_index for selectbox later
    
    cols_to_try = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status', 'score', 
                   'clientSentiment', 'days_to_confirmation',
                   'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
                   'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink']
    # Exclude fullTranscript from direct display in the main table
    cols_for_display = [col for col in cols_to_try if col in df_display_table.columns]
    other_cols = [col for col in df_display_table.columns if col not in cols_for_display and 
                  not col.endswith(('_utc', '_str_original', '_dt')) and col != 'fullTranscript']
    cols_for_display.extend(other_cols)

    if not df_display_table.empty:
        def style_df(df): # Simplified
            s = df.style
            if 'score' in df: s = s.background_gradient(subset=['score'],cmap='RdYlGn',low=0.3,high=0.7)
            if 'days_to_confirmation' in df: s = s.background_gradient(subset=['days_to_confirmation'],cmap='RdYlGn_r')
            return s
        st.dataframe(style_df(df_display_table[cols_for_display]), use_container_width=True, height=300)
        
        # --- Transcript Viewer ---
        st.markdown("---")
        st.subheader("View Full Transcript")
        if 'fullTranscript' in df_display_table.columns:
            # Create options for selectbox using index and a descriptive field
            transcript_options = {
                f"Index {idx}: {row.get('storeName', 'N/A')} - {row.get('onboardingDate', 'N/A')}": idx 
                for idx, row in df_display_table.iterrows()
            }
            if transcript_options:
                selected_option = st.selectbox(
                    "Select an onboarding to view its transcript:",
                    options=list(transcript_options.keys()),
                    index=None, # No default selection
                    placeholder="Choose an entry..."
                )
                if selected_option:
                    selected_idx = transcript_options[selected_option]
                    transcript_text = df_display_table.loc[selected_idx, 'fullTranscript']
                    st.markdown("#### Full Transcript:")
                    
                    # Formatted Transcript Display
                    if transcript_text and isinstance(transcript_text, str):
                        html_transcript = "<div class='transcript-container'>"
                        for line in transcript_text.split('\n'):
                            line = line.strip()
                            if not line: continue
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                speaker, message = parts[0].strip(), parts[1].strip()
                                # Try to bold known speaker patterns or the whole speaker part
                                if re.match(r"\(\d{3}\) \d{3}-\d{4}", speaker) or "Thomas Hinterleitner" in speaker:
                                    html_transcript += f"<p class='transcript-line'><strong>{speaker}:</strong> {message}</p>"
                                else:
                                    html_transcript += f"<p class='transcript-line'><strong>{speaker}:</strong> {message}</p>"
                            else:
                                html_transcript += f"<p class='transcript-line'>{line}</p>" # Line without a clear speaker
                        html_transcript += "</div>"
                        st.markdown(html_transcript, unsafe_allow_html=True)
                    elif transcript_text: # If not string but exists
                        st.text_area("Transcript", transcript_text, height=300, disabled=True)
                    else:
                        st.info("No transcript available for this selection or transcript is empty.")
            else:
                st.info("No data in the filtered table to select a transcript from.")
        else:
            st.warning("`fullTranscript` column not found in the data.")
        st.markdown("---")

        csv_data = convert_df_to_csv(df_filtered) 
        st.download_button("📥 Download Filtered Data", csv_data, 'filtered_data.csv', 'text/csv', use_container_width=True)
    elif not df_original.empty: st.info("No data matches filters for table.")
    
    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        c1, c2 = st.columns(2)
        with c1:
            if 'status' in df_filtered and df_filtered['status'].notna().any():
                fig = px.bar(df_filtered['status'].value_counts().reset_index(), x='status', y='count', 
                             color='status', title="Onboarding Status Distribution")
                fig.update_layout(plotly_layout)
                st.plotly_chart(fig, use_container_width=True)
            if 'repName' in df_filtered and df_filtered['repName'].notna().any():
                fig = px.bar(df_filtered['repName'].value_counts().reset_index(), x='repName', y='count', 
                             color='repName', title="Onboardings by Representative")
                fig.update_layout(plotly_layout)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if 'clientSentiment' in df_filtered and df_filtered['clientSentiment'].notna().any():
                sent_counts = df_filtered['clientSentiment'].value_counts().reset_index()
                color_map = {str(s).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s).lower() else 
                                             ('#2ca02c' if 'positive' in str(s).lower() else 
                                              ('#d62728' if 'negative' in str(s).lower() else None)))
                             for s in sent_counts['clientSentiment'].unique()}
                fig = px.pie(sent_counts, names='clientSentiment', values='count', hole=0.4, 
                             title="Client Sentiment Breakdown", color='clientSentiment', color_discrete_map=color_map)
                fig.update_layout(plotly_layout)
                st.plotly_chart(fig, use_container_width=True)

            df_conf = df_filtered[df_filtered['status'].astype(str).str.lower() == 'confirmed']
            key_items = ['expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 
                         'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink']
            actual_key_cols = [col for col in key_items if col in df_conf.columns]
            checklist_data = []
            if not df_conf.empty and actual_key_cols:
                for col in actual_key_cols:
                    map_bool = {'true':True,'yes':True,'1':True,1:True,'false':False,'no':False,'0':False,0:False}
                    bool_s = pd.to_numeric(df_conf[col].astype(str).str.lower().map(map_bool), errors='coerce')
                    if bool_s.notna().any():
                        true_c, total_v = bool_s.sum(), bool_s.notna().sum()
                        if total_v > 0:
                            name = ''.join([' '+c if c.isupper() else c for c in col]).strip().title()
                            checklist_data.append({"Key Requirement": name, "Completion (%)": (true_c/total_v)*100})
                if checklist_data:
                    df_chart = pd.DataFrame(checklist_data)
                    if not df_chart.empty:
                        fig = px.bar(df_chart.sort_values("Completion (%)", ascending=True), 
                                     x="Completion (%)", y="Key Requirement", orientation='h', 
                                     title="Key Requirement Completion (Confirmed Onboardings)",
                                     color_discrete_sequence=[GOLD_ACCENT_COLOR])
                        fig.update_layout(plotly_layout, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)
                else: st.info("No data for key requirement chart (confirmed).")
            else: st.info("No 'confirmed' onboardings or checklist columns for requirement chart.")
    else: st.info("No data matches filters for detailed visuals.")
with tab3:
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered and df_filtered['onboarding_date_only'].notna().any():
            df_trend = df_filtered.copy()
            df_trend['onboarding_date_only'] = pd.to_datetime(df_trend['onboarding_date_only'], errors='coerce').dropna()
            if not df_trend.empty:
                span = (df_trend['onboarding_date_only'].max() - df_trend['onboarding_date_only'].min()).days
                freq = 'D' if span <= 62 else ('W-MON' if span <= 365*1.5 else 'ME')
                data = df_trend.set_index('onboarding_date_only').resample(freq).size().reset_index(name='count')
                if not data.empty:
                    fig = px.line(data, x='onboarding_date_only', y='count', markers=True, 
                                  title="Onboardings Over Filtered Period")
                    fig.update_layout(plotly_layout)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Not enough data for trend plot.")
            else: st.info("No valid date data for trend chart.")
        if 'days_to_confirmation' in df_filtered and df_filtered['days_to_confirmation'].notna().any():
            days_data = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data.empty:
                nbins = max(10,min(50,int(len(days_data)/5))) if len(days_data)>20 else (len(days_data.unique()) or 10)
                fig = px.histogram(days_data, nbins=nbins, title="Days to Confirmation Distribution")
                fig.update_layout(plotly_layout)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No valid 'Days to Confirmation' for distribution plot.")
    else: st.info("No data matches filters for Trends & Distributions.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.4 | Secured Access")