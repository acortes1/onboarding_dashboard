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
# Using markdown to inject custom CSS for gold accents on titles and other specific elements
# Gold color: #FFD700 (standard gold), #B8860B (darker gold/bronze)
GOLD_ACCENT_COLOR = "#FFD700" # Using standard gold for high visibility

st.markdown(f"""
<style>
    /* Main title */
    .stApp > header {{
        background-color: transparent; /* Assuming header is part of stApp background */
    }}
    h1 {{ /* Main dashboard title */
        color: {GOLD_ACCENT_COLOR};
        text-align: center; /* Center the main title */
    }}
    /* Subheaders */
    h2, h3 {{
        color: {GOLD_ACCENT_COLOR}; /* Gold for section headers */
        border-bottom: 1px solid {GOLD_ACCENT_COLOR}; /* Gold underline for section headers */
        padding-bottom: 0.3em;
    }}
    /* Metric labels - a bit more complex to target directly, but can try with Streamlit's classes */
    /* You might need to inspect elements in browser to get exact classes if this doesn't work perfectly */
    div[data-testid="stMetricLabel"] > div, div[data-testid="stMetricValue"] > div {{
        color: #FFFFFF !important; /* Ensure metric text is white */
    }}
    div[data-testid="stMetricValue"] > div {{
        font-size: 1.75rem; /* Adjust metric value font size if needed */
    }}
    /* Change expander header color */
    .streamlit-expanderHeader {{
        color: {GOLD_ACCENT_COLOR};
    }}
    /* Style Streamlit buttons (default buttons are already using primaryColor) */
    /* Add specific gold borders or backgrounds to Plotly charts if desired via CSS (more complex) */
</style>
""", unsafe_allow_html=True)


# --- Google Sheets Authentication and Data Loading ---
# Define the scope for Google Sheets and Drive API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Function to authenticate with Google Sheets using service account
def authenticate_gspread(secrets_dict=None):
    try:
        if secrets_dict: # For Streamlit Cloud deployment using st.secrets
            creds_json = secrets_dict
        else: # For local development, expects 'google_credentials.json'
            creds_json = "google_credentials.json"
        
        creds = Credentials.from_service_account_info( # Use from_service_account_info for dict
            creds_json, scopes=SCOPES
        )
        gc = gspread.authorize(creds)
        return gc
    except FileNotFoundError: # Only relevant for local dev if file is missing
        st.error("Google Sheets authentication failed: 'google_credentials.json' not found.")
        st.info("For local development, ensure your service account JSON key file is named 'google_credentials.json' and is in the root directory.")
        return None
    except Exception as e:
        st.error(f"Google Sheets authentication error: {e}")
        st.info("Ensure your Google Cloud service account is correctly set up, the JSON key is valid, "
                "and the Google Sheets API & Drive API are enabled. Also, share your Google Sheet with the service account's email.")
        return None

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data_from_google_sheet(sheet_url_or_name, worksheet_name):
    # Determine if running locally or on Streamlit Cloud to fetch secrets
    try:
        secrets = st.secrets["gcp_service_account"]
        gc = authenticate_gspread(secrets_dict=secrets)
    except (FileNotFoundError, KeyError): # FileNotFoundError for local, KeyError for st.secrets if not set
        gc = authenticate_gspread() # Falls back to local 'google_credentials.json'

    if gc is None:
        return pd.DataFrame()

    try:
        st.write(f"Attempting to open Google Sheet: '{sheet_url_or_name}', Worksheet: '{worksheet_name}'...")
        try:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        except gspread.exceptions.APIError: # Try opening by name if URL fails (e.g. due to permissions before access)
             spreadsheet = gc.open(sheet_url_or_name)
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Spreadsheet '{sheet_url_or_name}' not found. Check the name/URL and sharing permissions with the service account.")
            return pd.DataFrame()

        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1) # Assumes first row is header
        df = pd.DataFrame(data)
        st.write(f"Successfully loaded {len(df)} rows from Google Sheet.")

        if df.empty:
            st.warning("No data loaded from Google Sheet. It might be empty or headers might be missing.")
            return pd.DataFrame()

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Error: Google Spreadsheet '{sheet_url_or_name}' not found or not shared with the service account.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: Worksheet '{worksheet_name}' not found in the spreadsheet.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

    # --- Data Preprocessing (adapted from your previous script) ---
    df.columns = df.columns.str.strip() # Clean column names

    # Date Preprocessing for 'onboardingDate'
    if 'onboardingDate' in df.columns:
        df['onboardingDate_str'] = df['onboardingDate'].astype(str) # Ensure it's string
        # Attempt to clean various potential issues before parsing
        df['onboardingDate_cleaned'] = df['onboardingDate_str'].str.replace('Z', '', regex=False).str.replace('\n', '', regex=False).str.strip()
        
        # Try parsing with a common format first, then more general if that fails
        try:
            df['onboardingDate_dt'] = pd.to_datetime(df['onboardingDate_cleaned'], format='%Y-%m-%dT%H:%M:%S.%f', errors='coerce')
        except ValueError: # If the above format fails for all, try a more general approach
            df['onboardingDate_dt'] = pd.to_datetime(df['onboardingDate_cleaned'], errors='coerce')
        
        df['onboarding_date_only'] = df['onboardingDate_dt'].dt.date
        if df['onboarding_date_only'].isnull().all():
             st.warning("Could not parse 'onboardingDate' for most rows. MTD calculations and date filters might not work as expected. Please check the date format in your Google Sheet.")
    else:
        st.warning("Column 'onboardingDate' not found. MTD calculations will not be available.")
        df['onboarding_date_only'] = pd.NaT
        df['onboardingDate_dt'] = pd.NaT


    # Ensure 'status' and 'score' columns exist and 'score' is numeric
    if 'status' not in df.columns:
        st.warning("Column 'status' not found. Success rate calculation might be affected.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found. Average score calculation might be affected.")
        df['score'] = pd.NA # Use pandas NA for missing numeric data

    return df

# --- Main Application ---

st.title("🌟 Onboarding Performance Dashboard 🌟") # Added emojis for flair
st.markdown("---")

# --- Inputs for Google Sheet Info in Sidebar ---
st.sidebar.header("⚙️ Data Source")
default_sheet_url = "YOUR_GOOGLE_SHEET_URL_HERE" # Replace with your actual sheet URL or Name
default_worksheet_name = "Sheet1" # Replace if your sheet has a different name

sheet_url_or_name_input = st.sidebar.text_input("Google Sheet URL or Name:", value=st.session_state.get("sheet_url", default_sheet_url))
worksheet_name_input = st.sidebar.text_input("Worksheet Name:", value=st.session_state.get("worksheet_name", default_worksheet_name))

# Store in session state to persist across reruns if user changes them
st.session_state.sheet_url = sheet_url_or_name_input
st.session_state.worksheet_name = worksheet_name_input

if st.sidebar.button("🔄 Refresh Data & Reload Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded = False # Force reload
    time.sleep(0.1) # Brief pause
    st.rerun()

# Load data only if inputs are provided and not the placeholder
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

if sheet_url_or_name_input and sheet_url_or_name_input != "YOUR_GOOGLE_SHEET_URL_HERE" and not st.session_state.data_loaded :
    with st.spinner(f"Loading data from '{worksheet_name_input}' in '{sheet_url_or_name_input}'..."):
        df_original = load_data_from_google_sheet(sheet_url_or_name_input, worksheet_name_input)
        if not df_original.empty:
            st.session_state.df_original = df_original
            st.session_state.data_loaded = True
        else:
            st.session_state.df_original = pd.DataFrame() # Ensure it's an empty DF
elif st.session_state.data_loaded:
    df_original = st.session_state.df_original
else:
    st.info("Please enter your Google Sheet URL/Name and Worksheet Name in the sidebar and click 'Refresh Data'.")
    st.stop()


if df_original.empty and st.session_state.data_loaded: # If tried loading but got empty
    st.error("Failed to load data or the sheet is empty. Please check sidebar inputs and sheet permissions.")
    st.stop()
elif df_original.empty: # If never successfully loaded
    st.stop()


# --- MTD Metrics Calculation ---
st.header("📈 Month-to-Date (MTD) Overview")
today = date.today()
current_month_start = today.replace(day=1)

if 'onboarding_date_only' in df_original.columns and pd.api.types.is_datetime64_any_dtype(pd.to_datetime(df_original['onboarding_date_only'], errors='coerce')):
    # Ensure comparison is between date objects
    valid_dates_mask = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').notna()
    df_mtd = df_original[valid_dates_mask &
        (pd.to_datetime(df_original['onboarding_date_only'][valid_dates_mask]).dt.date >= current_month_start) &
        (pd.to_datetime(df_original['onboarding_date_only'][valid_dates_mask]).dt.date <= today)
    ]
else:
    df_mtd = pd.DataFrame(columns=df_original.columns)

total_onboardings_mtd = len(df_mtd)

if total_onboardings_mtd > 0 and 'status' in df_mtd.columns:
    successful_onboardings_mtd = df_mtd[df_mtd['status'].astype(str).str.lower() == 'confirmed'].shape[0]
    success_rate_mtd = (successful_onboardings_mtd / total_onboardings_mtd) * 100
else:
    success_rate_mtd = 0

if 'score' in df_mtd.columns and df_mtd['score'].notna().any():
    avg_rep_score_mtd = df_mtd['score'].mean()
else:
    avg_rep_score_mtd = 0.0


col1, col2, col3 = st.columns(3)
col1.metric(label="Total Onboardings MTD", value=f"{total_onboardings_mtd}")
col2.metric(label="Overall Success Rate MTD", value=f"{success_rate_mtd:.1f}%") # Adjusted precision
col3.metric(label="Average Score MTD", value=f"{avg_rep_score_mtd:.2f}" if avg_rep_score_mtd else "N/A")

st.markdown("---")

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")

# Date filter
if 'onboarding_date_only' in df_original.columns and not df_original['onboarding_date_only'].dropna().empty:
    # Convert to datetime if not already, coercing errors, then take .dt.date
    temp_dates = pd.to_datetime(df_original['onboarding_date_only'], errors='coerce').dropna().dt.date
    if not temp_dates.empty:
        min_date_data = temp_dates.min()
        max_date_data = temp_dates.max()

        date_range = st.sidebar.date_input(
            "Onboarding Date Range:",
            value=(min_date_data, max_date_data),
            min_value=min_date_data,
            max_value=max_date_data,
            key="date_range_filter"
        )
        start_date_filter, end_date_filter = date_range
    else:
        st.sidebar.warning("No valid dates found in 'onboarding_date_only' for filtering.")
        start_date_filter, end_date_filter = None, None
else:
    st.sidebar.warning("Onboarding date data not available for filtering.")
    start_date_filter, end_date_filter = None, None


# Filter by Rep Name
if 'repName' in df_original.columns:
    rep_names = ["All"] + sorted(df_original['repName'].astype(str).dropna().unique())
    selected_rep = st.sidebar.selectbox("Select Rep:", rep_names, key="rep_filter")
else:
    selected_rep = "All"
    st.sidebar.warning("Rep Name data not available.")

# Filter by Status
if 'status' in df_original.columns:
    statuses = ["All"] + sorted(df_original['status'].astype(str).dropna().unique())
    selected_status = st.sidebar.selectbox("Select Status:", statuses, key="status_filter")
else:
    selected_status = "All"
    st.sidebar.warning("Status data not available.")

# Filter by Client Sentiment
if 'clientSentiment' in df_original.columns:
    sentiments = ["All"] + sorted(df_original['clientSentiment'].astype(str).dropna().unique())
    selected_sentiment = st.sidebar.selectbox("Select Client Sentiment:", sentiments, key="sentiment_filter")
else:
    selected_sentiment = "All"
    st.sidebar.warning("Client Sentiment data not available.")


# --- Apply Filters ---
df_filtered = df_original.copy()

if start_date_filter and end_date_filter and 'onboarding_date_only' in df_filtered.columns:
    valid_dates_mask_filter = pd.to_datetime(df_filtered['onboarding_date_only'], errors='coerce').notna()
    df_filtered = df_filtered[valid_dates_mask_filter &
        (pd.to_datetime(df_filtered['onboarding_date_only'][valid_dates_mask_filter]).dt.date >= start_date_filter) &
        (pd.to_datetime(df_filtered['onboarding_date_only'][valid_dates_mask_filter]).dt.date <= end_date_filter)
    ]

if selected_rep != "All" and 'repName' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['repName'] == selected_rep]

if selected_status != "All" and 'status' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['status'] == selected_status]

if selected_sentiment != "All" and 'clientSentiment' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['clientSentiment'] == selected_sentiment]

# --- Display Filtered Data Table ---
st.header("📋 Filtered Onboarding Data")
if not df_filtered.empty:
    st.dataframe(df_filtered.reset_index(drop=True)) # Reset index for cleaner display
else:
    st.info("No data matches the current filter criteria.")

st.markdown("---")

# --- Visualizations based on Filtered Data ---
st.header("📊 Visualizations")

if not df_filtered.empty:
    # Common Plotly layout updates for dark theme with gold accents
    plotly_layout_updates = {
        "plot_bgcolor": "rgba(0,0,0,0)", # Transparent plot background
        "paper_bgcolor": "rgba(0,0,0,0)", # Transparent paper background
        "font_color": "#FFFFFF", # White font for chart text
        "title_font_color": GOLD_ACCENT_COLOR,
        "legend_font_color": "#FFFFFF",
        # Potentially more styling for axes, ticks, etc.
    }
    # Define a gold color sequence, can be expanded if more distinct colors are needed
    gold_color_sequence = [GOLD_ACCENT_COLOR, "#DAA520", "#B8860B", "#C9B037"]


    col_viz1, col_viz2 = st.columns(2)

    with col_viz1:
        if 'status' in df_filtered.columns:
            st.subheader("Onboarding Status Distribution")
            status_counts = df_filtered['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_status = px.bar(status_counts, x='status', y='count', color='status',
                                title="Status of Onboardings", template="plotly_dark",
                                color_discrete_sequence=px.colors.qualitative.Set2) # Using a qualitative set for statuses
            fig_status.update_layout(plotly_layout_updates)
            fig_status.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1.5)
            st.plotly_chart(fig_status, use_container_width=True)

        if 'score' in df_filtered.columns and df_filtered['score'].notna().any():
            st.subheader("Client Score Distribution")
            fig_score = px.histogram(df_filtered.dropna(subset=['score']), x='score', nbins=10,
                                     title="Distribution of Client Scores (1-10)", template="plotly_dark")
            fig_score.update_layout(plotly_layout_updates)
            fig_score.update_traces(marker_color=GOLD_ACCENT_COLOR, marker_line_color='white', marker_line_width=0.5)
            st.plotly_chart(fig_score, use_container_width=True)

    with col_viz2:
        if 'clientSentiment' in df_filtered.columns:
            st.subheader("Client Sentiment")
            sentiment_counts = df_filtered['clientSentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['sentiment', 'count']
            # Define specific colors, making one gold for accent
            sentiment_color_map = {'Positive': '#2ca02c', 'Negative': '#d62728', 'Neutral': GOLD_ACCENT_COLOR}
            fig_sentiment = px.pie(sentiment_counts, names='sentiment', values='count',
                                   title="Client Sentiment Breakdown", hole=0.4, template="plotly_dark",
                                   color='sentiment', color_discrete_map=sentiment_color_map)
            fig_sentiment.update_layout(plotly_layout_updates)
            fig_sentiment.update_traces(marker_line_color='black', marker_line_width=1)
            st.plotly_chart(fig_sentiment, use_container_width=True)
        
        if 'repName' in df_filtered.columns and df_filtered['repName'].nunique() > 0 :
            st.subheader("Onboardings by Representative")
            rep_counts = df_filtered['repName'].value_counts().reset_index()
            rep_counts.columns = ['Representative', 'Count']
            fig_rep = px.bar(rep_counts, x='Representative', y='Count', color='Representative',
                             title="Number of Onboardings per Rep", template="plotly_dark",
                             color_discrete_sequence=px.colors.qualitative.Vivid) # Use a vivid sequence for reps
            fig_rep.update_layout(plotly_layout_updates)
            fig_rep.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1)
            st.plotly_chart(fig_rep, use_container_width=True)
else:
    if st.session_state.get('data_loaded', False): # Only show this if data loading was attempted
        st.info("No data to visualize based on current filters or the loaded sheet is empty.")


st.sidebar.markdown("---")
st.sidebar.info("Dashboard v1.1 | Black & Gold Edition")