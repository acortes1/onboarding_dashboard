import streamlit as st
from urllib.parse import urlencode
import requests
from requests_oauthlib import OAuth2Session # To create the auth URL and manage session
from google.oauth2 import id_token # To verify the ID token
from google.auth.transport import requests as google_requests # To make requests for token verification
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time # Not explicitly used in the final merge, but was in original
import numpy as np
import re
from dateutil import tz # For PST conversion

# --- Configuration from secrets.toml (SSO and Google Sheets) ---
try:
    # SSO Config
    GOOGLE_SSO_CLIENT_ID = st.secrets["GOOGLE_SSO_CLIENT_ID"]
    GOOGLE_SSO_CLIENT_SECRET = st.secrets["GOOGLE_SSO_CLIENT_SECRET"]
    ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]

    # Google Sheets (for the dashboard data, accessed via service account)
    GOOGLE_SHEET_URL_OR_NAME = st.secrets["GOOGLE_SHEET_URL_OR_NAME"]
    GOOGLE_WORKSHEET_NAME = st.secrets["GOOGLE_WORKSHEET_NAME"]
    GCP_SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]

except KeyError as e:
    st.error(f"🚨 Missing critical configuration in .streamlit/secrets.toml: {e}. "
               "Please ensure all SSO (GOOGLE_SSO_CLIENT_ID, GOOGLE_SSO_CLIENT_SECRET, ALLOWED_DOMAIN, REDIRECT_URI) "
               "and Google Sheets (GOOGLE_SHEET_URL_OR_NAME, GOOGLE_WORKSHEET_NAME, gcp_service_account) secrets are set.")
    st.stop()

# --- OAuth Endpoints ---
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# --- SSO Helper Functions ---
def get_google_auth_url():
    """Generates the Google Authentication URL."""
    scope = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
    oauth = OAuth2Session(client_id=GOOGLE_SSO_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=scope)
    auth_url, state = oauth.authorization_url(AUTHORIZATION_URL, access_type="offline", prompt="consent", hd=ALLOWED_DOMAIN)
    st.session_state["oauth_state"] = state
    return auth_url

def exchange_code_for_token(code):
    """Exchanges the authorization code for an access token and ID token."""
    data = {
        "code": code,
        "client_id": GOOGLE_SSO_CLIENT_ID,
        "client_secret": GOOGLE_SSO_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    try:
        token_response = requests.post(TOKEN_URL, data=data)
        token_response.raise_for_status()
        return token_response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Error exchanging code for token: {e}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_message += f"\nGoogle Error: {error_details.get('error_description', e.response.text)}"
            except ValueError:
                error_message += f"\nResponse content: {e.response.content.decode(errors='ignore')}"
        st.error(error_message)
        return None

def get_user_info_from_id_token(token_data):
    """Verifies the ID token and extracts user information, including domain check."""
    if "id_token" not in token_data:
        st.error("Login failed: ID token not found in token response from Google.")
        return None
    try:
        id_info = id_token.verify_oauth2_token(
            token_data["id_token"], google_requests.Request(), GOOGLE_SSO_CLIENT_ID
        )
        if 'hd' not in id_info or id_info['hd'].lower() != ALLOWED_DOMAIN.lower():
            st.error(f"Login failed: User's domain ('{id_info.get('hd', 'N/A')}') "
                       f"does not match the allowed domain ('{ALLOWED_DOMAIN}'). Access denied.")
            return None
        if id_info['aud'] != GOOGLE_SSO_CLIENT_ID:
            st.error("Login failed: Token audience mismatch. The token was not intended for this application.")
            return None
        st.session_state["user_info"] = {
            "email": id_info.get("email"), "name": id_info.get("name"),
            "picture": id_info.get("picture"), "hd": id_info.get("hd"),
            "sub": id_info.get("sub")
        }
        return st.session_state["user_info"]
    except ValueError as e:
        st.error(f"Login failed: Invalid ID token. ({e})")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during token verification: {e}")
        return None

# --- Streamlit App Logic: SSO Initialization and OAuth Callback Handling ---
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if "user_info" not in st.session_state: st.session_state["user_info"] = None
if "oauth_state" not in st.session_state: st.session_state["oauth_state"] = None

query_params = st.query_params
if not st.session_state.get("authenticated", False) and "code" in query_params:
    auth_code_list = query_params.get_all("code")
    returned_state_list = query_params.get_all("state")
    auth_code = auth_code_list[0] if auth_code_list else None
    returned_state = returned_state_list[0] if returned_state_list else None

    if not auth_code: st.error("Authentication failed: No authorization code received.")
    elif not returned_state or returned_state != st.session_state.get("oauth_state"):
        st.error("Login failed: State mismatch (CSRF suspected). Please try again.")
        st.session_state["oauth_state"] = None
    else:
        st.session_state["oauth_state"] = None
        token_data = exchange_code_for_token(auth_code)
        if token_data:
            user_details = get_user_info_from_id_token(token_data)
            if user_details:
                st.session_state["authenticated"] = True
                st.query_params.clear()
                st.rerun()
    if not st.session_state.get("authenticated", False) and ("code" in query_params or "state" in query_params):
        st.query_params.clear()
        if not st.session_state.get("authenticated", False): st.rerun()


# --- Main Application UI ---
if not st.session_state.get("authenticated", False):
    # --- Login Page ---
    st.set_page_config(layout="centered", page_title="Login - Onboarding Dashboard")
    st.title("Welcome to the Onboarding Dashboard 🛡️")
    st.markdown(f"Please log in with your **{ALLOWED_DOMAIN}** Google account to continue.")
    auth_url = get_google_auth_url()
    st.link_button("🔑 Login with Google", auth_url, use_container_width=True, type="primary")
    st.caption("You will be redirected to Google for authentication.")
else:
    # --- Authenticated User - Display Dashboard ---
    st.set_page_config(
        page_title="Onboarding Analytics Dashboard v4.3.1",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    user = st.session_state["user_info"] # User info from SSO

    # --- Custom CSS Injection (from original app) ---
    def load_custom_css():
        THEME = st.get_option("theme.base")
        if THEME == "light":
            SCORE_GOOD_BG = "#DFF0D8"; SCORE_GOOD_TEXT = "#3C763D"; SCORE_MEDIUM_BG = "#FCF8E3"; SCORE_MEDIUM_TEXT = "#8A6D3B"; SCORE_BAD_BG = "#F2DEDE"; SCORE_BAD_TEXT = "#A94442";
            SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT; SENTIMENT_NEUTRAL_BG = "#F0F2F6"; SENTIMENT_NEUTRAL_TEXT = "#4A5568"; SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT;
            DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT; DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT; DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT;
            REQ_MET_BG = "#E7F3E7"; REQ_MET_TEXT = "#256833"; REQ_NOT_MET_BG = "#F8EAEA"; REQ_NOT_MET_TEXT = "#9E3434"; REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)";
            TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)"; TABLE_BORDER_COLOR = "var(--border-color)"; TABLE_CELL_PADDING = "0.65em 0.8em"; TABLE_FONT_SIZE = "0.92rem";
        else: # Dark Theme
            SCORE_GOOD_BG = "#1E4620"; SCORE_GOOD_TEXT = "#A8D5B0"; SCORE_MEDIUM_BG = "#4A3F22"; SCORE_MEDIUM_TEXT = "#FFE0A2"; SCORE_BAD_BG = "#5A2222"; SCORE_BAD_TEXT = "#FFBDBD";
            SENTIMENT_POSITIVE_BG = SCORE_GOOD_BG; SENTIMENT_POSITIVE_TEXT = SCORE_GOOD_TEXT; SENTIMENT_NEUTRAL_BG = "#2D3748"; SENTIMENT_NEUTRAL_TEXT = "#A0AEC0"; SENTIMENT_NEGATIVE_BG = SCORE_BAD_BG; SENTIMENT_NEGATIVE_TEXT = SCORE_BAD_TEXT;
            DAYS_GOOD_BG = SCORE_GOOD_BG; DAYS_GOOD_TEXT = SCORE_GOOD_TEXT; DAYS_MEDIUM_BG = SCORE_MEDIUM_BG; DAYS_MEDIUM_TEXT = SCORE_MEDIUM_TEXT; DAYS_BAD_BG = SCORE_BAD_BG; DAYS_BAD_TEXT = SCORE_BAD_TEXT;
            REQ_MET_BG = "#1A3A21"; REQ_MET_TEXT = "#A7D7AE"; REQ_NOT_MET_BG = "#4D1A1A"; REQ_NOT_MET_TEXT = "#FFADAD"; REQ_NA_BG = "transparent"; REQ_NA_TEXT = "var(--text-color)";
            TABLE_HEADER_BG = "var(--secondary-background-color)"; TABLE_HEADER_TEXT = "var(--text-color)"; TABLE_BORDER_COLOR = "var(--border-color)"; TABLE_CELL_PADDING = "0.65em 0.8em"; TABLE_FONT_SIZE = "0.92rem";
        css = f"""<style>
            :root {{
                --score-good-bg: {SCORE_GOOD_BG}; --score-good-text: {SCORE_GOOD_TEXT}; --score-medium-bg: {SCORE_MEDIUM_BG}; --score-medium-text: {SCORE_MEDIUM_TEXT}; --score-bad-bg: {SCORE_BAD_BG}; --score-bad-text: {SCORE_BAD_TEXT};
                --sentiment-positive-bg: {SENTIMENT_POSITIVE_BG}; --sentiment-positive-text: {SENTIMENT_POSITIVE_TEXT}; --sentiment-neutral-bg: {SENTIMENT_NEUTRAL_BG}; --sentiment-neutral-text: {SENTIMENT_NEUTRAL_TEXT}; --sentiment-negative-bg: {SENTIMENT_NEGATIVE_BG}; --sentiment-negative-text: {SENTIMENT_NEGATIVE_TEXT};
                --days-good-bg: {DAYS_GOOD_BG}; --days-good-text: {DAYS_GOOD_TEXT}; --days-medium-bg: {DAYS_MEDIUM_BG}; --days-medium-text: {DAYS_MEDIUM_TEXT}; --days-bad-bg: {DAYS_BAD_BG}; --days-bad-text: {DAYS_BAD_TEXT};
                --req-met-bg: {REQ_MET_BG}; --req-met-text: {REQ_MET_TEXT}; --req-not-met-bg: {REQ_NOT_MET_BG}; --req-not-met-text: {REQ_NOT_MET_TEXT}; --req-na-bg: {REQ_NA_BG}; --req-na-text: {REQ_NA_TEXT};
                --table-header-bg: {TABLE_HEADER_BG}; --table-header-text: {TABLE_HEADER_TEXT}; --table-border-color: {TABLE_BORDER_COLOR}; --table-cell-padding: {TABLE_CELL_PADDING}; --table-font-size: {TABLE_FONT_SIZE};
            }}
            body {{ font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }} .stApp {{ padding: 0.5rem 1rem; }}
            h1, h2, h3, h4, h5, h6 {{ font-weight: 600; color: var(--primary-color); }}
            h1 {{ text-align: center; padding-top: 0.8em; padding-bottom: 0.8em; font-size: 2.4rem; letter-spacing: 0.5px; border-bottom: 2px solid var(--primary-color); margin-bottom: 1.5em; font-weight: 700; }}
            h2 {{ font-size: 1.8rem; margin-top: 2.2em; margin-bottom: 1.3em; padding-bottom: 0.5em; border-bottom: 1px solid var(--border-color); font-weight: 600; }}
            h3 {{ font-size: 1.5rem; margin-top: 2em; margin-bottom: 1.1em; font-weight: 600; color: var(--text-color); opacity: 0.9; }}
            h5 {{ color: var(--text-color); opacity: 0.95; margin-top: 1.8em; margin-bottom: 0.9em; font-weight: 500; letter-spacing: 0.1px; font-size: 1.1rem; }}
            div[data-testid="stMetric"], .metric-card {{ background-color: var(--secondary-background-color); padding: 1.4em 1.7em; border-radius: 10px; border: 1px solid var(--border-color); box-shadow: 0 5px 12px rgba(0,0,0,0.06); transition: transform 0.2s ease-out, box-shadow 0.2s ease-out; margin-bottom: 1.3em; }}
            div[data-testid="stMetric"]:hover, .metric-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.08); }}
            div[data-testid="stMetricLabel"] > div {{ color: var(--text-color); opacity: 0.85; font-weight: 500; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5em; }}
            div[data-testid="stMetricValue"] > div {{ color: var(--text-color); font-size: 2.6rem !important; font-weight: 700; line-height: 1.1; }}
            div[data-testid="stMetricDelta"] > div {{ color: var(--text-color); opacity: 0.8; font-weight: 500; font-size: 0.88rem; }}
            div[data-testid="stSidebarUserContent"] {{ padding: 1.8em 1.4em; background-color: var(--secondary-background-color); }}
            div[data-testid="stSidebarUserContent"] h2, div[data-testid="stSidebarUserContent"] h3 {{ color: var(--primary-color); border-bottom-color: var(--border-color); }}
            div[data-testid="stSidebarNavItems"] {{ padding-top: 1.3em; }}
            div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {{ border: none; padding: 11px 25px; border-radius: 8px; font-weight: 600; transition: background-color 0.2s ease, color 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.07); }}
            div[data-testid="stButton"] > button {{ background-color: var(--primary-color); color: white; }}
            div[data-testid="stButton"] > button:hover {{ background-color: color-mix(in srgb, var(--primary-color) 80%, black); transform: translateY(-2px); box-shadow: 0 4px 7px rgba(0,0,0,0.1); }}
            div[data-testid="stDownloadButton"] > button {{ background-color: var(--secondary-background-color); color: var(--primary-color); border: 1px solid var(--primary-color); }}
            div[data-testid="stDownloadButton"] > button:hover {{ background-color: var(--primary-color); color: white; transform: translateY(-2px); box-shadow: 0 4px 7px rgba(0,0,0,0.09); }}
            .streamlit-expanderHeader {{ color: var(--text-color) !important; font-weight: 600; font-size: 1.05em; padding: 1em 0.7em; }}
            .streamlit-expander {{ border: 1px solid var(--border-color); background-color: var(--background-color); border-radius: 10px; margin-bottom: 1.3em; }}
            .streamlit-expander > div > div > p {{ color: var(--text-color); }}
            div[data-testid="stRadio"] label {{ padding: 11px 20px; margin: 0 4px; border-radius: 8px 8px 0 0; border: 1px solid transparent; border-bottom: none; background-color: var(--secondary-background-color); color: var(--text-color); opacity: 0.8; transition: all 0.25s ease; font-weight: 500; font-size: 1rem; }}
            div[data-testid="stRadio"] input:checked + div label {{ background-color: var(--background-color); color: var(--primary-color); font-weight: 600; opacity: 1.0; border-top: 3px solid var(--primary-color); border-left: 1px solid var(--border-color); border-right: 1px solid var(--border-color); box-shadow: 0 -3px 6px rgba(0,0,0,0.04); }}
            div[data-testid="stRadio"] {{ padding-bottom: 0px; border-bottom: 2px solid var(--primary-color); margin-bottom: 28px; }}
            div[data-testid="stRadio"] > label > div:first-child {{ display: none; }}
            .transcript-details-section {{ margin-left: 20px; padding-left: 20px; border-left: 3px solid var(--primary-color); margin-top: 1.4em; }}
            .transcript-summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 1.3em; margin-bottom: 2em; color: var(--text-color); }}
            .transcript-summary-item {{ background-color: var(--secondary-background-color); padding: 1.1em 1.3em; border-radius: 8px; border: 1px solid var(--border-color); }}
            .transcript-summary-item strong {{ color: var(--primary-color); font-weight: 600; }}
            .transcript-summary-item-fullwidth {{ grid-column: 1 / -1; margin-top: 1.3em; padding-top: 1.3em; border-top: 1px dashed var(--border-color); }}
            .requirement-item {{ margin-bottom: 1em; padding: 1em 1.2em; border-left: 4px solid var(--primary-color); background-color: var(--secondary-background-color); border-radius: 6px; color: var(--text-color); font-size: 0.95rem; }}
            .requirement-item .type {{ font-weight: 500; color: var(--text-color); opacity: 0.75; font-size: 0.8rem; margin-left: 12px; background-color: var(--background-color); padding: 3px 8px; border-radius: 4px; }}
            .transcript-container {{ background-color: var(--secondary-background-color); color: var(--text-color); padding: 2em; border-radius: 10px; border: 1px solid var(--border-color); max-height: 580px; overflow-y: auto; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 0.9rem; line-height: 1.7; box-shadow: inset 0 2px 6px rgba(0,0,0,0.03); }}
            .transcript-line strong {{ color: var(--primary-color); font-weight: 600; }}
            .footer {{ font-size: 0.9rem; color: var(--text-color); opacity: 0.65; text-align: center; padding: 35px 0; border-top: 1px solid var(--border-color); margin-top: 60px; }}
            .active-filters-summary {{ font-size: 0.92rem; color: var(--text-color); opacity: 0.9; margin-top: 0px; margin-bottom: 2.2em; padding: 1em 1.4em; background-color: var(--secondary-background-color); border-radius: 8px; border: 1px solid var(--border-color); text-align: center; box-shadow: 0 3px 7px rgba(0,0,0,0.04); }}
            .no-data-message {{ text-align: center; padding: 35px; font-size: 1.2rem; color: var(--text-color); opacity: 0.7; background-color: var(--secondary-background-color); border-radius: 8px; border: 1px dashed var(--border-color); margin-top: 1.4em; }}
            div[data-testid="stTextInput"] input, div[data-testid="stDateInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stSelectbox"] div[role="combobox"], div[data-testid="stMultiSelect"] div[role="combobox"] {{ border-radius: 6px !important; border: 1px solid var(--border-color) !important; padding-top: 0.65em !important; padding-bottom: 0.65em !important; font-size: 0.95rem; }}
            div[data-testid="stTextInput"] input:focus, div[data-testid="stDateInput"] input:focus, div[data-testid="stNumberInput"] input:focus, div[data-testid="stSelectbox"] div[role="combobox"]:focus-within, div[data-testid="stMultiSelect"] div[role="combobox"]:focus-within {{ border-color: var(--primary-color) !important; box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 15%, transparent) !important; }}
            div[data-testid="stModal"] > div {{ border-radius: 12px !important; box-shadow: 0 12px 30px rgba(0,0,0,0.2) !important; }}
            div[data-testid="stModalHeader"] {{ font-size: 1.6rem; color: var(--primary-color); padding-bottom: 0.9em; border-bottom: 1px solid var(--border-color); font-weight: 600; }}
            .custom-table-container {{ overflow-x: auto; border: 1px solid var(--table-border-color); border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); margin-bottom: 1.8em; max-height: 480px; overflow-y: auto; }}
            .custom-styled-table {{ width: 100%; border-collapse: collapse; font-size: var(--table-font-size); color: var(--text-color); }}
            .custom-styled-table th, .custom-styled-table td {{ padding: var(--table-cell-padding); text-align: left; border-bottom: 1px solid var(--table-border-color); border-right: 1px solid var(--table-border-color); white-space: nowrap; }}
            .custom-styled-table th:last-child, .custom-styled-table td:last-child {{ border-right: none; }}
            .custom-styled-table thead tr {{ border-bottom: 2px solid var(--primary-color); }}
            .custom-styled-table th {{ background-color: var(--table-header-bg); color: var(--table-header-text); font-weight: 600; text-transform: capitalize; position: sticky; top: 0; z-index: 1; }}
            .custom-styled-table tbody tr:hover {{ background-color: color-mix(in srgb, var(--secondary-background-color) 75%, var(--primary-color) 8%); }}
            .custom-styled-table td {{ font-weight: 400; }}
            .cell-score-good {{ background-color: var(--score-good-bg); color: var(--score-good-text); }} .cell-score-medium {{ background-color: var(--score-medium-bg); color: var(--score-medium-text); }} .cell-score-bad {{ background-color: var(--score-bad-bg); color: var(--score-bad-text); }}
            .cell-sentiment-positive {{ background-color: var(--sentiment-positive-bg); color: var(--sentiment-positive-text); }} .cell-sentiment-neutral {{ background-color: var(--sentiment-neutral-bg); color: var(--sentiment-neutral-text); }} .cell-sentiment-negative {{ background-color: var(--sentiment-negative-bg); color: var(--sentiment-negative-text); }}
            .cell-days-good {{ background-color: var(--days-good-bg); color: var(--days-good-text); }} .cell-days-medium {{ background-color: var(--days-medium-bg); color: var(--days-medium-text); }} .cell-days-bad {{ background-color: var(--days-bad-bg); color: var(--days-bad-text); }}
            .cell-req-met {{ background-color: var(--req-met-bg); color: var(--req-met-text); }} .cell-req-not-met {{ background-color: var(--req-not-met-bg); color: var(--req-not-met-text); }} .cell-req-na {{ background-color: var(--req-na-bg); color: var(--req-na-text); }}
            .cell-status {{ font-weight: 500; }}
        </style>"""
        st.markdown(css, unsafe_allow_html=True)
    load_custom_css()

    # --- Constants & Configuration (from original app) ---
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    KEY_REQUIREMENT_DETAILS = {
        'introSelfAndDIME': {"description": "Warmly introduce yourself and DIME Industries.", "type": "Secondary", "chart_label": "Intro Self & DIME"},
        'confirmKitReceived': {"description": "Confirm kit and initial order received.", "type": "Primary", "chart_label": "Kit & Order Recv'd"},
        'offerDisplayHelp': {"description": "Ask about help setting up in-store display.", "type": "Secondary", "chart_label": "Offer Display Help"},
        'scheduleTrainingAndPromo': {"description": "Schedule budtender training & first promo.", "type": "Primary", "chart_label": "Sched. Training/Promo"},
        'providePromoCreditLink': {"description": "Provide link for promo-credit requests.", "type": "Secondary", "chart_label": "Promo Credit Link"},
        'expectationsSet': {"description": "Client expectations were clearly set.", "type": "Bonus Criterion", "chart_label": "Expectations Set"}
    }
    ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS = ['introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink', 'expectationsSet']
    ORDERED_CHART_REQUIREMENTS = ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS
    PST_TIMEZONE = tz.gettz('America/Los_Angeles'); UTC_TIMEZONE = tz.tzutc()
    THEME_PLOTLY = st.get_option("theme.base")
    PLOT_BG_COLOR_PLOTLY = "rgba(0,0,0,0)"
    if THEME_PLOTLY == "light":
        ACTIVE_PLOTLY_PRIMARY_SEQ = ['#6A0DAD', '#9B59B6', '#BE90D4', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Pastel1
        ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#2ECC71', 'negative': '#E74C3C', 'neutral': '#BDC3C7' }; TEXT_COLOR_FOR_PLOTLY = "#262730"; PRIMARY_COLOR_FOR_PLOTLY = "#6A0DAD"
    else:
        ACTIVE_PLOTLY_PRIMARY_SEQ = ['#BE90D4', '#9B59B6', '#6A0DAD', '#D2B4DE', '#E8DAEF']; ACTIVE_PLOTLY_QUALITATIVE_SEQ = px.colors.qualitative.Set3
        ACTIVE_PLOTLY_SENTIMENT_MAP = { 'positive': '#27AE60', 'negative': '#C0392B', 'neutral': '#7F8C8D' }; TEXT_COLOR_FOR_PLOTLY = "#FAFAFA"; PRIMARY_COLOR_FOR_PLOTLY = "#BE90D4"
    plotly_base_layout_settings = {"plot_bgcolor": PLOT_BG_COLOR_PLOTLY, "paper_bgcolor": PLOT_BG_COLOR_PLOTLY, "title_x":0.5, "xaxis_showgrid":False, "yaxis_showgrid":True, "yaxis_gridcolor": 'rgba(128,128,128,0.2)', "margin": dict(l=50, r=30, t=70, b=50), "font_color": TEXT_COLOR_FOR_PLOTLY, "title_font_color": PRIMARY_COLOR_FOR_PLOTLY, "title_font_size": 18, "xaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_title_font_color": TEXT_COLOR_FOR_PLOTLY, "xaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "yaxis_tickfont_color": TEXT_COLOR_FOR_PLOTLY, "legend_font_color": TEXT_COLOR_FOR_PLOTLY, "legend_title_font_color": PRIMARY_COLOR_FOR_PLOTLY}

    # --- Data Loading and Processing Functions (from original app) ---
    @st.cache_data(ttl=600) # Cache gspread connection
    def authenticate_gspread_cached():
        if not GCP_SERVICE_ACCOUNT_INFO: st.error("🚨 Error: GCP secrets (gcp_service_account) NOT FOUND in st.secrets."); return None
        if not isinstance(GCP_SERVICE_ACCOUNT_INFO, dict):
            try: gcp_secrets_dict = dict(GCP_SERVICE_ACCOUNT_INFO)
            except (TypeError, ValueError) as e: st.error(f"🚨 Error: Could not convert GCP secrets. Type: {type(GCP_SERVICE_ACCOUNT_INFO)}. Error: {e}"); return None
        else: gcp_secrets_dict = GCP_SERVICE_ACCOUNT_INFO
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing_keys = [k for k in required_keys if gcp_secrets_dict.get(k) is None]
        if missing_keys: st.error(f"🚨 Error: GCP secrets dict missing keys: {', '.join(missing_keys)}."); return None
        try:
            creds = Credentials.from_service_account_info(gcp_secrets_dict, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e: st.error(f"🔑 Google Auth Error (Service Account): {e}. Check credentials/permissions."); return None

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
        if not pd.api.types.is_datetime64_any_dtype(dt_series) or dt_series.isnull().all(): return dt_series
        def convert_element_to_pst(element):
            if pd.isna(element): return None
            try:
                if element.tzinfo is None: aware_element = element.replace(tzinfo=UTC_TIMEZONE)
                else: aware_element = element.astimezone(UTC_TIMEZONE)
                pst_element = aware_element.astimezone(PST_TIMEZONE); return pst_element.strftime('%Y-%m-%d %I:%M %p PST')
            except Exception: return str(element)
        try:
            if dt_series.dt.tz is None: utc_series = dt_series.dt.tz_localize(UTC_TIMEZONE, ambiguous='NaT', nonexistent='NaT')
            else: utc_series = dt_series.dt.tz_convert(UTC_TIMEZONE)
            pst_series = utc_series.dt.tz_convert(PST_TIMEZONE); return pst_series.apply(lambda x: x.strftime('%Y-%m-%d %I:%M %p PST') if pd.notnull(x) else None)
        except AttributeError: return dt_series.apply(convert_element_to_pst)
        except Exception: return dt_series.apply(convert_element_to_pst)

    def format_phone_number(number_str):
        if pd.isna(number_str) or str(number_str).strip() == "": return ""
        digits = re.sub(r'\D', '', str(number_str))
        if len(digits) == 10: return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits.startswith('1'): return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
        return str(number_str)

    def capitalize_name(name_str):
        if pd.isna(name_str) or str(name_str).strip() == "": return ""
        return ' '.join(word.capitalize() for word in str(name_str).split())

    @st.cache_data(ttl=600, show_spinner="🔄 Fetching latest onboarding data...")
    def load_data_from_google_sheet():
        gc = authenticate_gspread_cached(); current_time = datetime.now(UTC_TIMEZONE)
        if gc is None: st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
        if not GOOGLE_SHEET_URL_OR_NAME: st.error("🚨 Config: GOOGLE_SHEET_URL_OR_NAME missing."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
        if not GOOGLE_WORKSHEET_NAME: st.error("🚨 Config: GOOGLE_WORKSHEET_NAME missing."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
        try:
            if "docs.google.com" in GOOGLE_SHEET_URL_OR_NAME or "spreadsheets" in GOOGLE_SHEET_URL_OR_NAME: spreadsheet = gc.open_by_url(GOOGLE_SHEET_URL_OR_NAME)
            else: spreadsheet = gc.open(GOOGLE_SHEET_URL_OR_NAME)
            worksheet = spreadsheet.worksheet(GOOGLE_WORKSHEET_NAME); data = worksheet.get_all_records(head=1, expected_headers=None); st.session_state.last_data_refresh_time = current_time
            if not data: st.warning("⚠️ No data rows in Google Sheet."); return pd.DataFrame()
            df = pd.DataFrame(data)
            standardized_column_names = {col: "".join(str(col).strip().lower().split()) for col in df.columns}; df.rename(columns=standardized_column_names, inplace=True)
            column_name_map_to_code = {"licensenumber": "licenseNumber", "dcclicense": "licenseNumber", "dcc": "licenseNumber", "storename": "storeName", "accountname": "storeName", "repname": "repName", "representative": "repName", "onboardingdate": "onboardingDate", "deliverydate": "deliveryDate", "confirmationtimestamp": "confirmationTimestamp", "confirmedat": "confirmationTimestamp", "clientsentiment": "clientSentiment", "sentiment": "clientSentiment", "fulltranscript": "fullTranscript", "transcript": "fullTranscript", "score": "score", "onboardingscore": "score", "status": "status", "onboardingstatus": "status", "summary": "summary", "callsummary": "summary", "contactnumber": "contactNumber", "phone": "contactNumber", "confirmednumber": "confirmedNumber", "verifiednumber":"confirmedNumber", "contactname": "contactName", "clientcontact": "contactName"}
            for req_key_internal in KEY_REQUIREMENT_DETAILS.keys(): std_req_key = req_key_internal.lower(); column_name_map_to_code[std_req_key] = req_key_internal
            cols_to_rename_actual = {}; current_df_columns_std_list = list(df.columns)
            for standardized_sheet_col_name in current_df_columns_std_list:
                if standardized_sheet_col_name in column_name_map_to_code:
                    target_code_col_name = column_name_map_to_code[standardized_sheet_col_name]
                    if standardized_sheet_col_name != target_code_col_name and target_code_col_name not in cols_to_rename_actual.values() and target_code_col_name not in current_df_columns_std_list: cols_to_rename_actual[standardized_sheet_col_name] = target_code_col_name
            if cols_to_rename_actual: df.rename(columns=cols_to_rename_actual, inplace=True)
            date_cols_map = {'onboardingDate': 'onboardingDate_dt', 'deliveryDate': 'deliveryDate_dt', 'confirmationTimestamp': 'confirmationTimestamp_dt'}
            for original_col, dt_col in date_cols_map.items():
                if original_col in df.columns: df[original_col] = df[original_col].astype(str).str.replace('\n',' ',regex=False).str.strip(); df[dt_col] = robust_to_datetime(df[original_col]); df[original_col] = format_datetime_to_pst_str(df[dt_col])
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
                valid_dates_mask = delivery_utc.notna() & confirmation_utc.notna(); df['days_to_confirmation'] = pd.NA
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
        except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e: st.error(f"🚫 GS Error: {e}. Check URL/name & permissions."); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()
        except Exception as e: st.error(f"🌪️ Error loading data: {e}"); st.session_state.last_data_refresh_time = current_time; return pd.DataFrame()

    @st.cache_data # Cache CSV conversion
    def convert_df_to_csv(df_to_convert): return df_to_convert.to_csv(index=False).encode('utf-8')

    def calculate_metrics(df_input):
        if df_input.empty: return 0, 0.0, pd.NA, pd.NA
        total_onboardings = len(df_input)
        confirmed_onboardings = df_input[df_input['status'].astype(str).str.lower().str.contains('confirmed', na=False)].shape[0]
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

    # --- Initialize Session State for Dashboard (from original app) ---
    default_s_init, default_e_init, initial_min_data_date, initial_max_data_date = get_default_date_range(None) # Initial call before data load
    if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
    if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
    if 'last_data_refresh_time' not in st.session_state: st.session_state.last_data_refresh_time = None
    if 'date_range' not in st.session_state or not (isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range) == 2 and isinstance(st.session_state.date_range[0], date) and isinstance(st.session_state.date_range[1], date)): st.session_state.date_range = (default_s_init, default_e_init)
    if 'min_data_date_for_filter' not in st.session_state: st.session_state.min_data_date_for_filter = initial_min_data_date
    if 'max_data_date_for_filter' not in st.session_state: st.session_state.max_data_date_for_filter = initial_max_data_date
    if 'date_filter_is_active' not in st.session_state: st.session_state.date_filter_is_active = False
    categorical_filter_keys = ['repName_filter', 'status_filter', 'clientSentiment_filter']
    for f_key in categorical_filter_keys:
        if f_key not in st.session_state: st.session_state[f_key] = []
    search_field_keys = ['licenseNumber_search', 'storeName_search'] # Used for global search
    for s_key in search_field_keys:
        if s_key not in st.session_state: st.session_state[s_key] = ""
    TAB_OVERVIEW = "📊 Overview"; TAB_DETAILED_ANALYSIS = "🔎 Detailed Analysis"; TAB_TRENDS = "📈 Trends & Distributions"
    ALL_TABS = [TAB_OVERVIEW, TAB_DETAILED_ANALYSIS, TAB_TRENDS]
    if 'active_tab' not in st.session_state: st.session_state.active_tab = TAB_OVERVIEW
    if 'selected_transcript_key_dialog_global_search' not in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
    if 'selected_transcript_key_filtered_analysis' not in st.session_state: st.session_state.selected_transcript_key_filtered_analysis = None
    if 'show_global_search_dialog' not in st.session_state: st.session_state.show_global_search_dialog = False

    # --- Initial Data Load for Dashboard ---
    if not st.session_state.data_loaded and st.session_state.last_data_refresh_time is None:
        df_loaded = load_data_from_google_sheet() # This uses service account
        if st.session_state.last_data_refresh_time is None: st.session_state.last_data_refresh_time = datetime.now(UTC_TIMEZONE) # Mark refresh time
        if not df_loaded.empty:
            st.session_state.df_original = df_loaded
            st.session_state.data_loaded = True
            # Update date range defaults based on loaded data
            ds, de, min_d, max_d = get_default_date_range(df_loaded.get('onboarding_date_only'))
            st.session_state.date_range = (ds, de)
            st.session_state.min_data_date_for_filter = min_d
            st.session_state.max_data_date_for_filter = max_d
        else:
            st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF if load fails
            st.session_state.data_loaded = False # Explicitly set to false
    df_original = st.session_state.df_original


    # --- Sidebar UI (from original app, adapted for SSO context) ---
    st.sidebar.title("👤 User Profile") # SSO User
    if user.get("picture"): st.sidebar.image(user.get("picture"), width=80, use_column_width='auto', caption=user.get('name'))
    else: st.sidebar.markdown(f"**Name:** {user.get('name', 'N/A')}")
    st.sidebar.markdown(f"**Email:** {user.get('email', 'N/A')}")
    st.sidebar.markdown(f"**Domain:** {user.get('hd', 'N/A')}")
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary", key="sso_logout_button"):
        st.session_state["authenticated"] = False; st.session_state["user_info"] = None
        st.session_state["oauth_state"] = None; st.query_params.clear(); st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Dashboard Controls")
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Global Search"); st.sidebar.caption("Search all data. Overrides filters below.")
    global_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
    ln_search_val = st.sidebar.text_input(f"Search {global_search_cols['licenseNumber']}:", value=st.session_state.get("licenseNumber_search", ""), key="licenseNumber_global_search_widget_v4_3_1", help="Enter license number part.")
    if ln_search_val != st.session_state.get("licenseNumber_search"): st.session_state["licenseNumber_search"] = ln_search_val; st.session_state.show_global_search_dialog = bool(ln_search_val or st.session_state.get("storeName_search", "")); st.rerun()
    store_names_options = [""];
    if not df_original.empty and 'storeName' in df_original.columns: unique_stores = sorted(df_original['storeName'].astype(str).dropna().unique()); store_names_options.extend([name for name in unique_stores if str(name).strip()])
    current_store_search_val = st.session_state.get("storeName_search", "");
    try: current_store_idx = store_names_options.index(current_store_search_val) if current_store_search_val in store_names_options else 0
    except ValueError: current_store_idx = 0
    selected_store_val = st.sidebar.selectbox(f"Search {global_search_cols['storeName']}:", options=store_names_options, index=current_store_idx, key="storeName_global_search_widget_select_v4_3_1", help="Select or type store name.")
    if selected_store_val != st.session_state.get("storeName_search"): st.session_state["storeName_search"] = selected_store_val; st.session_state.show_global_search_dialog = bool(selected_store_val or st.session_state.get("licenseNumber_search", "")); st.rerun()
    st.sidebar.markdown("---"); global_search_active = bool(st.session_state.get("licenseNumber_search", "") or st.session_state.get("storeName_search", ""))
    st.sidebar.subheader("📊 Filters"); filter_caption = "ℹ️ Filters overridden by Global Search." if global_search_active else "Apply filters to dashboard data."; st.sidebar.caption(filter_caption)
    st.sidebar.markdown("##### Quick Date Ranges"); s_col1, s_col2, s_col3 = st.sidebar.columns(3); today_for_shortcuts = date.today()
    if s_col1.button("MTD", key="mtd_button_v4_3_1", use_container_width=True, disabled=global_search_active):
        if not global_search_active: start_mtd = today_for_shortcuts.replace(day=1); st.session_state.date_range = (start_mtd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
    if s_col2.button("YTD", key="ytd_button_v4_3_1", use_container_width=True, disabled=global_search_active):
        if not global_search_active: start_ytd = today_for_shortcuts.replace(month=1, day=1); st.session_state.date_range = (start_ytd, today_for_shortcuts); st.session_state.date_filter_is_active = True; st.rerun()
    if s_col3.button("ALL", key="all_button_v4_3_1", use_container_width=True, disabled=global_search_active):
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
            if col_key == 'status': options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().dropna().unique() if str(val).strip()])
            else: options_for_multiselect = sorted([val for val in df_original[col_key].astype(str).dropna().unique() if str(val).strip()])
        current_selection_for_multiselect = st.session_state.get(f"{col_key}_filter", []); valid_current_selection = [s for s in current_selection_for_multiselect if s in options_for_multiselect]
        new_selection_multiselect = st.sidebar.multiselect(f"Filter by {label_text}:", options=options_for_multiselect, default=valid_current_selection, key=f"{col_key}_category_filter_widget_v4_3_1", disabled=global_search_active or not options_for_multiselect, help=f"Select {label_text}." if options_for_multiselect else f"No {label_text} data.")
        if not global_search_active and new_selection_multiselect != valid_current_selection: st.session_state[f"{col_key}_filter"] = new_selection_multiselect; st.rerun()
        elif global_search_active and st.session_state.get(f"{col_key}_filter") != new_selection_multiselect: st.session_state[f"{col_key}_filter"] = new_selection_multiselect # Allow updating even if global search active, for when it's cleared
    def clear_all_filters_and_search_v4_3_1():
        ds_cleared, de_cleared, _, _ = get_default_date_range(st.session_state.df_original.get('onboarding_date_only')); st.session_state.date_range = (ds_cleared, de_cleared); st.session_state.date_filter_is_active = False
        st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""; st.session_state.show_global_search_dialog = False
        for cat_key in category_filters_map: st.session_state[f"{cat_key}_filter"]=[]
        st.session_state.selected_transcript_key_dialog_global_search = None; st.session_state.selected_transcript_key_filtered_analysis = None
        if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
        if "filtered_analysis_auto_selected_once" in st.session_state: st.session_state.filtered_analysis_auto_selected_once = False
        st.session_state.active_tab = TAB_OVERVIEW
    if st.sidebar.button("🧹 Clear Filters & Search", on_click=clear_all_filters_and_search_v4_3_1, use_container_width=True, key="clear_filters_button_v4_3_1"): st.rerun() # Changed label slightly
    with st.sidebar.expander("ℹ️ Score Breakdown (0-10 pts)", expanded=False):
        st.markdown("""Score (0-10 pts):\n- **Primary (4 pts):** Kit Recv'd (2), Train/Promo Sched. (2).\n- **Secondary (3 pts):** Intro (1), Display Help (1), Promo Link (1).\n- **Bonuses (3 pts):** +1 Positive Sentiment, +1 Expectations Set, +1 Full Checklist Completion.""")
    st.sidebar.markdown("---"); st.sidebar.header("🔄 Data Management");
    if st.sidebar.button("Refresh Data from Source", key="refresh_data_button_v4_3_1", use_container_width=True):
        st.cache_data.clear(); st.session_state.data_loaded = False; st.session_state.last_data_refresh_time = None; st.session_state.df_original = pd.DataFrame()
        clear_all_filters_and_search_v4_3_1(); st.rerun()
    if st.session_state.get('last_data_refresh_time'):
        refresh_time_pst = st.session_state.last_data_refresh_time.astimezone(PST_TIMEZONE); refresh_time_str_display = refresh_time_pst.strftime('%b %d, %Y %I:%M %p PST'); st.sidebar.caption(f"☁️ Last data sync: {refresh_time_str_display}")
        if not st.session_state.get('data_loaded', False) and st.session_state.df_original.empty : st.sidebar.caption("⚠️ No data loaded in last sync.")
    else: st.sidebar.caption("⏳ Data not yet loaded.")
    st.sidebar.markdown("---");
    st.sidebar.caption(f"Onboarding Dashboard v4.3.1\n\n© {datetime.now().year} Nexus Workflow")

    # --- Main Content Area (from original app) ---
    st.title("🚀 Onboarding Analytics Dashboard") # Changed icon from original for consistency
    if not st.session_state.data_loaded and df_original.empty:
        if st.session_state.get('last_data_refresh_time'): st.markdown("<div class='no-data-message'>🚧 No data loaded. Check Google Sheet connection/permissions/data. Try manual refresh. 🚧</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='no-data-message'>⏳ Initializing data... If persists, check configurations. ⏳</div>", unsafe_allow_html=True)
        st.stop() # Stop if no data after initial load attempt
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

    df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame()
    if not df_original.empty:
        if global_search_active:
            df_temp_gs = df_original.copy(); ln_term = st.session_state.get("licenseNumber_search", "").strip().lower(); sn_term = st.session_state.get("storeName_search", "").strip()
            if ln_term and "licenseNumber" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['licenseNumber'].astype(str).str.lower().str.contains(ln_term, na=False)]
            if sn_term and "storeName" in df_temp_gs.columns: df_temp_gs = df_temp_gs[df_temp_gs['storeName'] == sn_term] # Exact match for selectbox
            df_global_search_results_display = df_temp_gs.copy(); df_filtered = df_global_search_results_display.copy() # For consistency, df_filtered also holds search results when active
        else:
            df_temp_filters = df_original.copy();
            if 'onboarding_date_only' in df_temp_filters.columns and df_temp_filters['onboarding_date_only'].notna().any():
                date_objects_for_filter = pd.to_datetime(df_temp_filters['onboarding_date_only'], errors='coerce').dt.date; valid_dates_mask = date_objects_for_filter.notna(); date_filter_condition = pd.Series([False] * len(df_temp_filters), index=df_temp_filters.index)
                if valid_dates_mask.any(): date_filter_condition[valid_dates_mask] = (date_objects_for_filter[valid_dates_mask] >= start_dt_filter) & (date_objects_for_filter[valid_dates_mask] <= end_dt_filter)
                df_temp_filters = df_temp_filters[date_filter_condition]
            for col_name_cat, _ in category_filters_map.items():
                selected_values_cat = st.session_state.get(f"{col_name_cat}_filter", [])
                if selected_values_cat and col_name_cat in df_temp_filters.columns:
                    if col_name_cat == 'status': df_temp_filters = df_temp_filters[df_temp_filters[col_name_cat].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().isin(selected_values_cat)]
                    else: df_temp_filters = df_temp_filters[df_temp_filters[col_name_cat].astype(str).isin(selected_values_cat)]
            df_filtered = df_temp_filters.copy()
    else: df_filtered = pd.DataFrame(); df_global_search_results_display = pd.DataFrame() # Ensure they are empty DFs

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

    def get_cell_style_class(column_name, value):
        val_str = str(value).strip().lower()
        if pd.isna(value) or val_str == "" or val_str == "na": return "cell-req-na"
        if column_name == 'score':
            try: score_num = float(value)
            except: return ""
            if score_num >= 8: return "cell-score-good"
            elif score_num >= 4: return "cell-score-medium"
            else: return "cell-score-bad"
        elif column_name == 'clientSentiment':
            if val_str == 'positive': return "cell-sentiment-positive"
            elif val_str == 'neutral': return "cell-sentiment-neutral"
            elif val_str == 'negative': return "cell-sentiment-negative"
        elif column_name == 'days_to_confirmation':
            try: days_num = float(value)
            except: return ""
            if days_num <= 7: return "cell-days-good"
            elif days_num <= 14: return "cell-days-medium"
            else: return "cell-days-bad"
        elif column_name in ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS:
            if val_str in ['true', '1', 'yes', 'x', 'completed', 'done']: return "cell-req-met"
            elif val_str in ['false', '0', 'no']: return "cell-req-not-met"
        elif column_name == 'status': return "cell-status" # Generic class for status, actual emoji handled elsewhere
        return ""

    def display_html_table_and_details(df_to_display, context_key_prefix=""):
        if df_to_display is None or df_to_display.empty:
            context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','').strip();
            if not df_original.empty: st.markdown(f"<div class='no-data-message'>📊 No data for {context_name_display}. Try different filters! 📊</div>", unsafe_allow_html=True)
            return
        df_display_copy = df_to_display.copy().reset_index(drop=True)
        def map_status_to_emoji_html(status_val):
            status_str = str(status_val).strip().lower();
            if 'confirmed' in status_str : return "✅ Confirmed"; # More robust check
            if 'pending' in status_str: return "⏳ Pending";
            if 'failed' in status_str: return "❌ Failed";
            return status_val # Return original if no match
        if 'status' in df_display_copy.columns: df_display_copy['status_styled'] = df_display_copy['status'].apply(map_status_to_emoji_html)
        else: df_display_copy['status_styled'] = ""
        preferred_cols_order = ['onboardingDate', 'repName', 'storeName', 'licenseNumber', 'status_styled', 'score', 'clientSentiment', 'days_to_confirmation', 'contactName', 'contactNumber', 'confirmedNumber', 'deliveryDate', 'confirmationTimestamp']
        preferred_cols_order.extend(ORDERED_TRANSCRIPT_VIEW_REQUIREMENTS)
        cols_present_in_df = df_display_copy.columns.tolist(); final_display_cols = [col for col in preferred_cols_order if col in cols_present_in_df]
        excluded_suffixes = ('_dt', '_utc', '_str_original', '_date_only') # Removed _styled from here
        other_existing_cols_for_display = [col for col in cols_present_in_df if col not in final_display_cols and not col.endswith(excluded_suffixes) and col not in ['fullTranscript', 'summary', 'status', 'onboardingWelcome']]
        final_display_cols.extend(other_existing_cols_for_display); final_display_cols = list(dict.fromkeys(final_display_cols)) # Remove duplicates while preserving order
        if not final_display_cols or df_display_copy[final_display_cols].empty:
            context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','').strip(); st.markdown(f"<div class='no-data-message'>📋 No columns/data for {context_name_display}. 📋</div>", unsafe_allow_html=True); return
        html_table = ["<div class='custom-table-container'><table class='custom-styled-table'><thead><tr>"]
        column_display_names = {'status_styled': 'Status', 'onboardingDate': 'Onboarding Date', 'repName': 'Rep Name', 'storeName': 'Store Name', 'licenseNumber': 'License No.', 'clientSentiment': 'Sentiment', 'days_to_confirmation': 'Days to Confirm', 'contactName': 'Contact Name', 'contactNumber': 'Contact No.', 'confirmedNumber': 'Confirmed No.', 'deliveryDate': 'Delivery Date', 'confirmationTimestamp': 'Confirmation Time'}
        for req_key, details in KEY_REQUIREMENT_DETAILS.items(): column_display_names[req_key] = details.get("chart_label", req_key)
        for col_id in final_display_cols: display_name = column_display_names.get(col_id, col_id.replace("_", " ").title()); html_table.append(f"<th>{display_name}</th>")
        html_table.append("</tr></thead><tbody>")
        for index, row in df_display_copy.iterrows():
            html_table.append("<tr>")
            for col_id in final_display_cols:
                original_col_for_styling = 'status' if col_id == 'status_styled' else col_id; cell_value = row.get(col_id, "")
                style_class = get_cell_style_class(original_col_for_styling, row.get(original_col_for_styling, cell_value))
                if col_id == 'score' and pd.notna(cell_value): cell_value = f"{cell_value:.1f}"
                elif col_id == 'days_to_confirmation' and pd.notna(cell_value): cell_value = f"{cell_value:.0f}"
                html_table.append(f"<td class='{style_class}'>{cell_value}</td>")
            html_table.append("</tr>")
        html_table.append("</tbody></table></div>"); st.markdown("".join(html_table), unsafe_allow_html=True)
        st.markdown("---"); st.subheader("📄 View Full Record Details")
        transcript_session_key_local = f"selected_transcript_key_{context_key_prefix}";
        if transcript_session_key_local not in st.session_state: st.session_state[transcript_session_key_local] = None
        auto_selected_this_run = False
        if len(df_display_copy) == 1:
            first_row_details = df_display_copy.iloc[0]; auto_select_option_key = f"Idx 0: {first_row_details.get('storeName', 'N/A')} ({first_row_details.get('onboardingDate', 'N/A')})"
            if st.session_state[transcript_session_key_local] != auto_select_option_key: st.session_state[transcript_session_key_local] = auto_select_option_key; auto_selected_this_run = True
        auto_selected_once_key = f"{context_key_prefix}_auto_selected_once"
        if auto_selected_this_run and not st.session_state.get(auto_selected_once_key, False): st.session_state[auto_selected_once_key] = True; st.rerun()
        elif len(df_display_copy) != 1: st.session_state[auto_selected_once_key] = False # Reset if not single row
        if 'fullTranscript' in df_display_copy.columns or 'summary' in df_display_copy.columns:
            transcript_options_map = {f"Idx {idx}: {row.get('storeName', 'N/A')} ({row.get('onboardingDate', 'N/A')})": idx for idx, row in df_display_copy.iterrows()}
            if transcript_options_map:
                options_list_for_select = [None] + list(transcript_options_map.keys()); current_selection_for_select = st.session_state[transcript_session_key_local]
                try: current_index_for_select = options_list_for_select.index(current_selection_for_select) if current_selection_for_select in options_list_for_select else 0
                except ValueError: current_index_for_select = 0; st.session_state[transcript_session_key_local] = None
                selected_key_from_display = st.selectbox("Select record to view details:", options=options_list_for_select, index=current_index_for_select, format_func=lambda x: "📄 Choose an entry..." if x is None else x, key=f"transcript_selector_{context_key_prefix}_widget_v4_3_1")
                if selected_key_from_display != st.session_state[transcript_session_key_local]: st.session_state[transcript_session_key_local] = selected_key_from_display; st.session_state[auto_selected_once_key] = False; st.rerun()
                if st.session_state[transcript_session_key_local] and st.session_state[transcript_session_key_local] in transcript_options_map: # Check if key is valid
                    selected_original_idx = transcript_options_map[st.session_state[transcript_session_key_local]]; selected_row_details = df_display_copy.loc[selected_original_idx]
                    st.markdown("<h5>📋 Onboarding Summary & Checks:</h5>", unsafe_allow_html=True); summary_html_parts_list = ["<div class='transcript-summary-grid'>"]
                    summary_items_to_display = {"Store": selected_row_details.get('storeName', "N/A"), "Rep": selected_row_details.get('repName', "N/A"), "Score": f"{selected_row_details.get('score', 'N/A'):.1f}" if pd.notna(selected_row_details.get('score')) else "N/A", "Status": selected_row_details.get('status_styled', "N/A"), "Sentiment": selected_row_details.get('clientSentiment', "N/A")}
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
            else: context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','').strip(); st.markdown(f"<div class='no-data-message'>📋 No entries in table from {context_name_display} to select details. 📋</div>", unsafe_allow_html=True)
        else: context_name_display = context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','').strip(); st.markdown(f"<div class='no-data-message'>📜 Necessary columns ('fullTranscript'/'summary') missing for details viewer in {context_name_display}. 📜</div>", unsafe_allow_html=True)
        st.markdown("---"); csv_data_to_download = convert_df_to_csv(df_display_copy[final_display_cols]); download_label = f"📥 Download These {context_key_prefix.replace('_', ' ').title().replace('Tab','').replace('Dialog','').strip()} Results"
        st.download_button(label=download_label, data=csv_data_to_download, file_name=f'{context_key_prefix}_results_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', mime='text/csv', use_container_width=True, key=f"download_csv_{context_key_prefix}_button_v4_3_1")

    # --- Global Search Dialog (from original app) ---
    if st.session_state.get('show_global_search_dialog', False) and global_search_active:
        @st.dialog("🔍 Global Search Results", width="large") # Changed title slightly
        def show_global_search_dialog_content():
            st.markdown("##### Records matching global search criteria:");
            if not df_global_search_results_display.empty: display_html_table_and_details(df_global_search_results_display, context_key_prefix="dialog_global_search")
            else: st.info("ℹ️ No results for global search. Try broadening terms.")
            if st.button("Close & Clear Search", key="close_gs_dialog_clear_button_v4_3_1"):
                st.session_state.show_global_search_dialog = False; st.session_state.licenseNumber_search = ""; st.session_state.storeName_search = ""
                if 'selected_transcript_key_dialog_global_search' in st.session_state: st.session_state.selected_transcript_key_dialog_global_search = None
                if "dialog_global_search_auto_selected_once" in st.session_state: st.session_state.dialog_global_search_auto_selected_once = False
                st.rerun()
        show_global_search_dialog_content()

    # --- Tab Content (from original app) ---
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
            display_html_table_and_details(df_filtered, context_key_prefix="filtered_analysis")
            st.header("🎨 Key Visualizations (Filtered Data)")
            if not df_filtered.empty:
                chart_cols_1, chart_cols_2 = st.columns(2)
                with chart_cols_1:
                    if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                        status_counts_df = df_filtered['status'].astype(str).str.replace(r"✅|⏳|❌", "", regex=True).str.strip().value_counts().reset_index(); status_counts_df.columns = ['status', 'count']
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
                    if date_span_days > 90: resample_freq = 'W-MON'; # Weekly
                    if date_span_days > 730: resample_freq = 'ME' # Monthly End
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

    # --- Footer (from original app) ---
    st.markdown("---"); st.markdown(f"<div class='footer'>Onboarding Analytics Dashboard v4.3.1 © {datetime.now().year} Nexus Workflow. All Rights Reserved.</div>", unsafe_allow_html=True)
