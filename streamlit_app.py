import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta # Added timedelta
import gspread # For Google Sheets
from google.oauth2.service_account import Credentials # For Google Sheets auth
import time # For a small delay after clearing cache

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard",
    page_icon="🌟",
    layout="wide"
)

# --- Custom Styling (Gold Accents) ---
GOLD_ACCENT_COLOR = "#FFD700"

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
        color: #FFFFFF !important;
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
    .css-1d391kg p {{
        color: #FFFFFF !important;
    }}
</style>
""", unsafe_allow_html=True)


# --- Google Sheets Authentication and Data Loading ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread(secrets_dict=None):
    try:
        if secrets_dict:
            creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except FileNotFoundError:
        st.error("Authentication Error: 'google_credentials.json' not found for local development.")
        st.info("Ensure it's in the root directory or configure Streamlit Secrets for cloud deployment.")
        return None
    except Exception as e:
        st.error(f"Google Sheets Authentication Error: {e}")
        st.info("Check service account setup, JSON key validity, API enablement (Sheets & Drive), and sheet sharing permissions.")
        return None

@st.cache_data(ttl=600)
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    gc = None
    try:
        secrets = st.secrets["gcp_service_account"]
        gc = authenticate_gspread(secrets_dict=secrets)
    except (FileNotFoundError, KeyError):
        gc = authenticate_gspread()

    if gc is None:
        return pd.DataFrame()

    try:
        # *** MODIFICATION: Removed the "Attempting to open..." st.write message ***
        try:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound) as e_url:
            try:
                spreadsheet = gc.open(sheet_url_or_name)
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(f"Spreadsheet '{sheet_url_or_name}' not found by URL or Name. Check input and sharing permissions with the service account email.")
                return pd.DataFrame()
        
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1) # Removed value_render_option and datetime_render_option for wider gspread compatibility
        df = pd.DataFrame(data)
        
        # *** MODIFICATION: Kept this helpful message ***
        st.write(f"Successfully loaded {len(df)} records (rows of data, excluding header) from Google Sheet.")

        if df.empty:
            st.warning("No data records found in the Google Sheet. It might be empty or only contain a header row.")
            return pd.DataFrame()

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: Worksheet '{worksheet_name}' not found in the spreadsheet '{sheet_url_or_name}'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}") # This will now be the primary error message for loading issues
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    if 'onboardingDate' in df.columns:
        df['onboardingDate_str'] = df['onboardingDate'].astype(str)
        df['onboardingDate_cleaned'] = df['onboardingDate_str'].str.replace('Z', '', regex=False).str.replace('\n', '', regex=False).str.strip()
        parsed_dates = pd.to_datetime(df['onboardingDate_cleaned'], errors='coerce', infer_datetime_format=True)
        df['onboardingDate_dt'] = parsed_dates
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date
        if df['onboarding_date_only'].isnull().all():
             st.warning("Could not parse 'onboardingDate' for any rows. MTD calculations and date filters might not work. Please check the date format in your Google Sheet (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).")
    else:
        st.warning("Column 'onboardingDate' not found. MTD calculations and date filters will be unavailable.")
        df['onboarding_date_only'] = pd.NaT
        df['onboardingDate_dt'] = pd.NaT

    if 'status' not in df.columns: st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found.")
        df['score'] = pd.NA
            
    return df

# --- Main Application ---
st.title("🌟 Onboarding Performance Dashboard 🌟")
st.markdown("---")

# --- Initialize Session State & Define Hardcoded Data Source ---
# *** MODIFICATION: Data source is now effectively hardcoded by these defaults ***
default_sheet_url = "https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing"
default_worksheet_name = "Sheet1"

if "sheet_url" not in st.session_state:
    st.session_state.sheet_url = default_sheet_url
if "worksheet_name" not in st.session_state:
    st.session_state.worksheet_name = default_worksheet_name
if 'data_loaded_successfully' not in st.session_state:
    st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state:
    st.session_state.df_original = pd.DataFrame()

# --- Sidebar: Data Refresh Control ---
# *** MODIFICATION: Removed Data Source text inputs from sidebar. Header changed. ***
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False
    time.sleep(0.1) 
    st.rerun()

# --- Data Loading Logic ---
if not st.session_state.data_loaded_successfully:
    with st.spinner(f"Loading data from Google Sheet..."): # Simplified spinner message
        # Uses the sheet_url and worksheet_name from session state (which are the defaults now)
        df = load_data_from_google_sheet(st.session_state.sheet_url, st.session_state.worksheet_name)
        if not df.empty:
            st.session_state.df_original = df
            st.session_state.data_loaded_successfully = True
        else:
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded_successfully = False

df_original = st.session_state.df_original

if not st.session_state.data_loaded_successfully:
    st.error("Failed to load data. Please ensure Google Sheet permissions are correct and the sheet is available, then try refreshing. "
             "The application is configured to use a specific Google Sheet.")
    st.stop()
elif df_original.empty and st.session_state.data_loaded_successfully:
    st.warning("Data source connected, but the Google Sheet appears to be empty or only contains headers. Please check the sheet content.")

# --- MTD Metrics Calculation (No changes here from last version) ---
st.header("📈 Month-to-Date (MTD) Overview")
today = date.today()
current_month_start = today.replace(day=1)
df_mtd = pd.DataFrame(columns=df_original.columns)

if not df_original.empty and 'onboarding_date_only' in df_original.columns:
    valid_dates_mask = pd.Series(isinstance(x, date) for x in df_original['onboarding_date_only']) & df_original['onboarding_date_only'].notna()
    if valid_dates_mask.any():
        df_temp_dates = df_original[valid_dates_mask]
        df_mtd = df_temp_dates[
            (df_temp_dates['onboarding_date_only'] >= current_month_start) &
            (df_temp_dates['onboarding_date_only'] <= today)
        ]

total_onboardings_mtd = len(df_mtd)
success_rate_mtd = 0.0
avg_rep_score_mtd = 0.0

if total_onboardings_mtd > 0 and 'status' in df_mtd.columns:
    successful_onboardings_mtd = df_mtd[df_mtd['status'].astype(str).str.lower() == 'confirmed'].shape[0]
    success_rate_mtd = (successful_onboardings_mtd / total_onboardings_mtd) * 100

if not df_mtd.empty and 'score' in df_mtd.columns and df_mtd['score'].notna().any():
    avg_rep_score_mtd = df_mtd['score'].mean()

col1, col2, col3 = st.columns(3)
col1.metric(label="Total Onboardings MTD", value=f"{total_onboardings_mtd}")
col2.metric(label="Overall Success Rate MTD", value=f"{success_rate_mtd:.1f}%")
col3.metric(label="Average Score MTD", value=f"{avg_rep_score_mtd:.2f}" if not pd.isna(avg_rep_score_mtd) and avg_rep_score_mtd != 0 else "N/A")
st.markdown("---")

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
df_filtered = df_original.copy()

# Date filter - *** MODIFICATION: Default value changed to MTD ***
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    valid_dates_for_filter = df_original['onboarding_date_only'][pd.Series(isinstance(x, date) for x in df_original['onboarding_date_only']) & df_original['onboarding_date_only'].notna()]
    if not valid_dates_for_filter.empty:
        min_date_data = valid_dates_for_filter.min()
        max_date_data = valid_dates_for_filter.max()
        
        # Calculate MTD for default filter range
        filter_default_start_date = date.today().replace(day=1)
        filter_default_end_date = date.today()

        # Ensure default MTD range is within available data, otherwise use data bounds
        if filter_default_start_date < min_date_data:
            filter_default_start_date = min_date_data
        if filter_default_end_date > max_date_data:
            filter_default_end_date = max_date_data
        if filter_default_start_date > filter_default_end_date : # Handle edge case if current MTD is outside all data
            filter_default_start_date = min_date_data 
            filter_default_end_date = max_date_data


        date_range = st.sidebar.date_input(
            "Onboarding Date Range:",
            value=(filter_default_start_date, filter_default_end_date), # Default to MTD
            min_value=min_date_data,
            max_value=max_date_data,
            key="date_range_filter"
        )
        start_date_filter, end_date_filter = date_range
        
        df_filtered = df_filtered[
            df_filtered['onboarding_date_only'].apply(lambda x: isinstance(x, date) and start_date_filter <= x <= end_date_filter if pd.notna(x) else False)
        ]
    else:
        st.sidebar.warning("No valid dates found for date range filter.")
else:
    st.sidebar.warning("Onboarding date data not available for filtering.")

# Categorical Filters (no change in logic from last version)
for col_name in ['repName', 'status', 'clientSentiment']:
    if not df_original.empty and col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = ["All"] + sorted(df_original[col_name].astype(str).dropna().unique())
        selected_value = st.sidebar.selectbox(f"Select {col_name.replace('repName', 'Rep')}:", unique_values, key=f"{col_name}_filter")
        if selected_value != "All":
            df_filtered = df_filtered[df_filtered[col_name].astype(str) == selected_value]
    else:
        st.sidebar.text(f"{col_name.replace('repName', 'Rep')} data not available for filtering.")

# --- Display Filtered Data Table (no change from last version) ---
st.header("📋 Filtered Onboarding Data")
if not df_filtered.empty:
    st.dataframe(df_filtered.reset_index(drop=True))
elif not df_original.empty:
    st.info("No data matches the current filter criteria.")

st.markdown("---")

# --- Visualizations based on Filtered Data (no functional change from last version, styling remains) ---
st.header("📊 Visualizations")
if not df_filtered.empty:
    plotly_layout_updates = {
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#FFFFFF",
        "title_font_color": GOLD_ACCENT_COLOR,
        "legend_font_color": "#FFFFFF",
    }
    chart_colors = px.colors.qualitative.Vivid
    gold_color_sequence = [GOLD_ACCENT_COLOR, "#DAA520", "#B8860B", "#C9B037"]
    viz_cols = st.columns(2)

    with viz_cols[0]:
        if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
            st.subheader("Onboarding Status")
            status_counts = df_filtered['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_status = px.bar(status_counts, x='status', y='count', color='status',
                                template="plotly_dark", color_discrete_sequence=chart_colors)
            fig_status.update_layout(plotly_layout_updates)
            fig_status.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1)
            st.plotly_chart(fig_status, use_container_width=True)

        if 'score' in df_filtered.columns and df_filtered['score'].notna().any():
            st.subheader("Client Score Distribution")
            fig_score = px.histogram(df_filtered.dropna(subset=['score']), x='score', nbins=10, template="plotly_dark")
            fig_score.update_layout(plotly_layout_updates)
            fig_score.update_traces(marker_color=GOLD_ACCENT_COLOR, marker_line_color='rgba(255,255,255,0.7)', marker_line_width=0.5)
            st.plotly_chart(fig_score, use_container_width=True)

    with viz_cols[1]:
        if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
            st.subheader("Client Sentiment")
            sentiment_counts = df_filtered['clientSentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['sentiment', 'count']
            sentiment_color_map = {}
            unique_sentiments = sentiment_counts['sentiment'].unique()
            for i, sent in enumerate(unique_sentiments):
                if sent == 'Positive': sentiment_color_map[sent] = '#2ca02c' # Green
                elif sent == 'Negative': sentiment_color_map[sent] = '#d62728' # Red
                elif sent == 'Neutral': sentiment_color_map[sent] = GOLD_ACCENT_COLOR
                else: sentiment_color_map[sent] = chart_colors[i % len(chart_colors)]
            
            fig_sentiment = px.pie(sentiment_counts, names='sentiment', values='count',
                                   hole=0.4, template="plotly_dark",
                                   color='sentiment', color_discrete_map=sentiment_color_map)
            fig_sentiment.update_layout(plotly_layout_updates)
            fig_sentiment.update_traces(marker_line_color='black', marker_line_width=1.5)
            st.plotly_chart(fig_sentiment, use_container_width=True)
        
        if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
            st.subheader("Onboardings by Rep")
            rep_counts = df_filtered['repName'].value_counts().reset_index()
            rep_counts.columns = ['Representative', 'Count']
            fig_rep = px.bar(rep_counts, x='Representative', y='Count', color='Representative',
                             template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Bold)
            fig_rep.update_layout(plotly_layout_updates)
            fig_rep.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1)
            st.plotly_chart(fig_rep, use_container_width=True)

elif st.session_state.data_loaded_successfully and df_original.empty:
    pass 
elif st.session_state.data_loaded_successfully: 
    st.info("No data to visualize based on the current filter selection.")

st.sidebar.markdown("---")
st.sidebar.info("Dashboard v1.3 | Black & Gold | GSheets Edition")