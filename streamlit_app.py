import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
import time
import numpy as np
import matplotlib # Required for pandas styler background_gradient

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard v2.2", # Incremented version
    page_icon="🚀",
    layout="wide"
)

# --- Custom Styling (Gold Accents) ---
GOLD_ACCENT_COLOR = "#FFD700" # Gold
PRIMARY_TEXT_COLOR = "#FFFFFF" # White
SECONDARY_TEXT_COLOR = "#B0B0B0" # Light Gray
BACKGROUND_COLOR = "#0E1117" # Streamlit Dark Default
PLOT_BG_COLOR = "rgba(0,0,0,0)" # Transparent for plots

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
</style>
""", unsafe_allow_html=True)

# --- Application Access Control ---
def check_password():
    """Returns true if password is correct or if secrets are not set (allowing local dev without password)"""
    # Attempt to get password and hint from secrets
    app_password = st.secrets.get("APP_ACCESS_KEY")
    app_hint = st.secrets.get("APP_ACCESS_HINT", "Hint not available.")

    # If APP_ACCESS_KEY is not set in secrets, bypass password for easier local development.
    # Ensure it IS set for deployed environments.
    if app_password is None:
        st.sidebar.warning("APP_ACCESS_KEY not set in secrets. Bypassing password for local development.")
        return True

    if "password_entered" not in st.session_state:
        st.session_state.password_entered = False

    if st.session_state.password_entered:
        return True

    with st.form("password_form"):
        st.markdown("### 🔐 Access Required")
        password_attempt = st.text_input("Enter Access Key:", type="password", help=app_hint)
        submitted = st.form_submit_button("Submit")

        if submitted:
            if password_attempt == app_password:
                st.session_state.password_entered = True
                st.rerun() # Rerun to clear the form and show the app
            else:
                st.error("Incorrect Access Key. Please try again.")
                return False
    return False

if not check_password():
    st.stop() # Do not render the rest of the app if password is not correct

# --- Google Sheets Authentication and Data Loading ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread(secrets_dict=None):
    try:
        gcp_secrets = st.secrets.get("gcp_service_account")
        if not gcp_secrets:
            st.error("GCP service account secrets not found. Please configure them in Streamlit secrets.")
            return None
        creds = Credentials.from_service_account_info(gcp_secrets, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
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
       not series.isin(['', 'None', 'nan', 'NaT', None]).all():
        for fmt in common_formats:
            temp_dates = pd.to_datetime(series, format=fmt, errors='coerce')
            if temp_dates.notnull().sum() > dates.notnull().sum():
                dates = temp_dates
            if dates.notnull().all():
                break
    return dates


@st.cache_data(ttl=600)
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    if not sheet_url_or_name or not worksheet_name:
        st.error("Data source (Google Sheet URL/Name or Worksheet Name) is not configured in Streamlit Secrets.")
        return pd.DataFrame()

    gc = authenticate_gspread() # Removed secrets_dict argument as it's fetched inside
    if gc is None: return pd.DataFrame()

    try:
        if "docs.google.com" in sheet_url_or_name or "spreadsheets.google.com" in sheet_url_or_name:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        else:
            spreadsheet = gc.open(sheet_url_or_name) # Assumes it's a sheet title/name
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1)
        df = pd.DataFrame(data)
        st.sidebar.success(f"Loaded {len(df)} records.")
        if df.empty:
            st.warning("No data records found in the Google Sheet.")
            return pd.DataFrame()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet not found. Ensure the configured Google Sheet identifier ('{sheet_url_or_name}') is correct and the service account has access.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet. Please check the worksheet name.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading from Google Sheet: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    date_columns_to_parse = {
        'onboardingDate': 'onboardingDate_dt',
        'deliveryDate': 'deliveryDate_dt',
        'confirmationTimestamp': 'confirmationTimestamp_dt'
    }

    for original_col, new_dt_col in date_columns_to_parse.items():
        if original_col in df.columns:
            cleaned_series = df[original_col].astype(str).str.replace('\n', '', regex=False).str.strip()
            parsed_dates = robust_to_datetime(cleaned_series)
            df[new_dt_col] = parsed_dates
            if parsed_dates.isnull().all() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                 st.warning(f"Could not parse any dates in '{original_col}'. All values are NaT.")
            elif parsed_dates.isnull().any() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                 st.warning(f"Some dates in '{original_col}' could not be parsed and are NaT.")
            if original_col == 'onboardingDate':
                 df['onboarding_date_only'] = df[new_dt_col].dt.date
                 if df['onboarding_date_only'].isnull().all() and not cleaned_series.isin(['', 'None', 'nan', 'NaT', None]).all():
                    st.warning(f"Could not parse '{original_col}' for any rows to extract date part.")
        else:
            st.warning(f"Date column '{original_col}' not found.")
            df[new_dt_col] = pd.NaT
            if original_col == 'onboardingDate':
                df['onboarding_date_only'] = pd.NaT
    
    if 'deliveryDate_dt' in df.columns and 'confirmationTimestamp_dt' in df.columns:
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')

        def convert_series_to_utc(dt_series):
            if pd.api.types.is_datetime64_any_dtype(dt_series):
                if dt_series.notna().any():
                    if dt_series.dt.tz is None:
                        return dt_series.dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
                    else:
                        return dt_series.dt.tz_convert('UTC')
            return dt_series

        df['deliveryDate_dt_utc'] = convert_series_to_utc(df['deliveryDate_dt'])
        df['confirmationTimestamp_dt_utc'] = convert_series_to_utc(df['confirmationTimestamp_dt'])
        
        valid_dates_mask = df['deliveryDate_dt_utc'].notna() & df['confirmationTimestamp_dt_utc'].notna()
        df['days_to_confirmation'] = pd.NA
        
        if valid_dates_mask.any():
            time_difference = (df.loc[valid_dates_mask, 'confirmationTimestamp_dt_utc'] - 
                               df.loc[valid_dates_mask, 'deliveryDate_dt_utc'])
            df.loc[valid_dates_mask, 'days_to_confirmation'] = time_difference.dt.days
        
        if df['days_to_confirmation'].isnull().all() and valid_dates_mask.any():
            st.warning("Failed to calculate 'Days to Confirmation'.")
    else:
        st.warning("'deliveryDate' or 'confirmationTimestamp' column missing for 'Days to Confirmation'.")
        df['days_to_confirmation'] = pd.NA

    if 'status' not in df.columns: st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found.")
        df['score'] = pd.NA
            
    return df

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def calculate_metrics(df_input, period_name=""):
    if df_input.empty:
        return 0, 0.0, pd.NA, pd.NA

    total_onboardings = len(df_input)
    success_rate = 0.0
    avg_score = pd.NA
    avg_days_to_confirm = pd.NA

    if 'status' in df_input.columns:
        successful_onboardings = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
        if total_onboardings > 0:
            success_rate = (successful_onboardings / total_onboardings) * 100
    
    if 'score' in df_input.columns and df_input['score'].notna().any():
        avg_score = pd.to_numeric(df_input['score'], errors='coerce').mean()
    
    if 'days_to_confirmation' in df_input.columns and df_input['days_to_confirmation'].notna().any():
        numeric_days = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce')
        if numeric_days.notna().any():
             avg_days_to_confirm = numeric_days.mean()
    return total_onboardings, success_rate, avg_score, avg_days_to_confirm

def get_default_date_range(df_date_column_series):
    today = date.today()
    default_start_date = today.replace(day=1)
    default_end_date = today
    min_data_date, max_data_date = None, None

    if df_date_column_series is not None and not df_date_column_series.empty:
        date_objects = pd.to_datetime(df_date_column_series, errors='coerce').dt.date
        valid_dates = date_objects.dropna()
        if not valid_dates.empty:
            min_data_date = valid_dates.min()
            max_data_date = valid_dates.max()
            default_start_date = max(default_start_date, min_data_date)
            default_end_date = min(default_end_date, max_data_date)
            if default_start_date > default_end_date : 
                default_start_date = min_data_date 
                default_end_date = max_data_date
    return default_start_date, default_end_date, min_data_date, max_data_date

# --- Initialize Session State & Load Secrets ---
GOOGLE_SHEET_URL_OR_NAME = st.secrets.get("GOOGLE_SHEET_URL_OR_NAME")
GOOGLE_WORKSHEET_NAME = st.secrets.get("GOOGLE_WORKSHEET_NAME")

if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
if 'date_range_filter' not in st.session_state: st.session_state.date_range_filter = (date.today().replace(day=1), date.today())
if 'repName_filter' not in st.session_state: st.session_state.repName_filter = []
if 'status_filter' not in st.session_state: st.session_state.status_filter = []
if 'clientSentiment_filter' not in st.session_state: st.session_state.clientSentiment_filter = []
if 'licenseNumber_search' not in st.session_state: st.session_state.licenseNumber_search = ""
if 'storeName_search' not in st.session_state: st.session_state.storeName_search = ""

# --- Data Loading Trigger ---
if not st.session_state.data_loaded_successfully:
    if not GOOGLE_SHEET_URL_OR_NAME or not GOOGLE_WORKSHEET_NAME:
        st.error("Application is not configured. Please set GOOGLE_SHEET_URL_OR_NAME and GOOGLE_WORKSHEET_NAME in Streamlit secrets.")
        st.stop()
    else:
        with st.spinner("Connecting to Google Sheet and processing data..."):
            df = load_data_from_google_sheet(GOOGLE_SHEET_URL_OR_NAME, GOOGLE_WORKSHEET_NAME)
            if not df.empty:
                st.session_state.df_original = df
                st.session_state.data_loaded_successfully = True
                ds, de, _, _ = get_default_date_range(df['onboarding_date_only'] if 'onboarding_date_only' in df else None)
                st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
            else:
                st.session_state.df_original = pd.DataFrame()
                st.session_state.data_loaded_successfully = False

df_original = st.session_state.df_original

# --- Main Application UI Starts Here ---
st.title("🚀 Onboarding Performance Dashboard v2.2 🚀")

if not st.session_state.data_loaded_successfully or df_original.empty:
    if not GOOGLE_SHEET_URL_OR_NAME or not GOOGLE_WORKSHEET_NAME:
        st.error("Data source (Google Sheet URL/Name and Worksheet Name) is not configured in Streamlit Secrets. The app cannot load data.")
    else:
        st.error("Failed to load data or data source is empty. Check Google Sheet permissions/content, ensure secrets are correct. Try refreshing.")
    
    if st.sidebar.button("🔄 Force Refresh Data & Reload App"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()
    st.stop()

# --- Sidebar ---
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False
    st.rerun()

st.sidebar.header("🔍 Filters")

onboarding_dates_for_filter = df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original.columns else None
def_start, def_end, min_dt_data, max_dt_data = get_default_date_range(onboarding_dates_for_filter)

if 'date_range_filter' not in st.session_state or \
   (st.session_state.date_range_filter[0] is None and def_start is not None) or \
   (st.session_state.date_range_filter[0] != def_start or st.session_state.date_range_filter[1] != def_end):
    st.session_state.date_range_filter = (def_start, def_end)

if min_dt_data and max_dt_data:
    selected_date_range_widget = st.sidebar.date_input(
        "Onboarding Date Range:",
        value=st.session_state.date_range_filter,
        min_value=min_dt_data,
        max_value=max_dt_data,
        key="date_range_selector_widget" 
    )
    if selected_date_range_widget != st.session_state.date_range_filter:
        st.session_state.date_range_filter = selected_date_range_widget
else:
    st.sidebar.warning("Onboarding date data not available for date range filter.")
start_date_filter, end_date_filter = st.session_state.date_range_filter if isinstance(st.session_state.date_range_filter, tuple) and len(st.session_state.date_range_filter) == 2 else (None, None)

expected_search_cols = {"licenseNumber": "License Number", "storeName": "Store Name"}
actual_search_cols_present = {k: v for k, v in expected_search_cols.items() if k in df_original.columns}

for col_key, display_name in actual_search_cols_present.items():
    if f"{col_key}_search" not in st.session_state:
        st.session_state[f"{col_key}_search"] = ""
    st.session_state[f"{col_key}_search"] = st.sidebar.text_input(
        f"Search by {display_name}:", value=st.session_state[f"{col_key}_search"], key=f"{col_key}_search_widget"
    )

categorical_filter_cols = {'repName': 'Rep(s)', 'status': 'Status(es)', 'clientSentiment': 'Client Sentiment(s)'}
for col_name, display_label in categorical_filter_cols.items():
    if col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = sorted(df_original[col_name].astype(str).dropna().unique())
        if f"{col_name}_filter" not in st.session_state:
            st.session_state[f"{col_name}_filter"] = []
        st.session_state[f"{col_name}_filter"] = st.sidebar.multiselect(
            f"Select {display_label}:", options=unique_values, default=st.session_state[f"{col_name}_filter"], key=f"{col_name}_filter_widget"
        )
    else:
        st.sidebar.text(f"{display_label} data not available for filtering.")

def clear_all_filters_callback():
    ds, de, _, _ = get_default_date_range(df_original['onboarding_date_only'] if 'onboarding_date_only' in df_original else None)
    st.session_state.date_range_filter = (ds, de) if ds and de else (date.today().replace(day=1), date.today())
    if "date_range_selector_widget" in st.session_state:
        st.session_state.date_range_selector_widget = st.session_state.date_range_filter
    for col_key_search in actual_search_cols_present:
        st.session_state[f"{col_key_search}_search"] = ""
        if f"{col_key_search}_search_widget" in st.session_state:
             st.session_state[f"{col_key_search}_search_widget"] = ""
    for col_name_cat in categorical_filter_cols:
        st.session_state[f"{col_name_cat}_filter"] = []
        if f"{col_name_cat}_filter_widget" in st.session_state:
            st.session_state[f"{col_name_cat}_filter_widget"] = []

if st.sidebar.button("🧹 Clear All Filters", on_click=clear_all_filters_callback, use_container_width=True):
    st.rerun()

# --- Filtering Logic ---
df_filtered = df_original.copy()
if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
    date_objects_for_filtering = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').dt.date
    df_filtered = df_filtered[
        date_objects_for_filtering.notna() &
        (date_objects_for_filtering >= start_date_filter) &
        (date_objects_for_filtering <= end_date_filter)
    ]
for col_key, display_name in actual_search_cols_present.items():
    search_term = st.session_state.get(f"{col_key}_search", "")
    if search_term:
        df_filtered = df_filtered[df_filtered[col_key].astype(str).str.contains(search_term, case=False, na=False)]
for col_name, display_label in categorical_filter_cols.items():
    selected_values = st.session_state.get(f"{col_name}_filter", [])
    if selected_values:
        df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(selected_values)]

# --- Plotly Layout Configuration ---
plotly_layout_updates = {
    "plot_bgcolor": PLOT_BG_COLOR, "paper_bgcolor": PLOT_BG_COLOR,
    "font_color": PRIMARY_TEXT_COLOR, "title_font_color": GOLD_ACCENT_COLOR,
    "legend_font_color": PRIMARY_TEXT_COLOR, "title_x": 0.5
}

# --- MTD Metrics Calculation ---
today_date = date.today()
current_month_start_date = today_date.replace(day=1)
prev_month_end_date = current_month_start_date - timedelta(days=1)
prev_month_start_date = prev_month_end_date.replace(day=1)
df_mtd_calc = pd.DataFrame()
df_prev_mtd_calc = pd.DataFrame()

if 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    original_date_objects = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dt.date
    valid_original_dates_mask = original_date_objects.notna()
    if valid_original_dates_mask.any():
        df_mtd_calc = df_original[
            valid_original_dates_mask &
            (original_date_objects >= current_month_start_date) &
            (original_date_objects <= today_date)
        ]
        df_prev_mtd_calc = df_original[
            valid_original_dates_mask &
            (original_date_objects >= prev_month_start_date) &
            (original_date_objects <= prev_month_end_date)
        ]
total_mtd, success_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd_calc)
total_prev_mtd, _, _, _ = calculate_metrics(df_prev_mtd_calc)
mtd_onboarding_delta_val = total_mtd - total_prev_mtd if pd.notna(total_mtd) and pd.notna(total_prev_mtd) else None

# --- Main Content Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Detailed Analysis & Data", "💡 Trends & Distributions"])

with tab1:
    st.header("📈 Month-to-Date (MTD) Overview")
    mtd_cols_display = st.columns(4)
    mtd_cols_display[0].metric(
        label="Total Onboardings MTD", value=total_mtd, 
        delta=f"{mtd_onboarding_delta_val:+}" if mtd_onboarding_delta_val is not None else "N/A vs Prev Month",
        delta_color="normal" if mtd_onboarding_delta_val is None or mtd_onboarding_delta_val == 0 else ("inverse" if mtd_onboarding_delta_val < 0 else "normal")
    )
    mtd_cols_display[1].metric(label="Success Rate MTD", value=f"{success_mtd:.1f}%" if pd.notna(success_mtd) else "N/A")
    mtd_cols_display[2].metric(label="Avg Score MTD", value=f"{score_mtd:.2f}" if pd.notna(score_mtd) else "N/A")
    mtd_cols_display[3].metric(label="Avg Days to Confirm MTD", value=f"{days_mtd:.1f}" if pd.notna(days_mtd) else "N/A")

    st.header("📊 Filtered Data Overview")
    if not df_filtered.empty:
        total_filtered_val, success_filtered_val, score_filtered_val, days_filtered_val = calculate_metrics(df_filtered)
        filtered_cols_display = st.columns(4)
        filtered_cols_display[0].metric(label="Total Filtered Onboardings", value=total_filtered_val)
        filtered_cols_display[1].metric(label="Filtered Success Rate", value=f"{success_filtered_val:.1f}%" if pd.notna(success_filtered_val) else "N/A")
        filtered_cols_display[2].metric(label="Filtered Average Score", value=f"{score_filtered_val:.2f}" if pd.notna(score_filtered_val) else "N/A")
        filtered_cols_display[3].metric(label="Filtered Avg Days to Confirm", value=f"{days_filtered_val:.1f}" if pd.notna(days_filtered_val) else "N/A")
    else:
        st.info("No data matches the current filter criteria to display in Overview.")

with tab2:
    st.header("📋 Filtered Onboarding Data Table")
    if not df_filtered.empty:
        def style_dataframe_conditionally(df_to_style):
            styled_df = df_to_style.style
            if 'score' in df_to_style.columns and df_to_style['score'].notna().any():
                scores_numeric = pd.to_numeric(df_to_style['score'], errors='coerce')
                if scores_numeric.notna().any():
                    styled_df = styled_df.background_gradient(subset=['score'], cmap='RdYlGn', low=0.3, high=0.7, gmap=scores_numeric.fillna(scores_numeric.min() -1 ))
            if 'days_to_confirmation' in df_to_style.columns and df_to_style['days_to_confirmation'].notna().any():
                days_numeric = pd.to_numeric(df_to_style['days_to_confirmation'], errors='coerce')
                if days_numeric.notna().any():
                     styled_df = styled_df.background_gradient(subset=['days_to_confirmation'], cmap='RdYlGn_r', gmap=days_numeric.fillna(days_numeric.min() -1))
            return styled_df

        df_display_table = df_filtered.copy()
        if 'deliveryDate_dt' in df_display_table.columns and df_display_table['deliveryDate_dt'].notna().any():
            df_display_table_sorted = df_display_table.sort_values(by='deliveryDate_dt', ascending=True, na_position='last')
        else:
            df_display_table_sorted = df_display_table
        cols_for_display = [col for col in df_display_table_sorted.columns if not col.endswith('_utc') and not col.endswith('_str_original')]
        st.dataframe(style_dataframe_conditionally(df_display_table_sorted[cols_for_display].reset_index(drop=True)), use_container_width=True)
        csv_download_data = convert_df_to_csv(df_filtered)
        st.download_button(label="📥 Download Filtered Data as CSV", data=csv_download_data, file_name='filtered_onboarding_data.csv', mime='text/csv', use_container_width=True)
    elif not df_original.empty:
        st.info("No data matches current filter criteria for table display.")

    st.header("📊 Key Visuals (Based on Filtered Data)")
    if not df_filtered.empty:
        viz_cols_in_detail_tab = st.columns(2)
        with viz_cols_in_detail_tab[0]:
            if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
                st.subheader("Onboarding Status")
                status_counts_chart = df_filtered['status'].value_counts().reset_index()
                fig_status_chart = px.bar(status_counts_chart, x='status', y='count', color='status', template="plotly_dark")
                fig_status_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_status_chart, use_container_width=True)
            if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
                st.subheader("Onboardings by Rep")
                rep_counts_chart = df_filtered['repName'].value_counts().reset_index()
                fig_rep_chart = px.bar(rep_counts_chart, x='repName', y='count', color='repName', template="plotly_dark")
                fig_rep_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_rep_chart, use_container_width=True)
        with viz_cols_in_detail_tab[1]:
            if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
                st.subheader("Client Sentiment")
                sentiment_counts_chart = df_filtered['clientSentiment'].value_counts().reset_index()
                sentiment_color_map_def = {
                    str(s).lower(): (GOLD_ACCENT_COLOR if 'neutral' in str(s).lower() else ('#2ca02c' if 'positive' in str(s).lower() else ('#d62728' if 'negative' in str(s).lower() else None)))
                    for s in sentiment_counts_chart['clientSentiment'].unique()
                }
                fig_sentiment_chart = px.pie(sentiment_counts_chart, names='clientSentiment', values='count', hole=0.4, template="plotly_dark", color='clientSentiment', color_discrete_map=sentiment_color_map_def)
                fig_sentiment_chart.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_sentiment_chart, use_container_width=True)

            checklist_item_cols = ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 'providePromoCreditLink']
            actual_checklist_cols = [col for col in checklist_item_cols if col in df_filtered.columns]
            processed_checklist_cols_data = []
            for b_col in actual_checklist_cols:
                map_to_bool_strict = {'true': True, 'false': False, 'yes': True, 'no': False, '1':True, '0':False, 1:True, 0:False, '':pd.NA, 'nan':pd.NA, None:pd.NA}
                bool_series_strict = df_filtered[b_col].astype(str).str.lower().map(map_to_bool_strict).astype('boolean')
                if bool_series_strict.notna().any():
                    true_count = bool_series_strict.sum()
                    total_valid_responses = bool_series_strict.notna().sum()
                    if total_valid_responses > 0:
                        item_display_name = b_col.replace("onboarding", "").replace("provide", "Provided ").replace("confirm", "Confirmed ")
                        item_display_name = ''.join([' ' + char if char.isupper() else char for char in item_display_name]).strip().title()
                        processed_checklist_cols_data.append({"Checklist Item": item_display_name, "Completion (%)": (true_count / total_valid_responses) * 100})
            if processed_checklist_cols_data:
                st.subheader("Checklist Item Completion")
                completion_df_chart = pd.DataFrame(processed_checklist_cols_data)
                fig_checklist_chart = px.bar(completion_df_chart, x="Completion (%)", y="Checklist Item", orientation='h', template="plotly_dark", color_discrete_sequence=[GOLD_ACCENT_COLOR])
                fig_checklist_chart.update_layout(plotly_layout_updates, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_checklist_chart, use_container_width=True)
    else:
        st.info("No data matches current filters to display detailed visuals.")

with tab3:
    st.header("💡 Trends & Distributions (Based on Filtered Data)")
    if not df_filtered.empty:
        if 'onboarding_date_only' in df_filtered.columns and df_filtered['onboarding_date_only'].notna().any():
            st.subheader("Total Onboardings Over Time")
            df_trend_chart = df_filtered.copy()
            df_trend_chart['onboarding_date_only'] = pd.to_datetime(df_trend_chart['onboarding_date_only'], errors='coerce')
            df_trend_chart = df_trend_chart.dropna(subset=['onboarding_date_only'])
            if not df_trend_chart.empty:
                date_span_days_trend = (df_trend_chart['onboarding_date_only'].max() - df_trend_chart['onboarding_date_only'].min()).days
                if date_span_days_trend <= 62 : freq_resample = 'D'
                elif date_span_days_trend <= 365 * 1.5 : freq_resample = 'W-MON'
                else: freq_resample = 'ME'
                onboardings_over_time_data = df_trend_chart.set_index('onboarding_date_only').resample(freq_resample).size().reset_index(name='count')
                if not onboardings_over_time_data.empty:
                    fig_trend_line = px.line(onboardings_over_time_data, x='onboarding_date_only', y='count', markers=True, template="plotly_dark", labels={'onboarding_date_only': 'Date', 'count': 'Number of Onboardings'})
                    fig_trend_line.update_layout(plotly_layout_updates, title_text="Onboardings Over Filtered Period")
                    st.plotly_chart(fig_trend_line, use_container_width=True)
                else: 
                    st.info("Not enough data points to plot onboarding trend.")
            else: 
                st.info("No valid date data for onboarding trend chart.")
        if 'days_to_confirmation' in df_filtered.columns and df_filtered['days_to_confirmation'].notna().any():
            st.subheader("Distribution of Days to Confirmation")
            days_data_for_hist = pd.to_numeric(df_filtered['days_to_confirmation'], errors='coerce').dropna()
            if not days_data_for_hist.empty:
                nbins_hist = max(10, min(50, int(len(days_data_for_hist)/5))) if len(days_data_for_hist) > 20 else 10
                fig_days_dist_hist = px.histogram(days_data_for_hist, nbins=nbins_hist, title="Days to Confirmation Distribution", template="plotly_dark", labels={'value': 'Days to Confirmation'})
                fig_days_dist_hist.update_layout(plotly_layout_updates)
                st.plotly_chart(fig_days_dist_hist, use_container_width=True)
            else: 
                st.info("No valid 'Days to Confirmation' data to plot distribution.")
    else:
        st.info("No data matches current filter criteria to display Trends & Distributions.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.2 | Secured Access")