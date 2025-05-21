streamlit_app.py
import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from gspread_pandas import Spread, conf
import datetime

# Import AgGrid
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

# --- Configuration (Simulated - normally from secrets) ---
try:
    creds_json = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_json)
    conf.set_default_creds(creds)
except Exception as e:
    st.warning(f"Failed to load Google Sheets credentials from Streamlit secrets: {e}. Using fallback for local development if available.")
    try:
        creds = conf.get_creds_from_file() 
        conf.set_default_creds(creds)
    except Exception as e_local:
        st.error(f"Failed to load Google Sheets credentials locally: {e_local}. Please ensure creds.json is set up correctly for local development or secrets are configured for deployment.")
        st.stop()

# --- Data Loading ---
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data(sheet_id_or_url):
    try:
        spread = Spread(sheet_id_or_url)
        df = spread.sheet_to_df(index=None, header_rows=1)
        
        df = pd.to_datetime(df, errors='coerce')
        df = pd.to_datetime(df, errors='coerce')
        df = pd.to_datetime(df, unit='s', errors='coerce')
        df = pd.to_datetime(df, errors='coerce')
        
        required_cols =
        for col in required_cols:
            if col not in df.columns:
                if 'date' in col.lower() or 'timestamp' in col.lower():
                    df[col] = pd.NaT
                elif 'number' in col.lower() or 'id' in col.lower():
                    df[col] = pd.NA 
                else:
                    df[col] = None 
                st.warning(f"Column '{col}' was missing and has been added with null values.")

        df['confirmedNumber'] = pd.to_numeric(df['confirmedNumber'], errors='coerce').fillna(0)
        df = df.dropna(subset=)
        df = df.sort_values(by='onboardingDate', ascending=False) # Default sort
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

# --- Main App ---
st.set_page_config(layout="wide")
st.title("Onboarding Performance Dashboard")

GOOGLE_SHEET_ID = "1kHkZgFXAEAP86zZ20sH4u4A7g3r2R8_jdbU3g7G9z_A" # Replace with your sheet ID
data_df = load_data(GOOGLE_SHEET_ID)

if data_df.empty:
    st.warning("No data loaded. Please check the Google Sheet connection or data.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Date Range Filter
min_date = data_df.min().date()
max_date = data_df.max().date()

date_range = st.sidebar.date_input(
    "Select Date Range (Onboarding Date):",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    key="date_range_filter"
)

start_date, end_date = date_range
# Convert to datetime for comparison with DataFrame column
start_date_dt = pd.to_datetime(start_date)
end_date_dt = pd.to_datetime(end_date)


# Representative Filter
rep_names = sorted(data_df['repName'].astype(str).unique()) # astype(str) to handle potential non-string values
selected_reps = st.sidebar.multiselect(
    "Select Representative(s):",
    options=rep_names,
    default=,
    key="rep_filter"
)

# Status Filter
statuses = sorted(data_df['status'].astype(str).unique())
selected_statuses = st.sidebar.multiselect(
    "Select Status(es):",
    options=statuses,
    default=,
    key="status_filter"
)

# --- Filtering Logic ---
filtered_df = data_df.copy()

# Apply date filter
if start_date_dt and end_date_dt:
    filtered_df = filtered_df >= start_date_dt) & 
        (filtered_df <= end_date_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)) # Ensure end_date is inclusive
    ]

# Apply rep filter
if selected_reps: # If list is not empty
    filtered_df = filtered_df[filtered_df['repName'].isin(selected_reps)]

# Apply status filter
if selected_statuses: # If list is not empty
    filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]


# --- Headline KPIs (based on filtered data) ---
st.header("Headline KPIs")
if not filtered_df.empty:
    total_onboardings_filtered = len(filtered_df)
    confirmed_onboardings_filtered = len(filtered_df[filtered_df['status'] == 'confirmed'])
    pending_onboardings_filtered = len(filtered_df[filtered_df['status'] == 'pending'])
    failed_onboardings_filtered = len(filtered_df[filtered_df['status'] == 'failed'])

    if total_onboardings_filtered > 0:
        confirmation_rate_filtered = (confirmed_onboardings_filtered / total_onboardings_filtered) * 100
    else:
        confirmation_rate_filtered = 0
else:
    total_onboardings_filtered = 0
    confirmed_onboardings_filtered = 0
    pending_onboardings_filtered = 0
    failed_onboardings_filtered = 0
    confirmation_rate_filtered = 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Onboardings (Filtered)", total_onboardings_filtered)
col2.metric("Confirmed (Filtered)", confirmed_onboardings_filtered)
col3.metric("Pending (Filtered)", pending_onboardings_filtered)
col4.metric("Failed (Filtered)", failed_onboardings_filtered)
col5.metric("Confirmation Rate (Filtered)", f"{confirmation_rate_filtered:.2f}%")

# --- Confirmations Over Time (based on filtered data) ---
st.header("Confirmations Over Time")
if not filtered_df.empty and 'onboardingDate' in filtered_df.columns and 'status' in filtered_df.columns:
    confirmed_over_time_df = filtered_df[filtered_df['status'] == 'confirmed'].copy()
    
    if not confirmed_over_time_df.empty:
        confirmed_over_time_chart_data = confirmed_over_time_df.set_index('onboardingDate').resample('D')['onboardingId'].count().reset_index(name='count')
        
        chart = alt.Chart(confirmed_over_time_chart_data).mark_line().encode(
            x=alt.X('onboardingDate:T', title='Date'),
            y=alt.Y('count:Q', title='Number of Confirmations'),
            tooltip=
        ).properties(
            title='Daily Confirmed Onboardings (Filtered)'
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No confirmed onboardings in the selected filter range to display in the chart.")
else:
    st.write("Data for 'Confirmations Over Time' chart is not available or columns are missing in the filtered set.")

# --- Interactive Data Table (Ag-Grid) ---
st.header("Onboarding Data (Interactive)")
if not filtered_df.empty:
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15) # Add pagination
    gb.configure_side_bar() # Add a sidebar to the grid
    gb.configure_selection('single', use_checkbox=False, rowMultiSelectWithClick=False) # Enable single row selection
    gb.configure_default_column(groupable=True, valueGetter=True, sortable=True, filter=True, resizable=True)
    
    # Make specific columns more user-friendly if needed (e.g., date formatting)
    # Example: gb.configure_column("onboardingDate", type=, custom_format_string='yyyy-MM-dd')
    
    gridOptions = gb.build()

    grid_response = AgGrid(
        filtered_df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED, # Update when selection changes
        fit_columns_on_grid_load=False, # Adjust as needed, can be slow with many columns
        height=500, 
        width='100%',
        allow_unsafe_jscode=True, # Set to True if using custom JS in gridOptions
        enable_enterprise_modules=False # Set to True if you have enterprise license
    )
    
    selected_rows = grid_response['selected_rows']
else:
    st.write("No data to display in the table based on current filters.")
    selected_rows = # Ensure selected_rows is defined

# --- Side-Panel for Detailed Information ---
st.sidebar.header("Selected Onboarding Details")
if selected_rows:
    # Assuming single selection, take the first selected row
    detail = selected_rows
    # Convert to a more readable format if it's a DataFrame row
    if isinstance(detail, pd.Series):
        detail_dict = detail.to_dict()
    elif isinstance(detail, dict): # AgGrid often returns dicts
        detail_dict = detail
    else: # Fallback if it's some other type
        st.sidebar.write("Unexpected data type for selected row.")
        detail_dict = {}

    if detail_dict:
        for key, value in detail_dict.items():
            # Attempt to format datetime objects nicely
            if isinstance(value, (datetime.datetime, pd.Timestamp)):
                st.sidebar.text(f"{key}: {value.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(value) else 'N/A'}")
            elif pd.isna(value): # Handle other NA types
                 st.sidebar.text(f"{key}: N/A")
            else:
                st.sidebar.text(f"{key}: {value}")
else:
    st.sidebar.info("Select a row from the table above to see details.")


# --- Footer (Optional) ---
st.markdown("---")
st.markdown("Dashboard V1.1 - Interactive Filters Implemented")