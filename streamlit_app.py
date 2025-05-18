import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import gspread # For Google Sheets
from google.oauth2.service_account import Credentials # For Google Sheets auth
import time # For a small delay after clearing cache

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard",
    page_icon="🌟", # Gold star!
    layout="wide"
)

# --- Custom Styling (Gold Accents) ---
GOLD_ACCENT_COLOR = "#FFD700" # Standard gold

st.markdown(f"""
<style>
    /* Main title */
    .stApp > header {{
        background-color: transparent;
    }}
    h1 {{ /* Main dashboard title */
        color: {GOLD_ACCENT_COLOR};
        text-align: center;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
    }}
    /* Section headers */
    h2, h3 {{
        color: {GOLD_ACCENT_COLOR};
        border-bottom: 1px solid {GOLD_ACCENT_COLOR} !important;
        padding-bottom: 0.3em;
    }}
    /* Metric labels and values - ensure text is white if not overridden by theme */
    div[data-testid="stMetricLabel"] > div, 
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div {{
        color: #FFFFFF !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        font-size: 1.85rem; /* Slightly larger metric value */
    }}
    /* Expander header color */
    .streamlit-expanderHeader {{
        color: {GOLD_ACCENT_COLOR} !important;
        font-weight: bold;
    }}
    /* Dataframe styling to fit dark theme better */
    .stDataFrame {{
        border: 1px solid #333; /* Subtle border for dataframe */
    }}
    /* Ensure sidebar text is white */
    .css-1d391kg p {{ /* Adjust if Streamlit changes its classes */
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

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    gc = None
    try: # Try loading from Streamlit secrets first (for cloud deployment)
        secrets = st.secrets["gcp_service_account"]
        gc = authenticate_gspread(secrets_dict=secrets)
    except (FileNotFoundError, KeyError): # Fallback to local file if secrets fail or not found
        gc = authenticate_gspread() # Will look for 'google_credentials.json'

    if gc is None:
        return pd.DataFrame()

    try:
        st.write(f"Attempting to open Google Sheet: '{sheet_url_or_name}', Worksheet: '{worksheet_name}'...")
        try:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound) as e_url:
            try:
                spreadsheet = gc.open(sheet_url_or_name) # Try opening by name if URL fails
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(f"Spreadsheet '{sheet_url_or_name}' not found by URL or Name. Check input and sharing permissions with the service account email.")
                return pd.DataFrame()
        
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1)
        df = pd.DataFrame(data)
        
        # Debug: Print number of rows loaded
        st.write(f"Successfully loaded {len(df)} records (rows of data, excluding header) from Google Sheet.")

        if df.empty:
            st.warning("No data records found in the Google Sheet. It might be empty or only contain a header row.")
            return pd.DataFrame()

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: Worksheet '{worksheet_name}' not found in the spreadsheet '{sheet_url_or_name}'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

    # --- Data Preprocessing ---
    df.columns = df.columns.str.strip()

    if 'onboardingDate' in df.columns:
        df['onboardingDate_str'] = df['onboardingDate'].astype(str)
        df['onboardingDate_cleaned'] = df['onboardingDate_str'].str.replace('Z', '', regex=False).str.replace('\n', '', regex=False).str.strip()
        
        # Attempt to parse various datetime formats, including those with timezone info
        parsed_dates = pd.to_datetime(df['onboardingDate_cleaned'], errors='coerce', infer_datetime_format=True)
        
        df['onboardingDate_dt'] = parsed_dates
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date # Store as Python date objects

        if df['onboarding_date_only'].isnull().all():
             st.warning("Could not parse 'onboardingDate' for any rows. MTD calculations and date filters might not work. Please check the date format in your Google Sheet (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).")
    else:
        st.warning("Column 'onboardingDate' not found. MTD calculations and date filters will be unavailable.")
        df['onboarding_date_only'] = pd.NaT
        df['onboardingDate_dt'] = pd.NaT

    if 'status' not in df.columns:
        st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found.")
        df['score'] = pd.NA
            
    return df

# --- Main Application ---
st.title("🌟 Onboarding Performance Dashboard 🌟")
st.markdown("---")

# --- Initialize Session State ---
default_sheet_url = "https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing"
default_worksheet_name = "Sheet1"

if "sheet_url" not in st.session_state:
    st.session_state.sheet_url = default_sheet_url
if "worksheet_name" not in st.session_state:
    st.session_state.worksheet_name = default_worksheet_name
if 'data_loaded_successfully' not in st.session_state: # True if df is loaded AND not empty
    st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state:
    st.session_state.df_original = pd.DataFrame()

# --- Sidebar Inputs for Google Sheet Info ---
st.sidebar.header("⚙️ Data Source")
user_sheet_url = st.sidebar.text_input(
    "Google Sheet URL or Name:",
    value=st.session_state.sheet_url,
    key="sheet_url_input_key"
)
user_worksheet_name = st.sidebar.text_input(
    "Worksheet Name:",
    value=st.session_state.worksheet_name,
    key="worksheet_name_input_key"
)

url_changed = user_sheet_url != st.session_state.sheet_url
ws_changed = user_worksheet_name != st.session_state.worksheet_name

if url_changed:
    st.session_state.sheet_url = user_sheet_url
    st.session_state.data_loaded_successfully = False
if ws_changed:
    st.session_state.worksheet_name = user_worksheet_name
    st.session_state.data_loaded_successfully = False

if st.sidebar.button("🔄 Load/Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False
    time.sleep(0.1) 
    st.rerun()

# --- Data Loading Logic ---
if not st.session_state.data_loaded_successfully and st.session_state.sheet_url:
    with st.spinner(f"Loading data from worksheet '{st.session_state.worksheet_name}' in '{st.session_state.sheet_url}'..."):
        df = load_data_from_google_sheet(st.session_state.sheet_url, st.session_state.worksheet_name)
        if not df.empty:
            st.session_state.df_original = df
            st.session_state.data_loaded_successfully = True
        else:
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded_successfully = False
            # Error/warning is handled within load_data_from_google_sheet

df_original = st.session_state.df_original

if not st.session_state.data_loaded_successfully:
    st.info("Welcome! Please ensure the Google Sheet URL and Worksheet Name in the sidebar are correct. "
            "If they are, click 'Load/Refresh Data from Google Sheet'. Also, check Google Sheet sharing permissions and API setup.")
    st.stop()
elif df_original.empty and st.session_state.data_loaded_successfully:
    st.warning("Data source connected, but the Google Sheet appears to be empty or only contains headers. Please check the sheet content.")
    # Allow UI to render so user can try again or see the message.

# --- MTD Metrics Calculation ---
st.header("📈 Month-to-Date (MTD) Overview")
today = date.today()
current_month_start = today.replace(day=1)
df_mtd = pd.DataFrame(columns=df_original.columns) # Default to empty

if not df_original.empty and 'onboarding_date_only' in df_original.columns:
    # Ensure 'onboarding_date_only' contains valid date objects for comparison
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
df_filtered = df_original.copy() # Start with a copy of the original loaded data

# Date filter
if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    valid_dates_for_filter = df_original['onboarding_date_only'][pd.Series(isinstance(x, date) for x in df_original['onboarding_date_only']) & df_original['onboarding_date_only'].notna()]
    if not valid_dates_for_filter.empty:
        min_date_data = valid_dates_for_filter.min()
        max_date_data = valid_dates_for_filter.max()
        
        date_range = st.sidebar.date_input(
            "Onboarding Date Range:",
            value=(min_date_data, max_date_data),
            min_value=min_date_data,
            max_value=max_date_data,
            key="date_range_filter"
        )
        start_date_filter, end_date_filter = date_range
        # Apply date filter
        df_filtered = df_filtered[
            df_filtered['onboarding_date_only'].apply(lambda x: isinstance(x, date) and start_date_filter <= x <= end_date_filter if pd.notna(x) else False)
        ]
    else:
        st.sidebar.warning("No valid dates found for date range filter.")
else:
    st.sidebar.warning("Onboarding date data not available for filtering.")

# Categorical Filters
for col_name in ['repName', 'status', 'clientSentiment']:
    if not df_original.empty and col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = ["All"] + sorted(df_original[col_name].astype(str).dropna().unique())
        selected_value = st.sidebar.selectbox(f"Select {col_name.replace('repName', 'Rep')}:", unique_values, key=f"{col_name}_filter")
        if selected_value != "All":
            df_filtered = df_filtered[df_filtered[col_name].astype(str) == selected_value]
    else:
        st.sidebar.text(f"{col_name.replace('repName', 'Rep')} data not available for filtering.")

# --- Display Filtered Data Table ---
st.header("📋 Filtered Onboarding Data")
if not df_filtered.empty:
    st.dataframe(df_filtered.reset_index(drop=True))
elif not df_original.empty: # If original had data but filters removed all
    st.info("No data matches the current filter criteria.")
# If df_original itself was empty, the main stop/warning messages above handle it.

st.markdown("---")

# --- Visualizations based on Filtered Data ---
st.header("📊 Visualizations")

if not df_filtered.empty:
    plotly_layout_updates = {
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#FFFFFF",
        "title_font_color": GOLD_ACCENT_COLOR,
        "legend_font_color": "#FFFFFF",
    }
    
    chart_colors = px.colors.qualitative.Vivid # A color set that generally looks good on dark themes
    gold_color_sequence = [GOLD_ACCENT_COLOR, "#DAA520", "#B8860B", "#C9B037"] # Shades of gold

    viz_cols = st.columns(2) # Create two columns for visualizations

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
            sentiment_color_map = {
                sent: GOLD_ACCENT_COLOR if sent == "Neutral" else chart_colors[i % len(chart_colors)]
                for i, sent in enumerate(sentiment_counts['sentiment'].unique())
            }
             # Ensure 'Neutral' is gold, others cycle through chart_colors
            if 'Neutral' in sentiment_color_map: # Prioritize Neutral as gold
                 for sent in sentiment_counts['sentiment'].unique():
                     if sent == 'Positive': sentiment_color_map[sent] = '#2ca02c' # Green
                     elif sent == 'Negative': sentiment_color_map[sent] = '#d62728' # Red
                     elif sent == 'Neutral': sentiment_color_map[sent] = GOLD_ACCENT_COLOR

            fig_sentiment = px.pie(sentiment_counts, names='sentiment', values='count',
                                   hole=0.4, template="plotly_dark",
                                   color='sentiment', color_discrete_map=sentiment_color_map)
            fig_sentiment.update_layout(plotly_layout_updates)
            fig_sentiment.update_traces(marker_line_color='black', marker_line_width=1.5) # Thicker line for pie segments
            st.plotly_chart(fig_sentiment, use_container_width=True)
        
        if 'repName' in df_filtered.columns and df_filtered['repName'].notna().any():
            st.subheader("Onboardings by Rep")
            rep_counts = df_filtered['repName'].value_counts().reset_index()
            rep_counts.columns = ['Representative', 'Count']
            fig_rep = px.bar(rep_counts, x='Representative', y='Count', color='Representative',
                             template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Bold) # Another distinct color set
            fig_rep.update_layout(plotly_layout_updates)
            fig_rep.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1)
            st.plotly_chart(fig_rep, use_container_width=True)

elif st.session_state.data_loaded_successfully and df_original.empty: # Data loaded but sheet was empty
    pass # Warning already shown
elif st.session_state.data_loaded_successfully: # Data loaded but filters made df_filtered empty
    st.info("No data to visualize based on the current filter selection.")


st.sidebar.markdown("---")
st.sidebar.info("Dashboard v1.2 | Black & Gold | GSheets Edition")