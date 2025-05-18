import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time
import numpy as np # For NaN handling if needed

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
    h2, h3 {{ /* This targets st.header and st.subheader */
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
    .css-1d391kg p {{ /* General paragraph text in sidebar if not overridden */
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
        try:
            spreadsheet = gc.open_by_url(sheet_url_or_name)
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound):
            spreadsheet = gc.open(sheet_url_or_name)
        
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records(head=1) # Removed render options for wider gspread compatibility
        df = pd.DataFrame(data)
        
        st.write(f"Successfully loaded {len(df)} records (rows of data, excluding header) from Google Sheet.")

        if df.empty:
            st.warning("No data records found in the Google Sheet.")
            return pd.DataFrame()

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_url_or_name}' not found. Check name/URL and sharing permissions.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: Worksheet '{worksheet_name}' not found in '{sheet_url_or_name}'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

    # --- Data Preprocessing ---
    df.columns = df.columns.str.strip()

    date_columns_to_parse = {
        'onboardingDate': 'onboardingDate_dt',
        'deliveryDate': 'deliveryDate_dt', # Assuming this column exists
        'confirmationTimestamp': 'confirmationTimestamp_dt' # Assuming this column exists
    }

    for original_col, new_dt_col in date_columns_to_parse.items():
        if original_col in df.columns:
            df[f'{original_col}_str'] = df[original_col].astype(str)
            df[f'{original_col}_cleaned'] = df[f'{original_col}_str'].str.replace('Z', '', regex=False).str.replace('\n', '', regex=False).str.strip()
            parsed_dates = pd.to_datetime(df[f'{original_col}_cleaned'], errors='coerce', infer_datetime_format=True)
            df[new_dt_col] = parsed_dates
            if original_col == 'onboardingDate': # Keep specific logic for onboarding_date_only
                 df['onboarding_date_only'] = df[new_dt_col].dt.date
                 if df['onboarding_date_only'].isnull().all():
                    st.warning(f"Could not parse '{original_col}' for any rows. Date-dependent features might not work. Check format (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).")
        else:
            st.warning(f"Date column '{original_col}' not found. Dependent calculations might fail.")
            df[new_dt_col] = pd.NaT
            if original_col == 'onboardingDate':
                df['onboarding_date_only'] = pd.NaT
    
    # Calculate Days to Confirmation
    if 'deliveryDate_dt' in df and 'confirmationTimestamp_dt' in df:
        # Ensure both are datetime before subtraction
        df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate_dt'], errors='coerce')
        df['confirmationTimestamp_dt'] = pd.to_datetime(df['confirmationTimestamp_dt'], errors='coerce')
        
        # Calculate difference only for valid date pairs
        valid_dates_mask = df['deliveryDate_dt'].notna() & df['confirmationTimestamp_dt'].notna()
        df['days_to_confirmation'] = pd.NA # Initialize with Pandas NA
        df.loc[valid_dates_mask, 'days_to_confirmation'] = \
            (df.loc[valid_dates_mask, 'confirmationTimestamp_dt'] - df.loc[valid_dates_mask, 'deliveryDate_dt']).dt.days
    else:
        st.warning(" 'deliveryDate' or 'confirmationTimestamp' column missing for 'Days to Confirmation' calculation.")
        df['days_to_confirmation'] = pd.NA


    if 'status' not in df.columns: st.warning("Column 'status' not found.")
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
    else:
        st.warning("Column 'score' not found.")
        df['score'] = pd.NA
            
    return df

# --- Main Application ---
st.title("🌟 Onboarding Performance Dashboard 🌟")
# Removed st.markdown("---") here, as headers will have their own borders

# --- Initialize Session State & Define Hardcoded Data Source ---
default_sheet_url = "https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing"
default_worksheet_name = "Sheet1" # Make sure this is your actual worksheet name

if "sheet_url" not in st.session_state: st.session_state.sheet_url = default_sheet_url
if "worksheet_name" not in st.session_state: st.session_state.worksheet_name = default_worksheet_name
if 'data_loaded_successfully' not in st.session_state: st.session_state.data_loaded_successfully = False
if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()

# --- Sidebar: Data Refresh Control ---
st.sidebar.header("⚙️ Data Controls")
if st.sidebar.button("🔄 Refresh Data from Google Sheet"):
    st.cache_data.clear()
    st.session_state.data_loaded_successfully = False
    time.sleep(0.1) 
    st.rerun()

# --- Data Loading Logic ---
if not st.session_state.data_loaded_successfully:
    with st.spinner(f"Loading data from Google Sheet..."):
        df = load_data_from_google_sheet(st.session_state.sheet_url, st.session_state.worksheet_name)
        if not df.empty:
            st.session_state.df_original = df
            st.session_state.data_loaded_successfully = True
        else:
            st.session_state.df_original = pd.DataFrame()
            st.session_state.data_loaded_successfully = False

df_original = st.session_state.df_original

if not st.session_state.data_loaded_successfully:
    st.error("Failed to load data. Please check Google Sheet permissions/availability and try refreshing. "
             "The application is configured to use a specific Google Sheet.")
    st.stop()
elif df_original.empty and st.session_state.data_loaded_successfully:
    st.warning("Data source connected, but the Google Sheet appears to be empty or only contains headers. Please check the sheet content.")

# --- Helper function for calculating metrics ---
def calculate_metrics(df_input):
    if df_input.empty:
        return 0, 0.0, 0.0, 0.0 # total, success_rate, avg_score, avg_days_to_confirm

    total_onboardings = len(df_input)
    success_rate = 0.0
    avg_score = 0.0
    avg_days_to_confirm = 0.0

    if 'status' in df_input.columns:
        successful_onboardings = df_input[df_input['status'].astype(str).str.lower() == 'confirmed'].shape[0]
        if total_onboardings > 0:
            success_rate = (successful_onboardings / total_onboardings) * 100
    
    if 'score' in df_input.columns and df_input['score'].notna().any():
        avg_score = df_input['score'].mean()
    
    if 'days_to_confirmation' in df_input.columns and df_input['days_to_confirmation'].notna().any():
        # Ensure it's numeric before mean, as it could be object type if all are NA
        numeric_days_to_confirm = pd.to_numeric(df_input['days_to_confirmation'], errors='coerce')
        if numeric_days_to_confirm.notna().any():
             avg_days_to_confirm = numeric_days_to_confirm.mean()

    return total_onboardings, success_rate, avg_score, avg_days_to_confirm

# --- MTD Metrics Calculation ---
st.header("📈 Month-to-Date (MTD) Overview")
today = date.today()
current_month_start = today.replace(day=1)
df_mtd = pd.DataFrame(columns=df_original.columns)

if not df_original.empty and 'onboarding_date_only' in df_original.columns:
    valid_dates_mask = pd.Series(isinstance(x, date) for x in df_original['onboarding_date_only']) & df_original['onboarding_date_only'].notna()
    if valid_dates_mask.any():
        df_temp_dates = df_original[valid_dates_mask].copy() # Use .copy() to avoid SettingWithCopyWarning
        df_temp_dates.loc[:, 'onboarding_date_only_obj'] = df_temp_dates['onboarding_date_only'] # Work with date objects
        df_mtd = df_temp_dates[
            (df_temp_dates['onboarding_date_only_obj'] >= current_month_start) &
            (df_temp_dates['onboarding_date_only_obj'] <= today)
        ]

total_mtd, success_mtd, score_mtd, days_mtd = calculate_metrics(df_mtd)

mtd_cols = st.columns(4)
mtd_cols[0].metric(label="Total Onboardings MTD", value=f"{total_mtd}")
mtd_cols[1].metric(label="Success Rate MTD", value=f"{success_mtd:.1f}%")
mtd_cols[2].metric(label="Average Score MTD", value=f"{score_mtd:.2f}" if not pd.isna(score_mtd) and score_mtd != 0 else "N/A")
mtd_cols[3].metric(label="Avg Days to Confirm MTD", value=f"{days_mtd:.1f}" if not pd.isna(days_mtd) and days_mtd != 0 else "N/A")
# st.markdown("---") # Removed to rely on header bottom border

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
df_filtered = df_original.copy()

if not df_original.empty and 'onboarding_date_only' in df_original.columns and df_original['onboarding_date_only'].notna().any():
    valid_dates_for_filter = df_original['onboarding_date_only'][pd.Series(isinstance(x, date) for x in df_original['onboarding_date_only']) & df_original['onboarding_date_only'].notna()]
    if not valid_dates_for_filter.empty:
        min_date_data = valid_dates_for_filter.min()
        max_date_data = valid_dates_for_filter.max()
        
        filter_default_start_date = date.today().replace(day=1)
        filter_default_end_date = date.today()

        if filter_default_start_date < min_date_data: filter_default_start_date = min_date_data
        if filter_default_end_date > max_date_data: filter_default_end_date = max_date_data
        if filter_default_start_date > filter_default_end_date : 
            filter_default_start_date = min_date_data 
            filter_default_end_date = max_date_data

        date_range = st.sidebar.date_input(
            "Onboarding Date Range:",
            value=(filter_default_start_date, filter_default_end_date),
            min_value=min_date_data,
            max_value=max_date_data,
            key="date_range_filter"
        )
        start_date_filter, end_date_filter = date_range
        
        df_filtered = df_filtered[
            df_filtered['onboarding_date_only'].apply(lambda x: isinstance(x, date) and start_date_filter <= x <= end_date_filter if pd.notna(x) else False)
        ]
    else: st.sidebar.warning("No valid dates found for date range filter.")
else: st.sidebar.warning("Onboarding date data not available for filtering.")

for col_name in ['repName', 'status', 'clientSentiment']:
    if not df_original.empty and col_name in df_original.columns and df_original[col_name].notna().any():
        unique_values = ["All"] + sorted(df_original[col_name].astype(str).dropna().unique())
        selected_value = st.sidebar.selectbox(f"Select {col_name.replace('repName', 'Rep')}:", unique_values, key=f"{col_name}_filter")
        if selected_value != "All":
            df_filtered = df_filtered[df_filtered[col_name].astype(str) == selected_value]
    else: st.sidebar.text(f"{col_name.replace('repName', 'Rep')} data not available for filtering.")

# --- Filtered Data Metrics Section ---
st.header("📊 Filtered Data Overview")
if not df_filtered.empty:
    total_filtered, success_filtered, score_filtered, days_filtered = calculate_metrics(df_filtered)
    
    filtered_metrics_cols = st.columns(4)
    filtered_metrics_cols[0].metric(label="Total Filtered Onboardings", value=f"{total_filtered}")
    filtered_metrics_cols[1].metric(label="Filtered Success Rate", value=f"{success_filtered:.1f}%")
    filtered_metrics_cols[2].metric(label="Filtered Average Score", value=f"{score_filtered:.2f}" if not pd.isna(score_filtered) and score_filtered != 0 else "N/A")
    filtered_metrics_cols[3].metric(label="Filtered Avg Days to Confirm", value=f"{days_filtered:.1f}" if not pd.isna(days_filtered) and days_filtered != 0 else "N/A")
else:
    st.info("No data to display metrics for based on current filters.")
# st.markdown("---")

# --- Display Filtered Data Table (Sorted) ---
st.header("📋 Filtered Onboarding Data")
if not df_filtered.empty:
    # MODIFICATION: Sort by deliveryDate_dt (if it exists)
    if 'deliveryDate_dt' in df_filtered.columns:
        # Ensure it's datetime before sorting, handling potential NaT if some rows didn't parse
        df_filtered_sorted = df_filtered.copy()
        df_filtered_sorted['deliveryDate_dt_sortable'] = pd.to_datetime(df_filtered_sorted['deliveryDate_dt'], errors='coerce')
        df_filtered_sorted = df_filtered_sorted.sort_values(by='deliveryDate_dt_sortable', ascending=True).drop(columns=['deliveryDate_dt_sortable'])
        st.dataframe(df_filtered_sorted.reset_index(drop=True))
    else:
        st.warning("'deliveryDate' column not available for sorting.")
        st.dataframe(df_filtered.reset_index(drop=True)) # Display unsorted if no deliveryDate_dt
elif not df_original.empty:
    st.info("No data matches the current filter criteria.")

# st.markdown("---")

# --- Visualizations based on Filtered Data ---
st.header("🎨 Visual Insights") # Changed header for this section

if not df_filtered.empty:
    plotly_layout_updates = {
        "plot_bgcolor": "rgba(0,0,0,0)", "paper_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#FFFFFF", "title_font_color": GOLD_ACCENT_COLOR,
        "legend_font_color": "#FFFFFF",
        "title_text": " ", # Set a blank space for Plotly's internal title to avoid "undefined"
        "title_x": 0.5 # Center the (blank) Plotly title space
    }
    chart_colors = px.colors.qualitative.Vivid
    gold_color_sequence = [GOLD_ACCENT_COLOR, "#DAA520", "#B8860B", "#C9B037"]
    
    viz_cols = st.columns(2)

    with viz_cols[0]:
        # MODIFICATION: New chart for Boolean Checklist Items
        boolean_cols = ['onboardingWelcome', 'expectationsSet', 'introSelfAndDIME', 
                        'confirmKitReceived', 'offerDisplayHelp', 'scheduleTrainingAndPromo', 
                        'providePromoCreditLink']
        actual_boolean_cols = [col for col in boolean_cols if col in df_filtered.columns and df_filtered[col].dtype == 'bool']

        if actual_boolean_cols:
            st.subheader("Checklist Item Completion")
            completion_data = []
            for col in actual_boolean_cols:
                if df_filtered[col].notna().any(): # Check if there are any non-NA values
                    true_percentage = (df_filtered[col].sum() / df_filtered[col].notna().sum()) * 100
                    completion_data.append({"Checklist Item": col.replace("onboarding", "").replace("provide", "Provided ").replace("confirm", "Confirmed "), "Percentage True": true_percentage})
            
            if completion_data:
                completion_df = pd.DataFrame(completion_data)
                fig_checklist = px.bar(completion_df, x="Percentage True", y="Checklist Item", orientation='h',
                                       template="plotly_dark", color_discrete_sequence=[GOLD_ACCENT_COLOR])
                fig_checklist.update_layout(plotly_layout_updates)
                fig_checklist.update_layout(yaxis={'categoryorder':'total ascending'}) # Sort by percentage
                st.plotly_chart(fig_checklist, use_container_width=True)
            else:
                st.info("Not enough data in boolean columns to display checklist completion.")
        else:
            st.info("No boolean checklist columns found or they contain no valid data.")

        if 'status' in df_filtered.columns and df_filtered['status'].notna().any():
            st.subheader("Onboarding Status")
            status_counts = df_filtered['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_status = px.bar(status_counts, x='status', y='count', color='status',
                                template="plotly_dark", color_discrete_sequence=chart_colors)
            fig_status.update_layout(plotly_layout_updates)
            fig_status.update_traces(marker_line_color=GOLD_ACCENT_COLOR, marker_line_width=1)
            st.plotly_chart(fig_status, use_container_width=True)

    with viz_cols[1]:
        if 'clientSentiment' in df_filtered.columns and df_filtered['clientSentiment'].notna().any():
            st.subheader("Client Sentiment")
            sentiment_counts = df_filtered['clientSentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['sentiment', 'count']
            sentiment_color_map = {}
            unique_sentiments = sentiment_counts['sentiment'].unique()
            for i, sent in enumerate(unique_sentiments):
                if str(sent).lower() == 'positive': sentiment_color_map[str(sent)] = '#2ca02c'
                elif str(sent).lower() == 'negative': sentiment_color_map[str(sent)] = '#d62728'
                elif str(sent).lower() == 'neutral': sentiment_color_map[str(sent)] = GOLD_ACCENT_COLOR
                else: sentiment_color_map[str(sent)] = chart_colors[i % len(chart_colors)]
            
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
st.sidebar.info("Dashboard v1.4 | Black & Gold | GSheets Edition")