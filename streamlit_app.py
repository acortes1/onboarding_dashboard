# streamlit_app.py
# =================
# Fully revised build with: epoch-only date math, sanity log, version banner, cache bypass

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import re
from datetime import datetime, date, timedelta
from dateutil import tz
import gspread
from google.oauth2.service_account import Credentials
import traceback
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────────
# App Version banner (BUMP THIS EACH EDIT TO CONFIRM RELOAD)
APP_VERSION = "build-epoch-v6"
# ────────────────────────────────────────────────────────────────────────────────

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Show version + file path early (proves the code you see is the one running)
st.sidebar.markdown(f"**App Version:** `{APP_VERSION}`")
st.sidebar.caption(f"Loaded file: {Path(__file__).resolve()}")

# --- Theme/timezone/constants ---
PST_TIMEZONE = tz.gettz('America/Los_Angeles')
UTC_TIMEZONE = tz.tzutc()
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

KEY_REQUIREMENT_DETAILS = {
    'introSelfAndDIME': {"description": "Warmly introduce yourself and the Company.", "type": "Secondary", "chart_label": "Intro Self & Company"},
    'confirmKitReceived': {"description": "Confirm kit and initial order received.", "type": "Primary", "chart_label": "Kit & Order Recv'd"},
    'offerDisplayHelp': {"description": "Ask about help setting up in-store display.", "type": "Secondary", "chart_label": "Offer Display Help"},
    'scheduleTrainingAndPromo': {"description": "Schedule budtender training & first promo.", "type": "Primary", "chart_label": "Sched. Training/Promo"},
    'providePromoCreditLink': {"description": "Provide link for promo-credit requests.", "type": "Secondary", "chart_label": "Promo Credit Link"},
    'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
}
ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = [
    'introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp',
    'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet'
]
ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS

# --- Plotly theme colors (simple) ---
THEME_PLOTLY = st.get_option("theme.base")
PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)"
if THEME_PLOTLY == "light":
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
    ACTIVE_PLOTLY_SENTIMENT_MAP = {'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7'}
    TEXT_COLOR_FOR_PLOTLY = "#262730"; PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
else:
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
    ACTIVE_PLOTLY_SENTIMENT_MAP = {'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D'}
    TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"; PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"

plotly_base_layout_settings = dict(
    plot_bgcolor=PLOT_BG_COLOR_PLOTLY, paper_bgcolor=PLOT_BG_COLOR_PLOTLY, title_x=0.5,
    xaxis_showgrid=False, yaxis_showgrid=True, yaxis_gridcolor='rgba(128,128,128,0.2)',
    margin=dict(l=50, r=30, t=70, b=50), font_color=TEXT_COLOR_FOR_PLOTLY,
    title_font_color=PRIMARY_COLOR_FOR_PLOTLY, title_font_size=18,
    xaxis_title_font_color=TEXT_COLOR_FOR_PLOTLY, yaxis_title_font_color=TEXT_COLOR_FOR_PLOTLY,
    xaxis_tickfont_color=TEXT_COLOR_FOR_PLOTLY, yaxis_tickfont_color=TEXT_COLOR_FOR_PLOTLY,
    legend_font_color=TEXT_COLOR_FOR_PLOTLY, legend_title_font_color=PRIMARY_COLOR_FOR_PLOTLY
)

# --- Minimal CSS (keep it compact to focus on bugfixes) ---
st.markdown("""
<style>
.custom-table-container {overflow-x:auto;border:1px solid #ddd;border-radius:10px;}
.custom-styled-table {width:100%;border-collapse:collapse;font-size:0.92rem;}
.custom-styled-table th,.custom-styled-table td {padding:0.65em 0.8em;border-bottom:1px solid #eee;white-space:nowrap;}
.custom-styled-table th {position:sticky;top:0;background:var(--secondary-background-color);}
.cell-score-good{background:#DFF0D8;color:#3C763D;}
.cell-score-medium{background:#FCF8E3;color:#8A6D3B;}
.cell-score-bad{background:#F2DEDE;color:#A94442;}
.cell-days-good{background:#DFF0D8;color:#3C763D;}
.cell-days-medium{background:#FCF8E3;color:#8A6D3B;}
.cell-days-bad{background:#F2DEDE;color:#A94442;}
.cell-req-met{background:#E7F3E7;color:#256833;}
.cell-req-not-met{background:#F8EAEA;color:#9E3434;}
.cell-req-na{opacity:0.7;}
</style>
""", unsafe_allow_html=True)

# --- Helpers -------------------------------------------------------------------

def check_login_and_domain():
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", None)
    if not st.user.is_logged_in:
        return 'NOT_LOGGED_IN'
    user_email = getattr(st.user, "email", None)
    if not user_email:
        st.error("Could not retrieve user email. Please try logging in again.")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'ERROR'
    if allowed_domain and not user_email.endswith(f"@{allowed_domain}"):
        st.error(f"🚫 Access Denied. Only users from the '{allowed_domain}' domain are allowed.")
        st.info(f"You are attempting to log in as: {user_email}")
        st.button("Log out", on_click=st.logout, type="secondary")
        return 'DOMAIN_MISMATCH'
    return 'AUTHORIZED'

def robust_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors='coerce', utc=True)  # force tz-aware UTC immediately

def to_epoch_ms_any(v):
    """Coerce ANY input (epoch(s/ms), str, Timestamp) -> epoch milliseconds (float) or NaN."""
    if pd.isna(v) or v == "":
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        x = float(v)
        # Heuristic: seconds vs ms
        if x > 1e12:         # already ms
            return x
        elif x > 1e10:       # big seconds float
            return x * 1000.0
        else:
            return x * 1000.0
    ts = pd.to_datetime(str(v), errors='coerce', utc=True)
    if pd.isna(ts):
        return np.nan
    return ts.value / 1e6  # ns -> ms

def format_phone(n):
    if pd.isna(n) or not str(n).strip():
        return ""
    digits = re.sub(r'\D', '', str(n))
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits.startswith('1'):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return str(n)

def cap_words(s):
    if pd.isna(s) or not str(s).strip():
        return ""
    return ' '.join(w.capitalize() for w in str(s).split())

# --- Auth / Data loading -------------------------------------------------------

# Allow bypassing cache during debugging
bypass_cache = st.sidebar.checkbox("Bypass cache (debug)", value=True)
_cache_salt = datetime.utcnow().isoformat() if bypass_cache else ""

def authenticate_gspread():
    gcp_secrets_obj = st.secrets.get("gcp_service_account")
    if gcp_secrets_obj is None:
        st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND.")
        return None
    try:
        creds = Credentials.from_service_account_info(dict(gcp_secrets_obj), scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Error authenticating to Google: {e}")
        st.code(traceback.format_exc())
        return None

@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet(cache_salt: str = ""):
    gc = authenticate_gspread()
    now_utc = datetime.now(tz=UTC_TIMEZONE)
    if gc is None:
        return pd.DataFrame(), None
    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not sheet_url_or_name or not worksheet_name:
        st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME or GOOGLE_WORKSHEET_NAME missing.")
        return pd.DataFrame(), None
    try:
        spreadsheet = gc.open_by_url(sheet_url_or_name) if ("docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name) else gc.open(sheet_url_or_name)
        ws = spreadsheet.worksheet(worksheet_name)
        data = ws.get_all_records(head=1, expected_headers=None)
        if not data:
            st.warning("⚠️ No data rows in Google Sheet.")
            return pd.DataFrame(), now_utc
        df = pd.DataFrame(data)

        # 1) normalize column names
        df.rename(columns={c: "".join(str(c).strip().lower().split()) for c in df.columns}, inplace=True)

        # 2) map to internal schema
        colmap = {
            "licensenumber":"licenseNumber", "dcclicense":"licenseNumber", "dcc":"licenseNumber",
            "storename":"storeName", "accountname":"storeName",
            "repname":"repName", "representative":"repName",
            "onboardingdate":"onboardingDate",
            "deliverydate":"deliveryDate",
            "deliverydatets":"deliveryDateTs",
            "confirmationtimestamp":"confirmationTimestamp", "confirmedat":"confirmationTimestamp",
            "clientsentiment":"clientSentiment", "sentiment":"clientSentiment",
            "fulltranscript":"fullTranscript", "transcript":"fullTranscript",
            "score":"score", "onboardingscore":"score",
            "status":"status", "onboardingstatus":"status",
            "summary":"summary", "callsummary":"summary",
            "contactnumber":"contactNumber", "phone":"contactNumber",
            "confirmednumber":"confirmedNumber", "verifiednumber":"confirmedNumber",
            "contactname":"contactName", "clientcontact":"contactName"
        }
        for k in KEY_REQUIREMENT_DETAILS:
            colmap[k.lower()] = k
        ren = {std: code for std, code in colmap.items() if std in df.columns and code not in df.columns}
        if ren:
            df.rename(columns=ren, inplace=True)

        # 3) parse date-like strings to UTC-aware for display columns
        for src, dtcol in [('onboardingDate','onboardingDate_dt'),
                           ('deliveryDate','deliveryDate_dt'),
                           ('confirmationTimestamp','confirmationTimestamp_dt')]:
            if src in df.columns:
                df[src] = df[src].astype(str).str.replace('\n', ' ', regex=False).str.strip()
                df[dtcol] = robust_to_datetime(df[src])
            else:
                df[dtcol] = pd.NaT

        # 4) onboarding_date_only via epoch -> UTC -> PST -> .date
        try:
            src_onb = df['onboardingDate_dt'] if 'onboardingDate_dt' in df.columns else df.get('onboardingDate', pd.Series([np.nan]*len(df)))
            onb_epoch_ms = src_onb.apply(to_epoch_ms_any)
            onb_utc = pd.to_datetime(onb_epoch_ms, unit="ms", utc=True, errors="coerce")
            onb_pst = onb_utc.dt.tz_convert(PST_TIMEZONE)
            df['onboarding_date_only'] = onb_pst.dt.date
        except Exception:
            df['onboarding_date_only'] = pd.NaT

        # 5) days_to_confirmation using ONLY epoch math
        try:
            # Prefer explicit epoch ms if provided by sheet
            if 'deliveryDateTs' in df.columns and df['deliveryDateTs'].notna().any():
                delivery_epoch_ms = df['deliveryDateTs'].apply(to_epoch_ms_any)
            else:
                d_src = df['deliveryDate_dt'] if 'deliveryDate_dt' in df.columns else df.get('deliveryDate')
                delivery_epoch_ms = (d_src.apply(to_epoch_ms_any) if d_src is not None else pd.Series([np.nan]*len(df)))

            c_src = df['confirmationTimestamp_dt'] if 'confirmationTimestamp_dt' in df.columns else df.get('confirmationTimestamp')
            confirmation_epoch_ms = (c_src.apply(to_epoch_ms_any) if c_src is not None else pd.Series([np.nan]*len(df)))

            diff_ms = confirmation_epoch_ms - delivery_epoch_ms
            df['days_to_confirmation'] = (diff_ms / 86_400_000.0).round(0)  # 1000*60*60*24
        except Exception as e:
            st.error(f"Days-to-confirmation calc failed: {e}")
            st.code(traceback.format_exc())
            df['days_to_confirmation'] = np.nan

        # 6) display-friendly strings for the three main datetimes (PST)
        def fmt_pst(series_dt):
            pst = pd.to_datetime(series_dt, errors='coerce', utc=True).dt.tz_convert(PST_TIMEZONE)
            return pst.dt.strftime('%Y-%m-%d %I:%M %p PST')

        if 'onboardingDate_dt' in df.columns:
            df['onboardingDate'] = fmt_pst(df['onboardingDate_dt'])
        if 'deliveryDate_dt' in df.columns:
            df['deliveryDate'] = fmt_pst(df['deliveryDate_dt'])
        if 'confirmationTimestamp_dt' in df.columns:
            df['confirmationTimestamp'] = fmt_pst(df['confirmationTimestamp_dt'])

        # 7) phone + names
        for c in ['contactNumber','confirmedNumber']:
            if c in df.columns: df[c] = df[c].apply(format_phone)
        for c in ['repName','contactName','storeName']:
            if c in df.columns: df[c] = df[c].apply(cap_words)

        # 8) strings + score numeric
        for c in ['status','clientSentiment','repName','storeName','licenseNumber','fullTranscript','summary',
                  'contactName','contactNumber','confirmedNumber','onboardingDate','deliveryDate','confirmationTimestamp']:
            if c in df.columns:
                df[c] = df[c].astype(str).replace(['nan','NaN','None','NaT','<NA>'],"", regex=False)
        df['score'] = pd.to_numeric(df.get('score'), errors='coerce')

        # 9) ensure requirement booleans exist
        for c in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
            if c not in df.columns: df[c] = pd.NA

        # 10) drop legacy junk if present
        for c in ['deliverydatets_old','onboardingwelcome']:
            if c in df.columns: df.drop(columns=[c], inplace=True)

        return df, now_utc

    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 GS Error: {e}. Check URL/name & permissions.")
        st.code(traceback.format_exc())
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"🌪️ Error loading data: {e}")
        st.code(traceback.format_exc())
        return pd.DataFrame(), None

# --- Auth Gate ---
auth_status = check_login_and_domain()
if auth_status != 'AUTHORIZED':
    if auth_status == 'NOT_LOGGED_IN':
        st.markdown("""
        <div style='text-align:center;margin-top:10vh;'>
            <h2>Dashboard Access</h2>
            <p>Please log in using your <b>authorized</b> Google account to access the dashboard.</p>
        </div>""", unsafe_allow_html=True)
        _, c, _ = st.columns([1,1,1])
        with c:
            st.button("Log in with Google 🔑", on_click=st.login, use_container_width=True)
    st.stop()

# --- Session State Init ---
def get_default_date_range(date_series):
    today = date.today()
    start_of_month = today.replace(day=1)
    if date_series is not None:
        ser = pd.to_datetime(date_series, errors='coerce').dropna()
        if not ser.empty:
            min_date = ser.dt.date.min()
            max_date = ser.dt.date.max()
        else:
            min_date = max_date = None
    else:
        min_date = max_date = None
    start = max(start_of_month, min_date) if min_date else start_of_month
    end = min(today, max_date) if max_date else today
    return (start, end) if start <= end else ((min_date, max_date) if min_date and max_date else (start_of_month, today))

default_s_init, default_e_init = get_default_date_range(None)
ss = st.session_state
ss.setdefault('data_loaded', False)
ss.setdefault('df_original', pd.DataFrame())
ss.setdefault('last_data_refresh_time', None)
ss.setdefault('date_range', (default_s_init, default_e_init))
ss.setdefault('min_data_date_for_filter', None)
ss.setdefault('max_data_date_for_filter', None)
ss.setdefault('date_filter_is_active', False)
for k in ['repName_filter','status_filter','clientSentiment_filter']:
    ss.setdefault(k, [])
for k in ['licenseNumber_search','storeName_search']:
    ss.setdefault(k, "")
TAB_OVERVIEW = "📊 Overview"; TAB_DETAILED_ANALYSIS = "🔎 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
ss.setdefault('active_tab', TAB_OVERVIEW)
ss.setdefault('selected_transcript_key_dialog_global_search', None)
ss.setdefault('selected_transcript_key_filtered_analysis', None)
ss.setdefault('show_global_search_dialog', False)

# --- Load Data ---
if not ss.data_loaded:
    df_loaded, load_time = load_data_from_google_sheet(_cache_salt)
    if load_time:
        ss.last_data_refresh_time = load_time
        if not df_loaded.empty:
            ss.df_original = df_loaded
            ss.data_loaded = True
            ser = pd.to_datetime(df_loaded.get('onboarding_date_only'), errors='coerce')
            valid = ser.dropna()
            min_d = valid.dt.date.min() if not valid.empty else None
            max_d = valid.dt.date.max() if not valid.empty else None
            ss.min_data_date_for_filter = min_d
            ss.max_data_date_for_filter = max_d
            ss.date_range = get_default_date_range(df_loaded.get('onboarding_date_only'))
        else:
            ss.df_original = pd.DataFrame(); ss.data_loaded = False
    else:
        ss.df_original = pd.DataFrame(); ss.data_loaded = False

df_original = ss.df_original

# --- Sidebar controls (search / filters) ---
st.sidebar.header("⚙️ Dashboard Controls"); st.sidebar.markdown("---")

st.sidebar.subheader("🔍 Global Search")
ln_val = st.sidebar.text_input("Search License Number:", value=ss.get("licenseNumber_search",""))
if ln_val != ss["licenseNumber_search"]:
    ss["licenseNumber_search"] = ln_val; ss.show_global_search_dialog = bool(ln_val or ss.get("storeName_search","")); st.rerun()

store_opts = [""]
if not df_original.empty and 'storeName' in df_original.columns:
    store_opts += sorted([s for s in df_original['storeName'].astype(str).dropna().unique() if s.strip()])
cur_store = ss.get("storeName_search",""); idx = store_opts.index(cur_store) if cur_store in store_opts else 0
sel_store = st.sidebar.selectbox("Search Store Name:", options=store_opts, index=idx)
if sel_store != ss["storeName_search"]:
    ss["storeName_search"] = sel_store; ss.show_global_search_dialog = bool(sel_store or ss.get("licenseNumber_search","")); st.rerun()

st.sidebar.markdown("---")
global_search_active = bool(ss.get("licenseNumber_search","") or ss.get("storeName_search",""))

st.sidebar.subheader("📊 Filters")
st.sidebar.caption("Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data.")
today_short = date.today()
c1,c2,c3 = st.sidebar.columns(3)
if c1.button("MTD", use_container_width=True, disabled=global_search_active):
    ss.date_range = (today_short.replace(day=1), today_short); ss.date_filter_is_active=True; st.rerun()
if c2.button("YTD", use_container_width=True, disabled=global_search_active):
    ss.date_range = (today_short.replace(month=1, day=1), today_short); ss.date_filter_is_active=True; st.rerun()
if c3.button("ALL", use_container_width=True, disabled=global_search_active):
    a = ss.get('min_data_date_for_filter', today_short.replace(year=today_short.year-1))
    b = ss.get('max_data_date_for_filter', today_short)
    if a and b:
        ss.date_range = (a,b); ss.date_filter_is_active=True; st.rerun()

start_cur, end_cur = ss.date_range
min_w, max_w = ss.get('min_data_date_for_filter'), ss.get('max_data_date_for_filter')
vs, ve = start_cur, end_cur
if min_w and vs < min_w: vs = min_w
if max_w and ve > max_w: ve = max_w
if vs > ve: vs = ve
picked = st.sidebar.date_input("Custom Date Range (Onboarding):", value=(vs, ve),
                               min_value=min_w, max_value=max_w, disabled=global_search_active)
if (not global_search_active and isinstance(picked, tuple) and len(picked)==2 and picked != ss.date_range):
    ss.date_range = picked; ss.date_filter_is_active=True; st.rerun()

category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label in category_filters_map.items():
    options = []
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any():
        if col_key == 'status':
            options = sorted([v for v in df_original[col_key].astype(str).str.replace(r"✅|⏳|❌","",regex=True).str.strip().dropna().unique() if v.strip()])
        else:
            options = sorted([v for v in df_original[col_key].astype(str).dropna().unique() if v.strip()])
    cur = ss.get(f"{col_key}_filter", [])
    cur_valid = [x for x in cur if x in options]
    new = st.sidebar.multiselect(f"Filter by {label}:", options=options, default=cur_valid,
                                 disabled=global_search_active or not options)
    if not global_search_active and new != cur_valid:
        ss[f"{col_key}_filter"] = new; st.rerun()
    elif global_search_active and ss.get(f"{col_key}_filter") != new:
        ss[f"{col_key}_filter"] = new

def clear_all():
    ds,de = get_default_date_range(ss.df_original.get('onboarding_date_only'))
    ss.date_range=(ds,de); ss.date_filter_is_active=False
    ss.licenseNumber_search=""; ss.storeName_search=""; ss.show_global_search_dialog=False
    for k in category_filters_map: ss[f"{k}_filter"]=[]
    ss.selected_transcript_key_dialog_global_search=None; ss.selected_transcript_key_filtered_analysis=None
    ss.active_tab = TAB_OVERVIEW

if st.sidebar.button("🧹 Clear Filters", use_container_width=True):
    clear_all(); st.rerun()

# Refresh button
st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management")
if st.sidebar.button("Refresh Data from Source", use_container_width=True):
    st.cache_data.clear(); ss.data_loaded=False; ss.last_data_refresh_time=None; ss.df_original=pd.DataFrame()
    clear_all(); st.rerun()

# Last sync caption
if ss.get('data_loaded', False) and ss.get('last_data_refresh_time'):
    refresh_time_pst = ss.last_data_refresh_time.astimezone(PST_TIMEZONE)
    st.sidebar.caption(f"☁️ Last data sync: {refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST')}")
elif ss.get('last_data_refresh_time'):
    st.sidebar.caption("⚠️ No data found in last sync. Check Sheet or Refresh.")
else:
    st.sidebar.caption("⏳ Data not yet loaded.")

# --- MAIN ----------------------------------------------------------------------
st.title("📈 Onboarding Analytics Dashboard")

if not ss.data_loaded and df_original.empty:
    if ss.get('last_data_refresh_time'):
        st.info("🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh.")
    else:
        st.info("⏳ Initializing data...")
    st.stop()
elif df_original.empty:
    st.info("✅ Data source connected, but empty. Add data to Google Sheet.")
    st.stop()

# Sanity Log toggle
st.sidebar.markdown("---")
show_sanity = st.sidebar.checkbox("Show Sanity Log (debug)", value=True)
if show_sanity:
    try:
        st.subheader("🧪 Sanity Log")
        st.write("Columns:", list(df_original.columns))
        date_like = [c for c in df_original.columns if ("date" in c.lower()) or ("timestamp" in c.lower()) or c.endswith("_dt")]
        st.write("Date-like columns:", date_like)
        if date_like:
            st.write("dtypes:", df_original[date_like].dtypes)
            for c in ["onboardingDate","onboardingDate_dt","deliveryDate","deliveryDate_dt",
                      "deliveryDateTs","confirmationTimestamp","confirmationTimestamp_dt"]:
                if c in df_original.columns:
                    st.write(f"{c} (sample):", df_original[c].head(3).tolist())
    except Exception as e:
        st.error(f"Sanity log error: {e}")

# Tabs
if ss.active_tab not in ALL_TABS: ss.active_tab = TAB_OVERVIEW
try:
    cur_idx = ALL_TABS.index(ss.active_tab)
except ValueError:
    cur_idx=0; ss.active_tab = TAB_OVERVIEW
selected_tab = st.radio("Navigation:", ALL_TABS, index=cur_idx, horizontal=True)
if selected_tab != ss.active_tab:
    ss.active_tab = selected_tab; st.rerun()

# Summary banner
summary_parts=[]
if global_search_active:
    s_terms=[]
    if ss.get("licenseNumber_search",""): s_terms.append(f"License: '{ss['licenseNumber_search']}'")
    if ss.get("storeName_search",""): s_terms.append(f"Store: '{ss['storeName_search']}'")
    summary_parts.append("🔍 Global Search: " + "; ".join(s_terms))
    summary_parts.append("(Filters overridden. Results in pop-up.)")
else:
    start_dt_filter, end_dt_filter = ss.date_range
    sd, ed = start_dt_filter.strftime('%b %d, %Y'), end_dt_filter.strftime('%b %d, %Y')
    min_d, max_d = ss.get('min_data_date_for_filter'), ss.get('max_data_date_for_filter')
    is_all = (bool(min_d) and bool(max_d) and start_dt_filter==min_d and end_dt_filter==max_d and ss.get('date_filter_is_active',False))
    if is_all: summary_parts.append("🗓️ Dates: ALL Data")
    elif ss.get('date_filter_is_active', False) or ss.date_range!=(default_s_init, default_e_init):
        summary_parts.append(f"🗓️ Dates: {sd} to {ed}")
    else:
        summary_parts.append(f"🗓️ Dates: {sd} to {ed} (Default MTD)")
    active_cat=[]
    for col_key, label in category_filters_map.items():
        sel = ss.get(f"{col_key}_filter", [])
        if sel: active_cat.append(f"{label.replace('(s)','').strip()}: {', '.join(sel)}")
    if active_cat: summary_parts.append(" | ".join(active_cat))
    if not any(ss.get(f"{k}_filter") for k in category_filters_map) and not (ss.get('date_filter_is_active', False) or ss.date_range!=(default_s_init, default_e_init)):
        summary_parts.append("No category filters.")
st.markdown(f"ℹ️ {' | '.join(summary_parts) if summary_parts else 'Displaying data (default date range).'}")

# Apply filters / search
df_filtered = pd.DataFrame(); df_global_search = pd.DataFrame()
if not df_original.empty:
    if global_search_active:
        tmp = df_original.copy()
        ln_term = ss.get("licenseNumber_search","").strip().lower()
        sn_term = ss.get("storeName_search","").strip()
        if ln_term and "licenseNumber" in tmp.columns:
            tmp = tmp[tmp['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
        if sn_term and "storeName" in tmp.columns:
            tmp = tmp[tmp['storeName'] == sn_term]
        df_global_search = tmp.copy(); df_filtered = df_global_search.copy()
    else:
        tmp = df_original.copy()
        if 'onboarding_date_only' in tmp.columns and tmp['onboarding_date_only'].notna().any():
            dobj = pd.to_datetime(tmp['onboarding_date_only'], errors='coerce').dt.date
            valid = dobj.notna()
            cond = pd.Series(False, index=tmp.index)
            if valid.any():
                s,e = ss.date_range
                cond[valid] = (dobj[valid] >= s) & (dobj[valid] <= e)
            tmp = tmp[cond]
        for col_name_cat, _ in category_filters_map.items():
            picks = ss.get(f"{col_name_cat}_filter", [])
            if picks and col_name_cat in tmp.columns:
                if col_name_cat == 'status':
                    tmp = tmp[tmp[col_name_cat].astype(str).str.replace(r"✅|⏳|❌","",regex=True).str.strip().isin(picks)]
                else:
                    tmp = tmp[tmp[col_name_cat].astype(str).isin(picks)]
        df_filtered = tmp.copy()

# Metrics helpers
def calculate_metrics(df_input):
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA
    total = len(df_input)
    confirmed = df_input[df_input['status'].astype(str).str.lower().str.contains('confirmed', na=False)].shape[0] if 'status' in df_input.columns else 0
    success_rate = (confirmed / total * 100) if total > 0 else 0.0
    avg_score = pd.to_numeric(df_input.get('score'), errors='coerce').mean()
    avg_days = pd.to_numeric(df_input.get('days_to_confirmation'), errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

# MTD vs prev month
today_mtd = date.today()
mtd_start = today_mtd.replace(day=1)
prev_end = mtd_start - timedelta(days=1)
prev_start = prev_end.replace(day=1)
df_mtd = pd.DataFrame(); df_prev = pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    dates = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid = dates.notna()
    if valid.any():
        src = df_original[valid].copy(); dser = dates[valid]
        msk_mtd = (dser >= mtd_start) & (dser <= today_mtd)
        msk_prev = (dser >= prev_start) & (dser <= prev_end)
        df_mtd = src[msk_mtd.values if len(msk_mtd)==len(src) else msk_mtd[src.index]]
        df_prev = src[msk_prev.values if len(msk_prev)==len(src) else msk_prev[src.index]]
total_mtd, sr_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)
total_prev, _, _, _ = calculate_metrics(df_prev)
delta_mtd = (total_mtd - total_prev) if pd.notna(total_mtd) and pd.notna(total_prev) else None

# Basic table renderer
def cell_style(col, val):
    s = str(val).strip().lower()
    if pd.isna(val) or s=="" or s=="na": return "cell-req-na"
    if col=='score':
        try:
            x=float(val)
            return 'cell-score-good' if x>=8 else ('cell-score-medium' if x>=4 else 'cell-score-bad')
        except: return ""
    if col=='days_to_confirmation':
        try:
            x=float(val)
            return 'cell-days-good' if x<=7 else ('cell-days-medium' if x<=14 else 'cell-days-bad')
        except: return ""
    if col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
        if s in ['true','1','yes','x','completed','done']: return 'cell-req-met'
        if s in ['false','0','no']: return 'cell-req-not-met'
    return ""

def render_table(df_disp, key_prefix=""):
    if df_disp is None or df_disp.empty:
        st.info("📊 No data to show.")
        return
    dfc = df_disp.copy().reset_index(drop=True)
    def map_status(x):
        t=str(x).strip().lower()
        return "✅ Confirmed" if t=="confirmed" else ("⏳ Pending" if t=="pending" else ("❌ Failed" if t=="failed" else x))
    if 'status' in dfc.columns:
        dfc['status_styled'] = dfc['status'].apply(map_status)
    else:
        dfc['status_styled'] = ""
    order = ['onboardingDate','repName','storeName','licenseNumber','status_styled','score','clientSentiment',
             'days_to_confirmation','contactName','contactNumber','confirmedNumber','deliveryDate','confirmationTimestamp']
    order += ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
    cols_present = dfc.columns.tolist()
    show_cols = [c for c in order if c in cols_present]
    extra = [c for c in cols_present if c not in show_cols and c not in ['status']]
    show_cols += extra
    html = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
    for c in show_cols:
        name = {'status_styled':'Status','onboardingDate':'Onboarding Date','repName':'Rep Name',
                'storeName':'Store Name','licenseNumber':'License No.','clientSentiment':'Sentiment',
                'days_to_confirmation':'Days to Confirm','contactName':'Contact Name','contactNumber':'Contact No.',
                'confirmedNumber':'Confirmed No.','deliveryDate':'Delivery Date','confirmationTimestamp':'Confirmation Time'}.get(c, c)
        if c in KEY_REQUIREMENT_DETAILS: name = KEY_REQUIREMENT_DETAILS[c].get("chart_label", c)
        html.append(f"<th>{name}</th>")
    html.append("</tr></thead><tbody>")
    for _, row in dfc.iterrows():
        html.append("<tr>")
        for c in show_cols:
            base_col = 'status' if c=='status_styled' else c
            v = row.get(c,"")
            klass = cell_style(base_col, row.get(base_col, v))
            if c=='score' and pd.notna(v):
                try: v=f"{float(v):.1f}"
                except: pass
            if c=='days_to_confirmation' and pd.notna(v):
                try: v=f"{float(v):.0f}"
                except: pass
            html.append(f"<td class='{klass}'>{v}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# --- Overview Tab ---
if ss.active_tab == TAB_OVERVIEW:
    st.header("📈 Month-to-Date (MTD) Performance")
    c = st.columns(4)
    c[0].metric("🗓️ Onboardings MTD", f"{total_mtd:.0f}", delta=(f"{delta_mtd:+.0f} vs Prev. Month" if delta_mtd is not None else "N/A"))
    c[1].metric("✅ Success Rate MTD", f"{sr_mtd:.1f}%")
    c[2].metric("⭐ Avg. Score MTD", f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    c[3].metric("⏳ Avg. Days to Confirm MTD", f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")

    st.header("📊 Filtered Data Snapshot")
    if global_search_active:
        st.info("ℹ️ Global search active. Close pop-up or clear search for filtered overview.")
    else:
        tot, srate, ascore, adays = calculate_metrics(df_filtered)
        c2 = st.columns(4)
        c2[0].metric("📄 Onboardings (Filtered)", f"{tot:.0f}")
        c2[1].metric("🎯 Success Rate (Filtered)", f"{srate:.1f}%")
        c2[2].metric("🌟 Avg. Score (Filtered)", f"{ascore:.2f}" if pd.notna(ascore) else "N/A")
        c2[3].metric("⏱️ Avg. Days Confirm (Filtered)", f"{adays:.1f}" if pd.notna(adays) else "N/A")

# --- Detailed Analysis Tab ---
elif ss.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if global_search_active:
        st.info("ℹ️ Global Search active. Results in pop-up. Close/clear search for filters here.")
    else:
        render_table(df_filtered, key_prefix="filtered_analysis")

# --- Trends Tab ---
elif ss.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS)
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            src = df_filtered.copy()
            src['onboarding_datetime'] = pd.to_datetime(src['onboarding_date_only'], errors='coerce')
            src = src.dropna(subset=['onboarding_datetime'])
            if not src.empty:
                tmin = src['onboarding_datetime'].min()
                tmax = src['onboarding_datetime'].max()
                if pd.isna(tmin) or pd.isna(tmax):
                    date_span_days = 0
                else:
                    tmin = pd.to_datetime(tmin).tz_localize(None) if hasattr(tmin, "tzinfo") and tmin.tzinfo else pd.to_datetime(tmin)
                    tmax = pd.to_datetime(tmax).tz_localize(None) if hasattr(tmax, "tzinfo") and tmax.tzinfo else pd.to_datetime(tmax)
                    date_span_days = (tmax - tmin).days
                freq = 'D'
                if date_span_days > 90: freq='W-MON'
                if date_span_days > 730: freq='ME'
                trend = src.set_index('onboarding_datetime').resample(freq).size().reset_index(name='count')
                if not trend.empty:
                    fig = px.line(trend, x='onboarding_datetime', y='count', markers=True,
                                  title=f"Onboardings Over Time ({freq} Trend)",
                                  color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[0]])
                    fig.update_layout(plotly_base_layout_settings, xaxis_title="Date", yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📈 Not enough data for trend.")
            else:
                st.info("📅 No valid date data for trend.")
        else:
            st.info("🗓️ 'onboarding_date_only' missing for trend.")

        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            dd = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not dd.empty:
                nb = max(10, min(30, int(len(dd)/5))) if len(dd)>20 else (len(dd.unique()) or 10)
                fig2 = px.histogram(dd, nbins=nb, title="Distribution of Days to Confirmation",
                                    color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[1]])
                fig2.update_layout(plotly_base_layout_settings, xaxis_title="Days", yaxis_title="Frequency")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("⏳ No 'Days to Confirmation' values.")
        else:
            st.info("⏱️ 'Days to Confirmation' missing.")
    else:
        st.info("📉 No data for Trends. Adjust filters.")

st.markdown("---")
st.caption("Dashboard v4.6.7")
