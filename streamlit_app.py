# streamlit_app.py

# --- Imports ---
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import re
from dateutil import tz

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Onboarding Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Styling ----------------
def load_custom_css():
    THEME = st.get_option("theme.base")
    if THEME == "light":
        SCORE_GOOD_BG = "#DFF0D8"; SCORE_GOOD_TEXT = "#3C763D"
        SCORE_MEDIUM_BG = "#FCF8E3"; SCORE_MEDIUM_TEXT = "#8A6D3B"
        SCORE_BAD_BG = "#F2DEDE"; SCORE_BAD_TEXT = "#A94442"
        SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT
        SENTIMENT_NEUTRAL_BG = "#F0F2F6"; SENTIMENT_NEUTRAL_TEXT = "#4A5568"
        SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT
        DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT
        DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT
        DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT
        REQ_MET_BG = "#E7F3E7"; REQ_MET_TEXT = "#256833"
        REQ_NOT_MET_BG = "#F8EAEA"; REQ_NOT_MET_TEXT = "#9E3434"
        REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)"
        TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)"
        TABLE_BORDER_COLOR = "var(--border-color)"
        LOGIN_BOX_BG = "var(--background-color)"; LOGIN_BOX_SHADOW = "0 12px 35px rgba(0,0,0,0.07)"
        LOGOUT_BTN_BG = "#F2DEDE"; LOGOUT_BTN_TEXT = "#A94442"; LOGOUT_BTN_BORDER = "#A94442"
        LOGOUT_BTN_HOVER_BG = "#EBCFCF"
        PRIMARY_BTN_BG = "#6A0DAD"; PRIMARY_BTN_HOVER_BG = "#580A8F"
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#6A0DAD"; DOWNLOAD_BTN_BORDER = "#6A0DAD"
        DOWNLOAD_BTN_HOVER_BG = "#6A0DAD"; DOWNLOAD_BTN_HOVER_TEXT = "#FFFFFF"
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)"
    else:
        SCORE_GOOD_BG = "#1E4620"; SCORE_GOOD_TEXT = "#A8D5B0"
        SCORE_MEDIUM_BG = "#4A3F22"; SCORE_MEDIUM_TEXT = "#FFE0A2"
        SCORE_BAD_BG = "#5A2222"; SCORE_BAD_TEXT = "#FFBDBD"
        SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT
        SENTIMENT_NEUTRAL_BG = "#2D3748"; SENTIMENT_NEUTRAL_TEXT = "#A0AEC0"
        SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = "#FFBDBD"
        DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT
        DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT
        DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT
        REQ_MET_BG = "#1A3A21"; REQ_MET_TEXT = "#A7D7AE"
        REQ_NOT_MET_BG = "#4D1A1A"; REQ_NOT_MET_TEXT = "#FFADAD"
        REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)"
        TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)"
        TABLE_BORDER_COLOR = "var(--border-color)"
        LOGIN_BOX_BG = "var(--secondary-background-color)"; LOGIN_BOX_SHADOW = "0 10px 35px rgba(0,0,0,0.3)"
        LOGOUT_BTN_BG = "#5A2222"; LOGOUT_BTN_TEXT = "#FFBDBD"; LOGOUT_BTN_BORDER = "#FFBDBD"
        LOGOUT_BTN_HOVER_BG = "#6B3333"
        PRIMARY_BTN_BG = "#BE90D4"; PRIMARY_BTN_HOVER_BG = "#A77CBF"
        DOWNLOAD_BTN_BG = "var(--secondary-background-color)"; DOWNLOAD_BTN_TEXT = "#BE90D4"; DOWNLOAD_BTN_BORDER = "#BE90D4"
        DOWNLOAD_BTN_HOVER_BG = "#BE90D4"; DOWNLOAD_BTN_HOVER_TEXT = "#1E1E1E"
        GOOGLE_BTN_BG = "#4285F4"; GOOGLE_BTN_HOVER_BG = "#357AE8"; GOOGLE_BTN_SHADOW = "0 6px 12px rgba(66, 133, 244, 0.4)"

    TABLE_CELL_PADDING = "0.65em 0.8em"
    TABLE_FONT_SIZE = "0.92rem"

    css = f"""
    <style>
        :root {{
            --score-good-bg: {SCORE_GOOD_BG}; --score-good-text: {SCORE_GOOD_TEXT};
            --score-medium-bg: {SCORE_MEDIUM_BG}; --score-medium-text: {SCORE_MEDIUM_TEXT};
            --score-bad-bg: {SCORE_BAD_BG}; --score-bad-text: {SCORE_BAD_TEXT};
            --sentiment-positive-bg: {SENTIMENT_POSITIVE_BG}; --sentiment-positive-text: {SENTIMENT_POSITIVE_TEXT};
            --sentiment-neutral-bg: {SENTIMENT_NEUTRAL_BG}; --sentiment-neutral-text: {SENTIMENT_NEUTRAL_TEXT};
            --sentiment-negative-bg: {SENTIMENT_NEGATIVE_BG}; --sentiment-negative-text: {SENTIMENT_NEGATIVE_TEXT};
            --days-good-bg: {DAYS_GOOD_BG}; --days-good-text: {DAYS_GOOD_TEXT};
            --days-medium-bg: {SCORE_MEDIUM_BG}; --days-medium-text: {SCORE_MEDIUM_TEXT};
            --days-bad-bg: {SCORE_BAD_BG}; --days-bad-text: {SCORE_BAD_TEXT};
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
        }}
        body {{ font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .stApp {{ padding: 0.5rem 1rem; }}
        h1, h2, h3, h4, h5, h6 {{ font-weight: 600; color: var(--primary-color); }}
        h1 {{ text-align: center; padding: 0.8em 0.5em; font-size: 2.3rem; letter-spacing: 0.5px; border-bottom: 2px solid var(--primary-color); margin-bottom: 1.5em; font-weight: 700; }}
        h2 {{ font-size: 1.7rem; margin-top: 2.2em; margin-bottom: 1.3em; padding-bottom: 0.5em; border-bottom: 1px solid var(--border-color); font-weight: 600; }}
        h3 {{ font-size: 1.4rem; margin-top: 2em; margin-bottom: 1.1em; font-weight: 600; color: var(--text-color); opacity: 0.9; }}
        h5 {{ color: var(--text-color); opacity: 0.95; margin-top: 1.8em; margin-bottom: 0.9em; font-weight: 500; letter-spacing: 0.1px; font-size: 1.1rem; }}
        .custom-table-container {{ overflow-x: auto; border: 1px solid var(--table-border-color); border-radius: 10px; max-height: 500px; }}
        .custom-styled-table {{ width: 100%; border-collapse: collapse; font-size: var(--table-font-size); }}
        .custom-styled-table th, .custom-styled-table td {{ padding: var(--table-cell-padding); text-align: left; border-bottom: 1px solid var(--table-border-color); border-right: 1px solid var(--table-border-color); white-space: nowrap; }}
        .custom-styled-table th {{ background-color: var(--table-header-bg); position: sticky; top: 0; z-index: 2; }}
        .custom-styled-table tbody tr:hover {{ background-color: color-mix(in srgb, var(--secondary-background-color) 75%, var(--primary-color) 8%); }}
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
        .login-container {{ display: flex; justify-content: center; align-items: center; min-height: 60vh; flex-direction: column; text-align: center; padding: 1em; }}
        .login-box {{ background-color: var(--login-box-bg); padding: 2.5em 3em; border-radius: 15px; box-shadow: var(--login-box-shadow); max-width: 450px; width: 100%; }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8rem; }}
            .custom-styled-table th, .custom-styled-table td {{ white-space: normal; }}
        }}
        @media (max-width: 480px) {{
            h1 {{ font-size: 1.5rem; }}
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_custom_css()

# ---------------- Constants ----------------
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

PST_TIMEZONE = tz.gettz('America/Los_Angeles')
UTC_TIMEZONE = tz.tzutc()

THEME_PLOTLY = st.get_option("theme.base")
PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)"
if THEME_PLOTLY == "light":
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7' }
    TEXT_COLOR_FOR_PLOTLY = "#262730"; PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
else:
    ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']
    ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
    ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D' }
    TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"; PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"

plotly_base_layout_settings = dict(
    plot_bgcolor=PLOT_BG_COLOR_PLOTLY, paper_bgcolor=PLOT_BG_COLOR_PLOTLY, title_x=0.5,
    xaxis_showgrid=False, yaxis_showgrid=True, yaxis_gridcolor='rgba(128,128,128,0.2)',
    margin=dict(l=50, r=30, t=70, b=50),
    font_color=TEXT_COLOR_FOR_PLOTLY, title_font_color=PRIMARY_COLOR_FOR_PLOTLY,
    title_font_size=18, xaxis_title_font_color=TEXT_COLOR_FOR_PLOTLY, yaxis_title_font_color=TEXT_COLOR_FOR_PLOTLY,
    xaxis_tickfont_color=TEXT_COLOR_FOR_PLOTLY, yaxis_tickfont_color=TEXT_COLOR_FOR_PLOTLY,
    legend_font_color=TEXT_COLOR_FOR_PLOTLY, legend_title_font_color=PRIMARY_COLOR_FOR_PLOTLY
)

# ---------------- Auth / Login ----------------
def check_login_and_domain():
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", None)
    if not st.user.is_logged_in:
        return 'NOT_LOGGED_IN'
    user_email = st.user.email
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

# ---------------- Date Parsing Helpers ----------------
def parse_to_utc(series: pd.Series) -> pd.Series:
    """
    Robustly coerce a Series containing strings / Python datetimes / Pandas Timestamps /
    or 13-digit epoch milliseconds into tz-aware UTC datetimes.
    """
    if series is None:
        return pd.Series(pd.NaT, dtype="datetime64[ns, UTC]")

    s = series.astype("object")

    # Start with general parse (strings, ISO, with/without TZ)
    dt = pd.to_datetime(s, errors="coerce", utc=True)

    # Fix any 13-digit epoch ms that may have been parsed as NaT or strings
    as_str = s.astype(str).str.strip()
    mask_ms = as_str.str.match(r"^\d{13}$", na=False)
    if mask_ms.any():
        ms_vals = as_str[mask_ms].astype(np.int64)
        dt.loc[mask_ms] = pd.to_datetime(ms_vals, unit="ms", utc=True, errors="coerce")

    # If the original dtype is numeric (epoch ms), handle directly too
    if pd.api.types.is_numeric_dtype(s):
        dt_num = pd.to_datetime(s, unit="ms", utc=True, errors="coerce")
        dt = dt.fillna(dt_num)

    # Ensure final dtype is tz-aware UTC
    dt = pd.to_datetime(dt, utc=True, errors="coerce")
    return dt

def pst_display_from_utc(utc_series: pd.Series) -> pd.Series:
    """Format tz-aware UTC datetimes as PST strings for display."""
    if utc_series is None or utc_series.empty:
        return utc_series
    if not hasattr(utc_series, "dt"):
        return utc_series
    try:
        pst = utc_series.dt.tz_convert(PST_TIMEZONE)
        return pst.dt.strftime('%Y-%m-%d %I:%M %p PST')
    except Exception:
        return utc_series.astype(str)

# ---------------- Google Auth (gspread) ----------------
@st.cache_data(ttl=600)
def authenticate_gspread_cached():
    gcp_secrets_obj = st.secrets.get("gcp_service_account")
    if gcp_secrets_obj is None:
        st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND.")
        return None
    try:
        gcp_secrets_dict = dict(gcp_secrets_obj)
        required = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing = [k for k in required if gcp_secrets_dict.get(k) is None]
        if missing:
            st.error(f"🚨 Error: GCP secrets dict missing keys: {', '.join(missing)}.")
            return None
        creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Error authenticating with Google: {e}")
        return None

# ---------------- Load & Clean Data ----------------
@st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
def load_data_from_google_sheet():
    gc = authenticate_gspread_cached()
    now_utc = datetime.now(tz=UTC_TIMEZONE)
    if gc is None:
        return pd.DataFrame(), None

    sheet_url_or_name = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
    worksheet_name = st.secrets.get("GOOGLE_WORKSHEET_NAME")
    if not sheet_url_or_name:
        st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME missing.")
        return pd.DataFrame(), None
    if not worksheet_name:
        st.error("🚨 Config: GOOGLE_WORKSHEET_NAME missing.")
        return pd.DataFrame(), None

    try:
        ss = gc.open_by_url(sheet_url_or_name) if ("docs.google.com" in sheet_url_or_name or "spreadsheets" in sheet_url_or_name) else gc.open(sheet_url_or_name)
        ws = ss.worksheet(worksheet_name)
        rows = ws.get_all_records(head=1, expected_headers=None)
        if not rows:
            st.warning("⚠️ No data rows in Google Sheet.")
            return pd.DataFrame(), now_utc

        df = pd.DataFrame(rows)

        # --- Normalize column names ---
        df.rename(columns={c: "".join(str(c).strip().lower().split()) for c in df.columns}, inplace=True)

        # --- Map to internal names ---
        name_map = {
            "licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "dcc": "licenseNumber",
            "storename": "storeName", "accountname": "storeName",
            "repname": "repName", "representative": "repName",
            "onboardingdate": "onboardingDate",
            "deliverydate": "deliveryDate",
            "deliverydatets": "deliveryDateTs",
            "confirmationtimestamp": "confirmationTimestamp", "confirmedat": "confirmationTimestamp",
            "clientsentiment": "clientSentiment", "sentiment": "clientSentiment",
            "fulltranscript": "fullTranscript", "transcript": "fullTranscript",
            "score": "score", "onboardingscore": "score",
            "status": "status", "onboardingstatus": "status",
            "summary": "summary", "callsummary": "summary",
            "contactnumber": "contactNumber", "phone": "contactNumber",
            "confirmednumber": "confirmedNumber", "verifiednumber": "confirmedNumber",
            "contactname": "contactName", "clientcontact": "contactName",
        }
        for k in KEY_REQUIREMENT_DETAILS.keys():
            name_map[k.lower()] = k

        df.rename(columns={k: v for k, v in name_map.items() if k in df.columns and v not in df.columns}, inplace=True)

        # --- Build UTC datetime columns (tz-aware!) ---
        # Prefer deliveryDateTs if present and deliveryDate missing/blank
        if "deliveryDate" not in df.columns and "deliveryDateTs" in df.columns:
            df["deliveryDate"] = df["deliveryDateTs"]

        # Raw, pre-parse strings
        for col in ["onboardingDate", "deliveryDate", "confirmationTimestamp"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace("\n", " ", regex=False).str.strip()

        # Parse to tz-aware UTC
        df["onboardingDate_dt"] = parse_to_utc(df["onboardingDate"]) if "onboardingDate" in df.columns else pd.NaT
        df["deliveryDate_dt"] = parse_to_utc(df["deliveryDate"]) if "deliveryDate" in df.columns else pd.NaT
        df["confirmationTimestamp_dt"] = parse_to_utc(df["confirmationTimestamp"]) if "confirmationTimestamp" in df.columns else pd.NaT

        # Display strings in PST
        if "onboardingDate_dt" in df.columns:
            df["onboardingDate"] = pst_display_from_utc(df["onboardingDate_dt"])
        if "deliveryDate_dt" in df.columns:
            df["deliveryDate"] = pst_display_from_utc(df["deliveryDate_dt"])
        if "confirmationTimestamp_dt" in df.columns:
            df["confirmationTimestamp"] = pst_display_from_utc(df["confirmationTimestamp_dt"])

        # Date-only for filters (from tz-aware UTC → PST date)
        if "onboardingDate_dt" in df.columns:
            df["onboarding_date_only"] = df["onboardingDate_dt"].dt.tz_convert(PST_TIMEZONE).dt.date
        else:
            df["onboarding_date_only"] = pd.NaT

        # --- SAFE tz-aware subtraction for days_to_confirmation ---
        try:
            delivery_utc = df["deliveryDate_dt"]
            confirm_utc = df["confirmationTimestamp_dt"]
            diff = confirm_utc - delivery_utc
            df["days_to_confirmation"] = (diff.dt.total_seconds() / 86400.0).round(0)
        except Exception as e:
            st.warning(f"Days-to-confirmation calculation fallback: {e}")
            df["days_to_confirmation"] = np.nan

        # --- Clean & format other fields ---
        for phone_col in ["contactNumber", "confirmedNumber"]:
            if phone_col in df.columns:
                df[phone_col] = df[phone_col].apply(lambda x: "" if pd.isna(x) or not str(x).strip() else (
                    (lambda d: f"({d[0:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else
                     (f"+1 ({d[1:4]}) {d[4:7]}-{d[7:11]}" if len(d) == 11 and d.startswith('1') else str(x))
                    )(re.sub(r'\D', '', str(x)))
                ))
        for name_col in ["repName", "contactName"]:
            if name_col in df.columns:
                df[name_col] = df[name_col].apply(lambda s: "" if pd.isna(s) or not str(s).strip() else ' '.join(w.capitalize() for w in str(s).split()))

        string_cols = [
            'status', 'clientSentiment', 'repName', 'storeName', 'licenseNumber', 'fullTranscript',
            'summary', 'contactName', 'contactNumber', 'confirmedNumber',
            'onboardingDate', 'deliveryDate', 'confirmationTimestamp'
        ]
        for col in string_cols:
            df[col] = df.get(col, "").astype(str).replace(['nan', 'NaN', 'None', 'NaT', '<NA>'], "", regex=False).fillna("")

        df["score"] = pd.to_numeric(df.get("score"), errors="coerce")

        for col in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
            df[col] = df.get(col, pd.NA)

        # Drop legacy columns if present
        for c in ["deliverydatets", "onboardingwelcome"]:
            if c in df.columns:
                df.drop(columns=[c], inplace=True)

        return df, now_utc

    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        st.error(f"🚫 Google Sheets Error: {e}. Check URL/name & permissions.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"🌪️ Error loading data: {e}")
        return pd.DataFrame(), None

@st.cache_data
def convert_df_to_csv(df_to_convert):
    return df_to_convert.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input):
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA
    total = len(df_input)
    confirmed = df_input[df_input['status'].astype(str).str.lower().str.contains('confirmed', na=False)].shape[0]
    success_rate = (confirmed / total * 100) if total > 0 else 0.0
    avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    avg_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce').mean()
    return total, success_rate, avg_score, avg_days

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

# ---------------- Auth Gate ----------------
auth_status = check_login_and_domain()
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
        _, c, _ = st.columns([1,1,1])
        with c:
            st.button("Log in with Google 🔑", on_click=st.login, use_container_width=True, key="google_login_main_btn_centered")
    st.stop()

# ---------------- Session State ----------------
default_s_init, default_e_init = get_default_date_range(None)
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
if 'date_range' not in st.session_state: st.session_state.date_range = (default_s_init, default_e_init)
if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = None
if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = None
if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
for f_key in ['repName_filter', 'status_filter', 'clientSentiment_filter']:
    st.session_state.setdefault(f_key, [])
for s_key in ['licenseNumber_search', 'storeName_search']:
    st.session_state.setdefault(s_key, "")
TAB_OVERVIEW = "📊 Overview"; TAB_DETAILED_ANALYSIS = "🔎 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
st.session_state.setdefault('active_tab', TAB_OVERVIEW)
st.session_state.setdefault('selected_transcript_key_dialog_global_search', None)
st.session_state.setdefault('selected_transcript_key_filtered_analysis', None)
st.session_state.setdefault('show_global_search_dialog', False)

# ---------------- Load Data ----------------
if not st.session_state.data_loaded:
    df_loaded, load_time = load_data_from_google_sheet()
    if load_time:
        st.session_state.last_data_refresh_time = load_time
        if not df_loaded.empty:
            st.session_state.df_original = df_loaded
            st.session_state.data_loaded = True
            if 'onboarding_date_only' in df_loaded:
                series = pd.to_datetime(df_loaded['onboarding_date_only'], errors='coerce')
                valid = series.dropna()
                min_d = valid.dt.date.min() if not valid.empty else None
                max_d = valid.dt.date.max() if not valid.empty else None
            else:
                min_d = max_d = None
            st.session_state.min_data_date_for_filter = min_d
            st.session_state.max_data_date_for_filter = max_d
            st.session_state.date_range = get_default_date_range(df_loaded.get('onboarding_date_only'))
        else:
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded = False
    else:
        st.session_state.df_original = pd.DataFrame()
        st.session_state.data_loaded = False

df_original = st.session_state.df_original

# ---------------- Sidebar ----------------
st.sidebar.header("⚙️ Dashboard Controls"); st.sidebar.markdown("---")

st.sidebar.subheader("🔍 Global Search")
st.sidebar.caption("Search all data. Overrides filters below.")
global_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}

ln_search_val = st.sidebar.text_input(
    f"Search {global_search_cols['licenseNumber']}:",
    value=st.session_state.get("licenseNumber_search", ""),
    key="licenseNumber_global_search_widget",
    help="Enter license number part."
)
if ln_search_val != st.session_state["licenseNumber_search"]:
    st.session_state["licenseNumber_search"] = ln_search_val
    st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", ""))
    st.rerun()

store_names_options = [""]
if not df_original.empty and 'storeName' in df_original.columns:
    unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique())
    store_names_options.extend([x for x in unique_stores if str(x).strip()])
current_store_search_val = st.session_state.get("storeName_search", "")
try:
    current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
except ValueError:
    current_store_idx = 0
selected_store_val = st.sidebar.selectbox(
    f"Search {global_search_cols['storeName']}:",
    options=store_names_options, index=current_store_idx,
    key="storeName_global_search_widget",
    help="Select or type store name."
)
if selected_store_val != st.session_state["storeName_search"]:
    st.session_state["storeName_search"] = selected_store_val
    st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", ""))
    st.rerun()

st.sidebar.markdown("---")
global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))

st.sidebar.subheader("📊 Filters")
st.sidebar.caption("Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data.")
st.sidebar.markdown("##### Quick Date Ranges")
s1, s2, s3 = st.sidebar.columns(3)
today_for_shortcuts = date.today()
if s1.button("MTD", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active:
        st.session_state.date_range = (today_for_shortcuts.replace(day=1), today_for_shortcuts)
        st.session_state.date_filter_is_active = True
        st.rerun()
if s2.button("YTD", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active:
        st.session_state.date_range = (today_for_shortcuts.replace(month=1, day=1), today_for_shortcuts)
        st.session_state.date_filter_is_active = True
        st.rerun()
if s3.button("ALL", use_container_width=True, disabled=global_search_active, type="primary"):
    if not global_search_active:
        all_start = st.session_state.get('min_data_date_for_filter', today_for_shortcuts.replace(year=today_for_shortcuts.year-1))
        all_end = st.session_state.get('max_data_date_for_filter', today_for_shortcuts)
        if all_start and all_end:
            st.session_state.date_range = (all_start, all_end)
            st.session_state.date_filter_is_active = True
            st.rerun()

current_session_start, current_session_end = st.session_state.date_range
min_dt_for_widget = st.session_state.get('min_data_date_for_filter')
max_dt_for_widget = st.session_state.get('max_data_date_for_filter')
val_start_widget = current_session_start
if min_dt_for_widget and current_session_start < min_dt_for_widget:
    val_start_widget = min_dt_for_widget
val_end_widget = current_session_end
if max_dt_for_widget and current_session_end > max_dt_for_widget:
    val_end_widget = max_dt_for_widget
if val_start_widget > val_end_widget:
    val_start_widget = val_end_widget

selected_date_range_tuple = st.sidebar.date_input(
    "Custom Date Range (Onboarding):",
    value=(val_start_widget, val_end_widget),
    min_value=min_dt_for_widget, max_value=max_dt_for_widget,
    key="date_selector_custom",
    disabled=global_search_active,
    help="Select start/end dates."
)
if (not global_search_active and isinstance(selected_date_range_tuple, tuple) and
        len(selected_date_range_tuple) == 2 and selected_date_range_tuple != st.session_state.date_range):
    st.session_state.date_range = selected_date_range_tuple
    st.session_state.date_filter_is_active = True
    st.rerun()

start_dt_filter, end_dt_filter = st.session_state.date_range

category_filters_map = {'repName':'Representative(s)', 'status':'Status(es)', 'clientSentiment':'Client Sentiment(s)'}
for col_key, label_text in category_filters_map.items():
    options = []
    if not df_original.empty and col_key in df_original.columns and df_original[col_key].notna().any():
        if col_key == 'status':
            options = sorted([v for v in df_original[col_key].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().dropna().unique() if str(v).strip()])
        else:
            options = sorted([v for v in df_original[col_key].astype(str).dropna().unique() if str(v).strip()])
    current_sel = st.session_state.get(f"{col_key}_filter", [])
    valid_current_sel = [s for s in current_sel if s in options]
    new_sel = st.sidebar.multiselect(
        f"Filter by {label_text}:",
        options=options, default=valid_current_sel,
        key=f"{col_key}_category_filter_widget",
        disabled=global_search_active or not options,
        help=f"Select {label_text}." if options else f"No {label_text} data."
    )
    if not global_search_active and new_sel != valid_current_sel:
        st.session_state[f"{col_key}_filter"] = new_sel
        st.rerun()
    elif global_search_active and st.session_state.get(f"{col_key}_filter") != new_sel:
        st.session_state[f"{col_key}_filter"] = new_sel

def clear_all_filters_and_search():
    ds_cleared, de_cleared = get_default_date_range(st.session_state.df_original.get('onboarding_date_only'))
    st.session_state.date_range = (ds_cleared, de_cleared)
    st.session_state.date_filter_is_active = False
    st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
    for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
    st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
    st.session_state.active_tab = TAB_OVERVIEW

st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management")
if st.sidebar.button("Refresh Data from Source", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.session_state.data_loaded = False
    st.session_state.last_data_refresh_time = None
    st.session_state.df_original = pd.DataFrame()
    clear_all_filters_and_search()
    st.rerun()

if st.session_state.get('data_loaded', False) and st.session_state.get('last_data_refresh_time'):
    refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE)
    st.sidebar.caption(f"☁️ Last data sync: {refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST')}")
elif st.session_state.get('last_data_refresh_time'):
    st.sidebar.caption("⚠️ No data found in last sync. Check Sheet or Refresh.")
else:
    st.sidebar.caption("⏳ Data not yet loaded.")

st.sidebar.markdown("---")
user_display_name = "User"
if hasattr(st.user, "email") and st.user.email:
    user_email_prefix = st.user.email.split('@')[0]
    user_display_name = user_email_prefix
    if hasattr(st.user, "name") and st.user.name and st.user.name.strip():
        try: user_display_name = st.user.name.split()[0]
        except IndexError: user_display_name = st.user.name
    st.sidebar.caption(f"👤 {user_display_name} ({st.user.email})")
else:
    st.sidebar.caption("👤 Welcome!")
st.sidebar.button("Log Out", on_click=st.logout, use_container_width=True, type="secondary")
st.sidebar.caption("Dashboard v4.6.7")

# ---------------- Main ----------------
st.title("📈 Onboarding Analytics Dashboard")

if not st.session_state.data_loaded and df_original.empty:
    if st.session_state.get('last_data_refresh_time'):
        st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh. 🚧</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='no-data-message'>⏳ Initializing data... If persists, check configurations. ⏳</div>", unsafe_allow_html=True)
    st.stop()
elif df_original.empty:
    st.markdown("<div class='no-data-message'>✅ Data source connected, but empty. Add data to Google Sheet. ✅</div>", unsafe_allow_html=True)
    st.stop()

# ---------------- Active Filters Summary ----------------
if st.session_state.active_tab not in ALL_TABS: st.session_state.active_tab = TAB_OVERVIEW
try:
    current_tab_idx = ALL_TABS.index(st.session_state.active_tab)
except ValueError:
    current_tab_idx = 0; st.session_state.active_tab = TAB_OVERVIEW
selected_tab = st.radio("Navigation:", ALL_TABS, index=current_tab_idx, horizontal=True, key="main_tab_selector")
if selected_tab != st.session_state.active_tab:
    st.session_state.active_tab = selected_tab
    st.rerun()

summary_parts = []
global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))
if global_search_active:
    terms = []
    if st.session_state.get("licenseNumber_search", ""): terms.append(f"License: '{st.session_state['licenseNumber_search']}'")
    if st.session_state.get("storeName_search", ""): terms.append(f"Store: '{st.session_state['storeName_search']}'")
    summary_parts.append(f"🔍 Global Search: {'; '.join(terms)}")
    summary_parts.append("(Filters overridden. Results in pop-up.)")
else:
    start_display, end_display = st.session_state.date_range[0].strftime('%b %d, %Y'), st.session_state.date_range[1].strftime('%b %d, %Y')
    min_d = st.session_state.get('min_data_date_for_filter'); max_d = st.session_state.get('max_data_date_for_filter')
    is_all = bool(min_d) and bool(max_d) and st.session_state.date_range == (min_d, max_d) and st.session_state.get('date_filter_is_active', False)
    summary_parts.append("🗓️ Dates: ALL Data" if is_all else f"🗓️ Dates: {start_display} to {end_display}")
    act = []
    for col_key, label_text in category_filters_map.items():
        sel = st.session_state.get(f"{col_key}_filter", [])
        if sel: act.append(f"{label_text.replace('(s)','').strip()}: {', '.join(sel)}")
    if act: summary_parts.append(" | ".join(act))
final_summary_message = " | ".join(filter(None, summary_parts)) or "Displaying data (default date range)."
st.markdown(f"<div class='active-filters-summary'>ℹ️ {final_summary_message}</div>", unsafe_allow_html=True)

# ---------------- Apply Filters / Search ----------------
df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
if not df_original.empty:
    if global_search_active:
        df_temp = df_original.copy()
        ln_term = st.session_state.get("licenseNumber_search", "").strip().lower()
        sn_term = st.session_state.get("storeName_search", "").strip()
        if ln_term and "licenseNumber" in df_temp.columns:
            df_temp = df_temp[df_temp['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
        if sn_term and "storeName" in df_temp.columns:
            df_temp = df_temp[df_temp['storeName'] == sn_term]
        df_global_search_results_display = df_temp.copy()
        df_filtered = df_global_search_results_display.copy()
    else:
        df_temp = df_original.copy()
        if 'onboarding_date_only' in df_temp.columns and df_temp['onboarding_date_only'].notna().any():
            d = pd.to_datetime(df_temp['onboarding_date_only'], errors='coerce').dt.date
            valid = d.notna()
            cond = pd.Series(False, index=df_temp.index)
            if valid.any():
                cond[valid] = (d[valid] >= start_dt_filter) & (d[valid] <= end_dt_filter)
            df_temp = df_temp[cond]
        for col_name_cat, _ in category_filters_map.items():
            sel = st.session_state.get(f"{col_name_cat}_filter", [])
            if sel and col_name_cat in df_temp.columns:
                if col_name_cat == 'status':
                    df_temp = df_temp[df_temp[col_name_cat].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().isin(sel)]
                else:
                    df_temp = df_temp[df_temp[col_name_cat].astype(str).isin(sel)]
        df_filtered = df_temp.copy()
else:
    df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()

# ---------------- MTD Metrics ----------------
today_mtd = date.today()
mtd_start = today_mtd.replace(day=1)
prev_end = mtd_start - timedelta(days=1)
prev_start = prev_end.replace(day=1)
df_mtd_data = pd.DataFrame(); df_prev_mtd_data = pd.DataFrame()
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    d_all = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid = d_all.notna()
    if valid.any():
        base = df_original[valid].copy()
        d_valid = d_all[valid]
        mtd_mask = (d_valid >= mtd_start) & (d_valid <= today_mtd)
        prev_mask = (d_valid >= prev_start) & (d_valid <= prev_end)
        df_mtd_data = base[mtd_mask.values if len(mtd_mask) == len(base) else mtd_mask[base.index]]
        df_prev_mtd_data = base[prev_mask.values if len(prev_mask) == len(base) else prev_mask[base.index]]
total_mtd, sr_mtd, score_mtd, days_to_confirm_mtd = calculate_metrics(df_mtd_data)
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_data)
delta_onboardings_mtd = (total_mtd - total_prev_mtd) if pd.notna(total_mtd) and pd.notna(total_prev_mtd) else None

# ---------------- Table helpers ----------------
def get_cell_style_class(column_name, value):
    val_str = str(value).strip().lower()
    if pd.isna(value) or val_str == "" or val_str == "na":
        return "cell-req-na"

    if column_name == 'score':
        try:
            score_num = float(value)
        except:
            return ""
        if score_num >= 8:
            return "cell-score-good"
        elif score_num >= 4:
            return "cell-score-medium"
        else:
            return "cell-score-bad"

    elif column_name == 'clientSentiment':
        if val_str == 'positive':
            return "cell-sentiment-positive"
        elif val_str == 'neutral':
            return "cell-sentiment-neutral"
        elif val_str == 'negative':
            return "cell-sentiment-negative"

    elif column_name == 'days_to_confirmation':
        try:
            days_num = float(value)
        except:
            return ""
        if days_num <= 7:
            return "cell-days-good"
        elif days_num <= 14:
            return "cell-days-medium"
        else:
            return "cell-days-bad"

    elif column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
        if val_str in ['true', '1', 'yes', 'x', 'completed', 'done']:
            return "cell-req-met"
        elif val_str in ['false', '0', 'no']:
            return "cell-req-not-met"

    elif column_name == 'status':
        return "cell-status"

    return ""


def display_html_table_and_details(df_to_display, context_key_prefix=""):
    if df_to_display is None or df_to_display.empty:
        label = context_key_prefix.replace('_', ' ').title().replace('Tab', '').replace('Dialog', '')
        if not df_original.empty:
            st.markdown(
                f"<div class='no-data-message'>📊 No data for {label}. Try different filters! 📊</div>",
                unsafe_allow_html=True
            )
        return

    dfv = df_to_display.copy().reset_index(drop=True)

    def map_status(status_val):
        s = str(status_val).strip().lower()
        if s == 'confirmed':
            return "✅ Confirmed"
        if s == 'pending':
            return "⏳ Pending"
        if s == 'failed':
            return "❌ Failed"
        return status_val

    if 'status' in dfv.columns:
        dfv['status_styled'] = dfv['status'].apply(map_status)
    else:
        dfv['status_styled'] = ""

    preferred_cols = [
        'onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status_styled',
        'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 'contactNumber',
        'confirmedNumber', 'deliveryDate', 'confirmationTimestamp'
    ] + ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS

    cols_present = dfv.columns.tolist()
    final_cols = [c for c in preferred_cols if c in cols_present]
    excluded_suffixes = ('_dt', '_utc', '_str_original', '_date_only', '_styled')
    others = [
        c for c in cols_present
        if c not in final_cols and not c.endswith(excluded_suffixes)
        and c not in ['fullTranscript', 'summary', 'status', 'onboardingWelcome']
    ]
    final_cols.extend(others)
    final_cols = list(dict.fromkeys(final_cols))

    if not final_cols or dfv[final_cols].empty:
        label = context_key_prefix.replace('_', ' ').title().replace('Tab', '').replace('Dialog', '')
        st.markdown(
            f"<div class='no-data-message'>📋 No columns/data for {label}. 📋</div>",
            unsafe_allow_html=True
        )
        return

    header_map = {
        'status_styled': 'Status',
        'onboardingDate': 'Onboarding Date',
        'repName': 'Rep Name',
        'storeName': 'Store Name',
        'licenseNumber': 'License No.',
        'clientSentiment': 'Sentiment',
        'days_to_confirmation': 'Days to Confirm',
        'contactName': 'Contact Name',
        'contactNumber': 'Contact No.',
        'confirmedNumber': 'Confirmed No.',
        'deliveryDate': 'Delivery Date',
        'confirmationTimestamp': 'Confirmation Time'
    }
    for req_key, details in KEY_REQUIREMENT_DETAILS.items():
        header_map[req_key] = details.get("chart_label", req_key)

    html = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
    for c in final_cols:
        html.append(f"<th>{header_map.get(c, c.replace('_', ' ').title())}</th>")
    html.append("</tr></thead><tbody>")

    for _, row in dfv.iterrows():
        html.append("<tr>")
        for c in final_cols:
            base_col = 'status' if c == 'status_styled' else c
            val = row.get(c, "")
            cls = get_cell_style_class(base_col, row.get(base_col, val))
            if c == 'score' and pd.notna(val):
                try:
                    val = f"{float(val):.1f}"
                except:
                    pass
            elif c == 'days_to_confirmation' and pd.notna(val):
                try:
                    val = f"{float(val):.0f}"
                except:
                    pass
            html.append(f"<td class='{cls}'>{val}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📄 View Full Record Details")
    key_sel = f"selected_transcript_key_{context_key_prefix}"
    if key_sel not in st.session_state:
        st.session_state[key_sel] = None

    auto_selected_this_run = False
    if len(dfv) == 1:
        r = dfv.iloc[0]
        auto_key = f"Idx 0: {r.get('storeName','N/A')} ({r.get('onboardingDate','N/A')})"
        if st.session_state[key_sel] != auto_key:
            st.session_state[key_sel] = auto_key
            auto_selected_this_run = True

    auto_once_key = f"{context_key_prefix}_auto_selected_once"
    if auto_selected_this_run and not st.session_state.get(auto_once_key, False):
        st.session_state[auto_once_key] = True
        st.rerun()
    elif len(dfv) != 1:
        st.session_state[auto_once_key] = False

    if 'fullTranscript' in dfv.columns or 'summary' in dfv.columns:
        opts = {
            f"Idx {idx}: {row.get('storeName','N/A')} ({row.get('onboardingDate','N/A')})": idx
            for idx, row in dfv.iterrows()
        }
        if opts:
            opt_list = [None] + list(opts.keys())
            cur = st.session_state[key_sel]
            try:
                cur_idx = opt_list.index(cur)
            except ValueError:
                cur_idx = 0
                st.session_state[key_sel] = None

            sel = st.selectbox(
                "Select record to view details:",
                options=opt_list,
                index=cur_idx,
                format_func=lambda x: "📄 Choose an entry..." if x is None else x,
                key=f"transcript_selector_{context_key_prefix}"
            )
            if sel != st.session_state[key_sel]:
                st.session_state[key_sel] = sel
                st.session_state[auto_once_key] = False
                st.rerun()

            if st.session_state[key_sel]:
                idx = opts[st.session_state[key_sel]]
                row = dfv.loc[idx]
                st.markdown("<h5>📋 Onboarding Summary & Checks:</h5>", unsafe_allow_html=True)
                items = {
                    "Store": row.get('storeName', "N/A"),
                    "Rep": row.get('repName', "N/A"),
                    "Score": (f"{float(row.get('score')):.1f}" if pd.notna(row.get('score')) else "N/A"),
                    "Status": row.get('status_styled', "N/A"),
                    "Sentiment": row.get('clientSentiment', "N/A")
                }
                chunks = ["<div class='transcript-summary-grid'>"]
                for k, v in items.items():
                    chunks.append(f"<div class='transcript-summary-item'><strong>{k}:</strong> {v}</div>")
                call_sum = str(row.get('summary', '')).strip()
                if call_sum and call_sum.lower() not in ['na', 'n/a', '']:
                    chunks.append(
                        f"<div class='transcript-summary-item transcript-summary-item-fullwidth'><strong>📝 Call Summary:</strong> {call_sum}</div>"
                    )
                chunks.append("</div>")
                st.markdown("".join(chunks), unsafe_allow_html=True)

                st.markdown("<div class='transcript-details-section'>", unsafe_allow_html=True)
                st.markdown("<h6>Key Requirement Checks:</h6>", unsafe_allow_html=True)
                for c in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
                    det = KEY_REQUIREMENT_DETAILS.get(c, {})
                    desc = det.get("description", c.replace('_', ' ').title())
                    typ = det.get("type", "")
                    raw = row.get(c, pd.NA)
                    s = str(raw).strip().lower()
                    is_met = s in ['true', '1', 'yes', 'x', 'completed', 'done']
                    emoji = "✅" if is_met else ("❌" if pd.notna(raw) and s != "" else "➖")
                    tag = f"<span class='type'>[{typ}]</span>" if typ else ""
                    st.markdown(f"<div class='requirement-item'>{emoji} {desc} {tag}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("<h5>🎙️ Full Transcript:</h5>", unsafe_allow_html=True)
                transcript = str(row.get('fullTranscript', '')).strip()
                if transcript and transcript.lower() not in ['na', 'n/a', '']:
                    parts = ["<div class='transcript-pane-container'><div class='transcript-container'>"]
                    processed = transcript.replace('\\n', '\n')
                    for line in processed.split('\n'):
                        t = line.strip()
                        if not t:
                            continue
                        seg = t.split(":", 1)
                        speaker = f"<strong>{seg[0].strip()}:</strong>" if len(seg) == 2 else ""
                        msg = seg[1].strip() if len(seg) == 2 else t
                        parts.append(f"<p class='transcript-line'>{speaker} {msg}</p>")
                    parts.append("</div></div>")
                    st.markdown("".join(parts), unsafe_allow_html=True)
                else:
                    st.info("ℹ️ No transcript available or empty for this record.")
        else:
            st.markdown("<div class='no-data-message'>📋 No entries in table to select details. 📋</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='no-data-message'>📜 Necessary columns ('fullTranscript'/'summary') missing. 📜</div>", unsafe_allow_html=True)

    st.markdown("---")
    csv_bytes = convert_df_to_csv(dfv[final_cols])
    label = f"📥 Download These {context_key_prefix.replace('_',' ').title().replace('Tab','').replace('Dialog','')} Results"
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=f'{context_key_prefix}_results_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        mime='text/csv',
        use_container_width=True
    )


# ---------------- Global Search Dialog ----------------
if st.session_state.get('show_global_search_dialog', False) and global_search_active:
    @st.dialog("🔍 Global Search Results", width="large")
    def show_global_search_dialog_content():
        st.markdown("##### Records matching global search criteria:")
        if not df_global_search_results_display.empty:
            display_html_table_and_details(
                df_global_search_results_display,
                context_key_prefix="dialog_global_search"
            )
        else:
            st.info("ℹ️ No results for global search. Try broadening terms.")
        if st.button("Close & Clear Search"):
            st.session_state.show_global_search_dialog = False
            st.session_state.licenseNumber_search = ""
            st.session_state.storeName_search = ""
            if 'selected_transcript_key_dialog_global_search' in st.session_state:
                st.session_state.selected_transcript_key_dialog_global_search = None
            if "dialog_global_search_auto_selected_once" in st.session_state:
                st.session_state.dialog_global_search_auto_selected_once = False
            st.rerun()

    show_global_search_dialog_content()


# ---------------- Tabs ----------------
if st.session_state.active_tab == TAB_OVERVIEW:
    st.header("📈 Month-to-Date (MTD) Performance")
    c = st.columns(4)
    with c[0]:
        st.metric(
            "🗓️ Onboardings MTD",
            value=f"{total_mtd:.0f}" if pd.notna(total_mtd) else "0",
            delta=(f"{delta_onboardings_mtd:+.0f} vs Prev. Month"
                   if delta_onboardings_mtd is not None and pd.notna(delta_onboardings_mtd) else "N/A"),
            help="Total onboardings MTD vs. same period last month."
        )
    with c[1]:
        st.metric("✅ Success Rate MTD", value=f"{sr_mtd:.1f}%" if pd.notna(sr_mtd) else "N/A",
                  help="Confirmed onboardings MTD.")
    with c[2]:
        st.metric("⭐ Avg. Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A",
                  help="Average score (0-10) MTD.")
    with c[3]:
        st.metric("⏳ Avg. Days to Confirm MTD", value=f"{days_to_confirm_mtd:.1f}" if pd.notna(days_to_confirm_mtd) else "N/A",
                  help="Avg days delivery to confirmation MTD.")

    st.header("📊 Filtered Data Snapshot")
    if global_search_active:
        st.info("ℹ️ Global search active. Close pop-up or clear search for filtered overview.")
    elif not df_filtered.empty:
        total_f, sr_f, score_f, days_f = calculate_metrics(df_filtered)
        c2 = st.columns(4)
        with c2[0]:
            st.metric("📄 Onboardings (Filtered)", f"{total_f:.0f}" if pd.notna(total_f) else "0")
        with c2[1]:
            st.metric("🎯 Success Rate (Filtered)", f"{sr_f:.1f}%" if pd.notna(sr_f) else "N/A")
        with c2[2]:
            st.metric("🌟 Avg. Score (Filtered)", f"{score_f:.2f}" if pd.notna(score_f) else "N/A")
        with c2[3]:
            st.metric("⏱️ Avg. Days Confirm (Filtered)", f"{days_f:.1f}" if pd.notna(days_f) else "N/A")
    else:
        st.markdown(
            "<div class='no-data-message'>🤷 No data matches filters for Overview. Adjust selections! 🤷</div>",
            unsafe_allow_html=True
        )

elif st.session_state.active_tab == TAB_DETAILED_ANALYSIS:
    st.header(TAB_DETAILED_ANALYSIS)
    if global_search_active:
        st.info("ℹ️ Global Search active. Results in pop-up. Close/clear search for category/date filters here.")
    else:
        display_html_table_and_details(df_filtered, context_key_prefix="filtered_analysis")
        st.divider()
        st.header("🎨 Key Visualizations (Filtered Data)")
        if not df_filtered.empty:
            with st.container():
                colA, colB = st.columns(2)
                with colA:
                    # Status Distribution
                    if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                        s_counts = (
                            df_filtered['status']
                            .astype(str)
                            .str.replace(r"✅|⏳|❌", "", regex=True)
                            .str.strip()
                            .value_counts()
                            .reset_index()
                        )
                        s_counts.columns = ['status', 'count']
                        fig = px.bar(
                            s_counts, x='status', y='count', color='status',
                            title="Onboarding Status Distribution",
                            color_discrete_sequence=ACTIVE_PLOTLY_PRIMARY_SEQ
                        )
                        fig.update_layout(plotly_base_layout_settings)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.markdown("<div class='no-data-message'>📉 Status data unavailable.</div>", unsafe_allow_html=True)
                    # Rep counts
                    if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                        r_counts = df_filtered['repName'].value_counts().reset_index()
                        r_counts.columns = ['repName', 'count']
                        fig2 = px.bar(
                            r_counts, x='repName', y='count', color='repName',
                            title="Onboardings by Representative",
                            color_discrete_sequence=ACTIVE_PLOTLY_QUALITATIVE_SEQ
                        )
                        fig2.update_layout(
                            plotly_base_layout_settings,
                            xaxis_title="Representative", yaxis_title="Number of Onboardings"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.markdown("<div class='no-data-message'>👥 Rep data unavailable.</div>", unsafe_allow_html=True)

                with colB:
                    # Sentiment
                    if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                        sent = df_filtered['clientSentiment'].value_counts().reset_index()
                        sent.columns = ['clientSentiment', 'count']
                        cmap = {s.lower(): ACTIVE_PLOTLY_SENTIMENT_MAP.get(s.lower(), '#808080')
                                for s in sent['clientSentiment'].unique()}
                        pie = px.pie(
                            sent, names='clientSentiment', values='count', hole=0.4,
                            title="Client Sentiment Breakdown",
                            color='clientSentiment', color_discrete_map=cmap
                        )
                        pie.update_layout(plotly_base_layout_settings)
                        pie.update_traces(textinfo='percent+label', textfont_size=12)
                        st.plotly_chart(pie, use_container_width=True)
                    else:
                        st.markdown("<div class='no-data-message'>😊 Sentiment data unavailable.</div>", unsafe_allow_html=True)

                    # Key requirements (confirmed only)
                    df_conf = df_filtered[df_filtered['status'].astype(str).str.contains('confirmed', case=False, na=False)].copy()
                    key_cols = [c for c in ORDERED_CHART_REQUIREMENTS if c in df_conf.columns]
                    if not df_conf.empty and key_cols:
                        rows = []
                        for c in key_cols:
                            det = KEY_REQUIREMENT_DETAILS.get(c, {})
                            label = det.get("chart_label", c.replace('_', ' ').title())
                            raw = df_conf[c].astype(str).str.lower()
                            val = raw.isin(['true', '1', 'yes', 'x', 'completed', 'done'])
                            total = df_conf[c].notna().sum()
                            trues = val.sum()
                            if total > 0:
                                rows.append({"Key Requirement": label, "Completion (%)": (trues / total) * 100})
                        if rows:
                            dplot = pd.DataFrame(rows)
                            bar = px.bar(
                                dplot.sort_values("Completion (%)", ascending=True),
                                x="Completion (%)", y="Key Requirement", orientation='h',
                                title="Key Req Completion (Confirmed Only)",
                                color_discrete_sequence=[PRIMARY_COLOR_FOR_PLOTLY]
                            )
                            bar.update_layout(
                                plotly_base_layout_settings,
                                yaxis={'categoryorder': 'total ascending'},
                                xaxis_ticksuffix="%"
                            )
                            st.plotly_chart(bar, use_container_width=True)
                        else:
                            st.markdown("<div class='no-data-message'>📊 No data for key req chart.</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div class='no-data-message'>✅ No 'Confirmed' onboardings for req chart.</div>", unsafe_allow_html=True)
        elif not df_original.empty:
            st.markdown("<div class='no-data-message'>🖼️ No data matches filters for visuals. 🖼️</div>", unsafe_allow_html=True)

elif st.session_state.active_tab == TAB_TRENDS:
    st.header(TAB_TRENDS)
    st.markdown(f"*(Visuals based on {'Global Search (Pop-Up)' if global_search_active else 'Filtered Data'})*")
    if not df_filtered.empty:
        # Trend over time
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            src = df_filtered.copy()
            src['onboarding_datetime'] = pd.to_datetime(src['onboarding_date_only'], errors='coerce')
            src.dropna(subset=['onboarding_datetime'], inplace=True)
            if not src.empty:
                span = (src['onboarding_datetime'].max() - src['onboarding_datetime'].min()).days
                freq = 'D'
                if span > 90:
                    freq = 'W-MON'
                if span > 730:
                    freq = 'ME'
                trend = src.set_index('onboarding_datetime').resample(freq).size().reset_index(name='count')
                if not trend.empty:
                    line = px.line(
                        trend, x='onboarding_datetime', y='count', markers=True,
                        title=f"Onboardings Over Time ({freq} Trend)",
                        color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[0]]
                    )
                    line.update_layout(
                        plotly_base_layout_settings,
                        xaxis_title="Date", yaxis_title="Number of Onboardings"
                    )
                    st.plotly_chart(line, use_container_width=True)
                else:
                    st.markdown("<div class='no-data-message'>📈 Not enough data for trend plot.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='no-data-message'>📅 No valid date data for trend.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-data-message'>🗓️ 'onboarding_date_only' missing for trend.</div>", unsafe_allow_html=True)

        # Days to confirmation histogram
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            vals = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not vals.empty:
                nb = max(10, min(30, int(len(vals) / 5))) if len(vals) > 20 else (len(vals.unique()) or 10)
                hist = px.histogram(
                    vals, nbins=nb, title="Distribution of Days to Confirmation",
                    color_discrete_sequence=[ACTIVE_PLOTLY_PRIMARY_SEQ[1]]
                )
                hist.update_layout(
                    plotly_base_layout_settings,
                    xaxis_title="Days to Confirmation", yaxis_title="Frequency"
                )
                st.plotly_chart(hist, use_container_width=True)
            else:
                st.markdown("<div class='no-data-message'>⏳ No 'Days to Confirmation' data.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-data-message'>⏱️ 'Days to Confirmation' missing.</div>", unsafe_allow_html=True)
    elif not df_original.empty:
        st.markdown("<div class='no-data-message'>📉 No data for Trends. Adjust filters. 📉</div>", unsafe_allow_html=True)

# ---------------- Footer ----------------
st.markdown("---")
st.markdown("<div class='footer'>Dashboard v4.6.7</div>", unsafe_allow_html=True)

