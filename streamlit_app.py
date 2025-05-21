import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import GridUpdateMode
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import urllib.parse # For encoding rep names in URLs
import io # For in-memory file handling (PDF, CSV)
import base64 # For embedding images in PDF
from xhtml2pdf import pisa # For PDF generation

# --- Page Configuration ---
st.set_page_config(
    page_title="Onboarding Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Theme and Styling ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

STATUS_ICON_MAP = {"confirmed": "✅", "pending": "⏳", "failed": "❌", "N/A": "❓"}
STATUS_DISPLAY_MAP = {"confirmed": "✅ Confirmed", "pending": "⏳ Pending", "failed": "❌ Failed", "N/A": "❓ N/A"}

# --- Helper function to convert DataFrame to CSV for download ---
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Helper function for PDF Generation ---
def generate_pdf_report(title_text, kpi_metrics_html, chart_fig, df_to_export, plotly_template_for_image):
    """
    Generates a PDF report.
    Args:
        title_text (str): Title of the report.
        kpi_metrics_html (str): HTML string of KPI metrics.
        chart_fig (plotly.graph_objects.Figure): Plotly figure to include.
        df_to_export (pd.DataFrame): DataFrame to include as a table.
        plotly_template_for_image (str): Plotly template to use for static image generation.
    Returns:
        io.BytesIO: In-memory buffer containing the PDF.
    """
    pdf_buffer = io.BytesIO()

    # Convert Plotly chart to static image (PNG)
    try:
        # Apply template before converting to image for consistency
        chart_fig.update_layout(template=plotly_template_for_image)
        img_bytes = chart_fig.to_image(format="png", scale=2) # Increased scale for better resolution
        img_base64 = base64.b64encode(img_bytes).decode()
        chart_html = f'<img src="data:image/png;base64,{img_base64}" style="width:100%; max-width:700px; height:auto; display:block; margin-left:auto; margin-right:auto;">'
    except Exception as e:
        st.error(f"Error generating chart image for PDF: {e}")
        chart_html = "<p>Error generating chart image.</p>"

    # Convert DataFrame to HTML table
    try:
        # Select a subset of columns if df_to_export is too wide
        if df_to_export.shape[1] > 10: # Example threshold
            cols_to_show = ['onboardingDate', 'onboardingId', 'storeName', 'Representative', 'Status'] # Adjust as needed
            cols_to_show = [col for col in cols_to_show if col in df_to_export.columns]
            if not cols_to_show and not df_to_export.empty: # Fallback if predefined cols not present
                 cols_to_show = df_to_export.columns[:8].tolist()
            table_df = df_to_export[cols_to_show] if cols_to_show else df_to_export
        else:
            table_df = df_to_export
        
        # Basic styling for the HTML table
        table_html = table_df.to_html(index=False, border=1, classes="dataframe styled-table")
        table_html = table_html.replace('<table border="1" class="dataframe styled-table">',
                                        '<table border="1" class="dataframe styled-table" style="width:100%; border-collapse: collapse; margin-top: 20px;">')
        table_html = table_html.replace('<th>', '<th style="background-color: #f2f2f2; padding: 8px; text-align: left;">')
        table_html = table_html.replace('<td>', '<td style="padding: 8px; text-align: left; border: 1px solid #ddd;">')

    except Exception as e:
        st.error(f"Error converting table to HTML for PDF: {e}")
        table_html = "<p>Error generating data table.</p>"


    # Construct HTML content for PDF
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; }}
            h1 {{ text-align: center; color: #333; }}
            .kpi-container {{ display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px; padding: 10px; background-color: #f9f9f9; border-radius: 8px;}}
            .kpi-metric {{ margin: 10px; padding: 15px; background-color: #fff; border: 1px solid #eee; border-radius: 5px; text-align: center; min-width: 150px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}}
            .kpi-metric .label {{ font-size: 0.9em; color: #555; margin-bottom: 5px;}}
            .kpi-metric .value {{ font-size: 1.5em; font-weight: bold; color: #1E88E5; }}
            .styled-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 9pt; }}
            .styled-table th {{ background-color: #e0e0e0; padding: 8px; text-align: left; border-bottom: 2px solid #ccc; }}
            .styled-table td {{ padding: 6px; text-align: left; border: 1px solid #ddd; }}
            .styled-table tr:nth-child(even) {{ background-color: #f8f8f8; }}
        </style>
    </head>
    <body>
        <h1>{title_text}</h1>
        <h2>Key Performance Indicators</h2>
        <div class="kpi-container">
            {kpi_metrics_html}
        </div>
        <h2>Confirmations Over Time</h2>
        {chart_html}
        <h2>Data Details</h2>
        {table_html}
    </body>
    </html>
    """

    # Generate PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)

    if pisa_status.err:
        st.error(f"PDF generation error: {pisa_status.err}")
        return None
    
    pdf_buffer.seek(0)
    return pdf_buffer


# --- Google Sheets Connection and Data Loading ---
@st.cache_resource
def connect_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_json = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def load_data(client):
    if client is None: return pd.DataFrame()
    try:
        sheet_name = st.secrets.get("google_sheet_name", "Sheet1")
        spreadsheet = client.open_by_url(st.secrets["google_sheet_url"])
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            date_cols = ['onboardingDate', 'deliveryDate', 'confirmationTimestamp']
            for col in date_cols:
                if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
            if 'deliveryDateTs' in df.columns: df['deliveryDateTs'] = pd.to_numeric(df['deliveryDateTs'], errors='coerce')
            if 'confirmedNumber' in df.columns: df['confirmedNumber'] = pd.to_numeric(df['confirmedNumber'], errors='coerce')
            if 'repId' not in df.columns:
                if 'repName' in df.columns: df['repId'] = df['repName'].astype(str)
                else: df['repId'] = 'unknown_rep_' + df.index.astype(str)
            df['repId'] = df['repId'].fillna('N/A_repId').astype(str)
            string_cols = ['repName', 'status', 'storeName', 'accountId', 'dccLicense', 'repEmail', 'dialpadUserId', 'contactName', 'contactNumber']
            for col in string_cols:
                if col in df.columns: df[col] = df[col].fillna('N/A')
            if 'status' in df.columns:
                df['statusDisplay'] = df['status'].apply(lambda x: STATUS_DISPLAY_MAP.get(str(x).lower(), STATUS_DISPLAY_MAP['N/A']))
            else:
                df['statusDisplay'] = STATUS_DISPLAY_MAP['N/A']
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Main Dashboard View ---
def main_dashboard_view(df_original, plotly_template, aggrid_theme):
    st.title("🚀 Onboarding Performance Dashboard")

    st.sidebar.header("⚙️ Settings & Filters")
    if st.sidebar.toggle("🌙 Dark Mode", value=(st.session_state.theme == 'dark'), key="theme_toggle_main"):
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light'
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Filters")
    min_date = df_original['onboardingDate'].min().date() if not df_original['onboardingDate'].isnull().all() else date.today()
    max_date = df_original['onboardingDate'].max().date() if not df_original['onboardingDate'].isnull().all() else date.today()
    selected_date_range = st.sidebar.date_input("Select Onboarding Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="main_date_range")
    rep_list = sorted(df_original['repName'].unique().tolist())
    selected_reps = st.sidebar.multiselect("Select Representative(s)", options=rep_list, default=rep_list, key="main_reps")
    status_column_for_filter = 'statusDisplay' if 'statusDisplay' in df_original.columns else 'status'
    status_list_options = sorted(df_original[status_column_for_filter].unique().tolist())
    selected_statuses_display = st.sidebar.multiselect("Select Status(es)", options=status_list_options, default=status_list_options, key="main_statuses")

    filtered_df = df_original.copy()
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        filtered_df = filtered_df[(filtered_df['onboardingDate'].dt.date >= start_date) & (filtered_df['onboardingDate'].dt.date <= end_date)]
    if selected_reps:
        filtered_df = filtered_df[filtered_df['repName'].isin(selected_reps)]
    if selected_statuses_display:
        filtered_df = filtered_df[filtered_df[status_column_for_filter].isin(selected_statuses_display)]

    kpi_metrics = {} # To store for PDF
    fig_confirmations_time = None # Initialize

    if filtered_df.empty:
        st.warning("No data matches the current filter criteria.")
    else:
        st.header(" KPIs Overview")
        total_onboardings = filtered_df.shape[0]
        confirmed_onboardings = filtered_df[filtered_df['status'].str.lower() == 'confirmed'].shape[0]
        pending_onboardings = filtered_df[filtered_df['status'].str.lower() == 'pending'].shape[0]
        failed_onboardings = filtered_df[filtered_df['status'].str.lower() == 'failed'].shape[0]
        confirmation_rate = (confirmed_onboardings / total_onboardings * 100) if total_onboardings > 0 else 0
        
        kpi_metrics = {
            "Total Onboardings": total_onboardings,
            "✅ Confirmed": confirmed_onboardings,
            "⏳ Pending": pending_onboardings,
            "❌ Failed": failed_onboardings,
            "📈 Confirmation Rate": f"{confirmation_rate:.2f}%"
        }
        kpi_metrics_html_main = "".join([f'<div class="kpi-metric"><div class="label">{k}</div><div class="value">{v}</div></div>' for k,v in kpi_metrics.items()])


        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Onboardings", total_onboardings)
        col2.metric("✅ Confirmed", confirmed_onboardings)
        col3.metric("⏳ Pending", pending_onboardings)
        col4.metric("❌ Failed", failed_onboardings, delta_color="inverse")
        st.metric("📈 Confirmation Rate", f"{confirmation_rate:.2f}%")
        st.markdown("---")

        st.header("📈 Confirmations Over Time")
        if not filtered_df.empty and 'confirmationTimestamp' in filtered_df.columns and 'status' in filtered_df.columns:
            confirmed_chart_df = filtered_df[filtered_df['status'].str.lower() == 'confirmed'].copy()
            if not confirmed_chart_df.empty:
                confirmed_chart_df.loc[:, 'confirmationDate'] = confirmed_chart_df['confirmationTimestamp'].dt.date
                confirmations_by_date = confirmed_chart_df.groupby('confirmationDate').size().reset_index(name='count')
                confirmations_by_date = confirmations_by_date.sort_values('confirmationDate')
                fig_confirmations_time = px.line(
                    confirmations_by_date, x='confirmationDate', y='count',
                    title='Daily Confirmed Onboardings',
                    labels={'confirmationDate': 'Date', 'count': 'Number of Confirmations'},
                    template=plotly_template
                )
                fig_confirmations_time.update_layout(height=500)
                st.plotly_chart(fig_confirmations_time, use_container_width=True)
            else: st.info("No 'confirmed' onboardings in the selected period for this chart.")
        else: st.info("Confirmation data not available for this chart.")
        
        # --- Export Buttons for Main Dashboard ---
        st.markdown("---")
        st.subheader("📥 Export Options")
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            st.download_button(
                label="📄 Download Data as CSV",
                data=to_csv(filtered_df), # Use the filtered dataframe
                file_name=f"onboarding_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="csv_download_main",
                help="Download the currently filtered data table as a CSV file."
            )
        with col_export2:
            if fig_confirmations_time and not filtered_df.empty: # Ensure chart and data exist
                pdf_bytes_main = generate_pdf_report(
                    title_text="Onboarding Performance Dashboard Report",
                    kpi_metrics_html=kpi_metrics_html_main,
                    chart_fig=fig_confirmations_time,
                    df_to_export=filtered_df, # Pass the filtered_df for the table in PDF
                    plotly_template_for_image=plotly_template
                )
                if pdf_bytes_main:
                    st.download_button(
                        label="📊 Download PDF Snapshot",
                        data=pdf_bytes_main,
                        file_name=f"onboarding_dashboard_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="pdf_download_main",
                        help="Download a PDF snapshot of the current dashboard view (KPIs, chart, data table)."
                    )
            else:
                st.button("📊 Download PDF Snapshot", disabled=True, help="PDF snapshot requires data and chart to be visible.")
        st.markdown("---")


        st.header("📋 Onboarding Data Details")
        aggrid_display_df = filtered_df.copy()
        if 'status' in aggrid_display_df.columns and 'statusDisplay' in aggrid_display_df.columns:
            aggrid_display_df = aggrid_display_df.drop(columns=['status'])
            aggrid_display_df = aggrid_display_df.rename(columns={'statusDisplay': 'Status', 'repName': 'Representative'})
        gb = GridOptionsBuilder.from_dataframe(aggrid_display_df)
        cell_renderer_rep_name = JsCode(f"""
            class RepNameRenderer {{
                init(params) {{
                    this.eGui = document.createElement('a');
                    const repName = params.value;
                    const encodedRepName = encodeURIComponent(repName);
                    this.eGui.innerText = repName;
                    this.eGui.href = `?view=rep_details&rep_name=${{encodedRepName}}`;
                    this.eGui.style.textDecoration = 'underline';
                    this.eGui.style.cursor = 'pointer';
                    this.eGui.style.color = '{ "white" if st.session_state.theme == "dark" else "blue" }';
                }} getGui() {{ return this.eGui; }}
            }}""")
        if 'Representative' in aggrid_display_df.columns:
            gb.configure_column("Representative", cellRenderer=cell_renderer_rep_name)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        gb.configure_side_bar()
        gb.configure_selection('single', use_checkbox=True, groupSelectsChildren="Group checkbox select children")
        gb.configure_default_column(groupable=True, valueGetter=True, enableRowGroup=True, aggFunc='sum', editable=False, resizable=True)
        if 'Status' in aggrid_display_df.columns:
             gb.configure_column("Status", filter="agTextColumnFilter", suppressMenu=False)
        gridOptions = gb.build()
        grid_response = AgGrid(
            aggrid_display_df, gridOptions=gridOptions, height=600, width='100%',
            update_mode=GridUpdateMode.SELECTION_CHANGED, fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True, enable_enterprise_modules=False, theme=aggrid_theme
        )
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Selected Record Details")
        selected_rows = grid_response['selected_rows']
        if selected_rows:
            selected_row_data = selected_rows[0]
            onboarding_id_display = selected_row_data.get('onboardingId', 'N/A')
            if 'onboardingId' not in selected_row_data and '_selectedRowNodeInfo' in selected_row_data:
                original_data_for_id = filtered_df[filtered_df.index == selected_row_data['_selectedRowNodeInfo']['nodeRowIndex']]
                if not original_data_for_id.empty: onboarding_id_display = original_data_for_id.iloc[0].get('onboardingId', 'N/A')
            st.sidebar.subheader(f"Details for Onboarding ID: {onboarding_id_display}")
            for key, value in selected_row_data.items():
                if key == '_selectedRowNodeInfo': continue
                display_key = key.replace('_', ' ').title()
                if isinstance(value, (pd.Timestamp, datetime)): st.sidebar.text(f"{display_key}: {value.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(value) else 'N/A'}")
                elif isinstance(value, date): st.sidebar.text(f"{display_key}: {value.strftime('%Y-%m-%d') if pd.notnull(value) else 'N/A'}")
                else: st.sidebar.text(f"{display_key}: {value if pd.notnull(value) else 'N/A'}")
        else: st.sidebar.info("Click on a row in the table to see its details here.")

# --- Rep Details View ---
def rep_details_view(df_original, rep_name, plotly_template, aggrid_theme):
    st.title(f"📊 Performance for: {rep_name}")
    st.link_button("⬅️ Back to Main Dashboard", "?view=main", help="Return to the main dashboard view")
    st.markdown("---")
    rep_df = df_original[df_original['repName'] == rep_name].copy()

    kpi_metrics_rep = {}
    fig_rep_time = None

    if rep_df.empty:
        st.warning(f"No data found for representative: {rep_name}")
        return

    st.header(f" KPIs Overview for {rep_name}")
    total_onboardings = rep_df.shape[0]
    confirmed_onboardings = rep_df[rep_df['status'].str.lower() == 'confirmed'].shape[0]
    pending_onboardings = rep_df[rep_df['status'].str.lower() == 'pending'].shape[0]
    failed_onboardings = rep_df[rep_df['status'].str.lower() == 'failed'].shape[0]
    confirmation_rate = (confirmed_onboardings / total_onboardings * 100) if total_onboardings > 0 else 0
    
    kpi_metrics_rep = {
        "Total Onboardings": total_onboardings,
        "✅ Confirmed": confirmed_onboardings,
        "⏳ Pending": pending_onboardings,
        "❌ Failed": failed_onboardings,
        "📈 Confirmation Rate": f"{confirmation_rate:.2f}%"
    }
    kpi_metrics_html_rep = "".join([f'<div class="kpi-metric"><div class="label">{k}</div><div class="value">{v}</div></div>' for k,v in kpi_metrics_rep.items()])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Onboardings", total_onboardings)
    col2.metric("✅ Confirmed", confirmed_onboardings)
    col3.metric("⏳ Pending", pending_onboardings)
    col4.metric("❌ Failed", failed_onboardings, delta_color="inverse")
    st.metric("📈 Confirmation Rate", f"{confirmation_rate:.2f}%")
    st.markdown("---")

    st.header(f"📈 Confirmations Over Time for {rep_name}")
    if not rep_df.empty and 'confirmationTimestamp' in rep_df.columns and 'status' in rep_df.columns:
        confirmed_chart_df = rep_df[rep_df['status'].str.lower() == 'confirmed'].copy()
        if not confirmed_chart_df.empty:
            confirmed_chart_df.loc[:, 'confirmationDate'] = confirmed_chart_df['confirmationTimestamp'].dt.date
            confirmations_by_date = confirmed_chart_df.groupby('confirmationDate').size().reset_index(name='count')
            confirmations_by_date = confirmations_by_date.sort_values('confirmationDate')
            fig_rep_time = px.line(
                confirmations_by_date, x='confirmationDate', y='count',
                title=f'Daily Confirmed Onboardings by {rep_name}',
                labels={'confirmationDate': 'Date', 'count': 'Number of Confirmations'},
                template=plotly_template
            )
            fig_rep_time.update_layout(height=450)
            st.plotly_chart(fig_rep_time, use_container_width=True)
        else: st.info(f"No 'confirmed' onboardings for {rep_name} in the data.")
    else: st.info("Confirmation data not available for this representative.")
    
    # --- Export Buttons for Rep Details View ---
    st.markdown("---")
    st.subheader("📥 Export Options")
    col_export_rep1, col_export_rep2 = st.columns(2)
    with col_export_rep1:
        st.download_button(
            label="📄 Download Rep Data as CSV",
            data=to_csv(rep_df), # Use the rep-specific dataframe
            file_name=f"onboarding_data_{rep_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="csv_download_rep",
            help="Download this representative's data table as a CSV file."
        )
    with col_export_rep2:
        if fig_rep_time and not rep_df.empty: # Ensure chart and data exist
            pdf_bytes_rep = generate_pdf_report(
                title_text=f"Onboarding Performance Report for {rep_name}",
                kpi_metrics_html=kpi_metrics_html_rep,
                chart_fig=fig_rep_time,
                df_to_export=rep_df, # Pass the rep_df
                plotly_template_for_image=plotly_template
            )
            if pdf_bytes_rep:
                st.download_button(
                    label="📊 Download Rep PDF Snapshot",
                    data=pdf_bytes_rep,
                    file_name=f"onboarding_snapshot_{rep_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    key="pdf_download_rep",
                    help="Download a PDF snapshot of this representative's dashboard view."
                )
        else:
            st.button("📊 Download Rep PDF Snapshot", disabled=True, help="PDF snapshot requires data and chart to be visible.")
    st.markdown("---")

    st.header(f"📋 Onboarding Data for {rep_name}")
    rep_aggrid_display_df = rep_df.copy()
    if 'status' in rep_aggrid_display_df.columns and 'statusDisplay' in rep_aggrid_display_df.columns:
        rep_aggrid_display_df = rep_aggrid_display_df.drop(columns=['status'])
        rep_aggrid_display_df = rep_aggrid_display_df.rename(columns={'statusDisplay': 'Status'})
    gb_rep = GridOptionsBuilder.from_dataframe(rep_aggrid_display_df)
    gb_rep.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb_rep.configure_default_column(editable=False, resizable=True)
    if 'Status' in rep_aggrid_display_df.columns:
        gb_rep.configure_column("Status", filter="agTextColumnFilter", suppressMenu=False)
    gridOptions_rep = gb_rep.build()
    AgGrid(
        rep_aggrid_display_df, gridOptions=gridOptions_rep, height=400, width='100%',
        fit_columns_on_grid_load=True, enable_enterprise_modules=False, theme=aggrid_theme
    )

# --- Router and Main Execution ---
def run_app():
    if st.session_state.theme == 'dark':
        dark_mode_css = """<style> body { color: #FAFAFA; } 
                           .ag-theme-streamlit-dark .ag-header { background-color: #1C1E26; color: #FAFAFA; }
                           .ag-theme-streamlit-dark .ag-header-cell-label { color: #FAFAFA; } </style>"""
        st.markdown(dark_mode_css, unsafe_allow_html=True)
    
    plotly_template = "plotly_dark" if st.session_state.theme == 'dark' else "plotly"
    aggrid_theme = "streamlit-dark" if st.session_state.theme == 'dark' else "streamlit"

    gs_client = connect_gsheets()
    df_original = load_data(gs_client)
    if df_original.empty:
        st.warning("No data loaded. Please check Google Sheets connection and data availability.")
        return

    query_params = st.query_params
    current_view = query_params.get('view', ['main'])[0]
    selected_rep_name_encoded = query_params.get('rep_name', [None])[0]
    selected_rep_name = None
    if selected_rep_name_encoded: selected_rep_name = urllib.parse.unquote(selected_rep_name_encoded)

    if current_view == 'rep_details' and selected_rep_name:
        rep_details_view(df_original, selected_rep_name, plotly_template, aggrid_theme)
    else:
        if selected_rep_name and current_view != 'rep_details': st.query_params.clear()
        main_dashboard_view(df_original, plotly_template, aggrid_theme)

if __name__ == "__main__":
    run_app()
